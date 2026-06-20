"""
Kafka producer for event streaming.
Used for order events, notifications, and analytics.
"""
import logging
from aiokafka import AIOKafkaProducer
from typing import Dict, Any, Optional
import json
import time
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_random_exponential
from .config import settings

logger = logging.getLogger(__name__)

class KafkaEventBus:
    """Async Kafka event producer."""
    
    def __init__(self):
        self.producer: Optional[AIOKafkaProducer] = None
        self.enabled = settings.enable_kafka
        self.failures = 0
        self.circuit_open_until = 0.0
    
    async def connect(self):
        """Connect to Kafka broker."""
        if not self.enabled:
            logger.info("Kafka is disabled")
            return
        
        try:
            self.producer = AIOKafkaProducer(
                bootstrap_servers=settings.kafka_brokers,
                value_serializer=lambda v: json.dumps(v, default=str).encode('utf-8'),
                compression_type='gzip',
            )
            await self.producer.start()
            logger.info(f"Connected to Kafka at {settings.kafka_brokers}")
        except Exception as e:
            logger.warning(f"Failed to connect to Kafka: {e}")
            self.enabled = False
    
    async def disconnect(self):
        """Disconnect from Kafka."""
        if self.producer:
            await self.producer.stop()
    
    async def publish_order_created(self, order_id: int, customer_id: int, total_amount: float):
        """Publish order created event."""
        if not self.enabled or not self.producer:
            return
        
        await self.producer.send_and_wait(
            "order_created",
            value={
                "order_id": order_id,
                "customer_id": customer_id,
                "total_amount": total_amount,
                "event_type": "order_created",
            }
        )
    
    async def publish_order_cancelled(self, order_id: int, customer_id: int):
        """Publish order cancelled event."""
        if not self.enabled or not self.producer:
            return
        
        await self.producer.send_and_wait(
            "order_cancelled",
            value={
                "order_id": order_id,
                "customer_id": customer_id,
                "event_type": "order_cancelled",
            }
        )
    
    async def publish_inventory_low(self, product_id: int, product_name: str, quantity: int):
        """Publish low inventory alert."""
        if not self.enabled or not self.producer:
            return
        
        await self.producer.send_and_wait(
            "inventory_alert",
            value={
                "product_id": product_id,
                "product_name": product_name,
                "quantity": quantity,
                "event_type": "inventory_low",
            }
        )
    
    async def publish_event(self, topic: str, event: Dict[str, Any]):
        """Publish custom event to topic."""
        if not self.enabled or not self.producer:
            return
        
        if time.monotonic() < self.circuit_open_until:
            raise RuntimeError("Kafka circuit breaker is open")
        try:
            await self._send_with_retry(topic, event)
            self.failures = 0
            logger.debug("Published event", extra={"topic": topic, "event_id": event.get("event_id")})
        except Exception:
            self.failures += 1
            if self.failures >= 5:
                self.circuit_open_until = time.monotonic() + 30
            raise

    @retry(
        retry=retry_if_exception_type(Exception),
        wait=wait_random_exponential(multiplier=0.25, max=5),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    async def _send_with_retry(self, topic: str, event: Dict[str, Any]):
        await self.producer.send_and_wait(topic, value=event)

# Global Kafka event bus instance
event_bus = KafkaEventBus()
