import pytest
from src.core.customer import CustomerModel


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
