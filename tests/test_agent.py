"""Unit tests for the RA NEXUS agent routing and response formatting."""

import unittest
from backend.agent import run_agent, extract_expression, format_result


class TestAgent(unittest.TestCase):
    """Test suite for agent intent recognition and response generation."""

    def test_status_intent(self):
        """Test asking for system status."""
        response = run_agent("What is your system status?")
        self.assertEqual(response["type"], "system_status")
        self.assertEqual(response["status"], "completed")
        self.assertIn("online", response["response"].lower())

    def test_calculator_intent(self):
        """Test mathematical expressions routed to calculator."""
        response = run_agent("Calculate 25 plus 17")
        self.assertEqual(response["type"], "calculator")
        self.assertEqual(response["status"], "completed")
        self.assertIn("42", response["response"])

    def test_knowledge_intent(self):
        """Test campus queries routed to knowledge search."""
        response = run_agent("Where is the computer laboratory located?")
        self.assertEqual(response["type"], "knowledge")
        self.assertEqual(response["status"], "completed")
        self.assertIn("Block B", response["response"])

    def test_general_chat_intent(self):
        """Test unrouted queries fallback to general agent response."""
        response = run_agent("Hello there")
        self.assertEqual(response["type"], "chat")
        self.assertEqual(response["status"], "completed")
        self.assertIn("RA NEXUS", response["response"])

    def test_extract_expression(self):
        """Test natural language to math expression conversion."""
        self.assertEqual(extract_expression("Calculate 10 plus 5"), "10 + 5")
        self.assertEqual(extract_expression("What is 12 times 3?"), "12 * 3")
        self.assertEqual(extract_expression("Solve 20 divided by 4"), "20 / 4")

    def test_format_result(self):
        """Test formatting of knowledge item dictionary."""
        sample_item = {
            "title": "Robotics Lab",
            "location": "Block C, Ground Floor",
            "description": "Lab for autonomous robotics",
            "equipment": ["Robotic Arms", "Sensors"],
            "timings": "10:00 AM to 5:00 PM"
        }
        formatted = format_result(sample_item)
        self.assertIn("Robotics Lab", formatted)
        self.assertIn("Block C, Ground Floor", formatted)
        self.assertIn("Robotic Arms", formatted)
        self.assertIn("10:00 AM to 5:00 PM", formatted)


if __name__ == "__main__":
    unittest.main()
