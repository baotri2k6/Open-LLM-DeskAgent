#!/usr/bin/env python
"""
DeskAgent Auto Commit Tool.
Stages changes, queries the local AI to write a professional commit message based on git diff,
and commits changes automatically.
"""

from __future__ import annotations

import os
import sys
import subprocess
import asyncio
from pathlib import Path

# Add project root and api folder to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "api"))

from llm.manager import LLMService
from config.config import config


async def generate_commit_message(diff_text: str) -> str | None:
    """Gửi diff cho AI để sinh tin nhắn commit chuẩn hóa."""
    llm = LLMService()
    
    prompt = (
        f"You are a professional software engineer. Generate a clear, concise Conventional Commit message "
        f"and a summary of changes in Vietnamese for the following git diff:\n\n"
        f"{diff_text}\n\n"
        f"Instructions:\n"
        f"1. Start with a single-line Conventional Commit message in English (max 72 chars), "
        f"e.g., 'feat(module): description' or 'fix(module): description'.\n"
        f"2. Add a blank line.\n"
        f"3. Add bullet points in Vietnamese detailing what was added, modified, or fixed.\n"
        f"4. Do NOT include markdown backticks (```) or extra conversational text. Return ONLY the commit message content."
    )
    
    try:
        response = await llm.chat(prompt)
        return response.strip()
    except Exception as e:
        print(f"❌ Lỗi khi gửi yêu cầu tới AI: {e}")
        return None


async def main() -> None:
    print("====================================================")
    print("       DeskAgent AI Git Auto-Commit Helper          ")
    print("====================================================")

    # 1. Kiểm tra Git repository
    if not (PROJECT_ROOT / ".git").exists():
        print("❌ Lỗi: Thư mục hiện tại không phải là Git repository.")
        return

    # 2. Lấy dữ liệu git diff đã staged
    diff_res = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, encoding="utf-8")
    diff_text = diff_res.stdout.strip()

    if not diff_text:
        # Nếu chưa stage tệp nào, kiểm tra xem có thay đổi nào chưa stage không
        status_res = subprocess.run(["git", "status", "-s"], capture_output=True, text=True, encoding="utf-8")
        status_text = status_res.stdout.strip()
        
        if not status_text:
            print("✨ Không có thay đổi nào trong dự án để commit.")
            return

        print("⚠️ Chưa có tệp tin nào được thêm vào hàng chờ (staged).")
        print(status_text)
        print("----------------------------------------------------")
        
        try:
            stage_all = input("👉 Bạn có muốn tự động thêm tất cả tệp (git add .) không? (y/n): ").strip().lower()
        except (KeyboardInterrupt, EOFError):
            print("\nĐã hủy.")
            return
            
        if stage_all == "y":
            subprocess.run(["git", "add", "."])
            diff_res = subprocess.run(["git", "diff", "--cached"], capture_output=True, text=True, encoding="utf-8")
            diff_text = diff_res.stdout.strip()
        else:
            print("❌ Vui lòng tự thêm tệp bằng lệnh 'git add <tên_file>' trước khi chạy lại script.")
            return

    # Cắt ngắn diff nếu quá dài để tránh vượt giới hạn token của LLM
    max_char_limit = 25000
    if len(diff_text) > max_char_limit:
        diff_text = diff_text[:max_char_limit] + "\n\n[Diff quá lớn, đã được tự động cắt bớt...]"

    # 3. Gọi AI phân tích và sinh tin nhắn
    print("🤖 Đang phân tích mã nguồn thay đổi bằng AI để soạn tin nhắn commit...")
    commit_msg = await generate_commit_message(diff_text)

    if not commit_msg:
        print("❌ Không thể sinh tin nhắn commit bằng AI.")
        return

    # 4. Hiển thị đề xuất và xác nhận commit
    print("\n📝 TIN NHẮN COMMIT ĐƯỢC AI ĐỀ XUẤT:")
    print("----------------------------------------------------")
    print(commit_msg)
    print("----------------------------------------------------")

    try:
        confirm = input("\n👉 Bạn có muốn commit với nội dung trên không? (y/n): ").strip().lower()
    except (KeyboardInterrupt, EOFError):
        print("\nĐã hủy.")
        return

    if confirm == "y":
        # Tạo file tạm để ghi tin nhắn tránh lỗi ký tự đặc biệt trên terminal command line
        temp_msg_file = PROJECT_ROOT / ".git_commit_msg.tmp"
        try:
            with open(temp_msg_file, "w", encoding="utf-8") as f:
                f.write(commit_msg)
            
            # Commit bằng file tạm
            res = subprocess.run(["git", "commit", "-F", str(temp_msg_file)])
            if res.returncode == 0:
                print("✅ Đã tạo commit thành công lên Local Git của bạn!")
            else:
                print("❌ Lỗi khi thực hiện commit.")
        finally:
            if temp_msg_file.exists():
                temp_msg_file.unlink()
    else:
        print("🔕 Đã hủy commit. Bạn có thể tự commit thủ công.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nĐã hủy.")
