from src.core.customer import CustomerModel
from src.core.agent_run_request_model import (
    AgentRunRequest,
    ElevenLabsAgentRunRequest,
    SendGridInboundRequest,
    AgentRunResponse,
)


class TestCustomerModel:
    def test_create_customer(self):
        c = CustomerModel(
            id="1",
            phone="1234567890",
            email="test@test.com",
            name="Test User",
            plan="Free",
            status="active",
        )
        assert c.id == "1"
        assert c.phone == "1234567890"
        assert c.email == "test@test.com"

    def test_customer_serialization(self):
        c = CustomerModel(
            id="1",
            phone="1234567890",
            email="test@test.com",
            name="Test User",
            plan="Free",
            status="active",
        )
        data = c.model_dump()
        assert data["id"] == "1"
        assert data["phone"] == "1234567890"

    def test_customer_json_serialization(self):
        c = CustomerModel(
            id="1",
            phone="1234567890",
            email="test@test.com",
            name="Test User",
            plan="Free",
            status="active",
        )
        json_str = c.model_dump_json()
        assert '"id":"1"' in json_str
        assert '"phone":"1234567890"' in json_str


class TestAgentRunRequest:
    def test_create_request(self):
        req = AgentRunRequest(
            agent_name="customer_support_agent",
            request="Book an appointment",
        )
        assert req.agent_name == "customer_support_agent"
        assert req.request == "Book an appointment"

    def test_request_requires_fields(self):
        try:
            AgentRunRequest()
            assert False, "Should require fields"
        except Exception:
            pass


class TestElevenLabsAgentRunRequest:
    def test_create_elevenlabs_request(self):
        req = ElevenLabsAgentRunRequest(
            agent_name="customer_support_agent",
            request="Schedule a visit",
            call_sid="CA-123",
            caller_phone_number="1234567890",
            email_metadata={},
        )
        assert req.call_sid == "CA-123"
        assert req.caller_phone_number == "1234567890"

    def test_inherits_agent_run_request(self):
        req = ElevenLabsAgentRunRequest(
            agent_name="test",
            request="test",
            call_sid="CA-1",
            caller_phone_number="000",
            email_metadata={},
        )
        assert isinstance(req, AgentRunRequest)


class TestSendGridInboundRequest:
    def test_create_sendgrid_request(self):
        req = SendGridInboundRequest(
            agent_name="rxnorm_mapping_agent_email",
            request="metformin 500mg",
            message_id="<msg@test.com>",
            from_email="doc@clinic.com",
            to="rxnorm@support.com",
            subject="Reconciliation",
            references="<prev@test.com>",
        )
        assert req.message_id == "<msg@test.com>"
        assert req.from_email == "doc@clinic.com"
        assert req.references == "<prev@test.com>"

    def test_optional_fields(self):
        req = SendGridInboundRequest(
            agent_name="test",
            request="test",
            message_id="<msg@test.com>",
            from_email="a@b.com",
            to="c@d.com",
        )
        assert req.subject is None
        assert req.references is None


class TestAgentRunResponse:
    def test_success_response(self):
        resp = AgentRunResponse(result="Appointment booked", is_error=False)
        assert resp.result == "Appointment booked"
        assert resp.is_error is False

    def test_error_response(self):
        resp = AgentRunResponse(result="Error: Something went wrong", is_error=True)
        assert resp.is_error is True

    def test_default_is_error_false(self):
        resp = AgentRunResponse(result="OK")
        assert resp.is_error is False
