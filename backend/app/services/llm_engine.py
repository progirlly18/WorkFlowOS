"""LLM Intent and Workflow Synthesis Engine.

Uses the Google GenAI SDK (Gemini) to interpret a DetectedSequence and generate a
structured WorkflowDefinition. Provides a deterministic fallback when no API key is
present or the network call fails, so the hackathon demo never breaks.
"""
import json
import logging
import hashlib
from datetime import datetime
from typing import Optional

from ..config import GEMINI_API_KEY
from ..models.event import DetectedSequence
from ..models.workflow import WorkflowDefinition, WorkflowStep, WorkflowStatus

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# JSON schema for the LLM's structured response
# The LLM must return valid JSON matching this exact shape.
# ---------------------------------------------------------------------------
WORKFLOW_JSON_SCHEMA = {
    "type": "OBJECT",
    "required": [
        "name",
        "intent_summary",
        "trigger_description",
        "estimated_time_saved_minutes",
        "steps",
    ],
    "properties": {
        "name": {"type": "STRING"},
        "intent_summary": {"type": "STRING"},
        "trigger_description": {"type": "STRING"},
        "estimated_time_saved_minutes": {"type": "NUMBER"},
        "steps": {
            "type": "ARRAY",
            "items": {
                "type": "OBJECT",
                "required": ["step_id", "step_order", "app", "action_type", "title", "description"],
                "properties": {
                    "step_id": {"type": "STRING"},
                    "step_order": {"type": "INTEGER"},
                    "app": {"type": "STRING"},
                    "action_type": {"type": "STRING"},
                    "title": {"type": "STRING"},
                    "description": {"type": "STRING"},
                    "parameters": {
                        "type": "OBJECT",
                        "properties": {},
                        "additionalProperties": {"type": "STRING"},
                    },
                    "editable": {"type": "BOOLEAN"},
                },
            },
        },
    },
}

GEMINI_MODEL = "gemini-2.5-flash"


def _make_prompt(pattern: DetectedSequence) -> str:
    """Build the LLM prompt from the detected event sequence."""
    events_summary = "\n".join(
        f"  Step {i+1}: [{e.app}] {e.action} — metadata: {json.dumps(e.metadata, ensure_ascii=False)}"
        for i, e in enumerate(pattern.sample_events)
    )
    return f"""You are WorkFlowOS, an AI assistant that analyzes repeated user desktop actions and generates automation workflows.

A user has performed the following sequence of actions across multiple applications exactly {pattern.occurrence_count} times:

{events_summary}

Pattern description: {pattern.description or pattern.signature}
Confidence score: {pattern.confidence_score}

Your task:
1. Infer the user's high-level intent from the pattern (e.g., what goal are they trying to accomplish?).
2. Generate a concise, professional workflow automation definition.
3. For each step, provide practical parameters using realistic placeholder values (e.g., "{{{{attachment_name}}}}", "#billing-updates").
4. Estimate how many minutes this workflow would save per run compared to doing it manually.
5. Write the trigger description: what event or condition should kick off this automation.

Guidelines:
- Use clear, business-friendly language.
- Do NOT mention that this is AI generated or reference the input analysis.
- The workflow name should be a short, action-oriented title (e.g., "Process Customer Invoice Attachment").
- Steps should map 1-to-1 with the detected actions.
- Return ONLY a valid JSON object matching the required schema.
"""


def _build_workflow_from_dict(data: dict, pattern: DetectedSequence) -> WorkflowDefinition:
    """Construct a WorkflowDefinition from a parsed LLM JSON response."""
    sig_hash = hashlib.md5(pattern.signature.encode()).hexdigest()[:8]
    workflow_id = f"wf_{sig_hash}_{datetime.utcnow().strftime('%H%M%S')}"

    steps = []
    for i, raw_step in enumerate(data.get("steps", [])):
        steps.append(
            WorkflowStep(
                step_id=raw_step.get("step_id", f"step_{i+1:02d}"),
                step_order=raw_step.get("step_order", i + 1),
                app=raw_step.get("app", "Unknown App"),
                action_type=raw_step.get("action_type", "action"),
                title=raw_step.get("title", f"Step {i+1}"),
                description=raw_step.get("description", ""),
                parameters=raw_step.get("parameters", {}),
                editable=raw_step.get("editable", True),
            )
        )

    return WorkflowDefinition(
        workflow_id=workflow_id,
        name=data.get("name", "Automated Workflow"),
        intent_summary=data.get("intent_summary", "Automate repetitive cross-application task"),
        trigger_description=data.get("trigger_description", "When the pattern is detected"),
        estimated_time_saved_minutes=float(data.get("estimated_time_saved_minutes", 3.5)),
        status=WorkflowStatus.PENDING_APPROVAL,
        steps=steps,
    )


