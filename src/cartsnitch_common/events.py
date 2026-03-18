"""Event bus helpers for Redis pub/sub."""

from datetime import UTC, datetime
from typing import Any

from redis import Redis

from cartsnitch_common.constants import EventType
from cartsnitch_common.schemas.events import EventEnvelope


def publish_event(
    redis_client: Redis,
    event_type: EventType,
    service: str,
    payload: dict[str, Any],
) -> int:
    """Publish an event to the Redis pub/sub channel.

    Returns the number of subscribers that received the message.
    """
    envelope = EventEnvelope(
        event_type=event_type,
        timestamp=datetime.now(UTC),
        service=service,
        payload=payload,
    )
    result = redis_client.publish(event_type.value, envelope.model_dump_json())
    return int(result)
