"""Workflow Execution Service.

Implements simulated step adapters for the Gmail → Download → HubSpot CRM → Slack
workflow. No real third-party credentials are required. Each adapter logs realistic
output and raises a structured exception on configurable failure conditions.

Safety rule: if a customer record cannot be located in the CRM step,
execution halts immediately with INTERVENTION_REQUIRED and logs the reason.
"""
import time
import uuid
import logging
from datetime import datetime
from typing import Any, Dict, Optional, Tuple

from ..models.workflow import (
    WorkflowDefinition,
    WorkflowStep,
    ExecutionRecord,
    ExecutionStatus,
    StepExecutionResult,
    WorkflowStatus,
)

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Custom exceptions
# ---------------------------------------------------------------------------

class StepExecutionError(Exception):
    """Raised when a step fails and execution should stop."""
    def __init__(self, message: str, step_id: str):
        super().__init__(message)
        self.step_id = step_id


class CustomerNotFoundError(StepExecutionError):
    """Raised when the CRM step cannot locate the customer — triggers intervention."""
    pass


# ---------------------------------------------------------------------------
# Simulated step adapters
# ---------------------------------------------------------------------------

# A small in-memory "CRM database" of known customers (used by the simulation)
_KNOWN_CUSTOMERS = {
    "1042": {"name": "Acme Corp",          "invoice_status": "Pending"},
    "1043": {"name": "Stark Industries",   "invoice_status": "Pending"},
    "1044": {"name": "Wayne Enterprises",  "invoice_status": "Pending"},
    "demo": {"name": "Demo Customer",      "invoice_status": "Pending"},
}

# Simulated attachment store (populated by the download step)
_DOWNLOADED_FILES: Dict[str, str] = {}


def _simulate_delay(ms: int) -> None:
    """Sleep for `ms` milliseconds to make the demo feel realistic."""
    time.sleep(ms / 1000.0)


def _run_gmail_step(step: WorkflowStep, params: Dict[str, Any]) -> Tuple[str, int]:
    """Simulate reading a customer email from Gmail inbox."""
    _simulate_delay(120)
    sender = params.get("sender_domain") or step.parameters.get("sender_domain", "customer.com")
    subject_kw = params.get("subject_contains") or step.parameters.get("subject_contains", "Invoice")
    attachment = params.get("attachment_name") or params.get("file_name") or "INV-DEMO.pdf"

    output = (
        f"[Gmail] Scanned inbox for emails matching filter '{subject_kw}' from domain '{sender}'. "
        f"Found 1 matching email with attachment: {attachment}."
    )
    return output, 120


def _run_download_step(step: WorkflowStep, params: Dict[str, Any]) -> Tuple[str, int]:
    """Simulate downloading the email attachment."""
    _simulate_delay(200)
    file_name = (
        params.get("file_name")
        or params.get("attachment_name")
        or step.parameters.get("file_name")
        or "INV-DEMO.pdf"
    )
    save_path = step.parameters.get("save_path", "{{download_directory}}")
    resolved_path = save_path.replace("{{download_directory}}", "C:/WorkFlowOS/Downloads")
    full_path = f"{resolved_path}/{file_name}"

    # Record in the simulated store for downstream steps
    _DOWNLOADED_FILES["latest"] = full_path

    output = (
        f"[Download] Attachment '{file_name}' downloaded successfully. "
        f"Saved to: {full_path} (512 KB, application/pdf)."
    )
    return output, 200


def _run_crm_step(step: WorkflowStep, params: Dict[str, Any]) -> Tuple[str, int]:
    """Simulate updating a HubSpot CRM customer record.
    
    Safety condition: if the customer_id is not found, raises CustomerNotFoundError
    to halt execution and request user intervention.
    """
    _simulate_delay(280)
    customer_id = str(
        params.get("customer_id")
        or step.parameters.get("customer_id", "demo")
    ).replace("{{customer_id}}", "demo")

    # Safety check: customer must exist
    if customer_id not in _KNOWN_CUSTOMERS:
        raise CustomerNotFoundError(
            f"Customer ID '{customer_id}' not found in CRM. "
            "Execution halted — please verify the customer record before retrying.",
            step_id=step.step_id,
        )

    customer = _KNOWN_CUSTOMERS[customer_id]
    field = step.parameters.get("field", "invoice_status")
    value = (
        params.get("value")
        or step.parameters.get("value", "Paid")
    ).replace("{{status_value}}", "Paid")

    attachment_path = _DOWNLOADED_FILES.get("latest", "N/A")

    # Simulate the update
    customer[field] = value

    output = (
        f"[HubSpot CRM] Updated customer '{customer['name']}' (ID: {customer_id}): "
        f"set '{field}' = '{value}'. Attached document: {attachment_path}. "
        f"Record timestamp: {datetime.utcnow().isoformat()}Z."
    )
    return output, 280


