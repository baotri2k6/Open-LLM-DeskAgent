"""Subagent service — running isolated context agent loops."""

from __future__ import annotations

import logging
from typing import List, Optional

logger = logging.getLogger("ai-companion.subagent")


async def run_subagent(task: str, focus_files: Optional[List[str]] = None) -> dict:
    """
    Khởi chạy một subagent độc lập để thực hiện một tác vụ chuyên biệt với ngữ cảnh (context) tách biệt.
    Trả về tóm tắt kết quả thực hiện.
    """
    logger.info("Spawning subagent for task: %s (focus_files: %s)", task, focus_files)
    
    # Nhập muộn để tránh import vòng
    from llm.manager import LLMService

    files_str = ", ".join(focus_files) if focus_files else "Không chỉ định"
    system_prompt = (
        "Bạn là một Subagent lập trình chuyên biệt. Nhiệm vụ của bạn là giải quyết yêu cầu dưới đây "
        "tập trung vào các tệp tin được cung cấp.\n"
        f"Danh sách tệp tin mục tiêu: {files_str}\n"
        "Hãy tự do sử dụng các công cụ cần thiết (đọc file, chạy lệnh, tìm kiếm...) để hoàn thành công việc. "
        "Sau khi hoàn tất, hãy đưa ra câu trả lời cuối cùng tóm tắt kết quả chi tiết những gì đã làm, "
        "kết quả đạt được, và các điểm quan trọng để báo cáo lại cho Agent chính."
    )

    llm = LLMService()
    # Ghi đè phương thức build system prompt của đối tượng này để sử dụng prompt của subagent
    llm._build_system_prompt = lambda *args, **kwargs: system_prompt

    result_text = []
    try:
        # Chạy agent loop của subagent
        async for chunk in llm.chat_stream(f"Yêu cầu nhiệm vụ: {task}"):
            if isinstance(chunk, str):
                result_text.append(chunk)
            elif isinstance(chunk, dict) and chunk.get("type") == "text":
                result_text.append(chunk["text"])

        summary = "".join(result_text).strip()
        logger.info("Subagent finished successfully.")
        return {
            "success": True,
            "summary": summary if summary else "Nhiệm vụ hoàn thành nhưng không có tóm tắt phản hồi."
        }
    except Exception as e:
        logger.error("Error executing subagent loop: %s", e)
        return {
            "success": False,
            "error": str(e)
        }


async def run_parallel_subagents(tasks: List[str], focus_files_list: Optional[List[List[str]]] = None) -> List[dict]:
    """Khởi chạy nhiều subagent song song để xử lý các tác vụ độc lập."""
    logger.info("Spawning %d parallel subagents", len(tasks))
    
    import asyncio
    coros = []
    for idx, task in enumerate(tasks):
        focus = focus_files_list[idx] if focus_files_list and idx < len(focus_files_list) else None
        coros.append(run_subagent(task, focus))
        
    results = await asyncio.gather(*coros, return_exceptions=True)
    
    processed_results = []
    for res in results:
        if isinstance(res, Exception):
            processed_results.append({"success": False, "error": str(res)})
        else:
            processed_results.append(res)
            
    return processed_results

