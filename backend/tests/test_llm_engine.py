import json
import unittest
from unittest.mock import patch, MagicMock

from backend.app.models.event import UserEvent, DetectedSequence
from backend.app.models.workflow import WorkflowDefinition, WorkflowStep, WorkflowStatus
from backend.app.services.llm_engine import (
    LLMWorkflowEngine,
    _build_fallback_workflow,
    _build_workflow_from_dict,
    _make_prompt,
    llm_engine,
)
from backend.app.services.observer import observer_service
from backend.app.services.storage import storage_service


# ---------------------------------------------------------------------------
# Shared fixtures
# ---------------------------------------------------------------------------

def _make_sample_events():
    return [
        UserEvent(
            event_id="evt_001",
            timestamp="2026-09-26T09:15:00Z",
            app="Gmail (Chrome)",
            action="open_email",
            window_title="Gmail - Inbox - Invoice from Acme Corp",
            metadata={
                "sender": "billing@acmecorp.com",
                "subject": "Invoice INV-1042 Acme Corp",
                "has_attachment": True,
                "attachment_name": "INV-1042_AcmeCorp.pdf",
            },
        ),
        UserEvent(
            event_id="evt_002",
            timestamp="2026-09-26T09:15:20Z",
            app="Browser Download",
            action="download_file",
            window_title="Save Attachment",
            metadata={
                "file_name": "INV-1042_AcmeCorp.pdf",
                "file_path": "C:/Users/VIDYA/Downloads/INV-1042_AcmeCorp.pdf",
                "file_type": "application/pdf",
            },
        ),
        UserEvent(
            event_id="evt_003",
            timestamp="2026-09-26T09:16:05Z",
            app="HubSpot CRM",
            action="update_customer_record",
            window_title="HubSpot CRM - Acme Corp",
            metadata={
                "customer_id": "1042",
                "customer_name": "Acme Corp",
                "field_updated": "invoice_status",
                "value": "Paid",
                "attached_document": "INV-1042_AcmeCorp.pdf",
            },
        ),
        UserEvent(
            event_id="evt_004",
            timestamp="2026-09-26T09:16:45Z",
            app="Slack",
            action="send_message",
            window_title="Slack - #billing-updates",
            metadata={
                "channel": "#billing-updates",
                "message": "Processed invoice INV-1042 for Acme Corp. CRM record updated.",
            },
        ),
    ]


def _make_detected_sequence():
    events = _make_sample_events()
    return DetectedSequence(
        pattern_id="pat_422ac018",
        signature="Gmail (Chrome):open_email -> Browser Download:download_file -> HubSpot CRM:update_customer_record -> Slack:send_message",
        steps_summary=[
            "Gmail: Open Email",
            "Browser Download: Download File",
            "HubSpot CRM: Update Customer Record",
            "Slack: Send Message",
        ],
        occurrence_count=3,
        confidence_score=0.95,
        sample_events=events,
        description="Repeated workflow detected (4 steps across 4 apps), occurring 3 times with 95% confidence.",
    )


# ---------------------------------------------------------------------------
# Test cases
# ---------------------------------------------------------------------------

