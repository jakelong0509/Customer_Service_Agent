from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, List

from langchain_core.messages import SystemMessage, HumanMessage, AIMessage, RemoveMessage
from langgraph.graph import StateGraph, START, END
from langgraph.prebuilt import ToolNode
from langgraph.runtime import Runtime

from src.agents.agent_factory import AgentFactory
from src.agents.rxnorm_mapping_agent.tools import get_tools
from src.agents.rxnorm_mapping_agent.state import RxNormAgentState, MappingResult, MappingResults, ValidationResult
from src.core.agent_run_request_model import AgentRunRequest
from src.core.customer import CustomerModel
from src.utils.sendgrid import reply_to_email
from src.utils.logger import get_logger

logger = get_logger(__name__)

_PROMPTS_DIR = Path(__file__).parent / "prompts"

_NORMALIZE_PROMPT = (_PROMPTS_DIR / "normalize_note_prompt.md").read_text(encoding="utf-8")
_EXTRACT_PROMPT = (_PROMPTS_DIR / "extract_entities_prompt.md").read_text(encoding="utf-8")
_MAP_PROMPT = (_PROMPTS_DIR / "entities_mapping_prompt.md").read_text(encoding="utf-8")

_TOOLS = get_tools()
_NORMALIZE_TOOLS = _TOOLS["text_normalize_tools"]
_EXTRACT_TOOLS = _TOOLS["entity_extraction_tools"]
_MAP_TOOLS = _TOOLS["rxnorm_mapping_tools"]


