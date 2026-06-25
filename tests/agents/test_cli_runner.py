import sys
import unittest
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.agents.planner_agent import PlannerAgent

class TestPlannerAgent(unittest.TestCase):
    def test_planner_agent_initialization(self):
        """Verify that PlannerAgent can be initialized and possesses standard sub-agents."""
        planner = PlannerAgent()
        self.assertIsNotNone(planner)
        self.assertIsNotNone(planner.llm)
        self.assertIsNotNone(planner.memory)
        self.assertIsNotNone(planner.system)
        self.assertIsNotNone(planner.browser)
        self.assertIsNotNone(planner.vision)

    def test_intent_detection(self):
        """Verify basic intent detection works as expected."""
        planner = PlannerAgent()
        
        # Test time intent
        time_intent = planner.detect_intent("bây giờ là mấy giờ rồi nhỉ?")
        self.assertEqual(time_intent["name"], "time")
        
        # Test remember intent
        remember_intent = planner.detect_intent("ghi nhớ là ngày mai tớ đi siêu thị")
        self.assertEqual(remember_intent["name"], "remember")
        self.assertEqual(remember_intent["value"], "ngày mai tớ đi siêu thị")

if __name__ == "__main__":
    unittest.main()
