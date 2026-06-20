"""Transactional outbox creation and resilient background delivery."""
import json
import logging
from datetime import datetime, timezone
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .database import AsyncSessionLocal
from .events import event_bus
from .models import OutboxEvent

logger = logging.getLogger(__name__)


def add_event(db: AsyncSession, aggregate_type: str, aggregate_id: str, event_type: str, payload: dict) -> None:
    db.add(
        OutboxEvent(
            id=str(uuid4()), aggregate_type=aggregate_type, aggregate_id=aggregate_id,
            event_type=event_type, payload=json.dumps(payload, default=str),
        )
    )


async def dispatch_pending(limit: int = 100) -> int:
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(OutboxEvent).where(OutboxEvent.published_at.is_(None)).order_by(OutboxEvent.created_at).limit(limit)
        )
        events = result.scalars().all()
        delivered = 0
        for event in events:
            try:
                await event_bus.publish_event(event.event_type, {"event_id": event.id, **json.loads(event.payload)})
                event.published_at = datetime.now(timezone.utc).replace(tzinfo=None)
                event.last_error = None
                delivered += 1
            except Exception as exc:
                event.attempts += 1
                event.last_error = str(exc)[:1000]
                logger.exception("outbox delivery failed", extra={"event_id": event.id})
        await db.commit()
        return delivered
