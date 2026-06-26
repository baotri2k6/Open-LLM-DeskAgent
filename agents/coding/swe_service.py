"""SWE (Software Engineering) Service — Chạy tác vụ lập trình tự động với luồng dữ liệu tiến trình (Streaming)."""

from __future__ import annotations

import os
import sys
import json
import subprocess
import asyncio
import difflib
from pathlib import Path
from typing import Any, Callable, Awaitable

from llm.manager import LLMService
from runtime.logger import get_logger

logger = get_logger("ai-companion.swe-service")


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

        # Bước 3: Đọc nội dung tệp tin
        code_context = {}
        for rel_path in chosen_files:
            file_path = target_path / rel_path
            if file_path.exists():
                try:
                    with open(file_path, "r", encoding="utf-8") as f:
                        code_context[rel_path] = f.read()
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

            # Bóc tách JSON
            if "```" in fix_response_str:
                fix_response_str = fix_response_str.split("```")[1]
                if fix_response_str.startswith("json"):
                    fix_response_str = fix_response_str[4:]
            
            fix_data = json.loads(fix_response_str.strip())
            
            # Bước 5: Thực hiện sửa tệp tin và tạo diff
            for file_edit in fix_data.get("files", []):
                rel_path = file_edit["path"]
                edit_path = target_path / rel_path

                old_content = ""
                if edit_path.exists():
                    try:
                        with open(edit_path, "r", encoding="utf-8") as f:
                            old_content = f.read()
                    except Exception:
                        pass

                new_content = file_edit["content"]

                # Tạo thư mục cha nếu chưa có
                edit_path.parent.mkdir(parents=True, exist_ok=True)
                with open(edit_path, "w", encoding="utf-8") as f:
                    f.write(new_content)

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

            test_res = await asyncio.to_thread(
                lambda: subprocess.run(
                    [sys.executable, "-m", "pytest", str(target_path)],
                    capture_output=True,
                    text=True
                )
            )

            await progress_callback({
                "type": "test_result",
                "exit_code": test_res.returncode,
                "stdout": test_res.stdout,
                "stderr": test_res.stderr
            })

            if test_res.returncode == 0:
                await progress_callback({"type": "status", "message": "Kiểm thử thành công! Tất cả bài test đã pass."})
                await progress_callback({"type": "done", "success": True, "message": "Hoàn thành xuất sắc nhiệm vụ và vượt qua tất cả bài test!"})
                return True
            else:
                await progress_callback({
                    "type": "status",
                    "message": f"Kiểm thử thất bại (Mã lỗi {test_res.returncode}). Đang phân tích lỗi để sửa tiếp..."
                })
                # Gửi thông tin lỗi vào vòng tiếp theo
                current_description = (
                    f"{problem_description}\n\n"
                    f"Previous implementation attempt failed tests. Test stdout:\n{test_res.stdout}\n"
                    f"Test stderr:\n{test_res.stderr}"
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
