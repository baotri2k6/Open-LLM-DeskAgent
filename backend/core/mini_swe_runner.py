#!/usr/bin/env python
"""
Mini SWE (Software Engineering) Runner.
An autonomous agent loop that takes a coding task, reads target files,
attempts to implement the fix, runs tests, and iterates if there are test failures.
"""

from __future__ import annotations

import os
import sys
import json
import subprocess
from pathlib import Path
import asyncio

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from backend.services.llm_service import LLMService
from backend.core.logger import get_logger

logger = get_logger("ai-companion.swe-runner")

def scan_files(directory: str) -> list[str]:
    """Scan directory recursively, ignoring common build and git folders."""
    ignore_dirs = {".git", "node_modules", "venv", "__pycache__", "build", "dist", ".gradle", ".idea"}
    file_list = []
    
    for root, dirs, files in os.walk(directory):
        # Modify dirs in-place to skip ignored directories
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            # Skip common binary/unwanted extensions
            if f.endswith((".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bin", ".zip", ".tar.gz", ".lock")):
                continue
            full_path = Path(root) / f
            file_list.append(str(full_path.relative_to(directory)))
            
    return file_list

async def run_swe_task(problem_description: str, target_dir: str, max_iterations: int = 3) -> bool:
    """Runs the SWE loop to solve a problem in target_dir."""
    print(f"\n[SWE-Runner] Starting task in target directory: {target_dir}")
    print(f"[SWE-Runner] Problem: {problem_description}")
    
    llm = LLMService()
    target_path = Path(target_dir).resolve()
    
    for iteration in range(1, max_iterations + 1):
        print(f"\n--- Iteration {iteration} / {max_iterations} ---")
        
        # Step 1: Scan and list files
        files = scan_files(str(target_path))
        print(f"[SWE-Runner] Scanned {len(files)} files.")
        
        # Step 2: Choose files to read
        files_prompt = (
            f"You are a Software Engineering agent. We have a coding task:\n"
            f"Task: {problem_description}\n\n"
            f"Here is the list of files in the project:\n"
            f"{json.dumps(files, indent=2)}\n\n"
            f"Please identify which files are relevant to read to understand and fix this issue.\n"
            f"Respond ONLY with a JSON list of strings representing the relative file paths, e.g., [\"src/main.py\"]."
        )
        
        try:
            chosen_files_str = await llm.chat(files_prompt)
            # Simple JSON cleanup in case of markdown blocks
            if "```" in chosen_files_str:
                chosen_files_str = chosen_files_str.split("```")[1]
                if chosen_files_str.startswith("json"):
                    chosen_files_str = chosen_files_str[4:]
            chosen_files = json.loads(chosen_files_str.strip())
            print(f"[SWE-Runner] Selected files to read: {chosen_files}")
        except Exception as e:
            logger.warning(f"Failed to parse chosen files JSON, falling back to all python files: {e}")
            chosen_files = [f for f in files if f.endswith(".py")]
            
        # Step 3: Read file contents
        code_context = {}
        for rel_path in chosen_files:
            file_path = target_path / rel_path
            if file_path.exists():
                with open(file_path, "r", encoding="utf-8") as f:
                    code_context[rel_path] = f.read()
                    
        # Step 4: Ask LLM for the fix
        fix_prompt = (
            f"You are an autonomous SWE agent. Implement a fix for the following task:\n"
            f"Task: {problem_description}\n\n"
            f"Here are the contents of the relevant files:\n"
        )
        for rel_path, content in code_context.items():
            fix_prompt += f"--- FILE: {rel_path} ---\n{content}\n\n"
            
        fix_prompt += (
            f"Please write the modifications required. Return a JSON object with a single 'files' key, "
            f"which contains a list of objects with 'path' and 'content' (the complete new content for the file).\n"
            f"Example format:\n"
            f"{{\n"
            f"  \"files\": [\n"
            f"    {{\n"
            f"      \"path\": \"src/main.py\",\n"
            f"      \"content\": \"...\"\n"
            f"    }}\n"
            f"  ]\n"
            f"}}\n"
            f"Respond ONLY with the JSON object."
        )
        
        try:
            fix_response_str = await llm.chat(fix_prompt)
            if "```" in fix_response_str:
                fix_response_str = fix_response_str.split("```")[1]
                if fix_response_str.startswith("json"):
                    fix_response_str = fix_response_str[4:]
            fix_data = json.loads(fix_response_str.strip())
            
            # Step 5: Write fixes to disk
            for file_edit in fix_data.get("files", []):
                edit_path = target_path / file_edit["path"]
                edit_path.parent.mkdir(parents=True, exist_ok=True)
                with open(edit_path, "w", encoding="utf-8") as f:
                    f.write(file_edit["content"])
                print(f"[SWE-Runner] Wrote fix to: {file_edit['path']}")
        except Exception as e:
            print(f"[SWE-Runner] Failed to apply fix: {e}")
            continue
            
        # Step 6: Run tests
        print("[SWE-Runner] Running pytest tests to verify...")
        test_res = subprocess.run(
            [sys.executable, "-m", "pytest", str(target_path)],
            capture_output=True,
            text=True
        )
        
        if test_res.returncode == 0:
            print("[SWE-Runner] SUCCESS! All tests passed.")
            return True
        else:
            print("[SWE-Runner] Test failures detected!")
            print(test_res.stdout)
            print(test_res.stderr)
            # The test error will be fed back in the next iteration
            problem_description = (
                f"{problem_description}\n\n"
                f"Previous implementation attempt failed. Test stdout:\n{test_res.stdout}\n"
                f"Test stderr:\n{test_res.stderr}"
            )
            
    print("\n[SWE-Runner] Failed to resolve the task after maximum iterations.")
    return False

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python mini_swe_runner.py <problem_description> <target_directory>")
        sys.exit(1)
        
    desc = sys.argv[1]
    tdir = sys.argv[2]
    
    asyncio.run(run_swe_task(desc, tdir))
