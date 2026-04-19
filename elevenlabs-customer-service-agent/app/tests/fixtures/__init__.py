import pytest
from src.core.customer import CustomerModel
from src.core.agent_run_request_model import (
    AgentRunRequest,
    ElevenLabsAgentRunRequest,
    SendGridInboundRequest,
)


@pytest.fixture
def sample_customer():
    return CustomerModel(
        id="cust-001",
        phone="1234567890",
        email="john@example.com",
        name="John Doe",
        plan="Free",
        status="active",
    )


@pytest.fixture
def sample_customer_2():
    return CustomerModel(
        id="cust-002",
        phone="0987654321",
        email="jane@example.com",
        name="Jane Smith",
        plan="Premium",
        status="active",
    )


@pytest.fixture
def unregistered_customer():
    return CustomerModel(
        id="cust-unreg",
        phone="5555555555",
        email="",
        name="Unregistered Customer",
        plan="Free",
        status="active",
    )


@pytest.fixture
def agent_run_request():
    return AgentRunRequest(
        agent_name="customer_support_agent",
        request="I need to book an appointment",
    )


@pytest.fixture
def elevenlabs_run_request():
    return ElevenLabsAgentRunRequest(
        agent_name="customer_support_agent",
        request="I want to schedule a visit",
        call_sid="CA-test-call-sid-001",
        caller_phone_number="1234567890",
        email_metadata={},
    )


@pytest.fixture
def sendgrid_inbound_request():
    return SendGridInboundRequest(
        agent_name="rxnorm_mapping_agent_email",
        request="metformin 500mg bid, lisinopril 10mg qd",
        message_id="<msg-001@example.com>",
        from_email="doctor@clinic.com",
        to="rxnorm@support.example.com",
        subject="Medication reconciliation",
        references="",
    )
