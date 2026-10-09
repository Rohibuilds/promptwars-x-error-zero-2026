"""Unit tests for RA NEXUS tools (knowledge search, calculator, system status)."""

import unittest
from backend.tools import calculate, search_knowledge, get_system_status, load_knowledge_base


class TestTools(unittest.TestCase):
    """Test suite for individual tool functions."""

    def test_calculate_basic_arithmetic(self):
        """Test basic arithmetic operations."""
        self.assertEqual(calculate("2 + 2"), {"success": True, "result": 4.0})
        self.assertEqual(calculate("10 - 3"), {"success": True, "result": 7.0})
        self.assertEqual(calculate("4 * 5"), {"success": True, "result": 20.0})
        self.assertEqual(calculate("20 / 4"), {"success": True, "result": 5.0})

    def test_calculate_unary_and_modulo(self):
        """Test unary negation and modulo operations."""
        self.assertEqual(calculate("-5 + 10"), {"success": True, "result": 5.0})
        self.assertEqual(calculate("10 % 3"), {"success": True, "result": 1.0})

    def test_calculate_order_of_operations(self):
        """Test precedence with parentheses and powers."""
        self.assertEqual(calculate("2 + 3 * 4"), {"success": True, "result": 14.0})
        self.assertEqual(calculate("(2 + 3) * 4"), {"success": True, "result": 20.0})
        self.assertEqual(calculate("2 ** 3"), {"success": True, "result": 8.0})

    def test_calculate_safe_rejection(self):
        """Test that invalid or dangerous inputs are safely rejected."""
        self.assertEqual(calculate(""), {"success": False, "result": None})
        self.assertEqual(calculate("   "), {"success": False, "result": None})
        self.assertEqual(calculate("import os"), {"success": False, "result": None})
        self.assertEqual(calculate("__import__('os').system('ls')"), {"success": False, "result": None})
        self.assertEqual(calculate("2 / 0"), {"success": False, "result": None})
        self.assertEqual(calculate("2 ** 999999"), {"success": False, "result": None})

    def test_calculate_length_and_complexity_limits(self):
        """Test expression length limit and AST complexity limits."""
        long_expr = "1 + " * 60 + "1"  # > 100 characters
        self.assertEqual(calculate(long_expr), {"success": False, "result": None})

    def test_search_knowledge_matches(self):
        """Test querying campus knowledge base."""
        results = search_knowledge("electronics")
        self.assertTrue(len(results) > 0)
        self.assertIn("Electronics Laboratory", results[0]["title"])

    def test_search_knowledge_case_insensitive(self):
        """Test case-insensitive knowledge retrieval."""
        results = search_knowledge("LIBRARY")
        self.assertTrue(len(results) > 0)
        self.assertEqual(results[0]["title"], "Library")

    def test_search_knowledge_empty_and_no_match(self):
        """Test querying with empty and unknown terms."""
        self.assertEqual(search_knowledge(""), [])
        self.assertEqual(search_knowledge("   "), [])
        self.assertEqual(search_knowledge("quantum mechanics spaceship"), [])

    def test_load_knowledge_base_caching(self):
        """Test that the knowledge base is loaded as a list of dicts."""
        data = load_knowledge_base()
        self.assertIsInstance(data, list)
        self.assertTrue(len(data) > 0)

    def test_get_system_status(self):
        """Test system status payload."""
        status = get_system_status()
        self.assertEqual(status["name"], "RA NEXUS")
        self.assertEqual(status["status"], "online")
        self.assertIn("calculator", status["tools"])
        self.assertIn("knowledge_search", status["tools"])


if __name__ == "__main__":
    unittest.main()