class TestFallbackWorkflowGeneration(unittest.TestCase):
    """Test the deterministic fallback — no API key, no network."""

    def setUp(self):
        self.pattern = _make_detected_sequence()

    def test_fallback_returns_workflow_definition(self):
        wf = _build_fallback_workflow(self.pattern)
        self.assertIsInstance(wf, WorkflowDefinition)

    def test_fallback_schema_fields_present(self):
        """All required WorkflowDefinition fields must be populated."""
        wf = _build_fallback_workflow(self.pattern)
        self.assertTrue(wf.workflow_id.startswith("wf_"))
        self.assertIsInstance(wf.name, str)
        self.assertGreater(len(wf.name), 0)
        self.assertIsInstance(wf.intent_summary, str)
        self.assertGreater(len(wf.intent_summary), 0)
        self.assertIsInstance(wf.trigger_description, str)
        self.assertGreater(len(wf.trigger_description), 0)
        self.assertGreater(wf.estimated_time_saved_minutes, 0)
        self.assertEqual(wf.status, WorkflowStatus.PENDING_APPROVAL)
        self.assertIsInstance(wf.steps, list)

    def test_fallback_has_correct_step_count(self):
        """Must generate one step per detected event."""
        wf = _build_fallback_workflow(self.pattern)
        self.assertEqual(len(wf.steps), 4)

    def test_fallback_steps_schema(self):
        """Each step must have all required WorkflowStep fields."""
        wf = _build_fallback_workflow(self.pattern)
        for i, step in enumerate(wf.steps):
            self.assertIsInstance(step, WorkflowStep)
            self.assertIsNotNone(step.step_id)
            self.assertEqual(step.step_order, i + 1)
            self.assertIsInstance(step.app, str)
            self.assertIsInstance(step.action_type, str)
            self.assertIsInstance(step.title, str)
            self.assertIsInstance(step.description, str)
            self.assertIsInstance(step.parameters, dict)

    def test_fallback_infers_invoice_workflow_name(self):
        """For Gmail+Download+CRM+Slack, the name should reference invoice processing."""
        wf = _build_fallback_workflow(self.pattern)
        self.assertIn("Invoice", wf.name)

    def test_fallback_steps_have_parameters(self):
        """Key steps (email, download, crm, slack) must have non-empty parameters."""
        wf = _build_fallback_workflow(self.pattern)
        for step in wf.steps:
            self.assertGreater(len(step.parameters), 0, f"Step '{step.title}' has empty parameters")

    def test_fallback_slack_step_has_channel_param(self):
        """Slack step must include a channel parameter."""
        wf = _build_fallback_workflow(self.pattern)
        slack_step = next(s for s in wf.steps if "Slack" in s.app)
        self.assertIn("channel", slack_step.parameters)
        self.assertEqual(slack_step.parameters["channel"], "#billing-updates")

    def test_fallback_crm_step_has_field_param(self):
        """CRM step must include field and value parameters."""
        wf = _build_fallback_workflow(self.pattern)
        crm_step = next(s for s in wf.steps if "CRM" in s.app or "HubSpot" in s.app)
        self.assertIn("field", crm_step.parameters)
        self.assertIn("value", crm_step.parameters)


class TestLLMEngineWithMockedGemini(unittest.TestCase):
    """Test LLMWorkflowEngine using a mocked Gemini client — no real API call."""

    def setUp(self):
        self.pattern = _make_detected_sequence()
        self.engine = LLMWorkflowEngine()

    def test_uses_fallback_when_no_api_key(self):
        """Engine must fall back when GEMINI_API_KEY is empty."""
        with patch("backend.app.services.llm_engine.GEMINI_API_KEY", ""):
            wf = self.engine.synthesize_workflow(self.pattern)
        self.assertIsInstance(wf, WorkflowDefinition)
        self.assertEqual(len(wf.steps), 4)

    def test_falls_back_on_api_exception(self):
        """Engine must fall back when the Gemini API call raises an exception."""
        with patch("backend.app.services.llm_engine.GEMINI_API_KEY", "fake-api-key-xyz"):
            with patch.object(self.engine, "_call_gemini", side_effect=Exception("Network timeout")):
                wf = self.engine.synthesize_workflow(self.pattern)
        self.assertIsInstance(wf, WorkflowDefinition)
        self.assertEqual(len(wf.steps), 4)

    def test_uses_llm_result_when_api_key_present(self):
        """Engine should call _call_gemini when an API key is set (mock the result)."""
        mock_wf = _build_fallback_workflow(self.pattern)
        with patch("backend.app.services.llm_engine.GEMINI_API_KEY", "fake-api-key-xyz"):
            with patch.object(self.engine, "_call_gemini", return_value=mock_wf) as mock_call:
                wf = self.engine.synthesize_workflow(self.pattern)
                mock_call.assert_called_once_with(self.pattern)
        self.assertEqual(wf, mock_wf)


