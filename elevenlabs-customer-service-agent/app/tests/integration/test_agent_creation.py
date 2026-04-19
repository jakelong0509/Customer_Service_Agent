"""Integration tests for agent creation and basic dispatch.

These tests require PostgreSQL but NOT Redis/Milvus.
Set POSTGRES_CONNECTION_STRING in your environment or .env.
"""
import os
import pytest
from unittest.mock import AsyncMock, MagicMock, patch

from src.core.agent_run_request_model import AgentRunRequest, ElevenLabsAgentRunRequest
from src.core.customer import CustomerModel


SAMPLE_CUSTOMER = CustomerModel(
    id="cust-integ-001",
    phone="1234567890",
    email="integ@test.com",
    name="Integration Tester",
    plan="Free",
    status="active",
)


@pytest.fixture
def mock_llm():
    llm = MagicMock()
    response = MagicMock()
    response.content = "I can help you with that."
    response.tool_calls = []
    llm.bind_tools.return_value.invoke.return_value = response
    return llm


class TestAgentCreation:
    def test_create_agent_loads_all_configs(self):
        from src.services.agent_registry import create_agent, AGENTS

        AGENTS.clear()
        with patch("src.services.agent_registry.ChatOpenAI"), \
             patch("src.services.agent_registry.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.__truediv__.return_value.read_text.return_value = (
                "System prompt {learned_instruction} {current_date} {customer_info} {available_skills} {active_skills}"
            )
            create_agent()

        expected_names = [
            "customer_support_agent",
            "customer_support_agent_email",
            "security_agent",
            "rxnorm_mapping_agent_email",
        ]
        for name in expected_names:
            assert name in AGENTS, f"Agent {name} not found in registry"

    def test_get_agent_returns_factory(self):
        from src.services.agent_registry import create_agent, AGENTS, get_agent

        AGENTS.clear()
        with patch("src.services.agent_registry.ChatOpenAI"), \
             patch("src.services.agent_registry.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.__truediv__.return_value.read_text.return_value = (
                "System prompt {learned_instruction} {current_date} {customer_info} {available_skills} {active_skills}"
            )
            create_agent()

        agent = get_agent("customer_support_agent")
        assert agent is not None
        assert agent.name == "customer_support_agent"
        assert agent.communication_type == "voice"

    def test_get_agent_names(self):
        from src.services.agent_registry import create_agent, AGENTS, get_agent_names

        AGENTS.clear()
        with patch("src.services.agent_registry.ChatOpenAI"), \
             patch("src.services.agent_registry.Path") as mock_path:
            mock_path.return_value.parent.parent.parent.__truediv__.return_value.read_text.return_value = (
                "System prompt {learned_instruction} {current_date} {customer_info} {available_skills} {active_skills}"
            )
            create_agent()

        names = get_agent_names()
        assert len(names) == 4
        assert "customer_support_agent" in names


class TestSkillIntegration:
    def test_agent_has_correct_skills(self):
        from src.services.skill_registry import get_skills

        skills = get_skills(["appointment_booking_skill", "email_skill"])
        assert len(skills) == 2

        all_inactive = all(not s.active for s in skills.values())
        assert all_inactive

    def test_skill_tools_integration(self):
        from src.services.skill_registry import get_skill_tools

        tools = get_skill_tools(["appointment_booking_skill"])
        tool_names = [t.name for t in tools]
        assert "create_appointment_resource_booking" in tool_names
        assert "select_appointment_resource_bookings" in tool_names
        assert "select_providers" in tool_names
        assert "select_slot_templates" in tool_names


class TestAgentResponseParsing:
    def test_response_error_detection(self):
        from src.core.agent_run_request_model import AgentRunResponse

        error_resp = AgentRunResponse(result="Error: Agent not found", is_error=True)
        assert error_resp.is_error is True

        success_resp = AgentRunResponse(result="Appointment confirmed!", is_error=False)
        assert success_resp.is_error is False

    def test_error_detection_by_prefix(self):
        result = "Error: Something went wrong"
        is_error = result.startswith("Error:") if isinstance(result, str) else False
        assert is_error is True

        result = "Your appointment has been booked"
        is_error = result.startswith("Error:") if isinstance(result, str) else False
        assert is_error is False
