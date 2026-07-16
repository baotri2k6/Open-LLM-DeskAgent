"""Local HTTP/JSON server for AI Companion Desktop 2D.

Endpoints:
  GET  /health
  GET  /api/companion/state    ← Live emotion/mood/relationship state
  POST /chat
  GET  /memory/profile
  POST /voice/transcribe      ← STT
  POST /documents/import      ← RAG import
  GET  /documents             ← RAG list
  POST /documents/delete      ← RAG delete
  POST /model/import         ← Import Live2D model from ZIP
  GET  /tts/cache/<filename>  ← serve TTS audio files
"""


from __future__ import annotations

import sys
from pathlib import Path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

import asyncio
import base64
import json
import mimetypes
import os
import re
import socket
import tempfile
import zipfile
import time
from collections import deque
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse, parse_qs

from config.config import PROJECT_ROOT, WRITABLE_ROOT, config
from runtime.logger import get_logger
from runtime.eventbus.message_router import MessageRouter

logger = get_logger("ai-companion.server")
router = MessageRouter()


def clean_for_tts(text: str) -> str:
    """Làm sạch text trước khi đưa vào TTS — loại bỏ tag, markdown, ký tự đặc biệt.
    
    Port từ J.A.I.son filter pipeline — dùng nhất quán ở mọi chỗ trong TTS pipeline.
    """
    # Xóa emotion/motion tags: [emotion:happy], [motion:nod], [thinking]
    text = re.sub(r"\[.*?\]", "", text)
    # Xóa markdown bold/italic: **text**, *text*, __text__, _text_
    text = re.sub(r"\*{1,2}([^*]+)\*{1,2}", r"\1", text)
    text = re.sub(r"_{1,2}([^_]+)_{1,2}", r"\1", text)
    # Xóa inline code: `code`
    text = re.sub(r"`[^`]+`", "", text)
    # Xóa code blocks: ```...```
    text = re.sub(r"```[\s\S]*?```", "", text)
    # Xóa dấu ngoặc đơn
    text = text.replace("(", "").replace(")", "")
    # Xóa nhiều dấu cách thừa
    text = re.sub(r"\s+", " ", text).strip()
    return text

def is_safe_zip_path(zip_path: str) -> bool:
    if not zip_path:
        return False
    normalized = zip_path.replace("\\", "/")
    if ".." in normalized or "/../" in normalized:
        return False
    try:
        p = Path(zip_path).resolve()
        if p.suffix.lower() != ".zip":
            return False
        return p.is_file()
    except Exception:
        return False

def safe_extract_zip(zf, extract_to):
    extract_to_path = Path(extract_to).resolve()
    for member in zf.infolist():
        # Prevent Directory Traversal (Zip Slip)
        member_path = (extract_to_path / member.filename).resolve()
        if not member_path.as_posix().startswith(extract_to_path.as_posix()):
            raise Exception(f"Security Warning: Path Traversal detected in ZIP member: {member.filename}")
        zf.extract(member, extract_to_path)

# Lazy-init để không block startup
import threading
_init_lock = threading.Lock()
_stt_service = None
_tts_service = None
_rag_retriever = None

# ─── Globals & Locks for Vtuber Loops ─────────────────────────────────────────

_notifications_lock = threading.Lock()
_pending_notifications = {
    "avatar": [],
    "coding": []
}
_ai_busy = False
_generation_interrupted = False

_twitch_reader = None
_twitch_messages_lock = threading.Lock()
_recent_twitch_messages = deque(maxlen=50)
_msg_timestamps = deque(maxlen=100)


def _should_reply(messages_per_minute: float) -> bool:
    """Không spam khi chat sôi — chỉ reply ngẫu nhiên khi rate cao."""
    import random
    if messages_per_minute > 10:
        return random.random() < 0.3
    return True


_hotword_detector = None

_background_loop = None
_background_thread = None
_last_screen_text = ""
_last_interaction_time = time.time()
screen_watcher = None


def trigger_notification(data: dict):
    with _notifications_lock:
        for k in _pending_notifications:
            _pending_notifications[k].append(data)


def ws_broadcast(data: dict):
    """Broadcast helper alias to trigger notification to websocket and polling clients."""
    trigger_notification(data)


# ─── Twitch IRC Reader Client ──────────────────────────────────────────────────

class TwitchChatReader:
    def __init__(self, channel: str, message_callback):
        self.channel = channel.lower().strip().lstrip('#')
        self.callback = message_callback
        self.running = False
        self.socket = None
        self.thread = None

    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()

    def stop(self):
        self.running = False
        if self.socket:
            try:
                self.socket.close()
            except Exception:
                pass

    def _run(self):
        import random
        import time
        while self.running:
            try:
                self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.socket.settimeout(10.0)
                logger.info("TwitchChatReader: Connecting to irc.chat.twitch.tv:6667")
                self.socket.connect(("irc.chat.twitch.tv", 6667))
                
                # Anonymous credentials
                nick = f"justinfan{random.randint(10000, 99999)}"
                self.socket.send(f"PASS oauth:anything\r\n".encode("utf-8"))
                self.socket.send(f"NICK {nick}\r\n".encode("utf-8"))
                self.socket.send(f"JOIN #{self.channel}\r\n".encode("utf-8"))
                
                logger.info(f"TwitchChatReader: Joined channel #{self.channel}")
                
                buffer = ""
                while self.running:
                    try:
                        data = self.socket.recv(4096).decode("utf-8", errors="ignore")
                        if not data:
                            logger.warning("TwitchChatReader: Socket disconnected")
                            break
                        buffer += data
                        while "\r\n" in buffer:
                            line, buffer = buffer.split("\r\n", 1)
                            if line.startswith("PING"):
                                self.socket.send("PONG :tmi.twitch.tv\r\n".encode("utf-8"))
                            elif "PRIVMSG" in line:
                                # Parse sender and message
                                match = re.match(r":([^!]+)![^ ]+ PRIVMSG #[^ ]+ :(.*)", line)
                                if match:
                                    username = match.group(1)
                                    message_text = match.group(2)
                                    self.callback(username, message_text)
                    except socket.timeout:
                        continue
                    except Exception as e:
                        logger.warning(f"TwitchChatReader socket read error: {e}")
                        break
            except Exception as e:
                logger.warning(f"TwitchChatReader connection error: {e}")
            
            # Wait before reconnecting
            if self.running:
                time.sleep(5)


def handle_twitch_msg(username: str, text: str):
    # Perform moderation checks
    from social.moderation.content_moderator import content_moderator
    eval_res = content_moderator.evaluate(username, text)
    if eval_res.get("is_flagged"):
        logger.warning(f"Twitch Commentator blocked flagged chat: @{username}: {text} (Reason: {eval_res.get('reason')})")
        return
        
    logger.info(f"Twitch chat message (moderated): @{username}: {text}")
    with _twitch_messages_lock:
        _recent_twitch_messages.append((username, text))
        _msg_timestamps.append(time.time())


def sync_twitch_reader():
    global _twitch_reader
    enabled = config.get("features.twitchMode", False)
    channel = config.get("twitch.channel", "").strip()
    
    if not enabled or not channel:
        if _twitch_reader:
            logger.info("Stopping TwitchBridge...")
            _twitch_reader.stop()
            _twitch_reader = None
        return
        
    if _twitch_reader:
        if _twitch_reader.channel.lower() == channel.lower():
            return
        else:
            logger.info("Twitch channel changed, restarting TwitchBridge...")
            _twitch_reader.stop()
            _twitch_reader = None
            
    logger.info(f"Starting TwitchBridge for channel: {channel}")
    from interaction.chat.twitch_bridge import TwitchBridge
    _twitch_reader = TwitchBridge(channel, handle_twitch_msg)
    _twitch_reader.start()


# ─── Persistent Background Loop & Async Tasks ──────────────────────────────────

def start_background_loop():
    global _background_loop, _background_thread
    _background_loop = asyncio.new_event_loop()
    def run_loop(loop):
        asyncio.set_event_loop(loop)
        loop.run_forever()
    _background_thread = threading.Thread(target=run_loop, args=(_background_loop,), daemon=True)
    _background_thread.start()
    logger.info("Persistent background event loop started.")


