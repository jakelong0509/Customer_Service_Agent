from src.core.agent_state import AgentState
from src.core.customer import CustomerModel
from src.services.skill_registry import SkillRecord
from src.agents.security_agent.state import SecurityAgentState
from src.agents.rxnorm_mapping_agent.state import (
    RxNormAgentState,
    NormalizedText,
    ExtractedEntity,
    ExtractedEntities,
    MappingResult,
    MappingResults,
    NDCResult,
)


def _sample_skill():
    return SkillRecord(
        name="test_skill",
        description="test",
        when_to_use="test",
        isolation_fork=False,
        body="body",
    )


def _sample_customer():
    return CustomerModel(
        id="cust-001",
        phone="123",
        email="a@b.com",
        name="Test",
        plan="Free",
        status="active",
    )


class TestAgentState:
    def test_create_base_state(self):
        state = AgentState(
            messages=[],
            skills={"test_skill": _sample_skill()},
            session_id="sess-1",
            customer=_sample_customer(),
        )
        assert state.session_id == "sess-1"
        assert "test_skill" in state.skills
        assert len(state.messages) == 0

    def test_state_with_messages(self):
        from langchain_core.messages import HumanMessage

        state = AgentState(
            messages=[HumanMessage(content="Hello")],
            skills={"s": _sample_skill()},
            session_id="sess-2",
            customer=_sample_customer(),
        )
        assert len(state.messages) == 1


class TestSecurityAgentState:
    def test_default_values(self):
        state = SecurityAgentState(
            messages=[],
            skills={},
            session_id="sess-sec",
            customer=_sample_customer(),
        )
        assert state.attachment_metadata == {}
        assert state.threat_level == "unknown"
        assert state.conversation_context == ""

    def test_custom_values(self):
        state = SecurityAgentState(
            messages=[],
            skills={},
            session_id="sess-sec",
            customer=_sample_customer(),
            threat_level="high",
            conversation_context="Suspicious attachment detected",
        )
        assert state.threat_level == "high"
        assert "Suspicious" in state.conversation_context


class TestRxNormAgentState:
    def test_default_values(self):
        state = RxNormAgentState(
            messages=[],
            skills={},
            session_id="sess-rx",
            customer=_sample_customer(),
            normalized_text=NormalizedText(normalized_text=""),
            extracted_entities=ExtractedEntities(extracted_entities=[]),
            mapping_results=MappingResults(mapping_results=[], ndc_results=[]),
        )
        assert state.normalized_text.normalized_text == ""
        assert state.extracted_entities.extracted_entities == []
        assert state.mapping_results.mapping_results == []
        assert state.mapping_results.ndc_results == []

    def test_pipeline_models(self):
        norm = NormalizedText(normalized_text="metformin 500mg bid")
        assert norm.normalized_text == "metformin 500mg bid"

        entity = ExtractedEntity(
            entity_text="metformin",
            entity_type="medication",
            entity_med_info={"dose": "500mg"},
        )
        assert entity.entity_type == "medication"

        entities = ExtractedEntities(extracted_entities=[entity])
        assert len(entities.extracted_entities) == 1

        mapping = MappingResult(rxcui="861007", str="Metformin", tty="SCD", similarity_score=0.95)
        assert mapping.rxcui == "861007"

        ndc = NDCResult(atn="NDC", atv="0002-1234-01")
        assert ndc.atn == "NDC"

        results = MappingResults(
            mapping_results=[mapping],
            ndc_results=[ndc],
        )
        assert len(results.mapping_results) == 1
        assert len(results.ndc_results) == 1