def _run_slack_step(step: WorkflowStep, params: Dict[str, Any]) -> Tuple[str, int]:
    """Simulate posting a Slack notification to the billing channel."""
    _simulate_delay(90)
    channel = (
        params.get("channel")
        or step.parameters.get("channel", "#billing-updates")
    )
    message_template = step.parameters.get(
        "message",
        "Invoice {{invoice_id}} for {{customer_name}} has been processed. CRM updated.",
    )
    customer_id = str(params.get("customer_id", "demo")).replace("{{customer_id}}", "demo")
    customer_name = _KNOWN_CUSTOMERS.get(customer_id, {}).get("name", "Customer")
    message = (
        message_template
        .replace("{{invoice_id}}", params.get("invoice_id", "INV-DEMO"))
        .replace("{{customer_name}}", customer_name)
        .replace("{{customer_id}}", customer_id)
    )

    output = (
        f"[Slack] Message posted to '{channel}': \"{message}\" "
        f"| Delivered at {datetime.utcnow().isoformat()}Z."
    )
    return output, 90


# ---------------------------------------------------------------------------
# Adapter dispatch table
# ---------------------------------------------------------------------------

_STEP_ADAPTERS = {
    "open_email":            _run_gmail_step,
    "download_file":         _run_download_step,
    "update_customer_record": _run_crm_step,
    "send_message":          _run_slack_step,
}

_APP_FALLBACK_MAP = {
    "gmail":    "open_email",
    "download": "download_file",
    "crm":      "update_customer_record",
    "hubspot":  "update_customer_record",
    "slack":    "send_message",
}


def _resolve_adapter(step: WorkflowStep):
    """Return the best-matching adapter function for this step."""
    if step.action_type in _STEP_ADAPTERS:
        return _STEP_ADAPTERS[step.action_type]
    # Fallback: match by app name keyword
    app_lower = step.app.lower()
    for keyword, action in _APP_FALLBACK_MAP.items():
        if keyword in app_lower:
            return _STEP_ADAPTERS[action]
    return None


# ---------------------------------------------------------------------------
# Main executor service
# ---------------------------------------------------------------------------

