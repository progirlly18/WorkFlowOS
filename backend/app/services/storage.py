"""Lightweight Storage Service.

Stores active workflows, approval statuses, and execution history in memory.
Designed for a hackathon MVP — no external database required.
"""
from typing import Dict, List, Optional
from ..models.workflow import WorkflowDefinition, ExecutionRecord, WorkflowStatus


class WorkflowStorageService:
    def __init__(self):
        self._workflows: Dict[str, WorkflowDefinition] = {}
        self._execution_history: List[ExecutionRecord] = {}  # keyed for O(1) lookup
        self._execution_list: List[str] = []                  # ordered list of execution IDs

    def save_workflow(self, workflow: WorkflowDefinition) -> WorkflowDefinition:
        self._workflows[workflow.workflow_id] = workflow
        return workflow

    def get_workflow(self, workflow_id: str) -> Optional[WorkflowDefinition]:
        return self._workflows.get(workflow_id)

    def list_workflows(self) -> List[WorkflowDefinition]:
        return list(self._workflows.values())

    def update_workflow_status(
        self, workflow_id: str, status: WorkflowStatus
    ) -> Optional[WorkflowDefinition]:
        wf = self._workflows.get(workflow_id)
        if wf:
            wf.status = status
        return wf

    def record_execution(self, record: ExecutionRecord) -> ExecutionRecord:
        self._execution_history[record.execution_id] = record
        self._execution_list.append(record.execution_id)
        return record

    def get_execution(self, execution_id: str) -> Optional[ExecutionRecord]:
        return self._execution_history.get(execution_id)

    def get_execution_history(self) -> List[ExecutionRecord]:
        """Return all execution records, most recent first."""
        return [
            self._execution_history[eid]
            for eid in reversed(self._execution_list)
            if eid in self._execution_history
        ]


storage_service = WorkflowStorageService()