async def _speak_and_notify_proactive(full_reply, type_name):
    """P0-2: Proactive TTS dùng SentenceAudioStreamer — phát câu đầu ngay, không đợi full response."""
    global _ai_busy
    try:
        from persona.dialogue.emotion_parser import EmotionStreamParser
        parser = EmotionStreamParser()
        clean_reply_parts = []
        final_emotion = "thinking"

        emo_chunk = parser.feed(full_reply)
        if emo_chunk and emo_chunk.get("emotion"):
            final_emotion = emo_chunk["emotion"]

        safe_t = parser.flush_text()
        if safe_t:
            clean_reply_parts.append(safe_t)
        leftover = parser.flush_all()
        if leftover:
            clean_reply_parts.append(leftover)

        clean_reply = "".join(clean_reply_parts).strip()
        if not clean_reply:
            return

        tts = get_tts()
        if not tts:
            # Không có TTS — vẫn trigger notification nhưng không có audio
            trigger_notification({
                "type": type_name,
                "text": clean_reply,
                "emotion": final_emotion,
                "audio_url": None,
                "duration_ms": 0
            })
            return

        # Dùng SentenceAudioStreamer để stream audio theo từng câu (J.A.I.son pattern)
        audio_chunks = []

        def collect_chunk(chunk):
            """Collector thay vì gửi qua WebSocket — gom audio chunks lại."""
            if chunk.get("type") == "audio":
                audio_chunks.append(chunk)

        from runtime.state.state_store import state_store, CompanionState
        await state_store.transition(CompanionState.SPEAKING)

        streamer = SentenceAudioStreamer(tts, collect_chunk)

        # Feed từng câu vào streamer — clean_for_tts sẽ được gọi trong _speak_sentence
        for sentence in re.split(r"(?<=[.!?])\s+", clean_reply):
            if sentence.strip():
                await streamer.feed_text(sentence + " ")

        await streamer.flush()

        # Trigger notification với toàn bộ audio chunks để frontend phát lần lượt
        first_audio = audio_chunks[0] if audio_chunks else None
        trigger_notification({
            "type": type_name,
            "text": clean_reply,
            "emotion": final_emotion,
            "audio_url": first_audio["audio_url"] if first_audio else None,
            "duration_ms": sum(c.get("duration_ms", 0) for c in audio_chunks),
            "audio_chunks": audio_chunks
        })

    except Exception as e:
        logger.warning("Proactive TTS speak failed: %s", e)
    finally:
        from runtime.state.state_store import state_store, CompanionState
        await state_store.transition(CompanionState.IDLE)
        _ai_busy = False


async def _autonomous_agent_loop():
    logger.info("Autonomous Agent Loop started.")
    global _ai_busy, _last_interaction_time, _last_screen_text, screen_watcher
    import time
    import random
    
    # Cooldown for proactive statements: e.g. at least 20 seconds between proactive comments
    last_proactive_time = time.time()
    
    while True:
        await asyncio.sleep(5)
        
        now = time.time()
        
        # If user has interacted recently (less than 15 seconds ago), do not trigger proactive chat
        if now - _last_interaction_time < 15.0:
            continue

        # NÂNG CẤP: Kiểm tra và ghi nhật ký trong nền nếu người dùng đã nghỉ lâu (> 2 phút)
        if now - _last_interaction_time > 120.0:
            try:
                planner = router.planner
                memory = planner.memory.service
                memory.write_diary_if_needed()
            except Exception as e:
                logger.warning("Failed to check/write diary in autonomous loop: %s", e)
            
        if now - last_proactive_time < 180.0:
            continue
            
        if _ai_busy:
            continue
            
        try:
            rand = random.random()
            
            # 30% chance to comment on screen (if screen has changed)
            if rand < 0.30:
                screen_enabled = config.get("features.screenAwareness", False)
                if screen_enabled and screen_watcher:
                    text = screen_watcher.get_current_context().strip()
                    activity = screen_watcher.get_current_activity()
                    if text and len(text) >= 10 and text != _last_screen_text and text not in _last_screen_text:
                        _last_screen_text = text
                        _ai_busy = True
                        logger.info(f"Autonomous Loop: Commenting on screen text ({len(text)} chars)")
                        
                        from llm.manager import LLMService
                        llm = LLMService()
                        
                        planner = router.planner
                        memory = planner.memory.service
                        rel_info = memory.get_relationship()
                        mood = memory.get_mood()
                        time_note = memory.record_interaction()
                        
                        # Tầng 1: PerceptionFusion
                        from perception.fusion.perception_fusion import PerceptionFusion
                        context = {
                            "companion": {
                                "rel_level": rel_info["level"],
                                "rel_score": rel_info["score"],
                                "mood": mood,
                                "time_note": time_note
                            },
                            "memory": memory.recall(text),
                            "perception": PerceptionFusion.fuse(
                                screen_text=text,
                                last_interaction_time=_last_interaction_time,
                                activity=activity
                            )
                        }
                        
                        prompt = (
                            "[BỘT PHÁT: Bạn tự quan sát thấy một số nội dung mới xuất hiện trên màn hình của người dùng. "
                            "Hãy đưa ra một câu bình luận tự nhiên, vui nhộn hoặc hỏi han quan tâm ngắn gọn (1-2 câu). "
                            "Hãy bình luận như thể bạn tự nhìn thấy màn hình của họ mà không bị gượng gạo.]"
                        )
                        
                        full_reply_parts = []
                        async for token in llm.chat_stream(prompt, context):
                            full_reply_parts.append(token)
                            
                        full_reply = "".join(full_reply_parts).strip()
                        await _speak_and_notify_proactive(full_reply, "screen_comment")
                        last_proactive_time = time.time()
                        _last_interaction_time = time.time()
            
            # 20% chance to generate a random proactive thought (e.g. idle greeting/complaining)
            elif rand < 0.50:
                _ai_busy = True
                logger.info("Autonomous Loop: Generating proactive random thought")
                
                from llm.manager import LLMService
                llm = LLMService()
                
                planner = router.planner
                memory = planner.memory.service
                rel_info = memory.get_relationship()
                mood = memory.get_mood()
                time_note = memory.record_interaction()
                
                # Phân loại prompt autonomous theo mood
                AUTONOMOUS_PROMPTS = {
                    "vui vẻ": [
                        "[BỘT PHÁT] cậu đang làm gì vậy? Nói chuyện với tớ đi nào! [wink]",
                        "[BỘT PHÁT] Hôm nay tớ thấy vui ghê, không biết tại sao. [happy]",
                    ],
                    "hơi dỗi": [
                        "[BỘT PHÁT] cậu im lặng lâu quá, tớ ngồi một mình buồn lắm đó. [angry]",
                        "[BỘT PHÁT] Thôi được rồi, không cần nói chuyện với tớ cũng được. [tongue]",
                    ],
                    "suy nghĩ": [
                        "[BỘT PHÁT] Tớ đang nghĩ... không biết cậu nói gì. [thinking]",
                        "[BỘT PHÁT] Tớ đang nghĩ có biết rằng... thôi quên đi. [thinking]",
                    ]
                }
                
                # Fallback to "vui vẻ"
                prompts_list = AUTONOMOUS_PROMPTS.get(mood, AUTONOMOUS_PROMPTS["vui vẻ"])
                selected_base = random.choice(prompts_list)
                
                # Tầng 1: PerceptionFusion
                from perception.fusion.perception_fusion import PerceptionFusion
                current_screen = screen_watcher.get_current_context() if screen_watcher else ""
                current_act = screen_watcher.get_current_activity() if screen_watcher else "unknown"
                
                context = {
                    "companion": {
                        "rel_level": rel_info["level"],
                        "rel_score": rel_info["score"],
                        "mood": mood,
                        "time_note": time_note
                    },
                    "perception": PerceptionFusion.fuse(
                        screen_text=current_screen,
                        last_interaction_time=_last_interaction_time,
                        activity=current_act
                    )
                }
                
                prompt = (
                    f"[BỘT PHÁT: Người dùng đã im lặng một lúc lâu. Tâm trạng của bạn hiện tại là '{mood}'. "
                    f"Hãy tự suy nghĩ và nói 1 câu ngắn gọn để phá vỡ sự im lặng. "
                    f"Gợi ý chủ đề/cảm hứng: '{selected_base}'. "
                    f"Hãy nói 1 câu độc lập, tự nhiên, đúng tính cách của bạn.]"
                )
                
                full_reply_parts = []
                async for token in llm.chat_stream(prompt, context):
                    full_reply_parts.append(token)
                    
                full_reply = "".join(full_reply_parts).strip()
                await _speak_and_notify_proactive(full_reply, "screen_comment")
                last_proactive_time = time.time()
                _last_interaction_time = time.time()
        except Exception as e:
            logger.warning(f"Error in autonomous loop: {e}")
            _ai_busy = False



