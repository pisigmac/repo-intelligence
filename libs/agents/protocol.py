"""Agent communication protocol and message bus."""
import json
import logging
from typing import Callable, Awaitable
from libs.common.kafka_client import KafkaProducer, KafkaConsumer

logger = logging.getLogger(__name__)


class AgentMessageBus:
    """Kafka-based message bus for inter-agent communication."""

    def __init__(self, bootstrap_servers: str, group_id: str):
        self.bootstrap_servers = bootstrap_servers
        self.group_id = group_id
        self.producer: KafkaProducer | None = None
        self.consumer: KafkaConsumer | None = None

    async def start_producer(self):
        self.producer = KafkaProducer(self.bootstrap_servers)
        await self.producer.start()

    async def stop_producer(self):
        if self.producer:
            await self.producer.stop()

    async def send(self, topic: str, message: dict, key: str | None = None):
        if not self.producer:
            raise RuntimeError("Producer not started")
        await self.producer.send(topic, message, key=key)

    async def start_consumer(self, topics: list[str], handler: Callable[[str, dict], Awaitable[None]]):
        self.consumer = KafkaConsumer(
            bootstrap_servers=self.bootstrap_servers,
            topics=topics,
            group_id=self.group_id,
            handler=handler,
        )
        await self.consumer.start()

    async def run_consumer(self):
        if not self.consumer:
            raise RuntimeError("Consumer not started")
        await self.consumer.run()

    async def stop_consumer(self):
        if self.consumer:
            await self.consumer.stop()
