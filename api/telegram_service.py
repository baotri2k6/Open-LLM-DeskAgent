"""Telegram Remote Bridge Service â€” Cho phÃ©p trÃ² chuyá»‡n, ra lá»‡nh vÃ  chá»¥p áº£nh mÃ n hÃ¬nh tá»« xa."""

from __future__ import annotations

import asyncio
import io
import sys
import time
import logging
from pathlib import Path
from typing import Any

import aiohttp
import pyautogui
from PIL import Image

from config.config import config
from runtime.eventbus.message_router import MessageRouter
from perception.fusion.perception_fusion import PerceptionFusion

logger = logging.getLogger("ai-companion.telegram")

# Globals to manage task lifecycle from external sync calls
_telegram_task: asyncio.Task | None = None
_current_token: str | None = None


def sync_telegram_service() -> None:
    """Sync Telegram task state from HTTP thread into the background event loop."""
    background_loop = None
    main_module = sys.modules.get("__main__")
    if main_module is not None:
        background_loop = getattr(main_module, "_background_loop", None)
    if background_loop is None:
        server_module = sys.modules.get("api.server") or sys.modules.get("server")
        if server_module is not None:
            background_loop = getattr(server_module, "_background_loop", None)

    if not background_loop:
        logger.warning("Background event loop is not ready; Telegram service sync skipped.")
        return

    background_loop.call_soon_threadsafe(_sync_telegram_service_async)


def _sync_telegram_service_async() -> None:
    """Cháº¡y trá»±c tiáº¿p trong event loop ngáº§m Ä‘á»ƒ khá»Ÿi Ä‘á»™ng/há»§y tÃ¡c vá»¥ Telegram Bot."""
    global _telegram_task, _current_token
    bot_token = config.get("telegram.bot_token", "").strip()

    if bot_token != _current_token:
        # Náº¿u token thay Ä‘á»•i, há»§y bot cÅ© Ä‘ang cháº¡y
        if _telegram_task:
            logger.info("Telegram Bot: Token thay Ä‘á»•i. Äang Ä‘Ã³ng bot cÅ©...")
            _telegram_task.cancel()
            _telegram_task = None

        _current_token = bot_token
        if bot_token:
            logger.info("Telegram Bot: Äang khá»Ÿi Ä‘á»™ng bot vá»›i token má»›i...")
            _telegram_task = asyncio.create_task(telegram_bot_loop(bot_token))
    
    elif not bot_token and _telegram_task:
        logger.info("Telegram Bot: Token trá»‘ng. Äang dá»«ng bot...")
        _telegram_task.cancel()
        _telegram_task = None
        _current_token = None


async def send_telegram_message(session: aiohttp.ClientSession, url: str, chat_id: str, text: str) -> None:
    """Gá»­i tin nháº¯n vÄƒn báº£n Ä‘áº¿n ngÆ°á»i dÃ¹ng qua Telegram Bot API."""
    send_url = f"{url}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text
    }
    try:
        async with session.post(send_url, json=payload, timeout=10) as resp:
            if resp.status != 200:
                logger.error(f"Gá»­i tin nháº¯n Telegram tháº¥t báº¡i: status {resp.status}, response: {await resp.text()}")
    except Exception as e:
        logger.error(f"Lá»—i khi gá»­i tin nháº¯n Telegram: {e}")


