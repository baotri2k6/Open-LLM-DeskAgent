"""CodingAgent — Autonomous coding agent theo kiểu Claude Code / Codex.

Nhận một yêu cầu bằng ngôn ngữ tự nhiên → tự đọc codebase → hiểu vấn đề
→ viết/sửa code → chạy verify → tự sửa nếu fail → báo cáo kết quả.

Không cần UI. Không cần mở Coding Console. Chỉ cần nói với IceGirl.

Thiết kế theo nguyên tắc:
  - Context-first: đọc đúng file, không đọc toàn bộ
  - Tool-native: dùng đúng tools đã có (terminal_executor, file tools)
  - Self-correcting: tự phân tích lỗi và retry tối đa MAX_ITER lần
  - Transparent: mọi bước đều emit event để frontend hiển thị
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import AsyncIterator, Optional
from planning.task_graph.task_plan import TaskPlan, TaskPlanStep

logger = logging.getLogger("ai-companion.agents.coding")

# ── Cấu hình ─────────────────────────────────────────────────────────────────

MAX_ITER        = 5       # Tối đa bao nhiêu vòng sửa lỗi
MAX_FILES_READ  = 12      # Tối đa bao nhiêu file đọc trong 1 lần
MAX_FILE_LINES  = 400     # Tối đa bao nhiêu dòng đọc mỗi file
VERIFY_TIMEOUT  = 60      # Timeout chạy lệnh verify (giây)

IGNORE_DIRS = {
    ".git", "node_modules", "venv", "__pycache__",
    "build", "dist", ".gradle", ".idea", ".agents",
    "assets", "vendor", "live2d",
}
IGNORE_EXTS = {
    ".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".bin", ".zip", ".tar.gz", ".lock", ".db", ".mp3",
    ".wav", ".mp4", ".avi",
}


# ── Data classes ──────────────────────────────────────────────────────────────

@dataclass
class CodingStep:
    """Một bước trong quá trình coding agent."""
    step:    str            # "read" | "plan" | "edit" | "run" | "verify" | "done" | "error"
    message: str
    detail:  str = ""
    success: Optional[bool] = None


@dataclass
class CodingResult:
    """Kết quả sau khi coding agent hoàn thành."""
    success:       bool
    summary:       str
    files_changed: list[str] = field(default_factory=list)
    steps:         list[CodingStep] = field(default_factory=list)
    iterations:    int = 0
    error:         str = ""


# ── Utilities ─────────────────────────────────────────────────────────────────

def _scan_project(root: str) -> list[str]:
    """Quét project, trả về danh sách file relative path."""
    result = []
    root_path = Path(root)
    for dirpath, dirs, files in os.walk(root):
        dirs[:] = [d for d in dirs if d not in IGNORE_DIRS]
        for f in files:
            if any(f.endswith(ext) for ext in IGNORE_EXTS):
                continue
            try:
                rel = str(Path(dirpath, f).relative_to(root_path))
                result.append(rel)
            except ValueError:
                pass
    return sorted(result)


def _read_file_safe(root: str, rel_path: str, max_lines: int = MAX_FILE_LINES) -> str:
    """Đọc file an toàn, giới hạn số dòng."""
    try:
        full = Path(root) / rel_path
        lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
        if len(lines) > max_lines:
            half = max_lines // 2
            truncated = lines[:half] + [f"\n... [{len(lines) - max_lines} dòng bị cắt] ...\n"] + lines[-half:]
            return "\n".join(truncated)
        return "\n".join(lines)
    except Exception as e:
        return f"[Không đọc được: {e}]"


def _extract_code_blocks(text: str) -> list[tuple[str, str]]:
    """Trích xuất code blocks từ LLM response.

    Returns:
        List of (filename, code) tuples.
    """
    pattern = r"```(?:python|javascript|js|typescript|ts|json|yaml|html|css)?\s*\n?(?:#\s*file:\s*(.+?)\n)?(.*?)```"
    matches = re.findall(pattern, text, re.DOTALL | re.IGNORECASE)

    result = []
    for filename, code in matches:
        filename = filename.strip()
        code = code.strip()
        if code:
            result.append((filename, code))
    return result


def _extract_json_object(text: str) -> dict:
    """Extract a JSON object from raw LLM text, including fenced blocks."""
    candidate = text.strip()
    if "```" in candidate:
        blocks = re.findall(r"```(?:json)?\s*(.*?)```", candidate, re.DOTALL | re.IGNORECASE)
        for block in blocks:
            try:
                return json.loads(block.strip())
            except json.JSONDecodeError:
                continue

    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(candidate[start:end + 1])
        raise


def _apply_file_operation(root: str, operation: dict) -> dict:
    """Apply one create/replace file operation inside the project root."""
    op = str(operation.get("op", "")).strip()
    rel_path = str(operation.get("path", "")).replace("\\", "/").lstrip("/")
    if not rel_path:
        return {"success": False, "error": "Missing path"}

    root_path = Path(root).resolve()
    target = (root_path / rel_path).resolve()
    if root_path != target and root_path not in target.parents:
        return {"success": False, "error": f"Path escapes project root: {rel_path}"}

    if op == "replace":
        from tools.file_edit import str_replace_file
        return str_replace_file(
            str(target),
            str(operation.get("old_str", "")),
            str(operation.get("new_str", "")),
        )
    if op == "create":
        from tools.file_edit import create_file
        return create_file(str(target), str(operation.get("content", "")))
    return {"success": False, "error": f"Unsupported operation: {op}"}


# ── Core CodingAgent ──────────────────────────────────────────────────────────

class CodingAgent:
    """Autonomous coding agent — đọc, hiểu, sửa, verify.

    Usage:
        agent = CodingAgent(project_root="/path/to/project")
        async for step in agent.run("fix the lipsync bug"):
            print(step.message)
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        llm_service=None,
    ) -> None:
        from config.config import PROJECT_ROOT
        self._root = str(project_root or PROJECT_ROOT)
        self._llm  = llm_service
        self._steps: list[CodingStep] = []
        self.task_plan: Optional[TaskPlan] = None

    def _update_step_status(self, step_id_or_index: str | int, status: str) -> None:
        """Cập nhật trạng thái của một bước trong TaskPlan và emit event."""
        if not self.task_plan:
            return

        step = None
        step_idx = -1
        if isinstance(step_id_or_index, int):
            if 0 <= step_id_or_index < len(self.task_plan.steps):
                step = self.task_plan.steps[step_id_or_index]
                step_idx = step_id_or_index
        else:
            for idx, s in enumerate(self.task_plan.steps):
                if s.id == step_id_or_index:
                    step = s
                    step_idx = idx
                    break

        if not step or step.status == status:
            return

        step.status = status
        logger.info("TaskPlan step %d (%s) -> %s", step_idx, step.id, status)

        try:
            from runtime.eventbus.event_bus import event_bus
            from runtime.events.base_event import BaseEvent
            from runtime.events.event_types import EventType
            
            if status == "in_progress":
                event_type = EventType.PLAN_STEP_STARTED
            else:
                event_type = EventType.PLAN_STEP_FINISHED
                
            event_bus.publish(BaseEvent.create(
                event_type=event_type,
                source="coding_agent",
                payload={
                    "task_id": self.task_plan.task_id,
                    "step_index": step_idx,
                    "step_id": step.id,
                    "description": step.description,
                    "status": status,
                    "success": status == "done"
                }
            ))
        except Exception as e:
            logger.error("Failed to publish step update: %s", e)

    def _get_llm(self):
        if self._llm is None:
            from llm.manager import LLMService
            self._llm = LLMService()
        return self._llm

    async def _run_command(self, command: str) -> tuple[bool, str]:
        """Chạy lệnh terminal, trả về (success, output)."""
        try:
            from execution.terminal.terminal_executor import terminal_executor
            result = await terminal_executor.execute(command, timeout=VERIFY_TIMEOUT)
            output = result.get("stdout", "") + result.get("stderr", "")
            return result.get("success", False), output.strip()
        except Exception as e:
            return False, str(e)

    async def _ask_llm(self, prompt: str, max_tokens: int = 4096) -> str:
        """Gọi LLM, trả về text."""
        try:
            llm = self._get_llm()
            response = await llm.chat_async(prompt)
            return response or ""
        except Exception as e:
            logger.error("LLM error: %s", e)
            return ""

    # ── Step 1: Chọn file liên quan ──────────────────────────────────────────

    async def _select_relevant_files(
        self,
        task: str,
        all_files: list[str],
    ) -> list[str]:
        """Hỏi LLM file nào liên quan đến task."""

        file_list = "\n".join(f"  - {f}" for f in all_files[:200])  # Giới hạn để không vượt token

        prompt = f"""Đây là danh sách file trong dự án:
{file_list}

Task: {task}

Liệt kê tối đa {MAX_FILES_READ} file LIÊN QUAN NHẤT đến task trên.
Chỉ trả về danh sách file, mỗi file một dòng, không giải thích.
Ví dụ:
backend/life/life_loop.py
backend/persona/mood/mood_engine.py
"""
        response = await self._ask_llm(prompt, max_tokens=500)

        selected = []
        for line in response.strip().splitlines():
            line = line.strip().lstrip("-").strip()
            # Normalize path separators
            line = line.replace("\\", "/")
            # Match với file thực tế trong project
            for f in all_files:
                if f.replace("\\", "/").endswith(line) or line in f.replace("\\", "/"):
                    if f not in selected:
                        selected.append(f)
                    break

        return selected[:MAX_FILES_READ]

    # ── Step 2: Build context ────────────────────────────────────────────────

    def _build_context(self, task: str, files: dict[str, str]) -> str:
        """Build context string từ file contents."""
        parts = [f"# Task\n{task}\n\n# Codebase Context\n"]
        for path, content in files.items():
            if path == "__error__":
                continue
            parts.append(f"## {path}\n```\n{content}\n```\n")
        return "\n".join(parts)

    # ── Step 3: Generate fix ─────────────────────────────────────────────────

    async def _generate_fix(self, context: str, error_context: str = "") -> str:
        """Hỏi LLM sinh code fix."""

        error_section = f"\n\n# Lỗi từ lần chạy trước\n{error_context}" if error_context else ""

        prompt = f"""{context}{error_section}

# Yêu cầu
Phân tích và sửa vấn đề.

Chỉ trả về JSON object theo format:
```json
{
  "operations": [
    {
      "op": "replace",
      "path": "duong/dan/file.py",
      "old_str": "đoạn nguyên văn đang có trong file",
      "new_str": "đoạn thay thế"
    },
    {
      "op": "create",
      "path": "duong/dan/file_moi.py",
      "content": "nội dung file mới"
    }
  ]
}
```

Quy tắc bắt buộc:
- Không trả về toàn bộ nội dung file chỉ để ghi đè.
- old_str phải được copy nguyên văn từ context và xuất hiện đúng 1 lần trong file.
- Khi copy old_str, bỏ phần số dòng dạng "  123 | " nếu context có hiển thị số dòng.
- Dùng op=create chỉ cho file mới.
Nếu không cần sửa file nào, trả lời "NO_CHANGE" và giải thích tại sao.
"""
        return await self._ask_llm(prompt, max_tokens=4096)

    # ── Step 4: Determine verify command ────────────────────────────────────

    async def _get_verify_command(self, task: str, changed_files: list[str]) -> str:
        """Lấy verify command bằng cách tự động phát hiện (ưu tiên) hoặc hỏi LLM."""
        from execution.verifier.action_verifier import action_verifier
        auto_cmd = action_verifier.get_auto_verify_command(self._root, changed_files)
        if auto_cmd:
            logger.info("Automatically detected verify command: %s", auto_cmd)
            return auto_cmd

        files_str = ", ".join(changed_files[:5])
        prompt = f"""Task: {task}
Files changed: {files_str}
Project root: {self._root}

Lệnh nào phù hợp nhất để verify bản sửa này?
Chỉ trả về 1 lệnh duy nhất, không giải thích.
Ví dụ:
  python -m pytest tests/ -x -q
  python backend/server.py --test
  node --check renderer/scripts/app.js
  python -c "import backend.life.life_loop; print('OK')"

Nếu không có lệnh verify phù hợp, trả về "SKIP".
"""
        cmd = await self._ask_llm(prompt, max_tokens=100)
        cmd = cmd.strip().strip("`").strip()
        return cmd if cmd and cmd != "SKIP" else ""

    # ── Main loop ────────────────────────────────────────────────────────────

    async def run(self, task: str) -> AsyncIterator[CodingStep]:
        """Chạy coding agent, yield từng bước để frontend hiển thị.

        Args:
            task: Mô tả task bằng tiếng Việt hoặc tiếng Anh.

        Yields:
            CodingStep — mỗi bước trong quá trình.
        """
        start_time = time.time()
        self._steps = []

        # ── Bước 0: Scan project ─────────────────────────────────────────────
        step = CodingStep("read", "📂 Đang quét codebase...")
        self._steps.append(step)
        yield step

        all_files = _scan_project(self._root)
        if not all_files:
            step = CodingStep("error", "❌ Không tìm thấy file nào trong project", success=False)
            yield step
            return

        step = CodingStep("read", f"📂 Tìm thấy {len(all_files)} file", f"Root: {self._root}")
        yield step

        # ── Bước 1: Chọn file liên quan ─────────────────────────────────────
        step = CodingStep("read", "🔍 Đang chọn file liên quan...")
        yield step

        relevant_files = await self._select_relevant_files(task, all_files)

        if not relevant_files:
            # Fallback: dùng file Python/JS gần nhất
            relevant_files = [f for f in all_files if f.endswith((".py", ".js", ".ts"))][:8]

        step = CodingStep(
            "read",
            f"🔍 Chọn {len(relevant_files)} file liên quan",
            "\n".join(relevant_files),
        )
        yield step

        # ── Bước 2: Đọc file ────────────────────────────────────────────────
        step = CodingStep("read", f"📖 Đang đọc {len(relevant_files)} file...")
        yield step

        file_contents: dict[str, str] = {}
        for f in relevant_files:
            file_contents[f] = _read_file_safe(self._root, f)

        step = CodingStep("read", "📖 Đọc xong context", success=True)
        yield step

        # Generate TaskPlan steps
        plan_prompt = f"""Chúng ta cần hoàn thành task: {task}
Dưới đây là các file liên quan:
{json.dumps(relevant_files, indent=2)}

Hãy chia nhỏ task này thành một chuỗi từ 3 đến 8 bước thực hiện rõ ràng.
Trả về một JSON list các object, mỗi object có 'id' (string viết liền, ví dụ 'read_config') và 'description' (mô tả ngắn bằng tiếng Việt).
Ví dụ:
[
  {{"id": "inspect_code", "description": "Kiểm tra code hiện tại để tìm bug"}},
  {{"id": "apply_fix", "description": "Sửa logic trong main.py"}},
  {{"id": "run_test", "description": "Chạy pytest để xác minh"}}
]
Chỉ trả về JSON list, không giải thích.
"""
        task_plan_steps = []
        try:
            plan_response = await self._ask_llm(plan_prompt, max_tokens=1000)
            parsed_steps = _extract_json_object(plan_response)
            if isinstance(parsed_steps, list):
                for idx, step_data in enumerate(parsed_steps):
                    task_plan_steps.append(TaskPlanStep(
                        id=str(step_data.get("id", f"step_{idx}")),
                        description=str(step_data.get("description", "Không có mô tả")),
                        status="pending"
                    ))
        except Exception as e:
            logger.warning("Failed to generate/parse TaskPlan: %s", e)

        if not task_plan_steps:
            task_plan_steps = [
                TaskPlanStep(id="analyze", description="Phân tích lỗi và chuẩn bị sửa code", status="pending"),
                TaskPlanStep(id="patch", description="Áp dụng các thay đổi bằng công cụ patch", status="pending"),
                TaskPlanStep(id="verify", description="Chạy các bài kiểm thử xác minh", status="pending")
            ]

        self.task_plan = TaskPlan(task_id=f"coding_{int(time.time())}", steps=task_plan_steps)
        try:
            from runtime.eventbus.event_bus import event_bus
            from runtime.events.base_event import BaseEvent
            from runtime.events.event_types import EventType
            event_bus.publish(BaseEvent.create(
                event_type=EventType.PLAN_CREATED,
                source="coding_agent",
                payload=self.task_plan.to_dict()
            ))
        except Exception as e:
            logger.error("Failed to publish PLAN_CREATED: %s", e)

        # ── Main loop: Plan → Edit → Verify ─────────────────────────────────
        error_context = ""
        files_changed: list[str] = []

        for iteration in range(1, MAX_ITER + 1):
            if iteration == 1:
                self._update_step_status(0, "in_progress")

            step = CodingStep("plan", f"🤔 Vòng {iteration}/{MAX_ITER} — Đang phân tích...")
            yield step

            # Build context
            context = self._build_context(task, file_contents)

            # Generate fix
            step = CodingStep("plan", "✍️ Đang viết code fix...")
            yield step

            llm_response = await self._generate_fix(context, error_context)

            if not llm_response:
                step = CodingStep("error", "❌ LLM không trả về response", success=False)
                yield step
                return

            # Check NO_CHANGE
            if "NO_CHANGE" in llm_response.upper() and len(llm_response) < 500:
                step = CodingStep(
                    "done",
                    "✅ Không cần sửa code",
                    llm_response,
                    success=True,
                )
                yield step
                return

            try:
                fix_data = _extract_json_object(llm_response)
                operations = fix_data.get("operations", [])
            except Exception as exc:
                # LLM giải thích mà không viết code — có thể là câu trả lời thuần text
                step = CodingStep(
                    "error",
                    "❌ Không parse được JSON patch từ LLM",
                    f"{exc}\n\n{llm_response[:800]}",
                    success=False,
                )
                yield step
                return

            if not operations:
                step = CodingStep(
                    "done",
                    "💬 Phân tích hoàn tất (không có patch cần áp dụng)",
                    llm_response[:500],
                    success=True,
                )
                yield step
                return

            # ── Apply patch operations ──────────────────────────────────────
            num_steps = len(self.task_plan.steps)
            if num_steps > 2:
                self._update_step_status(0, "done")
                for i in range(1, num_steps - 1):
                    self._update_step_status(i, "in_progress")
            else:
                self._update_step_status(0, "done")
                self._update_step_status(1, "in_progress")

            written = []
            for operation in operations:
                rel_path = str(operation.get("path", "")).replace("\\", "/").lstrip("/")
                result = _apply_file_operation(self._root, operation)
                if result.get("success"):
                    written.append(rel_path)
                    file_contents[rel_path] = _read_file_safe(self._root, rel_path)
                    if rel_path not in files_changed:
                        files_changed.append(rel_path)

                    step = CodingStep(
                        "edit",
                        f"✏️ Đã sửa: {rel_path}",
                        result.get("message", ""),
                        success=True,
                    )
                    yield step
                else:
                    step = CodingStep(
                        "error",
                        f"❌ Không áp dụng được patch: {rel_path}",
                        result.get("error", "Unknown error"),
                        success=False,
                    )
                    yield step
                    return

            if not written:
                step = CodingStep(
                    "done",
                    "💬 Phân tích hoàn tất (không có file nào được ghi)",
                    llm_response[:500],
                    success=True,
                )
                yield step
                return

            # ── Verify ──────────────────────────────────────────────────────
            # Transition from editing to verifying
            num_steps = len(self.task_plan.steps)
            for i in range(num_steps - 1):
                self._update_step_status(i, "done")
            self._update_step_status(num_steps - 1, "in_progress")

            verify_cmd = await self._get_verify_command(task, written)

            if not verify_cmd:
                # Không có verify command → done
                # Mark verification step as done too
                self._update_step_status(num_steps - 1, "done")
                try:
                    from runtime.eventbus.event_bus import event_bus
                    from runtime.events.base_event import BaseEvent
                    from runtime.events.event_types import EventType
                    event_bus.publish(BaseEvent.create(
                        event_type=EventType.PLAN_FINISHED,
                        source="coding_agent",
                        payload={"task_id": self.task_plan.task_id, "success": True}
                    ))
                except Exception:
                    pass

                elapsed = round(time.time() - start_time, 1)
                step = CodingStep(
                    "done",
                    f"✅ Hoàn thành sau {elapsed}s",
                    f"Đã sửa: {', '.join(files_changed)}",
                    success=True,
                )
                yield step
                return

            step = CodingStep("run", f"🔄 Đang chạy: {verify_cmd}")
            yield step

            success, output = await self._run_command(verify_cmd)

            if success:
                self._update_step_status(num_steps - 1, "done")
                try:
                    from runtime.eventbus.event_bus import event_bus
                    from runtime.events.base_event import BaseEvent
                    from runtime.events.event_types import EventType
                    event_bus.publish(BaseEvent.create(
                        event_type=EventType.PLAN_FINISHED,
                        source="coding_agent",
                        payload={"task_id": self.task_plan.task_id, "success": True}
                    ))
                except Exception:
                    pass

                elapsed = round(time.time() - start_time, 1)
                step = CodingStep(
                    "verify",
                    f"✅ Verify thành công sau {elapsed}s",
                    f"Output:\n{output[:500]}",
                    success=True,
                )
                yield step

                # Final summary
                step = CodingStep(
                    "done",
                    f"🎉 Xong! Đã sửa {len(files_changed)} file sau {iteration} vòng",
                    "\n".join(files_changed),
                    success=True,
                )
                yield step
                return
            else:
                # Fail → retry
                self._update_step_status(num_steps - 1, "failed")
                try:
                    from runtime.eventbus.event_bus import event_bus
                    from runtime.events.base_event import BaseEvent
                    from runtime.events.event_types import EventType
                    event_bus.publish(BaseEvent.create(
                        event_type=EventType.PLAN_FAILED,
                        source="coding_agent",
                        payload={"task_id": self.task_plan.task_id, "reason": output[:300]}
                    ))
                except Exception:
                    pass

                tail = output[-3000:] if len(output) > 3000 else output
                error_context = f"Lệnh: {verify_cmd}\nOutput (phần cuối):\n{tail}"
                step = CodingStep(
                    "verify",
                    f"⚠️ Verify fail — Vòng {iteration}: đang phân tích lỗi...",
                    output[:300],
                    success=False,
                )
                yield step

                if iteration < MAX_ITER:
                    # Update context với error để vòng sau fix đúng hơn
                    file_contents["__error__"] = error_context

        # Hết MAX_ITER mà vẫn fail
        step = CodingStep(
            "error",
            f"❌ Đã thử {MAX_ITER} lần nhưng chưa sửa được",
            error_context[:500],
            success=False,
        )
        yield step


# ── Global singleton ──────────────────────────────────────────────────────────

coding_agent = CodingAgent()


# ── Tool wrapper để đăng ký vào ToolRegistry ──────────────────────────────────

async def run_coding_task(task: str, project_root: str = "") -> dict:
    """Tool entry point — được gọi từ PlannerAgent qua ToolRegistry.

    Args:
        task:         Mô tả task bằng ngôn ngữ tự nhiên.
        project_root: Đường dẫn project. Mặc định là PROJECT_ROOT.

    Returns:
        dict với success, summary, files_changed, steps.
    """
    agent = CodingAgent(project_root=project_root or None)

    steps_log = []
    last_step = None

    async for step in agent.run(task):
        steps_log.append({
            "step":    step.step,
            "message": step.message,
            "detail":  step.detail,
            "success": step.success,
        })
        last_step = step
        logger.info("[CodingAgent] %s — %s", step.step.upper(), step.message)

    success  = last_step.success if last_step else False
    summary  = last_step.message if last_step else "Không có kết quả"

    return {
        "success":       success,
        "summary":       summary,
        "steps":         steps_log,
        "files_changed": [s["detail"] for s in steps_log if s["step"] == "edit"],
    }
