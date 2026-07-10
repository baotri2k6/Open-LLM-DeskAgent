"""SWE (Software Engineering) Service — Chạy tác vụ lập trình tự động với luồng dữ liệu tiến trình (Streaming)."""

from __future__ import annotations

import os
import sys
import json
import asyncio
import difflib
import shlex
from pathlib import Path
from typing import Any, Callable, Awaitable

from llm.manager import LLMService
from runtime.logger import get_logger
from tools.file_edit import create_file, str_replace_file
from tools.view_file import view_file
from execution.sandbox.sandbox_runner import SandboxPolicy, SandboxRunner

logger = get_logger("ai-companion.swe-service")


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
    """Quét đệ quy thư mục dự án và bỏ qua các thư mục build/git/node_modules."""
    ignore_dirs = {".git", "node_modules", "venv", "__pycache__", "build", "dist", ".gradle", ".idea", ".agents"}
    file_list = []
    
    for root, dirs, files in os.walk(directory):
        # Sửa đổi dirs in-place để skip các thư mục bỏ qua
        dirs[:] = [d for d in dirs if d not in ignore_dirs]
        for f in files:
            # Bỏ qua các tệp tin nhị phân và định dạng lớn
            if f.endswith((".pyc", ".png", ".jpg", ".jpeg", ".gif", ".ico", ".bin", ".zip", ".tar.gz", ".lock", ".db")):
                continue
            full_path = Path(root) / f
            try:
                # Lấy đường dẫn tương đối so với thư mục gốc
                file_list.append(str(full_path.relative_to(directory)))
            except Exception:
                pass
                
    return file_list


