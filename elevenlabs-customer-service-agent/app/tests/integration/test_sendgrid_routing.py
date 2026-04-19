"""Integration tests for SendGrid inbound email routing.

These tests verify that inbound emails are correctly routed to the right agent
based on the recipient address, and that email headers are properly parsed.
"""
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestSendGridRouting:
    @pytest.fixture
    def client(self):
        from main import app
        return TestClient(app)

    def test_inbound_email_to_rxnorm(self, client):
        with patch("DAL.customerDA.CustomerDA.get_customer_by_email_address", new_callable=AsyncMock) as mock_cust, \
             patch("controllers.sendgrid._run_inbound_agent", new_callable=AsyncMock) as mock_run:

            mock_cust.return_value = MagicMock()

            response = client.post(
                "/api/sendgrid/inbound",
                data={
                    "from": "doctor@clinic.com",
                    "to": "rxnorm@support.example.com",
                    "subject": "Medication reconciliation",
                    "text": "metformin 500mg bid",
                    "headers": "Message-ID: <msg-001@clinic.com>",
                },
            )
            assert response.status_code == 200

    def test_inbound_email_to_support(self, client):
        with patch("DAL.customerDA.CustomerDA.get_customer_by_email_address", new_callable=AsyncMock) as mock_cust, \
             patch("controllers.sendgrid._run_inbound_agent", new_callable=AsyncMock) as mock_run:

            mock_cust.return_value = MagicMock()

            response = client.post(
                "/api/sendgrid/inbound",
                data={
                    "from": "patient@example.com",
                    "to": "support@support.example.com",
                    "subject": "Need appointment",
                    "text": "I need to reschedule",
                    "headers": "Message-ID: <msg-002@example.com>",
                },
            )
            assert response.status_code == 200

    def test_inbound_email_unknown_recipient(self, client):
        with patch("DAL.customerDA.CustomerDA.get_customer_by_email_address", new_callable=AsyncMock) as mock_cust:

            mock_cust.return_value = MagicMock()

            response = client.post(
                "/api/sendgrid/inbound",
                data={
                    "from": "someone@example.com",
                    "to": "unknown@example.com",
                    "subject": "Hello",
                    "text": "Test",
                    "headers": "",
                },
            )
            assert response.status_code == 200


class TestEmailHeaderParsing:
    def test_full_header_parsing(self):
        from controllers.sendgrid import extract_message_id, extract_references

        headers = (
            "From: doctor@clinic.com\r\n"
            "Message-ID: <abc-123@clinic.com>\r\n"
            "References: <prev-001@clinic.com> <prev-002@clinic.com>\r\n"
            "Subject: Test"
        )
        msg_id = extract_message_id(headers)
        refs = extract_references(headers)

        assert msg_id == "<abc-123@clinic.com>"
        assert len(refs) == 2
        assert "prev-001@clinic.com" in refs

    def test_no_headers(self):
        from controllers.sendgrid import extract_message_id, extract_references

        assert extract_message_id(None) is None
        assert extract_references(None) == []