class TestBuildWorkflowFromDict(unittest.TestCase):
    """Test the _build_workflow_from_dict helper for LLM-parsed JSON."""

    def setUp(self):
        self.pattern = _make_detected_sequence()

    def _make_llm_response_dict(self):
        return {
            "name": "Process Customer Invoice",
            "intent_summary": "Automate invoice ingestion from email to CRM and Slack notification.",
            "trigger_description": "When a new invoice email with an attachment is received in Gmail.",
            "estimated_time_saved_minutes": 4.5,
            "steps": [
                {
                    "step_id": "step_01",
                    "step_order": 1,
                    "app": "Gmail (Chrome)",
                    "action_type": "open_email",
                    "title": "Gmail: Open Invoice Email",
                    "description": "Detect new invoice emails with attachments.",
                    "parameters": {"filter": "has_attachment:true"},
                    "editable": True,
                },
                {
                    "step_id": "step_02",
                    "step_order": 2,
                    "app": "Browser Download",
                    "action_type": "download_file",
                    "title": "Download Attachment",
                    "description": "Save the attached PDF to the downloads folder.",
                    "parameters": {"save_path": "{{download_directory}}"},
                    "editable": True,
                },
                {
                    "step_id": "step_03",
                    "step_order": 3,
                    "app": "HubSpot CRM",
                    "action_type": "update_customer_record",
                    "title": "CRM: Update Invoice Status",
                    "description": "Mark the invoice as Paid and attach the document.",
                    "parameters": {"field": "invoice_status", "value": "Paid"},
                    "editable": True,
                },
                {
                    "step_id": "step_04",
                    "step_order": 4,
                    "app": "Slack",
                    "action_type": "send_message",
                    "title": "Slack: Notify Billing Team",
                    "description": "Post a confirmation in #billing-updates.",
                    "parameters": {"channel": "#billing-updates"},
                    "editable": True,
                },
            ],
        }

    def test_builds_valid_workflow_from_dict(self):
        data = self._make_llm_response_dict()
        wf = _build_workflow_from_dict(data, self.pattern)
        self.assertIsInstance(wf, WorkflowDefinition)
        self.assertEqual(wf.name, "Process Customer Invoice")
        self.assertEqual(len(wf.steps), 4)
        self.assertAlmostEqual(wf.estimated_time_saved_minutes, 4.5)

    def test_steps_preserve_order(self):
        data = self._make_llm_response_dict()
        wf = _build_workflow_from_dict(data, self.pattern)
        for i, step in enumerate(wf.steps):
            self.assertEqual(step.step_order, i + 1)

    def test_step_parameters_preserved(self):
        data = self._make_llm_response_dict()
        wf = _build_workflow_from_dict(data, self.pattern)
        slack_step = wf.steps[3]
        self.assertEqual(slack_step.parameters.get("channel"), "#billing-updates")


class TestPromptGeneration(unittest.TestCase):
    """Test that the LLM prompt is constructed correctly."""

    def test_prompt_contains_event_apps(self):
        pattern = _make_detected_sequence()
        prompt = _make_prompt(pattern)
        self.assertIn("Gmail", prompt)
        self.assertIn("Browser Download", prompt)
        self.assertIn("HubSpot CRM", prompt)
        self.assertIn("Slack", prompt)

    def test_prompt_contains_occurrence_count(self):
        pattern = _make_detected_sequence()
        prompt = _make_prompt(pattern)
        self.assertIn("3", prompt)


class TestGenerateWorkflowAPIRoute(unittest.TestCase):
    """Test the POST /api/workflows/generate endpoint via direct function call."""

    def setUp(self):
        self.pattern = _make_detected_sequence()
        # Clear storage before each test
        storage_service._workflows.clear()

    def test_generate_endpoint_returns_workflow(self):
        from backend.app.api.routes_workflows import generate_workflow
        with patch("backend.app.services.llm_engine.GEMINI_API_KEY", ""):
            wf = generate_workflow(pattern=self.pattern)
        self.assertIsInstance(wf, WorkflowDefinition)
        self.assertEqual(wf.status, WorkflowStatus.PENDING_APPROVAL)

    def test_generate_endpoint_saves_to_storage(self):
        from backend.app.api.routes_workflows import generate_workflow
        with patch("backend.app.services.llm_engine.GEMINI_API_KEY", ""):
            wf = generate_workflow(pattern=self.pattern)
        stored = storage_service.get_workflow(wf.workflow_id)
        self.assertIsNotNone(stored)
        self.assertEqual(stored.workflow_id, wf.workflow_id)

    def test_generate_endpoint_step_count(self):
        from backend.app.api.routes_workflows import generate_workflow
        with patch("backend.app.services.llm_engine.GEMINI_API_KEY", ""):
            wf = generate_workflow(pattern=self.pattern)
        self.assertEqual(len(wf.steps), 4)


if __name__ == "__main__":
    unittest.main()