class RxNormAgent(AgentFactory):
    def __init__(
        self,
        name: str,
        llm: Any,
        db_uri: str,
        communication_type: str = "email",
    ):
        super().__init__(
            system_prompt="",
            name=name,
            llm=llm,
            tools=[],
            db_uri=db_uri,
            skill_names=[],
            communication_type=communication_type,
            state_class=RxNormAgentState,
        )
        self.normalize_tool_node = ToolNode(_NORMALIZE_TOOLS)
        self.extract_tool_node = ToolNode(_EXTRACT_TOOLS)
        self.map_tool_node = ToolNode(_MAP_TOOLS)

    async def arun(self, request: AgentRunRequest, customer: CustomerModel, session_id: str) -> str:
        await self._ensure_compiled()
        thread_id = f"{self.name}:{customer.id}:{session_id}"
        config = {"configurable": {"thread_id": thread_id}}

        result = await self.graph.ainvoke(
            {
                "messages": [HumanMessage(content=request.request)],
                "skills": {},
                "session_id": session_id,
                "customer": customer,
            },
            config=config,
            context=request,
        )
        return self._last_message_text(result)
    
    def keep_it_fresh(self, state: RxNormAgentState) -> dict:
        """
        We should not keep the conversation history when jumping into the next step 
        -> graph state already have information the agent need to continue process the request
        """
        original = next(
            (m for m in state.messages if isinstance(m, HumanMessage)),
            None,
        )
        remove_all = [
            RemoveMessage(id=m.id) for m in state.messages
            if not (original and m.id == original.id)
        ]
        return {"messages": remove_all}

    def normalize_node(self, state: RxNormAgentState) -> dict:
        system_msg = SystemMessage(content=_NORMALIZE_PROMPT)
        messages = [system_msg] + state.messages
        response = self.llm.bind_tools(_NORMALIZE_TOOLS).invoke(messages)
        return {"messages": [response]}

    async def normalize_tools(self, state: RxNormAgentState) -> dict:
        return await self.normalize_tool_node.ainvoke(state)

    def extract_node(self, state: RxNormAgentState) -> dict:
        normalized = state.normalized_text.normalized_text or ""
        prompt = _EXTRACT_PROMPT.replace("{normalized_text}", normalized or "(not yet normalized — use the original message)")
        system_msg = SystemMessage(content=prompt)
        messages = [system_msg] + state.messages
        response = self.llm.bind_tools(_EXTRACT_TOOLS).invoke(messages)
        return {"messages": [response]}

    async def extract_tools(self, state: RxNormAgentState) -> dict:
        return await self.extract_tool_node.ainvoke(state)

    def map_node(self, state: RxNormAgentState) -> dict:
        entities = state.extracted_entities.extracted_entities
        entities_json = json.dumps(
            [e.model_dump() for e in entities],
            indent=2,
            default=str,
        ) if entities else "[]"
        prompt = _MAP_PROMPT.replace("{entities_json}", entities_json)
        system_msg = SystemMessage(content=prompt)
        messages = [system_msg] + state.messages
        response = self.llm.bind_tools(_MAP_TOOLS).invoke(messages)
        return {"messages": [response]}

    async def map_tools(self, state: RxNormAgentState) -> dict:
        return await self.map_tool_node.ainvoke(state)

    def validate_node(self, state: RxNormAgentState) -> dict:
        results = state.mapping_results.mapping_results
        low_confidence = [
            r.anchor_text for r in results
            if r.confidence_score < 0.70
        ]
        medium_confidence = [
            r.anchor_text for r in results
            if 0.70 <= r.confidence_score < 0.85
        ]

        validation = ValidationResult(
            all_confident=len(low_confidence) == 0,
            low_confidence_entities=low_confidence + medium_confidence,
        )

        parts = []
        if results:
            parts.append("## RxNorm Mapping Results\n")
            for r in results:
                status = ""
                if r.confidence_score < 0.70:
                    status = " [LOW CONFIDENCE — REQUIRES REVIEW]"
                elif r.confidence_score < 0.85:
                    status = " [MEDIUM CONFIDENCE]"
                parts.append(
                    f"- **{r.anchor_text}** → RXCUI: {r.rxcui} | "
                    f"{r.str} (TTY: {r.tty}) | "
                    f"Confidence: {r.confidence_score:.2f} | "
                    f"Strategy: {r.resolution_strategy}"
                    f"{status}"
                )
        else:
            parts.append("No medication entities were found in the clinical note.")

        if low_confidence:
            validation.warning_message = (
                f"WARNING: The following entities have low confidence scores "
                f"and require manual review: {', '.join(low_confidence)}"
            )
            parts.append(f"\n**{validation.warning_message}**")

        if medium_confidence:
            parts.append(
                f"\n*Note: Medium confidence for: {', '.join(medium_confidence)}.*"
            )

        parts.append(f"\n---\nProcessed at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        summary = "\n".join(parts)
        return {
            "messages": [AIMessage(content=summary)],
            "validation": validation,
        }

    async def email_node(self, state: RxNormAgentState, runtime: Runtime[AgentRunRequest]) -> dict:
        try:
            logger.info(
                f"Sending RxNorm mapping email to {runtime.context.from_email}",
                extra={"extra_data": {
                    "subject": runtime.context.subject,
                    "message_id": runtime.context.message_id,
                }},
            )
            await reply_to_email(
                original_message_id=runtime.context.message_id,
                original_sender=runtime.context.from_email,
                original_subject=runtime.context.subject,
                reply_body=state.messages[-1].content,
                references=runtime.context.references,
            )
        except Exception as e:
            logger.error(f"Error sending email: {e}", exc_info=True)
        return {}

    @staticmethod
    def _has_tool_calls(state: RxNormAgentState) -> str:
        if state.messages and hasattr(state.messages[-1], "tool_calls") and state.messages[-1].tool_calls:
            return "tools"
        return "next"

    def build_graph(self) -> StateGraph:
        graph = StateGraph(self.state_class, context_schema=AgentRunRequest)

        graph.add_node("normalize_node", self.normalize_node)
        graph.add_node("normalize_tools", self.normalize_tools)
        graph.add_node("trim_before_extract", self.keep_it_fresh)
        graph.add_node("extract_node", self.extract_node)
        graph.add_node("extract_tools", self.extract_tools)
        graph.add_node("trim_before_map", self.keep_it_fresh)
        graph.add_node("map_node", self.map_node)
        graph.add_node("map_tools", self.map_tools)
        graph.add_node("validate_node", self.validate_node)
        graph.add_node("email_node", self.email_node)

        graph.add_edge(START, "normalize_node")

        graph.add_conditional_edges(
            "normalize_node",
            self._has_tool_calls,
            {"tools": "normalize_tools", "next": "trim_before_extract"},
        )
        graph.add_edge("normalize_tools", "normalize_node")
        graph.add_edge("trim_before_extract", "extract_node")

        graph.add_conditional_edges(
            "extract_node",
            self._has_tool_calls,
            {"tools": "extract_tools", "next": "trim_before_map"},
        )
        graph.add_edge("extract_tools", "extract_node")
        graph.add_edge("trim_before_map", "map_node")

        graph.add_conditional_edges(
            "map_node",
            self._has_tool_calls,
            {"tools": "map_tools", "next": "validate_node"},
        )
        graph.add_edge("map_tools", "map_node")

        graph.add_edge("validate_node", "email_node")
        graph.add_edge("email_node", END)

        return graph