async def _twitch_commentator_loop():
    logger.info("Twitch commentator loop started.")
    global _ai_busy
    import time
    last_comment_time = 0.0
    
    while True:
        await asyncio.sleep(5)
        
        twitch_mode = config.get("features.twitchMode", False)
        if not twitch_mode:
            continue
            
        now = time.time()
        # Cooldown: 8 seconds minimum between comments to avoid self-interruption
        if now - last_comment_time < 8.0:
            continue
            
        if _ai_busy:
            continue
            
        username = None
        msg_text = None
        with _twitch_messages_lock:
            if _recent_twitch_messages:
                username, msg_text = _recent_twitch_messages.popleft()
                
        if not username or not msg_text:
            continue
            
        # Clean up old timestamps (older than 60s) to calculate messages per minute rate
        while _msg_timestamps and _msg_timestamps[0] < now - 60.0:
            _msg_timestamps.popleft()
        messages_per_minute = len(_msg_timestamps)
        
        # Decide if we should reply based on message density rate
        if not _should_reply(messages_per_minute):
            logger.info(f"Twitch Commentator: Skipping message from {username} due to high rate ({messages_per_minute} msg/min)")
            continue
            
        _ai_busy = True
        logger.info(f"Twitch Commentator: Commenting on message from {username}: {msg_text}")
        try:
            from llm.manager import LLMService
            llm = LLMService()
            
            planner = router.planner
            memory = planner.memory.service
            rel_info = memory.get_relationship()
            mood = memory.get_mood()
            time_note = memory.record_interaction()
            
            context = {
                "companion": {
                    "rel_level": rel_info["level"],
                    "rel_score": rel_info["score"],
                    "mood": mood,
                    "time_note": time_note
                },
                "memory": memory.recall(msg_text)
            }
            
            prompt = f"[Người xem '{username}' trên Twitch chat]: {msg_text}\nHãy trò chuyện, đối đáp ngắn gọn, dí dỏm và thân thiện trực tiếp với người xem này."
            
            full_reply_parts = []
            async for token in llm.chat_stream(prompt, context):
                full_reply_parts.append(token)
                
            full_reply = "".join(full_reply_parts).strip()
            
            from persona.dialogue.emotion_parser import EmotionStreamParser
            parser = EmotionStreamParser()
            clean_reply_parts = []
            final_emotion = "friendly"
            
            for token in full_reply_parts:
                emo_chunk = parser.feed(token)
                if emo_chunk and emo_chunk.get("emotion"):
                    final_emotion = emo_chunk["emotion"]
                safe_t = parser.flush_text()
                if safe_t:
                    clean_reply_parts.append(safe_t)
            leftover = parser.flush_all()
            if leftover:
                clean_reply_parts.append(leftover)
                
            clean_reply = "".join(clean_reply_parts).strip()
            
            if clean_reply:
                ws_broadcast({
                    "type": "twitch_response",
                    "text": clean_reply,
                    "username": username,
                    "emotion": final_emotion,
                    "motion": "motion_talk",
                })
                logger.info(f"Twitch Commentator: Broadcast response to UI — {len(clean_reply)} chars")
            
            audio_url = None
            duration_ms = 0
            tts = get_tts()
            if tts and clean_reply:
                speak_text = clean_for_tts(clean_reply)  # P0-1: dùng clean_for_tts nhất quán
                try:
                    tts_result = await tts.speak(speak_text)
                    if tts_result.get("success") and tts_result.get("audio_url"):
                        audio_url = tts_result["audio_url"]
                        duration_ms = tts_result.get("duration_ms", 0)
                except Exception as e:
                    logger.warning(f"Twitch Commentator TTS speak failed: {e}")
            
            trigger_notification({
                "type": "twitch_comment",
                "text": clean_reply,
                "emotion": final_emotion,
                "audio_url": audio_url,
                "duration_ms": duration_ms
            })
            
            last_comment_time = time.time()
        except Exception as e:
            logger.warning(f"Error in Twitch commentator: {e}")
        finally:
            _ai_busy = False


# ─── SentenceAudioStreamer for Real-time Stream-TTS ──────────────────────────

class SentenceAudioStreamer:
    def __init__(self, tts_service, send_chunk_fn):
        self.tts = tts_service
        self.send_chunk = send_chunk_fn
        self.buffer = ""
        self.delimiters = re.compile(r"([.!?\n])")
        self.queue = asyncio.Queue()
        self.worker_task = asyncio.create_task(self._worker())

    async def feed_text(self, text: str):
        global _generation_interrupted
        if _generation_interrupted:
            return
        self.buffer += text
        parts = self.delimiters.split(self.buffer)
        
        if len(parts) > 2:
            sentences_to_process = []
            for i in range(0, len(parts) - 1, 2):
                sentence = parts[i] + parts[i+1]
                sentences_to_process.append(sentence.strip())
            
            self.buffer = parts[-1]
            
            for s in sentences_to_process:
                if s:
                    self.queue.put_nowait(s)

    async def flush(self):
        global _generation_interrupted
        if _generation_interrupted:
            while not self.queue.empty():
                try:
                    self.queue.get_nowait()
                    self.queue.task_done()
                except asyncio.QueueEmpty:
                    break
            self.buffer = ""
        else:
            s = self.buffer.strip()
            self.buffer = ""
            if s:
                self.queue.put_nowait(s)
        
        # Đợi tất cả câu trong queue được xử lý xong
        await self.queue.join()
        
        # Hủy worker task sau khi hoàn thành
        if self.worker_task:
            self.worker_task.cancel()
            try:
                await self.worker_task
            except asyncio.CancelledError:
                pass

    async def _worker(self):
        global _generation_interrupted
        while True:
            try:
                sentence = await self.queue.get()
                if _generation_interrupted:
                    self.queue.task_done()
                    continue
                try:
                    await self._speak_sentence(sentence)
                finally:
                    self.queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.warning("Error in SentenceAudioStreamer worker loop: %s", e)

    async def _speak_sentence(self, sentence: str):
        # P0-1: Dùng clean_for_tts nhất quán — loại bỏ tag, markdown, ngoặc đơn
        clean_s = clean_for_tts(sentence)
        if not clean_s:
            return
            
        try:
            from runtime.state.state_store import state_store, CompanionState
            await state_store.transition(CompanionState.SPEAKING)
            
            tts_res = await self.tts.speak(clean_s)
            if tts_res.get("success") and tts_res.get("audio_url"):
                self.send_chunk({
                    "type": "audio",
                    "audio_url": tts_res["audio_url"],
                    "duration_ms": tts_res.get("duration_ms", 0)
                })
        except Exception as e:
            logger.warning("Failed to speak sentence stream: %s", e)



def get_stt():
    global _stt_service
    if _stt_service is None:
        with _init_lock:
            if _stt_service is None:
                try:
                    from speech.stt.stt_service import STTService
                    _stt_service = STTService()
                except Exception as exc:
                    logger.warning("STTService init failed: %s", exc)
    return _stt_service


def get_tts():
    global _tts_service
    if _tts_service is None:
        with _init_lock:
            if _tts_service is None:
                try:
                    from speech.tts.tts_service import TTSService
                    _tts_service = TTSService()
                except Exception as exc:
                    logger.warning("TTSService init failed: %s", exc)
    return _tts_service


def get_rag():
    global _rag_retriever
    if _rag_retriever is None:
        with _init_lock:
            if _rag_retriever is None:
                try:
                    from knowledge.rag.retriever import get_retriever
                    _rag_retriever = get_retriever()
                except Exception as exc:
                    logger.warning("RAGRetriever init failed: %s", exc)
    return _rag_retriever


TTS_CACHE_DIR = WRITABLE_ROOT / "cache" / "tts"
TTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)


