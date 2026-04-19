import pytest
from unittest.mock import MagicMock, patch
from langchain_core.messages import AIMessage, HumanMessage

from src.services.agent_registry import AgentRegistry


class TestAgentFactoryRouting:
    def _make_factory(self, communication_type="voice"):
        with patch("src.agents.agent_factory.PostgresStore"), \
             patch("src.agents.agent_factory.get_tools", return_value=[]):
            from src.agents.agent_factory import AgentFactory
            factory = AgentFactory.__new__(AgentFactory)
            factory.communication_type = communication_type
            return factory

    def test_routing_with_tool_calls_returns_tool(self):
        factory = self._make_factory("voice")
        state = MagicMock()
        state.messages = [AIMessage(content="", tool_calls=[{"name": "activate_skill", "id": "tc1", "args": {}}])]
        result = factory.routing(state)
        assert result == "tool"

    def test_routing_voice_no_tool_calls_returns_end(self):
        from langgraph.graph import END
        factory = self._make_factory("voice")
        state = MagicMock()
        state.messages = [AIMessage(content="How can I help you?")]
        result = factory.routing(state)
        assert result == END

    def test_routing_email_no_tool_calls_returns_email_node(self):
        factory = self._make_factory("email")
        state = MagicMock()
        state.messages = [AIMessage(content="Here is your email response")]
        result = factory.routing(state)
        assert result == "email_node"

    def test_routing_chat_no_tool_calls_returns_end(self):
        from langgraph.graph import END
        factory = self._make_factory("chat")
        state = MagicMock()
        state.messages = [AIMessage(content="Security check complete")]
        result = factory.routing(state)
        assert result == END

    def test_routing_email_with_tool_calls_returns_tool(self):
        factory = self._make_factory("email")
        state = MagicMock()
        state.messages = [AIMessage(content="", tool_calls=[{"name": "activate_skill", "id": "tc1", "args": {}}])]
        result = factory.routing(state)
        assert result == "tool"


class TestAgentFactoryLastMessageText:
    def test_empty_messages(self):
        from src.agents.agent_factory import AgentFactory
        assert AgentFactory._last_message_text({}) == ""
        assert AgentFactory._last_message_text({"messages": []}) == ""

    def test_string_content(self):
        from src.agents.agent_factory import AgentFactory
        msg = AIMessage(content="Hello there")
        result = AgentFactory._last_message_text({"messages": [msg]})
        assert result == "Hello there"

    def test_human_message(self):
        from src.agents.agent_factory import AgentFactory
        msg = HumanMessage(content="I need help")
        result = AgentFactory._last_message_text({"messages": [msg]})
        assert result == "I need help"

    def test_multiple_messages_returns_last(self):
        from src.agents.agent_factory import AgentFactory
        msgs = [
            HumanMessage(content="First"),
            AIMessage(content="Second"),
            HumanMessage(content="Third"),
        ]
        result = AgentFactory._last_message_text({"messages": msgs})
        assert result == "Third"


class TestAgentFactoryGraphStructure:
    def _build_factory(self):
        with patch("src.agents.agent_factory.PostgresStore") as mock_store_cm, \
             patch("src.agents.agent_factory.get_tools", return_value=[]), \
             patch("src.agents.agent_factory.get_skill_tools", return_value=[]):
            from src.agents.agent_factory import AgentFactory
            mock_store_cm.from_conn_string.return_value.__enter__ = MagicMock(return_value=MagicMock())
            mock_store_cm.from_conn_string.return_value.__exit__ = MagicMock(return_value=False)

            factory = AgentFactory(
                system_prompt="Test prompt {learned_instruction} {current_date} {customer_info} {available_skills} {active_skills}",
                name="test_agent",
                llm=MagicMock(),
                tools=[],
                db_uri="postgresql://test:test@localhost/test",
                skill_names=[],
                communication_type="voice",
                state_class=None,
            )
            return factory

    def test_build_graph_returns_state_graph(self):
        from langgraph.graph import StateGraph
        factory = self._build_factory()
        graph = factory.build_graph()
        assert isinstance(graph, StateGraph)

    def test_graph_has_agent_node(self):
        factory = self._build_factory()
        graph = factory.build_graph()
        assert "agent" in graph.nodes

    def test_graph_has_tool_node(self):
        factory = self._build_factory()
        graph = factory.build_graph()
        assert "tool_node" in graph.nodes

    def test_graph_has_email_node(self):
        factory = self._build_factory()
        graph = factory.build_graph()
        assert "email_node" in graph.nodes
