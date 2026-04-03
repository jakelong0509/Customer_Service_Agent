---
name: email_skill
description: Use this skill when you need to communicate by sending email or replying to an email
---

## Email Handling Workflow

Use this workflow when processing email communications (inbound emails from customers or when you need to send outbound emails).

### 1. Detect Email Context

When the request contains `EMAIL_METADATA`, you are handling an **inbound email**. The metadata contains:
- `message_id`: The original email's Message-ID (required for replies)
- `from`: The sender's email address
- `to`: The recipient (your support address)
- `subject`: The email subject
- `references`: Previous Message-IDs in the thread (if any)

### 2. Store Email Context

You MUST store the email metadata for later use when replying:
- Save `message_id`, `from`, `subject` to conversation history or context
- These values are required to send a properly threaded reply

### 3. Available Email Tools

When this skill is active, you have access to these tools:

#### `send_email`
Send a new email or a reply with threading headers.

**Parameters:**
- `recipient_email_address`: Email address to send to
- `subject`: Subject line (prefix with "Re: " for replies)
- `body`: HTML content of the email
- `in_reply_to`: (Optional) Message-ID of email being replied to
- `references`: (Optional) Previous Message-IDs in the thread
- `reply_to_email`: (Optional) Original sender's email for replies

#### `reply_to_email`
Convenience tool for sending threaded replies.

**Parameters:**
- `original_message_id`: Message-ID from the email being replied to
- `original_sender`: Email address of the original sender
- `original_subject`: Subject of the original email
- `reply_body`: HTML content of your reply
- `references`: (Optional) Comma-separated previous Message-IDs

### 4. When to Send Email Replies

Send an email reply when:
- You have received an inbound email (EMAIL_METADATA present)
- You need to provide information, answer questions, or resolve issues
- The customer expects a response via email

**Always use `reply_to_email` for responses to inbound emails.** This ensures:
- Proper email threading (reply appears in customer's inbox thread)
- Correct headers (In-Reply-To, References)
- The customer receives the email notification

### 5. Reply Format

```
reply_to_email(
    original_message_id="<message-id-from-EMAIL_METADATA>",
    original_sender="<from-address-from-EMAIL_METADATA>",
    original_subject="<subject-from-EMAIL_METADATA>",
    reply_body="<p>Your professional HTML response here</p>"
)
```

### 6. Email Etiquette Guidelines

- Always use `reply_to_email` for responses (the tool handles "Re: " prefix)
- Format body as HTML
- Include professional greeting (e.g., "Dear [Name]," or "Hello,")
- Keep responses clear, concise, and helpful
- Include a signature if appropriate
- Maintain a professional, courteous tone

### 7. Sending New Emails (Not Replies)

For proactive emails (not replies), use `send_email` directly:

```
send_email(
    recipient_email_address="customer@example.com",
    subject="Your Order Update",
    body="<p>Your order has shipped...</p>"
)
```