async def handle_telegram_screenshot(session: aiohttp.ClientSession, url: str, chat_id: str) -> None:
    """Chá»¥p áº£nh mÃ n hÃ¬nh mÃ¡y tÃ­nh hiá»‡n táº¡i vÃ  gá»­i vá» Ä‘iá»‡n thoáº¡i ngÆ°á»i dÃ¹ng qua Telegram."""
    # Hiá»ƒn thá»‹ tráº¡ng thÃ¡i Ä‘ang gá»­i áº£nh (Chat Action)
    try:
        action_url = f"{url}/sendChatAction"
        await session.post(action_url, json={"chat_id": chat_id, "action": "upload_photo"}, timeout=5)
    except Exception:
        pass

    try:
        screenshot = None
        try:
            # Cháº¡y hÃ m chá»¥p hÃ¬nh Ä‘á»“ng bá»™ cá»§a pyautogui trong Thread Ä‘á»ƒ khÃ´ng block event loop
            screenshot = await asyncio.to_thread(pyautogui.screenshot)
        except Exception as py_err:
            logger.warning(f"pyautogui.screenshot tháº¥t báº¡i: {py_err}. Äang dÃ¹ng mss fallback...")
            try:
                import mss
                with mss.mss() as sct:
                    monitor = sct.monitors[1]
                    sct_img = sct.grab(monitor)
                    screenshot = Image.frombytes("RGB", sct_img.size, sct_img.bgra, "raw", "BGRX")
            except Exception as mss_err:
                logger.error(f"mss screenshot fallback cÅ©ng tháº¥t báº¡i: {mss_err}")
                await send_telegram_message(session, url, chat_id, f"âŒ KhÃ´ng thá»ƒ chá»¥p mÃ n hÃ¬nh: {mss_err}")
                return

        # Resize áº£nh Ä‘á»ƒ tá»‘i Æ°u dung lÆ°á»£ng truyá»n táº£i
        width, height = screenshot.size
        max_size = 1280
        if max(width, height) > max_size:
            screenshot.thumbnail((max_size, max_size))

        buffered = io.BytesIO()
        screenshot.save(buffered, format="JPEG", quality=85)
        buffered.seek(0)

        # Gá»­i file Ä‘a pháº§n (multipart/form-data)
        send_photo_url = f"{url}/sendPhoto"
        data = aiohttp.FormData()
        data.add_field("chat_id", chat_id)
        data.add_field("caption", f"ðŸ–¥ï¸ áº¢nh chá»¥p mÃ n hÃ¬nh mÃ¡y tÃ­nh lÃºc {time.strftime('%H:%M:%S ngÃ y %d/%m/%Y')}")
        data.add_field("photo", buffered, filename="screenshot.jpg", content_type="image/jpeg")

        async with session.post(send_photo_url, data=data, timeout=20) as resp:
            if resp.status != 200:
                err_text = await resp.text()
                logger.error(f"Gá»­i áº£nh Telegram tháº¥t báº¡i: status {resp.status}, response: {err_text}")
                await send_telegram_message(session, url, chat_id, f"âŒ Gá»­i áº£nh mÃ n hÃ¬nh tháº¥t báº¡i: {err_text}")
            else:
                logger.info("ÄÃ£ gá»­i áº£nh chá»¥p mÃ n hÃ¬nh qua Telegram thÃ nh cÃ´ng.")

    except Exception as e:
        logger.error(f"Lá»—i xá»­ lÃ½ chá»¥p áº£nh mÃ n hÃ¬nh gá»­i Telegram: {e}", exc_info=True)
        await send_telegram_message(session, url, chat_id, f"âŒ Lá»—i khi chá»¥p mÃ n hÃ¬nh mÃ¡y tÃ­nh: {e}")


async def process_telegram_message(text: str) -> str:
    """Xá»­ lÃ½ há»™i thoáº¡i hoáº·c ra lá»‡nh nháº­n Ä‘Æ°á»£c tá»« Telegram gá»­i tá»›i PlannerAgent."""
    try:
        router = MessageRouter()
        planner = router.planner
        memory = planner.memory.service

        # Ghi nháº­n tÆ°Æ¡ng tÃ¡c & phÃ¢n tÃ­ch cáº£m xÃºc ngÆ°á»i dÃ¹ng
        time_note = memory.record_interaction()
        memory.analyze_sentiment_and_update(text)

        rel_info = memory.get_relationship()
        mood = memory.get_mood()

        # Táº¡o context bá»‘i cáº£nh cho Agent giá»‘ng nhÆ° giao diá»‡n GUI
        context: dict[str, Any] = {
            "companion": {
                "rel_level": rel_info["level"],
                "rel_score": rel_info["score"],
                "mood": mood,
                "time_note": time_note
            },
            "memory": memory.recall(text)
        }

        # Import lazily tá»« server.py Ä‘á»ƒ trÃ¡nh lá»—i circular imports
        from server import screen_watcher, _last_interaction_time, get_rag

        screen_text = screen_watcher.get_current_context() if screen_watcher else ""
        activity = screen_watcher.get_current_activity() if screen_watcher else "unknown"
        
        # Äá»“ng bá»™ thá»i gian tÆ°Æ¡ng tÃ¡c cuá»‘i cÃ¹ng trÃªn há»‡ thá»‘ng
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
                    logger.warning(f"RAG context query tháº¥t báº¡i: {exc}")

        # Gá»­i tin nháº¯n qua PlannerAgent xá»­ lÃ½ cÃ¡c cÃ´ng cá»¥ vÃ  sinh ná»™i dung pháº£n há»“i (KhÃ´ng dÃ¹ng stream)
        response = await planner.handle_message(text, context)
        reply_text = response.get("text", "")

        # Cáº­p nháº­t lá»‹ch sá»­ há»™i thoáº¡i vÃ  tá»± Ä‘á»™ng Ä‘Ãºc káº¿t pháº£n chiáº¿u kÃ½ á»©c (Reflection)
        try:
            memory.add_to_conversation_history("user", text)
            memory.add_to_conversation_history("assistant", reply_text)
            memory.write_back_memory(text, reply_text)

            # Cháº¡y báº¥t Ä‘á»“ng bá»™ phÃ¢n tÃ­ch cáº£m xÃºc & Ä‘Ãºc káº¿t nháº­t kÃ½
            memory.analyze_sentiment_async(text, reply_text)
            memory.write_diary_if_needed()
        except Exception as e:
            logger.warning(f"Cáº­p nháº­t Memory cho tin nháº¯n tá»« Telegram tháº¥t báº¡i: {e}")

        return reply_text

    except Exception as e:
        logger.error(f"Lá»—i khi xá»­ lÃ½ tin nháº¯n Telegram qua PlannerAgent: {e}", exc_info=True)
        return f"CÃ³ lá»—i xáº£y ra trong há»‡ thá»‘ng: {e}"


