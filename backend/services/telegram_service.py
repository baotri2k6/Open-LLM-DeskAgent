"""Telegram Remote Bridge Service — Cho phép trò chuyện, ra lệnh và chụp ảnh màn hình từ xa."""

from __future__ import annotations

import asyncio
import io
import time
import logging
from pathlib import Path
from typing import Any

import aiohttp
import pyautogui
from PIL import Image

from core.config import config
from core.message_router import MessageRouter
from core.perception_fusion import PerceptionFusion

logger = logging.getLogger("ai-companion.telegram")

# Globals to manage task lifecycle from external sync calls
_telegram_task: asyncio.Task | None = None
_current_token: str | None = None


def sync_telegram_service() -> None:
    """Đồng bộ hóa trạng thái của Telegram Service dựa trên cấu hình (Start/Stop/Restart).

    Gọi từ luồng ngoài (HTTP server) sang event loop chạy ngầm.
    """
    from server import _background_loop
    if not _background_loop:
        logger.warning("Event loop chạy nền chưa khởi động, không thể đồng bộ Telegram service.")
        return

    _background_loop.call_soon_threadsafe(_sync_telegram_service_async)


def _sync_telegram_service_async() -> None:
    """Chạy trực tiếp trong event loop ngầm để khởi động/hủy tác vụ Telegram Bot."""
    global _telegram_task, _current_token
    bot_token = config.get("telegram.bot_token", "").strip()

    if bot_token != _current_token:
        # Nếu token thay đổi, hủy bot cũ đang chạy
        if _telegram_task:
            logger.info("Telegram Bot: Token thay đổi. Đang đóng bot cũ...")
            _telegram_task.cancel()
            _telegram_task = None

        _current_token = bot_token
        if bot_token:
            logger.info("Telegram Bot: Đang khởi động bot với token mới...")
            _telegram_task = asyncio.create_task(telegram_bot_loop(bot_token))
    
    elif not bot_token and _telegram_task:
        logger.info("Telegram Bot: Token trống. Đang dừng bot...")
        _telegram_task.cancel()
        _telegram_task = None
        _current_token = None


async def send_telegram_message(session: aiohttp.ClientSession, url: str, chat_id: str, text: str) -> None:
    """Gửi tin nhắn văn bản đến người dùng qua Telegram Bot API."""
    send_url = f"{url}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        async with session.post(send_url, json=payload, timeout=10) as resp:
            if resp.status != 200:
                logger.error(f"Gửi tin nhắn Telegram thất bại: status {resp.status}, response: {await resp.text()}")
    except Exception as e:
        logger.error(f"Lỗi khi gửi tin nhắn Telegram: {e}")