def _build_fallback_workflow(pattern: DetectedSequence) -> WorkflowDefinition:
    """Generate a deterministic workflow definition without any LLM call.

    Used when GEMINI_API_KEY is absent or the API call fails.
    Produces a polished, realistic result based on the detected events.
    """
    sig_hash = hashlib.md5(pattern.signature.encode()).hexdigest()[:8]
    workflow_id = f"wf_{sig_hash}_{datetime.utcnow().strftime('%H%M%S')}"

    # Derive workflow name and intent from apps present in the sequence
    apps = [e.app for e in pattern.sample_events]
    actions = [e.action for e in pattern.sample_events]

    # Build a smart name from the app list
    def _clean(app: str) -> str:
        return app.split(" (")[0]

    app_labels = [_clean(a) for a in apps]
    workflow_name = f"Automate {' → '.join(app_labels)}"

    # Detect common patterns and generate relevant intent/trigger
    has_email = any("gmail" in a.lower() or "mail" in a.lower() for a in apps)
    has_download = any("download" in act.lower() for act in actions)
    has_crm = any("crm" in a.lower() or "hubspot" in a.lower() or "salesforce" in a.lower() for a in apps)
    has_slack = any("slack" in a.lower() for a in apps)

    if has_email and has_download and has_crm and has_slack:
        workflow_name = "Process Customer Invoice Attachment"
        intent_summary = (
            "Automate the end-to-end process of receiving an invoice email, "
            "downloading the attachment, updating the customer record in the CRM, "
            "and notifying the billing team in Slack — eliminating manual effort "
            f"across {len(set(apps))} applications."
        )
        trigger_description = (
            "Triggered when a new email with an attachment is received in Gmail "
            "from a known customer or vendor domain."
        )
    else:
        intent_summary = (
            f"Automate the repeated {len(pattern.steps_summary)}-step workflow detected across "
            f"{len(set(apps))} applications. Detected {pattern.occurrence_count} times "
            f"with {int(pattern.confidence_score * 100)}% confidence."
        )
        trigger_description = (
            f"Triggered when a new event matching the first step is observed: "
            f"{pattern.steps_summary[0] if pattern.steps_summary else 'workflow start'}."
        )

    # Build steps from detected events
    steps = []
    for i, event in enumerate(pattern.sample_events):
        app_name = _clean(event.app)
        action_title = event.action.replace("_", " ").title()
        meta = event.metadata or {}

        # Enrich step parameters with sanitized placeholders from metadata
        params: dict = {}
        if event.action == "open_email":
            params = {
                "filter": "has_attachment:true",
                "sender_domain": meta.get("sender", "{{sender_email}}").split("@")[-1] if "@" in meta.get("sender", "") else "{{sender_domain}}",
                "subject_contains": "Invoice",
            }
            description = "Monitor Gmail inbox for emails with attachments from customer domains."
        elif event.action == "download_file":
            params = {
                "file_type": meta.get("file_type", "application/pdf"),
                "save_path": "{{download_directory}}",
            }
            description = "Download the email attachment and save it to the designated folder."
        elif event.action == "update_customer_record":
            params = {
                "customer_id": "{{customer_id}}",
                "field": meta.get("field_updated", "invoice_status"),
                "value": meta.get("value", "{{status_value}}"),
                "attach_document": "{{attachment_path}}",
            }
            description = f"Update the customer record in {app_name} with the invoice status and attach the document."
        elif event.action == "send_message":
            params = {
                "channel": meta.get("channel", "{{slack_channel}}"),
                "message": "Invoice {{invoice_id}} for {{customer_name}} has been processed. CRM updated.",
            }
            description = "Post a confirmation message to the billing team Slack channel."
        else:
            params = {k: str(v) for k, v in meta.items() if isinstance(v, (str, int, float, bool))}
            description = f"Perform {action_title} in {app_name}."

        steps.append(
            WorkflowStep(
                step_id=f"step_{i+1:02d}",
                step_order=i + 1,
                app=event.app,
                action_type=event.action,
                title=f"{app_name}: {action_title}",
                description=description,
                parameters=params,
                editable=True,
            )
        )

    # Estimate time saved: ~3 min manual per run * occurrences per day estimate
    estimated_time_saved = round(len(steps) * 0.75, 1)

    return WorkflowDefinition(
        workflow_id=workflow_id,
        name=workflow_name,
        intent_summary=intent_summary,
        trigger_description=trigger_description,
        estimated_time_saved_minutes=estimated_time_saved,
        status=WorkflowStatus.PENDING_APPROVAL,
        steps=steps,
    )


class LLMWorkflowEngine:
    """Synthesizes a WorkflowDefinition from a DetectedSequence using Gemini LLM.
    
    Automatically falls back to deterministic generation if:
    - GEMINI_API_KEY is not set or empty
    - The API call raises any exception
    """

    def synthesize_workflow(self, pattern: DetectedSequence) -> WorkflowDefinition:
        """Primary entry point: attempt LLM generation, fall back on any failure."""
        if not GEMINI_API_KEY or GEMINI_API_KEY.strip() == "":
            logger.info("GEMINI_API_KEY not set — using deterministic fallback workflow.")
            return _build_fallback_workflow(pattern)

        try:
            return self._call_gemini(pattern)
        except Exception as exc:
            logger.warning("Gemini API call failed (%s) — falling back to deterministic workflow.", exc)
            return _build_fallback_workflow(pattern)

    def _call_gemini(self, pattern: DetectedSequence) -> WorkflowDefinition:
        """Call Gemini API with structured JSON output schema."""
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=GEMINI_API_KEY)
        prompt = _make_prompt(pattern)

        response = client.models.generate_content(
            model=GEMINI_MODEL,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_json_schema=WORKFLOW_JSON_SCHEMA,
                temperature=0.3,   # Lower temperature for more predictable structured output
                max_output_tokens=2048,
            ),
        )

        raw_text = response.text
        data = json.loads(raw_text)
        return _build_workflow_from_dict(data, pattern)


llm_engine = LLMWorkflowEngine()
