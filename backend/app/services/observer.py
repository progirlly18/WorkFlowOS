"""Event Observer and Ingest Service.

Observes and buffers incoming desktop events (or streams recorded demo sessions).
"""
import json
from typing import List, Optional
from ..models.event import UserEvent
from ..config import SCENARIO_FILE_PATH


class EventObserverService:
    def __init__(self):
        self._event_buffer: List[UserEvent] = []

    def ingest_event(self, event: UserEvent) -> UserEvent:
        """Add a single live event to the buffer."""
        self._event_buffer.append(event)
        return event

    def get_events(self, limit: int = 50) -> List[UserEvent]:
        """Get the latest observed events."""
        return self._event_buffer[-limit:]

    def clear_events(self):
        """Reset the observed event buffer."""
        self._event_buffer.clear()

    def load_demo_scenario(self, file_path: Optional[str] = None) -> List[UserEvent]:
        """Load pre-recorded demo events (e.g. Gmail -> Download -> CRM -> Slack)."""
        target_path = file_path or SCENARIO_FILE_PATH
        with open(target_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        events = [UserEvent(**item) for item in data.get("events", [])]
        self._event_buffer.extend(events)
        return events


observer_service = EventObserverService()