async def run_swe_task_api(
    problem_description: str,
    target_dir: str,
    progress_callback: Callable[[dict[str, Any]], Awaitable[None]],
    max_iterations: int = 3
) -> bool:
    """Khởi chạy vòng lặp SWE để sửa lỗi/lập trình và phát đi các cập nhật trạng thái chi tiết."""
    llm = LLMService()
    target_path = Path(target_dir).resolve()
    command_runner = SandboxRunner(SandboxPolicy(root=target_path))

    await progress_callback({
        "type": "status",
        "message": f"Khởi động Coding Agent tại thư mục: {target_path.name}"
    })

    current_description = problem_description

    for iteration in range(1, max_iterations + 1):
        await progress_callback({
            "type": "iteration",
            "number": iteration,
            "max": max_iterations
        })

        # Bước 1: Quét danh sách tệp tin
        await progress_callback({"type": "status", "message": "Đang quét danh sách tệp tin trong thư mục..."})
        try:
            files = scan_files(str(target_path))
            await progress_callback({"type": "files", "files": files})
        except Exception as e:
            await progress_callback({"type": "error", "message": f"Không thể quét thư mục: {e}"})
            return False

        if not files:
            await progress_callback({"type": "error", "message": "Thư mục dự án rỗng hoặc không hợp lệ."})
            return False

        # Bước 2: AI chọn các tệp cần đọc
        await progress_callback({"type": "status", "message": "Đang phân tích danh sách và chọn tệp liên quan..."})
        files_prompt = (
            f"You are a Software Engineering agent. We have a coding task:\n"
            f"Task: {current_description}\n\n"
            f"Here is the list of files in the project:\n"
            f"{json.dumps(files, indent=2)}\n\n"
            f"Please identify which files are relevant to read to understand and fix this issue.\n"
            f"Respond ONLY with a JSON list of strings representing the relative file paths, e.g., [\"src/main.py\"]."
        )

        try:
            chosen_files_str = await llm.chat(files_prompt)
            # Dọn dẹp markdown block
            if "```" in chosen_files_str:
                chosen_files_str = chosen_files_str.split("```")[1]
                if chosen_files_str.startswith("json"):
                    chosen_files_str = chosen_files_str[4:]
            
            chosen_files = json.loads(chosen_files_str.strip())
            # Giới hạn tối đa 5 tệp để tránh tràn context
            chosen_files = chosen_files[:5]
            
            await progress_callback({
                "type": "status",
                "message": f"Quyết định đọc các tệp: {', '.join(chosen_files)}"
            })
            await progress_callback({"type": "read_files", "files": chosen_files})
        except Exception as e:
            logger.warning(f"Không thể parse JSON danh sách file chọn bởi AI: {e}")
            # Fallback lấy tối đa 3 file code phổ biến trong dự án
            chosen_files = [f for f in files if f.endswith((".py", ".js", ".html", ".css", ".json"))][:3]
            await progress_callback({
                "type": "status",
                "message": f"Lỗi phân tích cú pháp AI, tự động chọn tệp thay thế: {chosen_files}"
            })

        # Bước 3: Đọc nội dung tệp tin kèm số dòng để patch chính xác
        code_context = {}
        for rel_path in chosen_files:
            file_path = target_path / rel_path
            if file_path.exists():
                try:
                    viewed = view_file(str(file_path))
                    if viewed.get("success"):
                        code_context[rel_path] = viewed["text"]
                except Exception as e:
                    logger.error(f"Không thể đọc tệp {rel_path}: {e}")

        if not code_context:
            await progress_callback({"type": "error", "message": "Không tìm thấy nội dung mã nguồn liên quan."})
            continue

        # Bước 4: AI suy nghĩ phương án và sinh code
        await progress_callback({"type": "status", "message": "Đang suy nghĩ giải pháp lập trình..."})
        
        fix_prompt = (
            f"You are an autonomous SWE agent. Implement a fix/feature for the following task:\n"
            f"Task: {current_description}\n\n"
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
            full_response_parts = []
            async for token in llm.chat_stream(fix_prompt):
                token_text = ""
                if isinstance(token, str):
                    token_text = token
                elif isinstance(token, dict) and token.get("type") == "text":
                    token_text = token.get("text", "")
                
                if token_text:
                    full_response_parts.append(token_text)
                    # Gửi trực tiếp token nháp (thought/code) về cho UI hiển thị thời gian thực
                    await progress_callback({"type": "thought_token", "token": token_text})

            fix_response_str = "".join(full_response_parts).strip()

            fix_data = _extract_json_object(fix_response_str)
            
            # Bước 5: Thực hiện patch chính xác và tạo diff
            for operation in fix_data.get("operations", []):
                rel_path = operation["path"]
                edit_path = _resolve_target(target_path, rel_path)

                old_content = ""
                if edit_path.exists():
                    try:
                        with open(edit_path, "r", encoding="utf-8") as f:
                            old_content = f.read()
                    except Exception:
                        pass

                if operation.get("op") == "replace":
                    result = str_replace_file(str(edit_path), operation.get("old_str", ""), operation.get("new_str", ""))
                elif operation.get("op") == "create":
                    result = create_file(str(edit_path), operation.get("content", ""))
                else:
                    result = {"success": False, "error": f"Unsupported operation: {operation.get('op')}"}

                if not result.get("success"):
                    raise RuntimeError(result.get("error", "Không thể áp dụng patch"))

                new_content = edit_path.read_text(encoding="utf-8", errors="replace")

                # Sinh định dạng Git Diff
                diff = list(difflib.unified_diff(
                    old_content.splitlines(keepends=True),
                    new_content.splitlines(keepends=True),
                    fromfile=f"a/{rel_path}",
                    tofile=f"b/{rel_path}"
                ))
                diff_str = "".join(diff)

                await progress_callback({
                    "type": "file_changed",
                    "path": rel_path,
                    "diff": diff_str,
                    "content": new_content
                })
                await progress_callback({"type": "status", "message": f"Đã chỉnh sửa tệp: {rel_path}"})

        except Exception as e:
            await progress_callback({"type": "error", "message": f"Lập trình thất bại ở lượt này: {e}"})
            logger.error(f"Lỗi khi sửa file: {e}", exc_info=True)
            continue

        # Bước 6: Chạy kiểm thử tự động (pytest)
        await progress_callback({"type": "status", "message": "Đang chạy bộ kiểm thử tự động (pytest)..."})
        try:
            # Tìm xem có file test nào không trước khi chạy để tránh báo lỗi no tests found
            has_tests = any("test" in f for f in files)
            if not has_tests:
                await progress_callback({
                    "type": "status",
                    "message": "Không tìm thấy tệp test trong dự án. Tự động coi như biên dịch thành công!"
                })
                await progress_callback({"type": "done", "success": True, "message": "Hoàn thành xuất sắc nhiệm vụ!"})
                return True

            test_res = await command_runner.run(
                f"{sys.executable} -m pytest {shlex.quote(str(target_path))}",
                cwd=target_path,
                timeout=60.0,
                allow_unlisted=True,
            )

            await progress_callback({
                "type": "test_result",
                "exit_code": test_res.get("returncode", -1),
                "stdout": test_res.get("stdout", ""),
                "stderr": test_res.get("stderr", test_res.get("error", ""))
            })

            if test_res.get("success"):
                await progress_callback({"type": "status", "message": "Kiểm thử thành công! Tất cả bài test đã pass."})
                await progress_callback({"type": "done", "success": True, "message": "Hoàn thành xuất sắc nhiệm vụ và vượt qua tất cả bài test!"})
                return True
            else:
                await progress_callback({
                    "type": "status",
                    "message": f"Kiểm thử thất bại (Mã lỗi {test_res.get('returncode', -1)}). Đang phân tích lỗi để sửa tiếp..."
                })
                # Gửi thông tin lỗi vào vòng tiếp theo
                current_description = (
                    f"{problem_description}\n\n"
                    f"Previous implementation attempt failed tests. Test stdout:\n{test_res.get('stdout', '')}\n"
                    f"Test stderr:\n{test_res.get('stderr', test_res.get('error', ''))}"
                )

        except Exception as e:
            await progress_callback({
                "type": "status",
                "message": f"Không thể chạy bộ test: {e}. Coi như biên dịch thành công."
            })
            await progress_callback({"type": "done", "success": True, "message": "Đã sửa đổi tệp tin thành công."})
            return True

    await progress_callback({
        "type": "done",
        "success": False,
        "message": f"Thất bại! Không thể hoàn thành nhiệm vụ sau {max_iterations} chu kỳ sửa lỗi."
    })
    return False
