#!/usr/bin/env python
"""
Batch Runner.
Runs multiple SWE tasks in sequence or parallel and reports status.
"""

from __future__ import annotations

import sys
import json
from pathlib import Path
import asyncio

# Ensure project root is in path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from runtime.mini_swe_runner import run_swe_task
from runtime.logger import get_logger

logger = get_logger("ai-companion.batch-runner")

async def run_batch_tasks(tasks_file: str, target_dir: str):
    """Load tasks from a JSON file and run them in sequence."""
    tasks_path = Path(tasks_file)
    if not tasks_path.exists():
        print(f"Tasks file not found: {tasks_file}")
        return
        
    with open(tasks_path, "r", encoding="utf-8") as f:
        tasks = json.load(f)
        
    print(f"\n[Batch-Runner] Starting batch of {len(tasks)} tasks on {target_dir}")
    print("====================================================")
    
    results = {}
    for i, task in enumerate(tasks, 1):
        task_id = task.get("id", f"task_{i}")
        description = task.get("description", "")
        print(f"\n[Batch-Runner] Running Task {i}/{len(tasks)}: {task_id}")
        
        success = await run_swe_task(description, target_dir)
        results[task_id] = "SUCCESS" if success else "FAILED"
        
    print("\n====================================================")
    print("                  Batch Results Summary              ")
    print("====================================================")
    for tid, status in results.items():
        print(f"Task {tid}: {status}")
    print("====================================================")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python batch_runner.py <tasks_json_file> <target_directory>")
        print("Example JSON format:")
        print("[\n  { \"id\": \"fix_math\", \"description\": \"Fix sum calculation in calculator.py\" }\n]")
        sys.exit(1)
        
    tfile = sys.argv[1]
    tdir = sys.argv[2]
    
    asyncio.run(run_batch_tasks(tfile, tdir))
