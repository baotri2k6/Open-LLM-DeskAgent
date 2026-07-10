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
import shlex
from pathlib import Path
import asyncio

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from llm.manager import LLMService
from runtime.logger import get_logger
from tools.file_edit import create_file, str_replace_file
from tools.view_file import view_file
from execution.sandbox.sandbox_runner import SandboxPolicy, SandboxRunner

logger = get_logger("ai-companion.swe-runner")


def _extract_json_object(text: str) -> dict:
    candidate = text.strip()
    if "```" in candidate:
        candidate = candidate.split("```")[1]
        if candidate.startswith("json"):
            candidate = candidate[4:]
    return json.loads(candidate.strip())


def _resolve_target(root: Path, rel_path: str) -> Path:
    root_path = root.resolve()
    target = (root_path / rel_path).resolve()
    if root_path != target and root_path not in target.parents:
        raise ValueError(f"Path escapes target directory: {rel_path}")
    return target

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
    command_runner = SandboxRunner(SandboxPolicy(root=target_path))
    
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
            
        # Step 3: Read file contents with line numbers
        code_context = {}
        for rel_path in chosen_files:
            file_path = target_path / rel_path
            if file_path.exists():
                viewed = view_file(str(file_path))
                if viewed.get("success"):
                    code_context[rel_path] = viewed["text"]
                    
        # Step 4: Ask LLM for the fix
        fix_prompt = (
            f"You are an autonomous SWE agent. Implement a fix for the following task:\n"
            f"Task: {problem_description}\n\n"
            f"Here are the contents of the relevant files:\n"
        )
        for rel_path, content in code_context.items():
            fix_prompt += f"--- FILE: {rel_path} ---\n{content}\n\n"
            
        fix_prompt += (
            f"Please write the modifications required as precise patch operations. Return a JSON object "
            f"with a single 'operations' key. Use op='replace' with path, old_str, new_str for existing files; "
            f"use op='create' with path and content only for new files. old_str must be copied verbatim "
            f"from the file and appear exactly once. Do not return complete rewritten file contents.\n"
            f"If file context includes line numbers like '  123 | ', do not include that prefix in old_str.\n"
            f"Example format:\n"
            f"{{\n"
            f"  \"operations\": [\n"
            f"    {{\"op\": \"replace\", \"path\": \"src/main.py\", \"old_str\": \"old\", \"new_str\": \"new\"}},\n"
            f"    {{\"op\": \"create\", \"path\": \"src/new.py\", \"content\": \"...\"}}\n"
            f"  ]\n"
            f"}}\n"
            f"Respond ONLY with the JSON object."
        )
        
        try:
            fix_response_str = await llm.chat(fix_prompt)
            fix_data = _extract_json_object(fix_response_str)
            
            # Step 5: Apply precise patch operations
            for operation in fix_data.get("operations", []):
                rel_path = operation["path"]
                edit_path = _resolve_target(target_path, rel_path)
                if operation.get("op") == "replace":
                    result = str_replace_file(str(edit_path), operation.get("old_str", ""), operation.get("new_str", ""))
                elif operation.get("op") == "create":
                    result = create_file(str(edit_path), operation.get("content", ""))
                else:
                    result = {"success": False, "error": f"Unsupported operation: {operation.get('op')}"}

                if not result.get("success"):
                    raise RuntimeError(result.get("error", "Failed to apply patch"))
                print(f"[SWE-Runner] Applied patch to: {rel_path}")
        except Exception as e:
            print(f"[SWE-Runner] Failed to apply fix: {e}")
            continue
            
        # Step 6: Run tests
        print("[SWE-Runner] Running pytest tests to verify...")
        test_res = await command_runner.run(
            f"{sys.executable} -m pytest {shlex.quote(str(target_path))}",
            cwd=target_path,
            timeout=60.0,
            allow_unlisted=True,
        )
        
        if test_res.get("success"):
            print("[SWE-Runner] SUCCESS! All tests passed.")
            return True
        else:
            print("[SWE-Runner] Test failures detected!")
            print(test_res.get("stdout", ""))
            print(test_res.get("stderr", ""))
            # The test error will be fed back in the next iteration
            problem_description = (
                f"{problem_description}\n\n"
                f"Previous implementation attempt failed. Test stdout:\n{test_res.get('stdout', '')}\n"
                f"Test stderr:\n{test_res.get('stderr', test_res.get('error', ''))}"
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
