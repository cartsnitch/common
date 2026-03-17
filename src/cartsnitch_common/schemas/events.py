"""Redis pub/sub event envelope and payload schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel

from cartsnitch_common.constants import EventType


class EventEnvelope(BaseModel):
    """Standard event wrapper for all Redis pub/sub messages."""

    event_type: EventType
    timestamp: datetime
    service: str
    payload: dict[str, Any]
