"""Async Kafka producer and consumer wrapper using aiokafka."""
import json
import logging
from typing import Callable, Awaitable, Optional
from aiokafka import AIOKafkaProducer, AIOKafkaConsumer
from aiokafka.helpers import create_ssl_context

logger = logging.getLogger(__name__)


class KafkaProducer:
    def __init__(self, bootstrap_servers: str):
        self.bootstrap_servers = bootstrap_servers
        self._producer: Optional[AIOKafkaProducer] = None

    async def start(self):
        self._producer = AIOKafkaProducer(
            bootstrap_servers=self.bootstrap_servers,
            value_serializer=lambda v: json.dumps(v).encode("utf-8"),
            key_serializer=lambda k: k.encode("utf-8") if k else None,
        )
        await self._producer.start()
        logger.info("Kafka producer started", extra={"servers": self.bootstrap_servers})

    async def stop(self):
        if self._producer:
            await self._producer.stop()

    async def send(self, topic: str, message: dict, key: Optional[str] = None):
        if not self._producer:
            raise RuntimeError("Producer not started")
        await self._producer.send(topic, message, key=key)
        logger.debug("Sent message to Kafka", extra={"topic": topic, "key": key})


class KafkaConsumer:
    def __init__(
        self,
        bootstrap_servers: str,
        topics: list[str],
        group_id: str,
        handler: Callable[[str, dict], Awaitable[None]],
    ):
        self.bootstrap_servers = bootstrap_servers
        self.topics = topics
        self.group_id = group_id
        self.handler = handler
        self._consumer: Optional[AIOKafkaConsumer] = None

    async def start(self):
        self._consumer = AIOKafkaConsumer(
            *self.topics,
            bootstrap_servers=self.bootstrap_servers,
            group_id=self.group_id,
            auto_offset_reset="earliest",
            value_deserializer=lambda m: json.loads(m.decode("utf-8")),
        )
        await self._consumer.start()
        logger.info(
            "Kafka consumer started",
            extra={"topics": self.topics, "group": self.group_id},
        )

    async def run(self):
        if not self._consumer:
            raise RuntimeError("Consumer not started")
        try:
            async for msg in self._consumer:
                try:
                    await self.handler(msg.topic, msg.value)
                    await self._consumer.commit()
                except Exception as e:
                    logger.exception("Error handling Kafka message", extra={"topic": msg.topic})
        finally:
            await self.stop()

    async def stop(self):
        if self._consumer:
            await self._consumer.stop()
