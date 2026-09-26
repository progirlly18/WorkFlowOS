"""API Routes for User Events."""
from fastapi import APIRouter
from typing import List
from ..models.event import UserEvent
from ..services.observer import observer_service

router = APIRouter(prefix="/events", tags=["events"])


@router.get("", response_model=List[UserEvent])
def get_recent_events(limit: int = 50):
    return observer_service.get_events(limit=limit)


@router.post("", response_model=UserEvent)
def ingest_event(event: UserEvent):
    return observer_service.ingest_event(event)


@router.post("/demo/load", response_model=List[UserEvent])
def load_demo_scenario():
    """Load the hackathon Gmail -> CRM -> Slack demo dataset."""
    return observer_service.load_demo_scenario()


@router.delete("/clear")
def clear_events():
    observer_service.clear_events()
    return {"status": "cleared"}
