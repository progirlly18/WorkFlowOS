"""API Routes for Repetition Detection, Intent Understanding, and Workflow Approval."""
from fastapi import APIRouter, HTTPException, Body
from typing import List, Dict, Any, Optional
from ..models.event import DetectedSequence
from ..models.workflow import WorkflowDefinition, WorkflowStatus
from ..services.observer import observer_service
from ..services.detector import detector_service
from ..services.llm_engine import llm_engine
from ..services.storage import storage_service

router = APIRouter(prefix="/workflows", tags=["workflows"])


@router.get("/detect", response_model=List[DetectedSequence])
@router.post("/detect", response_model=List[DetectedSequence])
def detect_repeated_patterns(
    min_occurrences: int = 2,
    window_size: Optional[int] = None,
    auto_load_demo: bool = True,
):
    """Scans buffered events for repetition across applications.

    If the event buffer is empty and auto_load_demo is True,
    it loads the demo scenario (Gmail -> Download -> CRM -> Slack).
    """
    events = observer_service.get_events(limit=200)
    if not events and auto_load_demo:
        events = observer_service.load_demo_scenario()
    patterns = detector_service.detect_patterns(
        events, min_occurrences=min_occurrences, window_size=window_size
    )
    return patterns


@router.post("/generate", response_model=WorkflowDefinition)
def generate_workflow(
    pattern: DetectedSequence = Body(..., description="A DetectedSequence from /detect"),
):
    """Use LLM (Gemini) to synthesize a WorkflowDefinition from a detected repetition pattern.

    Falls back to deterministic generation if no API key is present or the call fails.
    The generated workflow is saved in memory with status PENDING_APPROVAL.
    """
    workflow = llm_engine.synthesize_workflow(pattern)
    storage_service.save_workflow(workflow)
    return workflow


@router.get("", response_model=List[WorkflowDefinition])
def list_workflows():
    """List all generated workflows (pending approval, approved, or rejected)."""
    return storage_service.list_workflows()


@router.post("/{workflow_id}/approve", response_model=WorkflowDefinition)
def approve_workflow(workflow_id: str):
    """User approves the AI-generated workflow so it can be executed.

    Only workflows in PENDING_APPROVAL status can be approved.
    """
    wf = storage_service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    if wf.status == WorkflowStatus.APPROVED:
        raise HTTPException(status_code=409, detail="Workflow is already APPROVED.")
    if wf.status == WorkflowStatus.REJECTED:
        raise HTTPException(
            status_code=409,
            detail="Workflow has been REJECTED and cannot be approved. Generate a new one.",
        )
    storage_service.update_workflow_status(workflow_id, WorkflowStatus.APPROVED)
    return wf


@router.post("/{workflow_id}/reject", response_model=WorkflowDefinition)
def reject_workflow(workflow_id: str):
    """User rejects the AI-generated workflow.

    Only workflows in PENDING_APPROVAL status can be rejected.
    """
    wf = storage_service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail=f"Workflow '{workflow_id}' not found.")
    if wf.status == WorkflowStatus.REJECTED:
        raise HTTPException(status_code=409, detail="Workflow is already REJECTED.")
    if wf.status == WorkflowStatus.APPROVED:
        raise HTTPException(
            status_code=409,
            detail="An APPROVED workflow cannot be rejected. Disable it instead.",
        )
    storage_service.update_workflow_status(workflow_id, WorkflowStatus.REJECTED)
    return wf
