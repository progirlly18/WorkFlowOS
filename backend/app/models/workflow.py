from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from datetime import datetime
from enum import Enum


class WorkflowStatus(str, Enum):
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"


class ExecutionStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    INTERVENTION_REQUIRED = "INTERVENTION_REQUIRED"


class WorkflowStep(BaseModel):
    step_id: str
    step_order: int
    app: str
    action_type: str
    title: str
    description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    editable: bool = True


class WorkflowDefinition(BaseModel):
    workflow_id: str
    name: str
    intent_summary: str
    trigger_description: str
    estimated_time_saved_minutes: float = 3.5
    status: WorkflowStatus = WorkflowStatus.PENDING_APPROVAL
    steps: List[WorkflowStep]
    created_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class StepExecutionResult(BaseModel):
    step_id: str
    step_title: str
    status: ExecutionStatus
    output_summary: str
    duration_ms: int
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")


class ExecutionRecord(BaseModel):
    execution_id: str
    workflow_id: str
    workflow_name: str
    status: ExecutionStatus
    step_results: List[StepExecutionResult] = Field(default_factory=list)
    total_duration_ms: int = 0
    estimated_time_saved_minutes: float = 0.0
    logs: List[str] = Field(default_factory=list)
    intervention_reason: Optional[str] = None
    executed_at: str = Field(default_factory=lambda: datetime.utcnow().isoformat() + "Z")