async def handle_telegram_screenshot(session: aiohttp.ClientSession, url: str, chat_id: str) -> None:
    """Chụp ảnh màn hình máy tính hiện tại và gửi về điện thoại người dùng qua Telegram."""
    # Hiển thị trạng thái đang gửi ảnh (Chat Action)
    try:
        action_url = f"{url}/sendChatAction"
        await session.post(action_url, json={"chat_id": chat_id, "action": "upload_photo"}, timeout=5)
    except Exception:
        pass

    try:
        screenshot = None
        try:
            # Chạy hàm chụp hình đồng bộ của pyautogui trong Thread để không block event loop
            screenshot = await asyncio.to_thread(pyautogui.screenshot)
        except Exception as py_err:
            logger.warning(f"pyautogui.screenshot thất bại: {py_err}. Đang dùng mss fallback...")
            try:
                import mss
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as mss_err:
                logger.error(f"mss screenshot fallback cũng thất bại: {mss_err}")
                await send_telegram_message(session, url, chat_id, f"❌ Không thể chụp màn hình: {mss_err}")
                return

        # Resize ảnh để tối ưu dung lượng truyền tải
        width, height = screenshot.size
        max_size = 1280
        if max(width, height) > max_size:
            screenshot.thumbnail((max_size, max_size))

        buffered = io.BytesIO()
        screenshot.save(buffered, format="JPEG", quality=85)
        buffered.seek(0)

        # Gửi file đa phần (multipart/form-data)
        send_photo_url = f"{url}/sendPhoto"
        data = aiohttp.FormData()
        data.add_field("chat_id", chat_id)
        data.add_field("caption", f"🖥️ Ảnh chụp màn hình máy tính lúc {time.strftime('%H:%M:%S ngày %d/%m/%Y')}")
        data.add_field("photo", buffered, filename="screenshot.jpg", content_type="image/jpeg")

        async with session.post(send_photo_url, data=data, timeout=20) as resp:
            if resp.status != 200:
                err_text = await resp.text()
                logger.error(f"Gửi ảnh Telegram thất bại: status {resp.status}, response: {err_text}")
                await send_telegram_message(session, url, chat_id, f"❌ Gửi ảnh màn hình thất bại: {err_text}")
            else:
                logger.info("Đã gửi ảnh chụp màn hình qua Telegram thành công.")

    except Exception as e:
        logger.error(f"Lỗi xử lý chụp ảnh màn hình gửi Telegram: {e}", exc_info=True)
        await send_telegram_message(session, url, chat_id, f"❌ Lỗi khi chụp màn hình máy tính: {e}")


async def process_telegram_message(text: str) -> str:
    """Xử lý hội thoại hoặc ra lệnh nhận được từ Telegram gửi tới PlannerAgent."""
    try:
        router = MessageRouter()
        planner = router.planner
        memory = planner.memory.service

        # Ghi nhận tương tác & phân tích cảm xúc người dùng
        time_note = memory.record_interaction()
        memory.analyze_sentiment_and_update(text)

        rel_info = memory.get_relationship()
        mood = memory.get_mood()

        # Tạo context bối cảnh cho Agent giống như giao diện GUI
        context: dict[str, Any] = {
            "companion": {
                "rel_level": rel_info["level"],
                "rel_score": rel_info["score"],
                "mood": mood,
                "time_note": time_note
            },
            "memory": memory.recall(text)
        }

        # Import lazily từ server.py để tránh lỗi circular imports
        from server import screen_watcher, _last_interaction_time, get_rag

        screen_text = screen_watcher.get_current_context() if screen_watcher else ""
        activity = screen_watcher.get_current_activity() if screen_watcher else "unknown"
        
        # Đồng bộ thời gian tương tác cuối cùng trên hệ thống
        last_time = _last_interaction_time if isinstance(_last_interaction_time, (int, float)) else time.time()

        context["perception"] = PerceptionFusion.fuse(
            user_message=text,
            screen_text=screen_text,
            last_interaction_time=last_time,
            activity=activity
        )

        intent = planner.detect_intent(text)
        if intent["name"] == "rag_query":
            rag = get_rag()
            if rag:
                try:
                    rag_context = rag.build_context(text, n_results=3)
                    if rag_context:
                        context["rag_context"] = rag_context
                except Exception as exc:
                    logger.warning(f"RAG context query thất bại: {exc}")

        # Gửi tin nhắn qua PlannerAgent xử lý các công cụ và sinh nội dung phản hồi (Không dùng stream)
        response = await planner.handle_message(text, context)
        reply_text = response.get("text", "")

        # Cập nhật lịch sử hội thoại và tự động đúc kết phản chiếu ký ức (Reflection)
        try:
            memory.add_to_conversation_history("user", text)
            memory.add_to_conversation_history("assistant", reply_text)
            memory.write_back_memory(text, reply_text)

            # Chạy bất đồng bộ phân tích cảm xúc & đúc kết nhật ký
            memory.analyze_sentiment_async(text, reply_text)
            memory.write_diary_if_needed()
        except Exception as e:
            logger.warning(f"Cập nhật Memory cho tin nhắn từ Telegram thất bại: {e}")

        return reply_text

    except Exception as e:
        logger.error(f"Lỗi khi xử lý tin nhắn Telegram qua PlannerAgent: {e}", exc_info=True)
        return f"Có lỗi xảy ra trong hệ thống: {e}"


