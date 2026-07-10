from __future__ import annotations

import json
import pytest
from pathlib import Path
from execution.verifier.action_verifier import action_verifier


def test_get_auto_verify_command_python_with_tests(tmp_path):
    # Setup mock tests dir
    tests_dir = tmp_path / "tests"
    tests_dir.mkdir()
    
    cmd = action_verifier.get_auto_verify_command(str(tmp_path), ["src/main.py"])
    assert cmd == "python -m pytest"


def test_get_auto_verify_command_python_without_tests(tmp_path):
    cmd = action_verifier.get_auto_verify_command(str(tmp_path), ["src/main.py", "src/helper.py"])
    assert cmd == "python -m py_compile src/main.py src/helper.py"


def test_get_auto_verify_command_js_with_package_json(tmp_path):
    # package.json with test script
    pkg = {
        "scripts": {
            "test": "jest"
        }
    }
    with open(tmp_path / "package.json", "w", encoding="utf-8") as f:
        json.dump(pkg, f)
        
    cmd = action_verifier.get_auto_verify_command(str(tmp_path), ["renderer/app.js"])
    assert cmd == "npm test"


def test_get_auto_verify_command_js_with_pnpm(tmp_path):
    # package.json and pnpm-lock.yaml
    pkg = {
        "scripts": {
            "test": "jest"
        }
    }
    with open(tmp_path / "package.json", "w", encoding="utf-8") as f:
        json.dump(pkg, f)
    with open(tmp_path / "pnpm-lock.yaml", "w", encoding="utf-8") as f:
        f.write("")
        
    cmd = action_verifier.get_auto_verify_command(str(tmp_path), ["renderer/app.js"])
    assert cmd == "pnpm test"


def test_get_auto_verify_command_ts_tsconfig(tmp_path):
    # tsconfig.json present
    with open(tmp_path / "tsconfig.json", "w", encoding="utf-8") as f:
        f.write("{}")
        
    cmd = action_verifier.get_auto_verify_command(str(tmp_path), ["renderer/app.ts"])
    assert cmd == "npx tsc --noEmit"


def test_get_auto_verify_command_js_fallback(tmp_path):
    cmd = action_verifier.get_auto_verify_command(str(tmp_path), ["renderer/app.js"])
    assert cmd == "node --check renderer/app.js"
