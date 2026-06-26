import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from agents.planner.planner_agent import PlannerAgent

def test_intents():
    # Mock resources for PlannerAgent
    class MockResource:
        pass
        
    planner = PlannerAgent(
        llm_service=MockResource(),
        memory_agent=MockResource(),
        system_service=MockResource(),
        browser_agent=MockResource(),
        vision_agent=MockResource()
    )
    
    test_cases = [
        ("thông số máy tính", "system_info"),
        ("cpu và ram hiện tại", "system_info"),
        ("1 phút nữa tắt máy tính", "llm_chat"),
        ("tắt máy tính giúp tớ", "llm_chat"),
        ("khởi động lại máy tính", "llm_chat"),
        ("hủy hẹn giờ tắt máy", "llm_chat"),
        ("mở google chrome", "open_app"),
    ]
    
    print("Running PlannerAgent intent routing tests...")
    success = True
    for text, expected in test_cases:
        res = planner.detect_intent(text)
        actual = res["name"]
        print(f"Input: '{text}' -> Detected: '{actual}' (Expected: '{expected}')")
        if actual != expected:
            print("  FAIL!")
            success = False
        else:
            print("  OK")
            
    if success:
        print("\nAll tests PASSED!")
    else:
        print("\nSome tests FAILED!")

if __name__ == "__main__":
    test_intents()
