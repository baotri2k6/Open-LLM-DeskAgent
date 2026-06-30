"""Phase 4 Integration Tests — kiểm tra World Model và Computer Use (OS execution) stack."""

import asyncio
import sys
from pathlib import Path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

PASS = 0
FAIL = 0


def test(name, fn):
    global PASS, FAIL
    try:
        fn()
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1


def test_async(name, coro_fn):
    global PASS, FAIL
    try:
        asyncio.get_event_loop().run_until_complete(coro_fn())
        print(f"  [PASS] {name}")
        PASS += 1
    except Exception as e:
        print(f"  [FAIL] {name}: {e}")
        FAIL += 1


# ── World Model ─────────────────────────────────────────────────────────────
print("\n=== World Model ===")

def t_window_tracker():
    from world.windows.window_tracker import window_tracker
    res = window_tracker.get_active_window()
    assert "title" in res
    assert "app" in res
test("WindowTracker — active window scanning", t_window_tracker)

def t_app_tracker():
    from world.applications.app_tracker import app_tracker
    apps = app_tracker.get_running_apps()
    assert isinstance(apps, list)
test("AppTracker — running applications scanning", t_app_tracker)

def t_activity_tracker():
    from world.activity.activity_tracker import activity_tracker
    act = activity_tracker.get_current_activity()
    assert "activity" in act
    assert "details" in act
test("ActivityTracker — user activity inference", t_activity_tracker)

def t_world_model():
    from world.world_model import world_model
    summary = world_model.get_summary()
    assert isinstance(summary, str)
    assert len(summary) > 5
test("WorldModel — state description aggregation", t_world_model)


# ── Computer Use (OS Execution) ──────────────────────────────────────────────
print("\n=== Computer Use (OS Execution) ===")

def t_mouse_controller():
    from execution.mouse.mouse_controller import mouse_controller
    # Validation checks
    x, y = mouse_controller.validate_coordinates("100", 200)
    assert x == 100
    assert y == 200
test("MouseController — coordinates validation", t_mouse_controller)

def t_keyboard_controller():
    from execution.keyboard.keyboard_controller import keyboard_controller
    assert keyboard_controller is not None
test("KeyboardController — importable", t_keyboard_controller)

async def t_terminal_executor():
    from config.config import config
    from execution.terminal.terminal_executor import terminal_executor
    
    # Save original setting
    original = config.get("agent.autoMode", False)
    config.set("agent.autoMode", True)
    
    try:
        # Run safe command (like dir or echo) which bypasses approval or auto-approves
        res = await terminal_executor.execute("echo 'hello world'")
        assert res["success"]
        assert "hello" in res["stdout"].lower()
    finally:
        # Restore setting
        config.set("agent.autoMode", original)

test_async("TerminalExecutor — safe command execution", t_terminal_executor)

def t_action_verifier():
    from execution.verifier.action_verifier import action_verifier
    r1 = action_verifier.verify_command_success({"success": True, "returncode": 0})
    assert r1["verified"]
    
    r2 = action_verifier.verify_command_success({"success": False, "returncode": 1, "stderr": "Error"})
    assert not r2["verified"]
test("ActionVerifier — command completion validation", t_action_verifier)


# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n{'='*50}")
print(f"Results: {PASS} PASS / {FAIL} FAIL / {PASS+FAIL} TOTAL")
if FAIL == 0:
    print("ALL TESTS PASSED! Phase 4 stack verified successfully.")
else:
    print(f"WARNING: {FAIL} tests failed. Review above.")
