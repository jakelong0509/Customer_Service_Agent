import pika
import json
import sys
import os
import asyncio
import dotenv
from src.services.dispatch_agent import invoke_agent
from src.core.agent_run_request_model import SendGridInboundRequest
from src.infrastructure.database import init_pool, close_pool
from src.infrastructure.redis import init_redis, close_redis
from src.infrastructure.milvus import init_milvus, close_milvus
from src.services.agent_registry import create_agent

dotenv.load_dotenv()

MAX_RETRIES  = 3

async def process_message(data: dict):
    agent_request = SendGridInboundRequest(**data)
    session_id = agent_request.message_id or ""
    customer = None
    result = await invoke_agent(
        agent_request.agent_name,
        agent_request,
        customer,
        session_id,
    )
    return result

def callback(ch, method, properties, body):
    data = json.loads(body)
    retry_count = 0
    if properties.headers and 'x-retry-count' in properties.headers:
        retry_count = int(properties.headers['x-retry-count'])

    try:
        print(f"[Worker] Processing: {data.get('subject', 'no subject')} (attempt {retry_count + 1})")
        result = asyncio.run(process_message(data))
        print(f"[Worker] Done: {result}")
        ch.basic_ack(delivery_tag=method.delivery_tag)

    except Exception as e:
        print(f"[Worker] Error: {e}")
        if retry_count < MAX_RETRIES:
            ch.basic_publish(
                exchange='',
                routing_key=method.routing_key,
                body=body,
                properties=pika.BasicProperties(
                    delivery_mode=2,
                    headers={'x-retry-count': retry_count + 1},
                ),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"[Worker] Re-queued (attempt {retry_count + 1}/{MAX_RETRIES})")
        else:
            ch.basic_publish(
                exchange='',
                routing_key='email_inbound_dlq',
                body=body,
                properties=pika.BasicProperties(delivery_mode=2),
            )
            ch.basic_ack(delivery_tag=method.delivery_tag)
            print(f"[Worker] Sent to DLQ after {MAX_RETRIES} retries")

async def startup():
    init_milvus()
    await init_pool()
    await init_redis()
    create_agent()

async def shutdown():
    await close_pool()
    await close_redis()
    close_milvus()

if __name__ == '__main__':
    asyncio.run(startup())

    connection = pika.BlockingConnection(
        pika.ConnectionParameters(
            host=os.getenv('RABBITMQ_HOST', 'localhost'),
            port=int(os.getenv('RABBITMQ_PORT', '5672')),
            credentials=pika.PlainCredentials(
                os.getenv('RABBITMQ_USER', 'guest'),
                os.getenv('RABBITMQ_PASS', 'guest'),
            ),
        )
    )
    channel = connection.channel()
    channel.queue_declare(queue='sendgrid_email_inbound_queue', durable=True)
    channel.queue_declare(queue='email_inbound_dlq', durable=True)
    channel.basic_qos(prefetch_count=1)
    channel.basic_consume(queue='sendgrid_email_inbound_queue', on_message_callback=callback)

    print("[Worker] Started. Waiting for messages... (Ctrl+C to stop)")
    try:
        channel.start_consuming()
    except KeyboardInterrupt:
        print("\n[Worker] Stopping...")
        channel.stop_consuming()
        connection.close()
        asyncio.run(shutdown())