class CompanionRequestHandler(BaseHTTPRequestHandler):
    server_version = "AICompanionHTTP/0.2"

    def do_OPTIONS(self) -> None:
        self._send_empty(204)

    # ─── GET ─────────────────────────────────────────────────────────────────

    def do_GET(self) -> None:
        path = urlparse(self.path).path

        if path == "/health":
            from runtime.services.service_registry import service_registry
            checks = service_registry.check_all()
            
            # Format to match expectations of settings UI exactly
            formatted_checks = {}
            for name, svc_stat in checks.items():
                status_str = "Online" if svc_stat["status"] == "online" else "Offline"
                # Backend is always Online
                if name == "backend":
                    status_str = "Online"
                
                details = svc_stat.get("details", {})
                formatted_checks[name] = {
                    "status": status_str,
                    **details
                }
                if svc_stat.get("error"):
                    formatted_checks[name]["error"] = svc_stat["error"]
            
            self._send_json({
                "status": "READY",
                "name": config.get("app.name"),
                "version": "0.2.0",
                "checks": formatted_checks
            })
            return

        if path == "/memory/profile":
            self._send_json(router.planner.memory.profile())
            return

        if path == "/memories":
            planner = router.planner
            memory = planner.memory.service
            self._send_json({"success": True, "memories": memory.get_all_memories()})
            return

        if path == "/documents":
            rag = get_rag()
            docs = rag.list_documents() if rag else []
            self._send_json({"success": True, "documents": docs})
            return

        if path == "/config":
            self._send_json({
                "llm_provider":    config.get("llm.provider",              "ollama"),
                "ollama_model":    config.get("llm.model",                 "llama3.2:3b"),
                "gemini_key":      config.get("llm.gemini_api_key",        ""),
                "gemini_model":    config.get("llm.gemini_model",          "gemini-2.5-flash"),
                "openai_key":      config.get("llm.openai_api_key",        ""),
                "openai_model":    config.get("llm.openai_model",          "gpt-4o-mini"),
                "deepseek_key":    config.get("llm.deepseek_api_key",      ""),
                "deepseek_model":  config.get("llm.deepseek_model",        "deepseek-chat"),
                "glm_key":         config.get("llm.glm_api_key",           ""),
                "glm_model":       config.get("llm.glm_model",             "glm-4"),
                "qwen_key":        config.get("llm.qwen_api_key",          ""),
                "qwen_model":      config.get("llm.qwen_model",            "qwen-plus"),
                "openai_compatible_key": config.get("llm.openai_compatible_api_key", ""),
                "openai_compatible_model": config.get("llm.openai_compatible_model", ""),
                "openai_compatible_base_url": config.get("llm.openai_compatible_base_url", ""),
                "stt_model":       config.get("stt.model",                 "base"),
                "stt_language":    config.get("stt.language",              "vi"),
                "stt_funasr_model": config.get("stt.funasr_model",         "iic/SenseVoiceSmall"),
                "tts_backend":     config.get("tts.backend", config.get("tts.api", "edge")),
                "tts_voice":       config.get("tts.voice",                 "en-us-AriaNeural"),
                "fish_api_key":    config.get("tts.fish_audio_api_key",    ""),
                "fish_model_id":   config.get("tts.fish_audio_model_id",   ""),
                "screen_awareness":config.get("features.screenAwareness",  False),
                "twitch_mode":     config.get("features.twitchMode",       False),
                "twitch_channel":  config.get("twitch.channel",            ""),
                "interaction_mode": config.get("app.interactionMode",       "streamer"),
                "avatar_model":     config.get("app.avatarModel",            "assets/live2d/IceGirl/IceGirl.model3.json"),
                "avatar_scale":     config.get("app.avatarScale",            "1.0"),
                "background_image":  config.get("app.backgroundImage",        ""),
                "memory":           config.get("features.memory",           True),
            })
            return

        if path == "/notifications" or path.startswith("/notifications?"):
            client = "avatar"
            if "?" in path:
                parsed = urlparse(path)
                params = parse_qs(parsed.query)
                client = params.get("client", ["avatar"])[0]

            with _notifications_lock:
                if client not in _pending_notifications:
                    _pending_notifications[client] = []
                notes = list(_pending_notifications[client])
                _pending_notifications[client].clear()
            self._send_json({"notifications": notes})
            return

        # Serve TTS cache files
        if path.startswith("/tts/cache/"):
            filename = path.removeprefix("/tts/cache/")
            self._serve_file(TTS_CACHE_DIR / filename)
            return

        if path == "/api/companion/state":
            try:
                from persona.emotion.emotion_engine import emotion_engine
                from persona.mood.mood_engine import mood_engine
                from persona.relationship.relationship_tracker import relationship_tracker
                from persona.goals.goal_manager import goal_manager
                from motivation.motivation_manager import motivation_manager
                self._send_json({
                    "emotion":      emotion_engine.snapshot(),
                    "mood":         mood_engine.get_snapshot(),
                    "relationship": relationship_tracker.snapshot(),
                    "goals":        goal_manager.snapshot(),
                    "motivation":   motivation_manager.get_state_snapshot(),
                })
            except Exception as exc:
                self._send_json({"error": str(exc)}, status=500)
            return

        if path == "/model/list":
            self._handle_GET_model_list()
            return

        self._send_json({"type": "error", "message": "Not found"}, status=404)


    # ─── POST ────────────────────────────────────────────────────────────────

    def do_POST(self) -> None:
        global _last_interaction_time
        path = urlparse(self.path).path
        payload = self._read_json()

        if path == "/chat":
            _last_interaction_time = time.time()
            
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            asyncio.run(self._handle_chat_stream(payload))
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except Exception:
                pass
            return

        if path == "/chat/cancel":
            global _generation_interrupted
            _generation_interrupted = True
            self._send_json({"success": True})
            return

        if path == "/chat/approve":
            req_id = payload.get("req_id")
            approved = payload.get("approved", False)
            from execution.approval.approval_registry import submit_approval
            success = submit_approval(req_id, approved)
            self._send_json({"success": success})
            return

        if path == "/voice/transcribe":
            _last_interaction_time = time.time()
            
            result = asyncio.run(self._handle_stt(payload))
            self._send_json(result)
            return

        if path == "/voice/tts":
            text = payload.get("text", "")
            tts_service = get_tts()
            if tts_service:
                result = asyncio.run(tts_service.speak(text))
                self._send_json(result)
            else:
                self._send_json({"success": False, "error": "TTS Service chưa được khởi tạo."})
            return

        if path == "/interact":
            _last_interaction_time = time.time()
            self._send_json({"success": True})
            return

        if path == "/documents/import":
            result = asyncio.run(self._handle_rag_import(payload))
            self._send_json(result)
            return

        if path == "/documents/delete":
            result = self._handle_rag_delete(payload)
            self._send_json(result)
            return

        if path == "/memories/update":
            planner = router.planner
            memory = planner.memory.service
            fact_id = payload.get("id")
            new_text = payload.get("text", "")
            success = memory.update_memory(fact_id, new_text)
            self._send_json({"success": success})
            return

        if path == "/memories/delete":
            planner = router.planner
            memory = planner.memory.service
            fact_id = payload.get("id")
            success = memory.delete_memory(fact_id)
            self._send_json({"success": success})
            return

        if path == "/memories/add":
            planner = router.planner
            memory = planner.memory.service
            text = payload.get("text", "")
            if text:
                fact = memory.remember(text, category="manual")
                self._send_json({"success": True, "memory": fact})
            else:
                self._send_json({"success": False, "error": "Text is empty"})
            return

        if path == "/swe/run":
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Transfer-Encoding", "chunked")
            self.end_headers()

            asyncio.run(self._handle_swe_stream(payload))
            try:
                self.wfile.write(b"0\r\n\r\n")
                self.wfile.flush()
            except Exception:
                pass
            return

        if path == "/swe/scan":
            directory = payload.get("directory", "").strip()
            if not directory:
                self._send_json({"success": False, "error": "Thiếu thông tin directory."})
                return
            try:
                from agents.coding.swe_service import scan_files
                files = scan_files(directory)
                self._send_json({"success": True, "files": files})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        if path == "/config/update":
            key = payload.get("key")
            value = payload.get("value")
            try:
                config.set(key, value)
                if key == "stt.model":
                    global _stt_service
                    _stt_service = None
                    def reload_stt():
                        try:
                            get_stt()
                            logger.info("STT reloaded dynamically with model %s", value)
                        except Exception as e:
                            logger.error("Failed to reload STT: %s", e)
                    import threading
                    threading.Thread(target=reload_stt, daemon=True).start()
                
                if key in ["features.twitchMode", "twitch.channel"]:
                    sync_twitch_reader()
                if key in ["telegram.bot_token", "telegram.allowed_chat_id"]:
                    from api.telegram_service import sync_telegram_service
                    sync_telegram_service()
                self._send_json({"success": True})
            except Exception as e:
                self._send_json({"success": False, "error": str(e)}, status=500)
            return

        if path == "/model/scan-zip":
            try:
                zip_path = payload.get("zip_path", "").strip()
                if not is_safe_zip_path(zip_path):
                    self._send_json({"success": False, "error": "Đường dẫn tệp ZIP không hợp lệ hoặc không an toàn."})
                    return
                
                import zipfile as _zipfile
                import pathlib as _pathlib
                zip_path_obj = _pathlib.Path(zip_path).resolve()
                
                with _zipfile.ZipFile(zip_path_obj, "r") as zf:
                    for name in zf.namelist():
                        if ".." in name or name.startswith("/") or name.startswith("\\"):
                            self._send_json({"success": False, "error": f"Phát hiện Zip Slip (Path Traversal) trong tệp ZIP: {name}"})
                            return
                    namelist = zf.namelist()
                
                # Find all model3.json or json config files
                model_files = []
                for name in namelist:
                    if name.lower().endswith(".model3.json"):
                        model_files.append(name)
                    elif name.lower().endswith(".json") and not name.lower().endswith(".model3.json"):
                        # Exclude general non-character configs
                        if "manifest" not in name.lower() and "models" not in name.lower() and "package" not in name.lower() and "metadata" not in name.lower():
                            model_files.append(name)
                
                self._send_json({"success": True, "files": model_files})
            except Exception as e:
                logger.error("[ModelScan] Failed to scan zip: %s", e, exc_info=True)
                self._send_json({"success": False, "error": f"Lỗi quét file ZIP: {str(e)}"})
            return

        if path == "/model/import":
            try:
                result = self._handle_model_import(payload)
                self._send_json(result)
            except Exception as e:
                logger.error("[ModelImport] Failed to import model: %s", e, exc_info=True)
                self._send_json({"success": False, "error": f"Lỗi giải nén nhân vật: {str(e)}"})
            return

        if path == "/model/remove":
            try:
                result = self._handle_model_remove(payload)
                self._send_json(result)
            except Exception as e:
                logger.error("[ModelRemove] Error: %s", e, exc_info=True)
                self._send_json({"success": False, "error": str(e)})
            return

        self._send_json({"type": "error", "message": "Not found"}, status=404)


    # ─── Handlers ────────────────────────────────────────────────────────────


    def _handle_model_import(self, payload: dict) -> dict:
        """Extract a Live2D model ZIP and register it in assets/live2d/models.json.

        Expected payload:
          { "zip_path": "<absolute path to .zip file>", "selected_config": "<optional relative path inside zip>" }

        Returns:
          { "success": true, "model": { ...entry } }
          { "success": false, "error": "..." }
        """
        import zipfile as _zipfile
        import shutil
        import pathlib

        zip_path = payload.get("zip_path", "").strip()
        selected_config = payload.get("selected_config", "").strip()
        if not is_safe_zip_path(zip_path):
            return {"success": False, "error": "Đường dẫn tệp ZIP không hợp lệ hoặc không an toàn."}

        zip_path = pathlib.Path(zip_path).resolve()

        live2d_dir = PROJECT_ROOT / "assets" / "live2d"
        live2d_dir.mkdir(parents=True, exist_ok=True)
        manifest_path = live2d_dir / "models.json"
        
    
        # ── Extract ZIP to a temp folder, then inspect ──────────────────────
        with tempfile.TemporaryDirectory() as tmp:
            tmp = pathlib.Path(tmp)
            try:
                with _zipfile.ZipFile(zip_path, "r") as zf:
                    safe_extract_zip(zf, tmp)
            except Exception as exc:
                return {"success": False, "error": f"Lỗi giải nén tệp ZIP an toàn: {exc}"}

            if selected_config:
                # Find the specified config file in extracted files
                model3_file = tmp / selected_config
                if not model3_file.exists():
                    model3_files = list(tmp.rglob(selected_config))
                    if not model3_files:
                        model3_files = list(tmp.rglob(pathlib.Path(selected_config).name))
                    if model3_files:
                        model3_file = model3_files[0]
                    else:
                        return {"success": False, "error": f"Selected config {selected_config} not found in ZIP"}
            else:
                # Fallback: Find model3.json automatically
                model3_files = list(tmp.rglob("*.model3.json"))
                if not model3_files:
                    model3_files = [f for f in tmp.rglob("*.json") if not f.name.endswith(".model3.json") and "manifest" not in f.name.lower() and "models" not in f.name.lower()]
                if not model3_files:
                    return {"success": False, "error": "No *.model3.json or model configuration found in ZIP"}
                model3_file = model3_files[0]

            # The model folder is the parent of model3.json
            model_src_dir = model3_file.parent

            # Derive a clean folder name and id from the model3 filename
            stem = model3_file.stem  # e.g. "IceGirl.model3" -> need to strip .model3
            if stem.endswith(".model3"):
                stem = stem[: -len(".model3")]
            model_id = stem.lower().replace(" ", "_").replace("-", "_")
            dest_dir = live2d_dir / stem

            # Copy (overwrite if exists)
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(model_src_dir, dest_dir)
            logger.info("[ModelImport] Extracted '%s' to %s", stem, dest_dir)

        # ── Build relative path for manifest ────────────────────────────────
        rel_path = f"assets/live2d/{stem}/{model3_file.name}"

        # Try to find a preview/thumbnail image (priority: root folder preview, then textures)
        thumbnail = ""
        preview_files = []
        for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
            preview_files.extend(list(dest_dir.glob(ext)))

        # Look for files containing preview keywords (case-insensitive)
        keywords = ["thumbnail", "preview", "avatar", "icon", "show", "portrait"]
        matched_preview = None
        for pf in preview_files:
            name_lower = pf.name.lower()
            if any(kw in name_lower for kw in keywords):
                matched_preview = pf
                break

        # If no keyword match, but we have images at root, pick the first one (usually it is the preview image)
        if not matched_preview and preview_files:
            matched_preview = preview_files[0]

        if matched_preview:
            thumbnail = f"assets/live2d/{stem}/{matched_preview.name}"
        else:
            # Fallback: search in textures folder
            tex_pngs = []
            if (dest_dir / "textures").exists():
                for ext in ["*.png", "*.jpg", "*.jpeg", "*.webp"]:
                    tex_pngs.extend(list((dest_dir / "textures").glob(ext)))
            if tex_pngs:
                tex_pngs = sorted(tex_pngs, key=lambda x: x.name)
                thumbnail = f"assets/live2d/{stem}/textures/{tex_pngs[0].name}"

        # ── Register in Character Registry ────────────────────────────────────
        characters_dir = _pathlib.Path(__file__).resolve().parent.parent / "characters"
        characters_dir.mkdir(parents=True, exist_ok=True)
        
        char_dir = characters_dir / model_id
        char_dir.mkdir(parents=True, exist_ok=True)
        img_dir = char_dir / "images"
        img_dir.mkdir(parents=True, exist_ok=True)
        
        char_json_path = char_dir / "character.json"
        
        char_data = {
            "id": model_id,
            "name": stem,
            "version": "1.0.0",
            "description": f"Imported from {zip_path.name}",
            "tags": ["live2d", "imported"],
            "model": {
                "type": "live2d",
                "path": rel_path,
                "scale": 0.85
            },
            "images": {
                "avatar": thumbnail,
                "card": thumbnail
            },
            "persona": {
                "name": stem
            },
            "accessories": [],
            "hitReactions": {
                "head": [
                    {"expression": "surprised", "motion": "nod"},
                    {"expression": "thinking", "motion": "thinking"}
                ],
                "body": [
                    {"expression": "smile", "motion": "nod"},
                    {"expression": "happy", "motion": "excited"}
                ]
            },
            "expressionFallback": {}
        }
        
        char_json_path.write_text(json.dumps(char_data, ensure_ascii=False, indent=2), encoding="utf-8")
        
        registry_path = characters_dir / "registry.json"
        if registry_path.exists():
            try:
                registry = json.loads(registry_path.read_text(encoding="utf-8"))
            except Exception:
                registry = {"version": "2.0.0", "characters": []}
        else:
            registry = {"version": "2.0.0", "characters": []}
            
        chars_list = registry.get("characters", [])
        chars_list = [c for c in chars_list if c.get("id") != model_id]
        
        new_entry = {
            "id": model_id,
            "path": f"characters/{model_id}/character.json",
            "default": False
        }
        chars_list.append(new_entry)
        registry["characters"] = chars_list
        registry_path.write_text(json.dumps(registry, ensure_ascii=False, indent=2), encoding="utf-8")
        
        # Sync via character registry
        try:
            from api.character_registry import character_registry
            character_registry.reload()
        except Exception as e:
            logger.error("Failed to reload character registry: %s", e)
        
        logger.info("[ModelImport] Registered model '%s' in character registry", model_id)

        return {"success": True, "model": new_entry}

    def _handle_GET_model_list(self):
        """
        GET /model/list
        Trả về danh sách model từ CharacterRegistry (cấu trúc mới).
        """
        try:
            from api.character_registry import character_registry
            # Reload to pick up any changes
            character_registry.reload()
            models = character_registry.get_all()
            
            # Thêm trường 'thumbnail_url' để backward compatibility nếu frontend cũ cần
            for m in models:
                if "images" in m and m["images"].get("avatar"):
                    m["thumbnail_url"] = m["images"]["avatar"]
                elif "thumbnail" in m:
                    m["thumbnail_url"] = m["thumbnail"]
                    
            self._send_json({"success": True, "models": models})
        except Exception as e:
            logger.error("[ModelList] Failed to read from registry: %s", e)
            self._send_json({"success": False, "models": [], "error": str(e)})


    def _handle_model_remove(self, payload: dict) -> dict:
        """
        POST /model/remove
        Payload: { "model_id": "<id>" }
        Xóa character khỏi character registry (characters/) và đồng bộ lại models.json.
        """
        model_id = (payload.get("model_id") or "").strip()
        if not model_id:
            return {"success": False, "error": "model_id is required"}

        from api.character_registry import character_registry

        success = character_registry.remove_character(model_id)
        if success:
            logger.info(f"[ModelRemove] Removed model '{model_id}' from character registry")
            return {"success": True, "removed": model_id}
        else:
            logger.warning(f"[ModelRemove] Model '{model_id}' not found or could not be removed")
            return {"success": False, "error": f"Model '{model_id}' not found or failed to remove"}

    def _send_chunk(self, data: dict) -> None:
        chunk_data = (json.dumps(data, ensure_ascii=False) + "\n").encode('utf-8')
        try:
            self.wfile.write(f"{len(chunk_data):x}\r\n".encode())
            self.wfile.write(chunk_data + b"\r\n")
            self.wfile.flush()
        except Exception as e:
            logger.warning("Failed to send chunk: %s", e)
            global _generation_interrupted
            _generation_interrupted = True
            raise ConnectionError("Client disconnected")

    async def _actual_handle_chat_stream(self, payload: dict) -> None:
        global _generation_interrupted
        _generation_interrupted = False
        text = str(payload.get("text", "")).strip()
        image = payload.get("image")
        context = payload.get("context", {})

        # Handle Pose & Mic Prop Commands
        if text.startswith("/sit"):
            self._send_chunk({"type": "command", "command": "sit"})
            self._send_chunk({"type": "text", "text": "Mình ngồi xuống đây nha! [smile]"})
            self._send_chunk({"type": "done", "text": "", "emotion": "smile", "motion": "nod", "audio_url": None, "duration_ms": 0})
            return

        if text.startswith("/stand"):
            self._send_chunk({"type": "command", "command": "stand"})
            self._send_chunk({"type": "text", "text": "Đứng lên thui nào! [happy]"})
            self._send_chunk({"type": "done", "text": "", "emotion": "happy", "motion": "nod", "audio_url": None, "duration_ms": 0})
            return

        if text.startswith("/mic"):
            self._send_chunk({"type": "command", "command": "mic"})
            self._send_chunk({"type": "text", "text": "Đã bật/tắt micro của mình rồi nhé! [wink]"})
            self._send_chunk({"type": "done", "text": "", "emotion": "wink", "motion": "nod", "audio_url": None, "duration_ms": 0})
            return

        # Xử lý các lệnh chat đổi mô hình nhanh
        if text.startswith("/model "):
            new_provider = text.removeprefix("/model ").strip().lower()
            if new_provider in ["ollama", "gemini", "openai", "deepseek", "glm", "qwen", "openai-compatible"]:
                try:
                    config.set("llm.provider", new_provider)
                    provider_names = {
                        "ollama": "Ollama (Chạy local trên máy)",
                        "gemini": "Gemini API (Đám mây siêu nhẹ)",
                        "openai": "OpenAI API (Đám mây)",
                        "deepseek": "DeepSeek API",
                        "glm": "Zhipu GLM API",
                        "qwen": "DashScope Qwen API",
                        "openai-compatible": "OpenAI-Compatible Custom API"
                    }
                    self._send_chunk({"type": "text", "text": f"Đã chuyển sang dùng bộ não {provider_names[new_provider]} thành công! [wink] Từ giờ mình sẽ dùng mô hình này nhé."})
                    self._send_chunk({"type": "done", "text": "", "emotion": "wink", "motion": "nod", "audio_url": None, "duration_ms": 0})
                    return
                except Exception as e:
                    self._send_chunk({"type": "text", "text": f"Có lỗi khi chuyển mô hình: {e}"})
                    self._send_chunk({"type": "done", "text": "", "emotion": "sad", "motion": "shake", "audio_url": None, "duration_ms": 0})
                    return
            else:
                self._send_chunk({"type": "text", "text": "Mô hình không hợp lệ. Vui lòng gõ: `/model ollama`, `/model gemini`, `/model openai`, `/model deepseek`, `/model glm`, `/model qwen`, hoặc `/model openai-compatible` nhé!"})
                self._send_chunk({"type": "done", "text": "", "emotion": "thinking", "motion": "idle", "audio_url": None, "duration_ms": 0})
                return

        if text.startswith("/stt "):
            new_stt = text.removeprefix("/stt ").strip().lower()
            if new_stt in ["tiny", "base", "small", "funasr"]:
                try:
                    config.set("stt.model", new_stt)
                    
                    # Tải lại STT Service
                    global _stt_service
                    _stt_service = None
                    
                    self._send_chunk({"type": "text", "text": f"Đang tải lại bộ nhận dạng giọng nói mô hình '{new_stt}'... [thinking]"})
                    
                    def reload_stt_thread():
                        try:
                            get_stt()
                            logger.info("STT reloaded with model %s", new_stt)
                        except Exception as e:
                            logger.error("Failed to reload STT: %s", e)
                            
                    import threading
                    threading.Thread(target=reload_stt_thread, daemon=True).start()
                    
                    self._send_chunk({"type": "text", "text": f"Đã chuyển mô hình nhận dạng giọng nói sang '{new_stt}' thành công! [happy]"})
                    self._send_chunk({"type": "done", "text": "", "emotion": "happy", "motion": "nod", "audio_url": None, "duration_ms": 0})
                    return
                except Exception as e:
                    self._send_chunk({"type": "text", "text": f"Có lỗi khi chuyển mô hình STT: {e}"})
                    self._send_chunk({"type": "done", "text": "", "emotion": "sad", "motion": "shake", "audio_url": None, "duration_ms": 0})
                    return
            else:
                self._send_chunk({"type": "text", "text": "Mô hình STT không hợp lệ. Vui lòng gõ: `/stt tiny`, `/stt base`, `/stt small` hoặc `/stt funasr` nhé!"})
                self._send_chunk({"type": "done", "text": "", "emotion": "thinking", "motion": "idle", "audio_url": None, "duration_ms": 0})
                return

        # Trích xuất tri thức từ câu thoại của người dùng (Real-time learning)
        try:
            from learning.knowledge.knowledge_extractor import knowledge_extractor
            knowledge_extractor.extract_from_text(text)
        except Exception as le_err:
            logger.warning("Failed to run knowledge_extractor on chat message stream: %s", le_err)

        # 1. Quản lý Mối quan hệ và Tâm trạng
        planner = router.planner
        memory = planner.memory.service
        
        # Ghi nhận thời gian tương tác và lấy bối cảnh thời gian trôi qua (nếu có)
        time_note = memory.record_interaction()
        
        # Phân tích thái độ câu chat của người dùng và cập nhật điểm mối quan hệ, tâm trạng
        memory.analyze_sentiment_and_update(text)
        
        # Lấy trạng thái hiện tại để đưa vào bối cảnh hệ thống
        rel_info = memory.get_relationship()
        mood = memory.get_mood()
        
        # Nạp trạng thái vào context gửi cho LLM
        context["companion"] = {
            "rel_level": rel_info["level"],
            "rel_score": rel_info["score"],
            "mood": mood,
            "time_note": time_note
        }

        # Truy xuất ký ức/facts liên quan (Memory) để đưa vào context
        context["memory"] = memory.recall(text)

        # Tầng 1: PerceptionFusion
        from perception.fusion.perception_fusion import PerceptionFusion
        from cognition.context.context_manager import context_manager
        from dataclasses import asdict
        
        context_packet = PerceptionFusion.fuse(
            user_message=text,
            screen_text=screen_watcher.get_current_context() if screen_watcher else "",
            last_interaction_time=_last_interaction_time,
            activity=screen_watcher.get_current_activity() if screen_watcher else "unknown"
        )
        context_manager.add_packet(context_packet)
        context["perception"] = asdict(context_packet)

        # Intent detection
        intent = planner.detect_intent(text)

        # RAG context injection (Only if RAG query is detected)
        if intent["name"] == "rag_query":
            rag = get_rag()
            if rag:
                try:
                    rag_context = rag.build_context(text, n_results=3)
                    if rag_context:
                        context["rag_context"] = rag_context
                except Exception as exc:
                    logger.warning("RAG retrieval failed: %s", exc)

        # Trạng thái cảm xúc khởi đầu dựa trên tâm trạng hiện tại
        initial_emotion = "thinking"
        if mood == "hơi dỗi":
            initial_emotion = "angry"
        elif mood == "vui vẻ":
            initial_emotion = "smile"
            
        if intent["name"] in ["open_app"]:
            initial_emotion = "excited"

        initial_motion = "thinking" if intent["name"] in ["llm_chat", "rag_query"] else "idle"

        self._send_chunk({"type": "start", "emotion": initial_emotion, "motion": initial_motion})

        if intent["name"] in ["llm_chat", "rag_query"]:
            from runtime.state.state_store import state_store, CompanionState
            await state_store.transition(CompanionState.THINKING)

            # Tầng 4: Cognition — LLM Reasoning
            from cognition.reasoning.cognition import CognitionEngine
            cognition = CognitionEngine(planner.llm)
            
            # Khởi tạo SentenceAudioStreamer để tạo TTS ngay lập tức khi xong câu
            tts_service = get_tts()
            audio_streamer = SentenceAudioStreamer(tts_service, self._send_chunk) if tts_service else None
            
            text_chunks = []
            current_emotion = initial_emotion

            # P2: Fan-out multiplexor — UI + TTS + Emotion chạy song song (J.A.I.son pattern)
            async def _ui_collect_consumer(stream):
                """Consumer 1: gửi text/approval ra UI và collect full reply."""
                async for chunk in stream:
                    if _generation_interrupted:
                        logger.info("Generation interrupted by client request.")
                        break
                    if chunk["type"] == "request_approval":
                        self._send_chunk(chunk)
                    elif chunk["type"] == "text":
                        text_chunks.append(chunk["text"])
                        self._send_chunk(chunk)

            async def _tts_consumer(stream):
                """Consumer 2: feed vào SentenceAudioStreamer — TTS song song với UI."""
                if not audio_streamer:
                    return
                async for chunk in stream:
                    if _generation_interrupted:
                        break
                    if chunk["type"] == "text" and not chunk.get("thought"):
                        await audio_streamer.feed_text(chunk["text"])

            async def _emotion_consumer(stream):
                """Consumer 3: detect emotion từ LLM tag."""
                nonlocal current_emotion
                async for chunk in stream:
                    if chunk["type"] == "emotion":
                        current_emotion = chunk["emotion"]
                        self._send_chunk(chunk)

            from utils.stream_helpers import fanout
            await fanout(
                cognition.reason_stream(text, context, image=image),
                [_ui_collect_consumer, _tts_consumer, _emotion_consumer]
            )

            # Flush remaining buffer của audio streamer
            if audio_streamer:
                await audio_streamer.flush()

            full_reply = "".join(text_chunks).strip()

            # P1: Emotion roberta fallback — nếu LLM không trả về emotion tag
            if current_emotion in ("thinking", initial_emotion):
                try:
                    from persona.dialogue.emotion_roberta import detect_emotion
                    detected = detect_emotion(full_reply)
                    if detected and detected != "normal":
                        current_emotion = detected
                        self._send_chunk({"type": "emotion", "emotion": current_emotion})
                except Exception:
                    pass  # Silent fallback — không crash nếu model chưa load

            # Ghi nhận hội thoại để tự phản chiếu ký ức và gọi Memory Write-back
            try:
                memory.add_to_conversation_history("user", text)
                memory.add_to_conversation_history("assistant", full_reply)
                memory.write_back_memory(text, full_reply)
                
                # NÂNG CẤP: Chạy nền phân tích cảm xúc & đúc kết nhật ký nếu đủ câu thoại
                memory.analyze_sentiment_async(text, full_reply)
                memory.write_diary_if_needed()
            except Exception as e:
                logger.warning("Error in background memory/sentiment/diary processing: %s", e)

            # Không cần tạo TTS tổng ở cuối nữa vì đã phát gối đầu theo từng câu trong luồng stream rồi
            self._send_chunk({
                "type": "done",
                "text": full_reply,
                "emotion": current_emotion,
                "motion": "idle",
                "audio_url": None,
                "duration_ms": 0
            })
            from runtime.state.state_store import state_store, CompanionState
            await state_store.transition(CompanionState.IDLE)
        elif intent["name"] == "coding_task":
            # Coding task: run CodingAgent
            from runtime.state.state_store import state_store, CompanionState
            await state_store.transition(CompanionState.PLANNING)

            task = intent.get("task", text)
            from tools.registry import dispatch_tool
            result = await dispatch_tool("run_coding_task", {"task": task})
            reply_text = result.get("summary", "Xong rồi!")

            # Stream từng step về frontend qua WebSocket
            for step in result.get("steps", []):
                ws_broadcast({
                    "type": "coding_step",
                    "step": step["step"],
                    "message": step["message"],
                })

            response = {
                "emotion": "excited" if result.get("success") else "sad",
                "avatar": {
                    "motion": "nod" if result.get("success") else "shake"
                }
            }

            self._send_chunk({"type": "text", "text": reply_text})
        else:
            # Local intent: execute synchronously
            from runtime.state.state_store import state_store, CompanionState
            await state_store.transition(CompanionState.PLANNING)
            
            response = await router.route({**payload, "text": text, "context": context})
            reply_text = response.get("text", "")

            self._send_chunk({"type": "text", "text": reply_text})

            # Run TTS
            audio_url = None
            duration_ms = 0
            tts = get_tts()
            if tts and reply_text:
                try:
                    await state_store.transition(CompanionState.SPEAKING)
                    tts_result = await tts.speak(reply_text)
                    if tts_result.get("success") and tts_result.get("audio_url"):
                        audio_url = tts_result["audio_url"]
                        duration_ms = tts_result.get("duration_ms", 0)
                except Exception as exc:
                    logger.warning("TTS failed: %s", exc)

            self._send_chunk({
                "type": "done",
                "text": reply_text,
                "emotion": response.get("emotion", "friendly"),
                "motion": response.get("avatar", {}).get("motion", "nod"),
                "audio_url": audio_url,
                "duration_ms": duration_ms
            })
            await state_store.transition(CompanionState.IDLE)

    async def _handle_chat_stream(self, payload: dict) -> None:
        global _ai_busy
        _ai_busy = True
        try:
            await self._actual_handle_chat_stream(payload)
        finally:
            _ai_busy = False

    async def _handle_swe_stream(self, payload: dict) -> None:
        prompt = payload.get("prompt", "").strip()
        directory = payload.get("directory", "").strip()

        if not prompt or not directory:
            self._send_chunk({"type": "error", "message": "Thiếu thông tin prompt hoặc directory."})
            return

        from agents.coding.swe_service import run_swe_task_api

        async def progress_callback(event: dict):
            self._send_chunk(event)

        try:
            await run_swe_task_api(prompt, directory, progress_callback)
        except Exception as e:
            logger.error(f"Error in SWE stream execution: {e}", exc_info=True)
            self._send_chunk({"type": "error", "message": f"Hệ thống gặp lỗi: {e}"})

    async def _handle_chat(self, payload: dict) -> dict:
        global _ai_busy
        _ai_busy = True
        try:
            return await self._actual_handle_chat(payload)
        finally:
            _ai_busy = False

    async def _actual_handle_chat(self, payload: dict) -> dict:
        text = str(payload.get("text", "")).strip()
        context = payload.get("context", {})

        # Trích xuất tri thức từ câu thoại của người dùng (Real-time learning)
        try:
            from learning.knowledge.knowledge_extractor import knowledge_extractor
            knowledge_extractor.extract_from_text(text)
        except Exception as le_err:
            logger.warning("Failed to run knowledge_extractor on chat message: %s", le_err)

        # Intent detection
        planner = router.planner
        intent = planner.detect_intent(text)

        # RAG context injection (Only if RAG query is detected)
        if intent["name"] == "rag_query":
            rag = get_rag()
            if rag:
                try:
                    rag_context = rag.build_context(text, n_results=3)
                    if rag_context:
                        context["rag_context"] = rag_context
                except Exception as exc:
                    logger.warning("RAG retrieval failed: %s", exc)

        if intent["name"] == "coding_task":
            task = intent.get("task", text)
            from tools.registry import dispatch_tool
            result = await dispatch_tool("run_coding_task", {"task": task})
            reply = result.get("summary", "Xong rồi!")
            # Stream từng step về frontend qua WebSocket
            for step in result.get("steps", []):
                ws_broadcast({
                    "type": "coding_step",
                    "step": step["step"],
                    "message": step["message"],
                })
            response = {
                "type": "assistant.response",
                "text": reply,
                "emotion": "excited" if result.get("success") else "sad",
                "avatar": {
                    "expression": "excited" if result.get("success") else "sad",
                    "motion": "nod" if result.get("success") else "shake",
                    "lipsync": True
                }
            }
        else:
            response = await router.route({**payload, "text": text, "context": context})

        # TTS
        tts = get_tts()
        if tts and response.get("text"):
            try:
                tts_result = await tts.speak(response["text"])
                if tts_result.get("success") and tts_result.get("audio_url"):
                    response["audio_url"] = tts_result["audio_url"]
                    response["duration_ms"] = tts_result.get("duration_ms", 0)
            except Exception as exc:
                logger.warning("TTS failed: %s", exc)

        # Ghi nhận hội thoại để tự phản chiếu ký ức
        try:
            memory = planner.memory.service
            memory.add_to_conversation_history("user", text)
            memory.add_to_conversation_history("assistant", response.get("text", ""))
        except Exception:
            pass

        response.setdefault("id", payload.get("id", "assistant_response"))
        return response

    async def _handle_stt(self, payload: dict) -> dict:
        stt = get_stt()
        if not stt:
            return {
                "success": False,
                "error": "STT chưa sẵn sàng. Cài: pip install faster-whisper",
            }

        from runtime.state.state_store import state_store, CompanionState
        await state_store.transition(CompanionState.LISTENING)

        sequence = payload.get("sequence")
        timestamp = payload.get("timestamp")
        is_draft = payload.get("is_draft", False)
        if sequence is not None:
            logger.info("ASR Transcribing Frame: seq=%s, ts=%s, is_draft=%s", sequence, timestamp, is_draft)

        audio_bytes_list = payload.get("audio_bytes")
        mime_type = payload.get("mime_type", "audio/webm")

        if not audio_bytes_list:
            await state_store.transition(CompanionState.IDLE)
            return {"success": False, "error": "Không có audio_bytes."}

        try:
            raw = bytes(audio_bytes_list)
        except Exception:
            await state_store.transition(CompanionState.IDLE)
            return {"success": False, "error": "audio_bytes không hợp lệ."}

        suffix = ".webm" if "webm" in mime_type else ".wav"
        try:
            res = await stt.transcribe_bytes(raw, suffix=suffix)
            return res
        finally:
            await state_store.transition(CompanionState.IDLE)

    async def _handle_rag_import(self, payload: dict) -> dict:
        rag = get_rag()
        if not rag:
            return {"success": False, "error": "RAG chưa sẵn sàng."}
        doc_path = payload.get("path", "")
        if not doc_path:
            return {"success": False, "error": "Thiếu path."}
        return rag.import_document(doc_path)

    def _handle_rag_delete(self, payload: dict) -> dict:
        rag = get_rag()
        if not rag:
            return {"success": False, "error": "RAG chưa sẵn sàng."}
        doc_id = payload.get("doc_id", "")
        if not doc_id:
            return {"success": False, "error": "Thiếu doc_id."}
        try:
            rag.delete_document(doc_id)
            return {"success": True, "doc_id": doc_id}
        except Exception as exc:
            return {"success": False, "error": str(exc)}

    # ─── Utilities ───────────────────────────────────────────────────────────

    def _serve_file(self, file_path: Path) -> None:
        if not file_path.exists() or not file_path.is_file():
            self._send_json({"error": "File not found"}, status=404)
            return
        mime, _ = mimetypes.guess_type(str(file_path))
        mime = mime or "application/octet-stream"
        try:
            data = file_path.read_bytes()
            self.send_response(200)
            self._send_cors_headers()
            self.send_header("Content-Type", mime)
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Cache-Control", "max-age=3600")
            self.end_headers()
            self.wfile.write(data)
        except Exception as e:
            logger.warning("Failed to serve file %s: %s", file_path, e)


    def _read_json(self) -> dict[str, Any]:
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0:
            return {}
        raw = self.rfile.read(length).decode("utf-8")
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}

    def _send_empty(self, status: int) -> None:
        try:
            self.send_response(status)
            self._send_cors_headers()
            self.end_headers()
        except Exception as e:
            logger.warning("Failed to send empty response: %s", e)

    def _send_json(self, payload: dict[str, Any], status: int = 200) -> None:
        try:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._send_cors_headers()
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except Exception as e:
            logger.warning("Failed to send json response: %s", e)


    def _send_cors_headers(self) -> None:
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def log_message(self, fmt: str, *args: Any) -> None:
        logger.info("%s - %s", self.address_string(), fmt % args)