class WorkflowExecutorService:
    def execute_workflow(
        self,
        workflow: WorkflowDefinition,
        runtime_params: Optional[Dict[str, Any]] = None,
    ) -> ExecutionRecord:
        """Execute each step of an APPROVED workflow sequentially.

        Behaviour:
        - Only APPROVED workflows may run.
        - Each step transitions: PENDING → RUNNING → SUCCESS | FAILED.
        - If a CustomerNotFoundError is raised, execution halts with
          INTERVENTION_REQUIRED and the reason is recorded.
        - Any other StepExecutionError halts with FAILED.
        - Duration is measured per-step and aggregated.
        - Estimated time saved is pulled from the workflow definition.

        Returns:
            ExecutionRecord with full step-by-step results and logs.
        """
        if workflow.status != WorkflowStatus.APPROVED:
            raise ValueError(
                f"Workflow '{workflow.workflow_id}' must be APPROVED before execution. "
                f"Current status: {workflow.status}."
            )

        execution_id = f"exec_{uuid.uuid4().hex[:10]}"
        params = runtime_params or {}
        start_ts = time.monotonic()
        logs: list[str] = []
        step_results: list[StepExecutionResult] = []
        overall_status = ExecutionStatus.RUNNING
        intervention_reason: Optional[str] = None

        logs.append(
            f"[{datetime.utcnow().isoformat()}Z] Execution {execution_id} started for "
            f"workflow '{workflow.name}' ({len(workflow.steps)} steps)."
        )

        for step in sorted(workflow.steps, key=lambda s: s.step_order):
            step_start = time.monotonic()
            logs.append(
                f"[{datetime.utcnow().isoformat()}Z] Step {step.step_order}: "
                f"'{step.title}' — RUNNING"
            )
            adapter = _resolve_adapter(step)

            if adapter is None:
                # Unknown step type: skip with a warning, don't fail the run
                output = f"[{step.app}] No adapter available for action '{step.action_type}' — skipped."
                duration_ms = 0
                step_status = ExecutionStatus.SUCCESS
                logs.append(f"  ⚠ Skipped (unknown adapter): {output}")
            else:
                try:
                    output, duration_ms = adapter(step, params)
                    step_status = ExecutionStatus.SUCCESS
                    logs.append(f"  ✓ {output}")
                except CustomerNotFoundError as exc:
                    duration_ms = int((time.monotonic() - step_start) * 1000)
                    step_status = ExecutionStatus.INTERVENTION_REQUIRED
                    overall_status = ExecutionStatus.INTERVENTION_REQUIRED
                    intervention_reason = str(exc)
                    logs.append(f"  ⚠ INTERVENTION REQUIRED: {exc}")
                    step_results.append(
                        StepExecutionResult(
                            step_id=step.step_id,
                            step_title=step.title,
                            status=step_status,
                            output_summary=str(exc),
                            duration_ms=duration_ms,
                        )
                    )
                    break  # Halt immediately
                except StepExecutionError as exc:
                    duration_ms = int((time.monotonic() - step_start) * 1000)
                    step_status = ExecutionStatus.FAILED
                    overall_status = ExecutionStatus.FAILED
                    logs.append(f"  ✗ FAILED: {exc}")
                    step_results.append(
                        StepExecutionResult(
                            step_id=step.step_id,
                            step_title=step.title,
                            status=step_status,
                            output_summary=str(exc),
                            duration_ms=duration_ms,
                        )
                    )
                    break  # Halt on step failure
                except Exception as exc:
                    duration_ms = int((time.monotonic() - step_start) * 1000)
                    step_status = ExecutionStatus.FAILED
                    overall_status = ExecutionStatus.FAILED
                    error_msg = f"Unexpected error in step '{step.title}': {exc}"
                    logs.append(f"  ✗ ERROR: {error_msg}")
                    step_results.append(
                        StepExecutionResult(
                            step_id=step.step_id,
                            step_title=step.title,
                            status=step_status,
                            output_summary=error_msg,
                            duration_ms=duration_ms,
                        )
                    )
                    break

            step_results.append(
                StepExecutionResult(
                    step_id=step.step_id,
                    step_title=step.title,
                    status=step_status,
                    output_summary=output,
                    duration_ms=duration_ms,
                )
            )

        # Determine final status if no failure occurred
        if overall_status == ExecutionStatus.RUNNING:
            all_success = all(r.status == ExecutionStatus.SUCCESS for r in step_results)
            overall_status = ExecutionStatus.SUCCESS if all_success else ExecutionStatus.FAILED

        total_ms = int((time.monotonic() - start_ts) * 1000)

        if overall_status == ExecutionStatus.SUCCESS:
            logs.append(
                f"[{datetime.utcnow().isoformat()}Z] ✓ Execution completed successfully "
                f"in {total_ms}ms. Estimated time saved: {workflow.estimated_time_saved_minutes} min."
            )
        elif overall_status == ExecutionStatus.INTERVENTION_REQUIRED:
            logs.append(
                f"[{datetime.utcnow().isoformat()}Z] ⚠ Execution halted — intervention required. "
                f"Reason: {intervention_reason}"
            )
        else:
            logs.append(
                f"[{datetime.utcnow().isoformat()}Z] ✗ Execution failed after {total_ms}ms."
            )

        record = ExecutionRecord(
            execution_id=execution_id,
            workflow_id=workflow.workflow_id,
            workflow_name=workflow.name,
            status=overall_status,
            step_results=step_results,
            total_duration_ms=total_ms,
            estimated_time_saved_minutes=workflow.estimated_time_saved_minutes,
            logs=logs,
            intervention_reason=intervention_reason,
        )

        # Persist to storage
        from ..services.storage import storage_service
        storage_service.record_execution(record)
        return record


executor_service = WorkflowExecutorService()