async def telegram_bot_loop(bot_token: str) -> None:
    """Vòng lặp polling tin nhắn từ Telegram API."""
    offset = 0
    url = f"https://api.telegram.org/bot{bot_token}"

    logger.info("Telegram Bot polling loop đã bắt đầu hoạt động.")

    async with aiohttp.ClientSession() as session:
        while True:
            try:
                get_updates_url = f"{url}/getUpdates"
                params = {
                    "offset": offset,
                    "timeout": 30,
                    "allowed_updates": ["message"]
                }

                async with session.get(get_updates_url, params=params, timeout=35) as resp:
                    if resp.status == 401:
                        logger.error("Token Telegram Bot bị từ chối (Unauthorized). Đang đóng vòng lặp...")
                        break
                    
                    if resp.status != 200:
                        logger.error(f"Telegram API trả về mã lỗi: {resp.status}")
                        await asyncio.sleep(10)
                        continue

                    data = await resp.json()
                    if not data.get("ok"):
                        logger.error(f"Telegram API ok=False: {data}")
                        await asyncio.sleep(10)
                        continue

                    updates = data.get("result", [])
                    for update in updates:
                        offset = update.get("update_id", 0) + 1
                        message = update.get("message")
                        if not message:
                            continue

                        chat = message.get("chat")
                        if not chat:
                            continue

                        chat_id = str(chat.get("id"))
                        text = message.get("text", "").strip()

                        # Đọc cấu hình allowed_chat_id động để có thể thay đổi bất cứ lúc nào
                        allowed_chat_id = config.get("telegram.allowed_chat_id", "").strip()

                        if not allowed_chat_id:
                            # Hướng dẫn người dùng cấu hình đúng ID khi chat với Bot lần đầu
                            response_text = (
                                f"👋 Chào bạn! ID cuộc trò chuyện (chat ID) của bạn là: `{chat_id}`.\n\n"
                                f"Vui lòng thêm ID này vào mục `telegram.allowed_chat_id` trong file "
                                f"`config/companion.config.json` để kích hoạt quyền điều khiển máy tính từ xa nhé!"
                            )
                            await send_telegram_message(session, url, chat_id, response_text)
                            continue

                        if chat_id != allowed_chat_id:
                            logger.warning(f"Cố gắng truy cập trái phép từ chat_id: {chat_id}")
                            await send_telegram_message(session, url, chat_id, "🔒 Bạn không có quyền truy cập bot này!")
                            continue

                        if not text:
                            continue

                        logger.info(f"Telegram Bot nhận yêu cầu: '{text}' từ chat_id {chat_id}")

                        # Xử lý các lệnh đặc biệt
                        if text.lower().strip() == "/screenshot":
                            await handle_telegram_screenshot(session, url, chat_id)
                        elif text.lower().strip() == "/start":
                            await send_telegram_message(
                                session,
                                url,
                                chat_id,
                                "👋 Chào mừng cậu quay trở lại! Tớ luôn sẵn sàng hỗ trợ.\n"
                                "👉 Cậu có thể gửi tin nhắn trò chuyện, ra lệnh mở ứng dụng, hoặc dùng lệnh `/screenshot` để xem màn hình máy tính của cậu nhé."
                            )
                        else:
                            # Xử lý hội thoại qua AI
                            reply = await process_telegram_message(text)
                            await send_telegram_message(session, url, chat_id, reply)

            except asyncio.CancelledError:
                logger.info("Vòng lặp Telegram Bot polling đã được yêu cầu dừng.")
                break
            except Exception as e:
                logger.error(f"Lỗi xảy ra trong vòng lặp Telegram Bot: {e}", exc_info=True)
                await asyncio.sleep(5)