# ─── PlannerAgent — RAG context injection ────────────────────────────────────
# Patch planner_agent để nhận rag_context và inject vào LLM prompt.
# Đặt ở đây để không sửa file planner_agent.py cũ.

def _patch_llm_service_for_rag():
    """No-op: RAG context support is now implemented natively inside LLMService."""
    pass


# ─── Entry ───────────────────────────────────────────────────────────────────

def main() -> None:
    global screen_watcher
    _patch_llm_service_for_rag()

    # Register services with the ServiceRegistry
    from runtime.services.service_registry import service_registry

    # 1. Backend check
    service_registry.register("backend", lambda: {"ok": True})

    # 2. LLM check
    def check_llm():
        llm_ok = False
        llm_error = None
        provider = "Unknown"
        model = "Unknown"
        try:
            from llm.manager import _get_llm_credentials
            provider, api_key, model, base_url = _get_llm_credentials()
            if provider == "ollama":
                import urllib.request
                try:
                    with urllib.request.urlopen("http://127.0.0.1:11434", timeout=1.0) as response:
                        llm_ok = response.status == 200 or response.status == 404
                except Exception as e:
                    llm_error = f"Ollama offline: {e}"
            else:
                if api_key:
                    llm_ok = True
                else:
                    llm_error = f"Missing API key for {provider}"
        except Exception as e:
            llm_error = str(e)
        return {"ok": llm_ok, "provider": provider, "model": model, "error": llm_error}

    service_registry.register("llm", check_llm)

    # 3. TTS check
    def check_tts():
        global _tts_service
        tts_ok = False
        tts_backend = config.get("tts.backend", config.get("tts.api", "edge"))
        try:
            tts_svc = _tts_service
            tts_ok = tts_svc is not None and tts_svc.available
        except Exception:
            pass
        return {"ok": tts_ok, "backend": tts_backend}

    service_registry.register("tts", check_tts)

    # 4. STT check
    def check_stt():
        global _stt_service
        stt_ok = False
        stt_model = config.get("stt.model", "base")
        try:
            stt_svc = _stt_service
            stt_ok = stt_svc is not None and stt_svc.available
        except Exception:
            pass
        return {"ok": stt_ok, "model": stt_model}

    service_registry.register("stt", check_stt)

    # 5. Memory check
    def check_memory():
        global _rag_retriever
        memory_ok = False
        try:
            rag_svc = _rag_retriever
            memory_ok = rag_svc is not None
        except Exception:
            pass
        return {"ok": memory_ok}

    service_registry.register("memory", check_memory)

    import threading

    def warmup():
        get_tts()
        get_rag()
        # STT warm-up chỉ nếu feature enabled
        if config.get("features.voice", False):
            get_stt()

        # Nạp trước mô hình Ollama vào bộ nhớ (RAM/VRAM)
        try:
            from llm.manager import _get_llm_credentials
            import urllib.request
            import json
            _, _, model, _ = _get_llm_credentials()
            payload = json.dumps({"model": model}).encode("utf-8")
            req = urllib.request.Request(
                "http://127.0.0.1:11434/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            # Dùng timeout ngắn để không block thread, nhưng Ollama sẽ nạp model ở nền
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp.read()
            logger.info("Ollama model '%s' preloaded successfully", model)
        except Exception as exc:
            logger.warning("Ollama preloading failed (Ollama server might not be running yet): %s", exc)

    def init_background_services():
        global screen_watcher
        try:
            logger.info("Starting background services initialization...")
            # P0: Khởi tạo CharacterRegistry để sync models.json
            from api.character_registry import character_registry
            character_registry.reload()

            # Khởi động ScreenWatcher
            from perception.screen.screen_watcher import ScreenWatcher
            screen_watcher = ScreenWatcher()
            screen_watcher.start()

            # Khởi động event loop chạy ngầm
            start_background_loop()

            # Đăng ký các tác vụ ngầm chạy tuần kỳ vào event loop
            asyncio.run_coroutine_threadsafe(_autonomous_agent_loop(), _background_loop)
            asyncio.run_coroutine_threadsafe(_twitch_commentator_loop(), _background_loop)

            # P1: Preload emotion roberta model ở background để tránh latency lần đầu
            def _preload_emotion_model():
                try:
                    from persona.dialogue.emotion_roberta import preload
                    preload()
                except Exception as e:
                    logger.warning("Emotion roberta model preload skipped: %s", e)
            import threading as _threading
            _threading.Thread(target=_preload_emotion_model, daemon=True).start()

            # ── Khởi động Life Loop (autonomous companion cycle) ──────────
            try:
                from life.life_loop import life_loop
                asyncio.run_coroutine_threadsafe(life_loop.start_async(), _background_loop)
                logger.info("LifeLoop: Scheduled for startup ✓")
            except Exception as ll_err:
                logger.warning("LifeLoop startup failed (non-critical): %s", ll_err)

            # Wire IdleAnimator and ReactionLibrary to notify UI
            try:
                from persona.behavior.idle.idle_animator import idle_animator
                from persona.behavior.reactions.reaction_library import reaction_library
                from persona.behavior.expression.expression_controller import expression_controller
                from persona.behavior.attention.attention_controller import attention_controller
                from persona.behavior.greeting.greeting_behavior import greeting_behavior

                idle_animator.set_send_callback(ws_broadcast)
                reaction_library.set_send_callback(ws_broadcast)
                expression_controller.set_send_callback(ws_broadcast)
                attention_controller.set_send_callback(ws_broadcast)
                greeting_behavior.set_send_callback(ws_broadcast)

                # Start idle animator loop
                asyncio.run_coroutine_threadsafe(idle_animator.start(), _background_loop)
                logger.info("IdleAnimator: Wired and scheduled for startup ✓")

                # Bridge EventBus Planning events to ws_broadcast (UI notifications)
                from runtime.eventbus.event_bus import event_bus
                from runtime.events.event_types import EventType

                def forward_planning_to_ws(event):
                    if hasattr(event, "to_dict"):
                        ws_broadcast(event.to_dict())
                    else:
                        ws_broadcast(event)

                event_bus.subscribe(EventType.PLAN_CREATED, forward_planning_to_ws)
                event_bus.subscribe(EventType.PLAN_STEP_STARTED, forward_planning_to_ws)
                event_bus.subscribe(EventType.PLAN_STEP_FINISHED, forward_planning_to_ws)
                event_bus.subscribe(EventType.PLAN_FINISHED, forward_planning_to_ws)
                event_bus.subscribe(EventType.PLAN_FAILED, forward_planning_to_ws)
                logger.info("EventBus Planning Bridge: Connected to WebSocket broadcast ✓")
            except Exception as anim_err:
                logger.warning("Failed to wire or start animator services / plan bridge: %s", anim_err)

            # Khởi động Twitch Client nếu được cấu hình sẵn
            sync_twitch_reader()

            # Khởi động Telegram Bot nếu được cấu hình sẵn
            try:
                from api.telegram_service import sync_telegram_service
                sync_telegram_service()
            except Exception as tg_err:
                logger.error("Failed to start Telegram service: %s", tg_err)

            # Khởi động Hotword Detector nếu được cấu hình sẵn
            global _hotword_detector
            if config.get("features.voice", False):
                try:
                    from speech.hotword.hotword_detector import HotwordDetector
                    def on_hotword_trigger():
                        logger.info("Hotword wake word detected. Broadcasting voice_listen start.")
                        trigger_notification({
                            "type": "voice_listen",
                            "action": "start"
                        })
                    _hotword_detector = HotwordDetector(on_wake=on_hotword_trigger)
                    _hotword_detector.start()
                    logger.info("HotwordDetector: Initialized and started background monitoring ✓")
                except Exception as hw_err:
                    logger.error("Failed to start HotwordDetector: %s", hw_err)

            # Chạy warm-up mô hình và tài nguyên
            warmup()
            logger.info("Background services initialization completed.")
        except Exception as err:
            logger.error("Error in init_background_services: %s", err)

    # Chạy khởi tạo ngầm để không block cổng kết nối HTTP
    threading.Thread(target=init_background_services, daemon=True).start()

    address = (config.host, config.port)
    httpd = ThreadingHTTPServer(address, CompanionRequestHandler)
    logger.info(
        "AI Companion Python service v0.2.0 listening on http://%s:%s",
        *address,
    )
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down.")
        if screen_watcher:
            screen_watcher.stop()
        if _hotword_detector:
            _hotword_detector.stop()
        
        # Đóng các session MCP
        try:
            from llm.manager import LLMService
            if LLMService._mcp_manager:
                logger.info("MCP: Đang đóng các mcp server...")
                asyncio.run(LLMService._mcp_manager.aclose())
        except Exception as e:
            logger.error(f"MCP: Lỗi khi đóng mcp server: {e}")

        httpd.server_close()


if __name__ == "__main__":
    main()
