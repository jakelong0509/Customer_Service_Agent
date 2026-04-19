import json, pika, aio_pika, os, dotenv
from typing import Any
dotenv.load_dotenv()

class RabbitMQService:
  @classmethod
  async def asend_message(self, request: Any):
    connection = await aio_pika.connect_robus(os.getenv("RABBITMQ_URL"))
    async with connection:
      channel = await connection.channel()
      await channel.default_exchange.publish(
        aio_pika.Message(
          body = json.dumps(request.dict()).encode(),
          delivery_mode = aio_pika.DeliveryMode.PERSISTENT
        ),
        routing_key="sendgrid_email_inbound_queue"
      )
