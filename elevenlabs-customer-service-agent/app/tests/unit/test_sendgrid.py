from controllers.sendgrid import extract_message_id, extract_references


class TestExtractMessageId:
    def test_standard_format(self):
        headers = "Message-ID: <abc-123@example.com>"
        result = extract_message_id(headers)
        assert result == "<abc-123@example.com>"

    def test_case_insensitive(self):
        headers = "message-id: <abc@example.com>"
        result = extract_message_id(headers)
        assert result == "<abc@example.com>"

    def test_none_headers(self):
        assert extract_message_id(None) is None

    def test_empty_headers(self):
        assert extract_message_id("") is None

    def test_no_message_id(self):
        headers = "From: test@example.com\r\nTo: dest@example.com"
        assert extract_message_id(headers) is None

    def test_multiline_headers(self):
        headers = "From: test@example.com\r\nMessage-ID: <msg-456@test.com>\r\nTo: dest@example.com"
        result = extract_message_id(headers)
        assert result == "<msg-456@test.com>"

    def test_without_angle_brackets(self):
        headers = "Message-ID: abc@example.com"
        result = extract_message_id(headers)
        assert result == "<abc@example.com>"


class TestExtractReferences:
    def test_single_reference(self):
        headers = "References: <msg-001@example.com>"
        result = extract_references(headers)
        assert result == ["msg-001@example.com"]

    def test_multiple_references(self):
        headers = "References: <msg-001@example.com> <msg-002@example.com> <msg-003@example.com>"
        result = extract_references(headers)
        assert len(result) == 3
        assert "msg-001@example.com" in result
        assert "msg-003@example.com" in result

    def test_none_headers(self):
        assert extract_references(None) == []

    def test_empty_headers(self):
        assert extract_references("") == []

    def test_no_references_header(self):
        headers = "From: test@example.com\r\nTo: dest@example.com"
        assert extract_references(headers) == []
