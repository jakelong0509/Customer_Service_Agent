import os
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from langchain.tools import tool
import dotenv
from typing import List, Callable
dotenv.load_dotenv()

@tool
async def send_email(recipient_email_address: str, subject: str, body: str) -> str:
  """
  Send an email to the customer
  Args:
    email: str - The email address to send the email to
    subject: str - The subject of the email
    body: str - The body of the email
  Returns:
    str: The result of the email send
  """
  try:
    message = Mail(
      from_email=os.getenv("SENDGRID_FROM_EMAIL"),
      to_emails=recipient_email_address,
      subject=subject,
      html_content=body
    )
    sendgrid_client = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    response = sendgrid_client.send(message)
    if response.status_code == 202:
      return "Email sent successfully"
    else:
      return f"Error sending email: {response.status_code}"
  except Exception as e:
    return f"Error sending email: {e}"

@tool
async def reply_to_email(message_id: str, body: str) -> str:
  """
  Reply to an email
  Args:
    message_id: str - The id of the message to reply to
    body: str - The body of the reply
  Returns:
    str: The result of the email reply
  """
  try:
    sendgrid_client = SendGridAPIClient(os.getenv("SENDGRID_API_KEY"))
    response = sendgrid_client.reply(message_id, body)
    if response.status_code == 202:
      return "Email replied successfully"
    else:
      return f"Error replying to email: {response.status_code}"
  except Exception as e:
    return f"Error replying to email: {e}"

TOOLS = [send_email, reply_to_email]
def get_tools() -> List[Callable]:
  return TOOLS