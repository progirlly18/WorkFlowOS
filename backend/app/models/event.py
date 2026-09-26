from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


class UserEvent(BaseModel):
    """Represents a single user desktop or application event observed by WorkFlowOS."""
    event_id: str
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
    app: str
    action: str
    window_title: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DetectedSequence(BaseModel):
    """Represents a repeated pattern detected by the sequence miner."""
    pattern_id: str
    signature: str
    steps_summary: List[str]
    occurrence_count: int
    confidence_score: float
    sample_events: List[UserEvent]
    description: Optional[str] = None
