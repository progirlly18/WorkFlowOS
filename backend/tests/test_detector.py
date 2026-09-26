import os
import json
import unittest
from backend.app.models.event import UserEvent
from backend.app.services.detector import detector_service, _calculate_confidence
from backend.app.services.observer import observer_service
from backend.app.main import app


class TestPatternDetector(unittest.TestCase):
    def setUp(self):
        scenario_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "demo_scenarios", "gmail_crm_slack.json"
        )
        with open(scenario_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        self.demo_events = [UserEvent(**item) for item in data["events"]]

    def test_detect_demo_scenario_repetition(self):
        """Test detection on the 12-event Gmail -> Download -> CRM -> Slack stream."""
        patterns = detector_service.detect_patterns(self.demo_events)
        
        self.assertGreaterEqual(len(patterns), 1)
        top = patterns[0]
        
        # Must detect exactly 3 occurrences
        self.assertEqual(top.occurrence_count, 3)
        
        # Must detect a 4-step sequence
        self.assertEqual(len(top.steps_summary), 4)
        
        # Verify the sequence steps match the target flow
        expected_apps = ["Gmail", "Browser Download", "HubSpot CRM", "Slack"]
        for expected_app, step_title in zip(expected_apps, top.steps_summary):
            self.assertIn(expected_app, step_title)
            
        # Verify confidence score calculation
        self.assertGreaterEqual(top.confidence_score, 0.90)
        self.assertLessEqual(top.confidence_score, 1.0)
        
        # Verify sample events are attached
        self.assertEqual(len(top.sample_events), 4)
        self.assertEqual(top.sample_events[0].app, "Gmail (Chrome)")
        self.assertEqual(top.sample_events[1].action, "download_file")
        self.assertEqual(top.sample_events[2].app, "HubSpot CRM")
        self.assertEqual(top.sample_events[3].action, "send_message")

    def test_empty_events_list(self):
        """Empty event list should return no patterns."""
        patterns = detector_service.detect_patterns([])
        self.assertEqual(patterns, [])

    def test_single_occurrence_ignored(self):
        """A sequence occurring only once should not be flagged as a repeated pattern."""
        single_flow = self.demo_events[:4]
        patterns = detector_service.detect_patterns(single_flow, min_occurrences=2)
        self.assertEqual(patterns, [])

    def test_confidence_scoring(self):
        """Verify confidence scoring logic."""
        self.assertLess(_calculate_confidence(1, 4), 0.50)
        self.assertGreaterEqual(_calculate_confidence(2, 4), 0.80)
        self.assertGreaterEqual(_calculate_confidence(3, 4), 0.90)
        self.assertGreaterEqual(_calculate_confidence(5, 4), 0.95)

    def test_api_workflow_detect_endpoint(self):
        """Verify API integration through routes_workflows router."""
        try:
            from fastapi.testclient import TestClient
            client = TestClient(app)
            response = client.get("/api/workflows/detect?auto_load_demo=true")
            self.assertEqual(response.status_code, 200)
            data = response.json()
            self.assertIsInstance(data, list)
            self.assertGreaterEqual(len(data), 1)
            self.assertEqual(data[0]["occurrence_count"], 3)
            self.assertEqual(len(data[0]["steps_summary"]), 4)
        except (RuntimeError, ImportError):
            from backend.app.api.routes_workflows import detect_repeated_patterns
            observer_service.clear_events()
            patterns = detect_repeated_patterns(auto_load_demo=True)
            self.assertGreaterEqual(len(patterns), 1)
            self.assertEqual(patterns[0].occurrence_count, 3)
            self.assertEqual(len(patterns[0].steps_summary), 4)


if __name__ == "__main__":
    unittest.main()