async def telegram_bot_loop(bot_token: str) -> None:
    """VÃ²ng láº·p polling tin nháº¯n tá»« Telegram API."""
    offset = 0
    url = f"https://api.telegram.org/bot{bot_token}"

    logger.info("Telegram Bot polling loop Ä‘Ã£ báº¯t Ä‘áº§u hoáº¡t Ä‘á»™ng.")

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
                        logger.error("Token Telegram Bot bá»‹ tá»« chá»‘i (Unauthorized). Äang Ä‘Ã³ng vÃ²ng láº·p...")
                        break
                    
                    if resp.status != 200:
                        logger.error(f"Telegram API tráº£ vá» mÃ£ lá»—i: {resp.status}")
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

                        # Äá»c cáº¥u hÃ¬nh allowed_chat_id Ä‘á»™ng Ä‘á»ƒ cÃ³ thá»ƒ thay Ä‘á»•i báº¥t cá»© lÃºc nÃ o
                        allowed_chat_id = config.get("telegram.allowed_chat_id", "").strip()

                        if not allowed_chat_id:
                            # HÆ°á»›ng dáº«n ngÆ°á»i dÃ¹ng cáº¥u hÃ¬nh Ä‘Ãºng ID khi chat vá»›i Bot láº§n Ä‘áº§u
                            response_text = (
                                f"ðŸ‘‹ ChÃ o báº¡n! ID cuá»™c trÃ² chuyá»‡n (chat ID) cá»§a báº¡n lÃ : `{chat_id}`.\n\n"
                                f"Vui lÃ²ng thÃªm ID nÃ y vÃ o má»¥c `telegram.allowed_chat_id` trong file "
                                f"`config/companion.config.json` Ä‘á»ƒ kÃ­ch hoáº¡t quyá»n Ä‘iá»u khiá»ƒn mÃ¡y tÃ­nh tá»« xa nhÃ©!"
                            )
                            await send_telegram_message(session, url, chat_id, response_text)
                            continue

                        if chat_id != allowed_chat_id:
                            logger.warning(f"Cá»‘ gáº¯ng truy cáº­p trÃ¡i phÃ©p tá»« chat_id: {chat_id}")
                            await send_telegram_message(session, url, chat_id, "ðŸ”’ Báº¡n khÃ´ng cÃ³ quyá»n truy cáº­p bot nÃ y!")
                            continue

                        if not text:
                            continue

                        logger.info(f"Telegram Bot nháº­n yÃªu cáº§u: '{text}' tá»« chat_id {chat_id}")

                        # Xá»­ lÃ½ cÃ¡c lá»‡nh Ä‘áº·c biá»‡t
                        if text.lower().strip() == "/screenshot":
                            await handle_telegram_screenshot(session, url, chat_id)
                        elif text.lower().strip() == "/start":
                            await send_telegram_message(
                                session,
                                url,
                                chat_id,
                                "ðŸ‘‹ ChÃ o má»«ng cáº­u quay trá»Ÿ láº¡i! Tá»› luÃ´n sáºµn sÃ ng há»— trá»£.\n"
                                "ðŸ‘‰ Cáº­u cÃ³ thá»ƒ gá»­i tin nháº¯n trÃ² chuyá»‡n, ra lá»‡nh má»Ÿ á»©ng dá»¥ng, hoáº·c dÃ¹ng lá»‡nh `/screenshot` Ä‘á»ƒ xem mÃ n hÃ¬nh mÃ¡y tÃ­nh cá»§a cáº­u nhÃ©."
                            )
                        else:
                            # Xá»­ lÃ½ há»™i thoáº¡i qua AI
                            reply = await process_telegram_message(text)
                            await send_telegram_message(session, url, chat_id, reply)

            except asyncio.CancelledError:
                logger.info("VÃ²ng láº·p Telegram Bot polling Ä‘Ã£ Ä‘Æ°á»£c yÃªu cáº§u dá»«ng.")
                break
            except Exception as e:
                logger.error(f"Lá»—i xáº£y ra trong vÃ²ng láº·p Telegram Bot: {e}", exc_info=True)
                await asyncio.sleep(5)

