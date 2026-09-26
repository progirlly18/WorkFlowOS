"""API Routes for Executing Workflows and Checking Execution Records."""
from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from ..models.workflow import ExecutionRecord
from ..services.executor import executor_service
from ..services.storage import storage_service

router = APIRouter(prefix="/execution", tags=["execution"])


@router.post("/run/{workflow_id}", response_model=ExecutionRecord)
def execute_workflow(workflow_id: str, params: Dict[str, Any] = None):
    """Executes an approved workflow and returns step results and execution logs."""
    wf = storage_service.get_workflow(workflow_id)
    if not wf:
        raise HTTPException(status_code=404, detail="Workflow not found")
    record = executor_service.execute_workflow(wf, runtime_params=params)
    return record


@router.get("/history", response_model=List[ExecutionRecord])
def get_execution_history():
    """Returns past automation execution runs and metrics."""
    return storage_service.get_execution_history()
