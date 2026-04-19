import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from src.services.dispatch_agent import invoke_agent, AgentResponse


class TestAgentResponse:
    def test_default_values(self):
        resp = AgentResponse(content="Hello")
        assert resp.content == "Hello"
        assert resp.action_type == "response"
        assert resp.requires_followup is False
        assert resp.async_job_id is None
        assert resp.suggested_tools == []

    def test_custom_values(self):
        resp = AgentResponse(
            content="Processing",
            action_type="tool_call",
            requires_followup=True,
            async_job_id="job-123",
            suggested_tools=["activate_skill"],
        )
        assert resp.action_type == "tool_call"
        assert resp.requires_followup is True
        assert resp.async_job_id == "job-123"
        assert resp.suggested_tools == ["activate_skill"]

    def test_to_dict(self):
        resp = AgentResponse(
            content="Done",
            action_type="response",
            requires_followup=False,
            suggested_tools=["tool_a"],
        )
        d = resp.to_dict()
        assert d["content"] == "Done"
        assert d["action_type"] == "response"
        assert d["requires_followup"] is False
        assert d["async_job_id"] is None
        assert d["suggested_tools"] == ["tool_a"]


class TestInvokeAgent:
    @pytest.mark.asyncio
    async def test_invoke_agent_calls_arun(self):
        mock_agent = AsyncMock()
        mock_agent.arun.return_value = "Appointment booked"

        with patch("src.services.dispatch_agent.get_agent", return_value=mock_agent):
            from src.core.agent_run_request_model import AgentRunRequest
            from src.core.customer import CustomerModel

            req = AgentRunRequest(agent_name="customer_support_agent", request="Book appointment")
            cust = CustomerModel(id="1", phone="123", email="a@b.com", name="Test", plan="Free", status="active")

            result = await invoke_agent("customer_support_agent", req, cust, "session-1")
            assert result == "Appointment booked"
            mock_agent.arun.assert_called_once_with(req, cust, "session-1")

    @pytest.mark.asyncio
    async def test_invoke_agent_not_found_raises(self):
        with patch("src.services.dispatch_agent.get_agent", return_value=None):
            from src.core.agent_run_request_model import AgentRunRequest
            from src.core.customer import CustomerModel

            req = AgentRunRequest(agent_name="nonexistent_agent", request="test")
            cust = CustomerModel(id="1", phone="123", email="a@b.com", name="Test", plan="Free", status="active")

            with pytest.raises(ValueError, match="not found"):
                await invoke_agent("nonexistent_agent", req, cust, "session-1")
