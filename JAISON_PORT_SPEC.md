# Port tính năng từ J.A.I.son — Spec cho antigravity

> Đọc kỹ từng task. Mỗi task có: **trạng thái hiện tại**, **vấn đề**, **code cụ thể cần viết**, **file cần sửa**, **DoD**.
> Làm theo thứ tự P0 → P1 → P2.

---

## Tóm tắt nhanh những gì cần làm

| Task | File | Độ khó | Thời gian |
|------|------|--------|-----------|
| P0-1: `filter_clean` cho proactive TTS | `api/server.py` | Dễ | 15 phút |
| P0-2: `_speak_and_notify_proactive` dùng SentenceAudioStreamer | `api/server.py` | Trung bình | 30 phút |
| P1: `emotion_roberta` fallback | `persona/dialogue/emotion_parser.py` + `api/server.py` | Trung bình | 1.5 giờ |
| P2: `multiplexor` fan-out | `api/server.py` | Khó | 2 giờ |

---

## Bối cảnh: Những gì J.A.I.son làm mà DeskAgent học được

Đọc source code J.A.I.son thực tế (không phải README) — 3 pattern quan trọng:

1. **Text filter pipeline** — clean tag trước TTS, split câu trước TTS, detect emotion độc lập với LLM
2. **Streaming pipeline** — LLM generate → split câu → TTS song song, không đợi toàn bộ response
3. **Fan-out multiplexor** — 1 stream broadcast đến nhiều consumer (emotion + TTS + log) đồng thời

DeskAgent V8 đã có `SentenceAudioStreamer` trong chat chính — tốt. Nhưng còn 3 chỗ chưa áp dụng.

---

## P0-1 — `filter_clean` nhất quán toàn bộ TTS pipeline (15 phút)

### Vấn đề hiện tại

`_speak_sentence()` trong `SentenceAudioStreamer` đã clean:
```python
clean_s = re.sub(r"\[.*?\]", "", sentence).strip()
clean_s = clean_s.replace("(", "").replace(")", "").strip()
```

Nhưng `_speak_and_notify_proactive()` dòng 275 chỉ làm một phần:
```python
speak_text = re.sub(r"\[.*?\]", "", clean_reply).strip()
# Thiếu: không strip dấu ngoặc đơn ()
# Thiếu: không strip dấu * (markdown bold/italic từ LLM)
# Thiếu: không strip ``` code blocks
```

Và Twitch commentator dòng 564 cũng làm tương tự — thiếu các pattern trên.

### Sửa

**Bước 1 — Tạo hàm utility chung** trong `api/server.py`, đặt ngay sau phần `import`:

```python
def clean_for_tts(text: str) -> str:
    """Làm sạch text trước khi đưa vào TTS — loại bỏ tag, markdown, ký tự đặc biệt."""
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
```

**Bước 2 — Thay thế tất cả chỗ dùng `re.sub(r"\[.*?\]", ...)` bằng `clean_for_tts()`:**

Trong `_speak_and_notify_proactive()` dòng 275:
```python
# Thay:
speak_text = re.sub(r"\[.*?\]", "", clean_reply).strip()

# Bằng:
speak_text = clean_for_tts(clean_reply)
```

Trong Twitch commentator dòng 564:
```python
# Thay:
speak_text = re.sub(r"\[.*?\]", "", clean_reply).strip()

# Bằng:
speak_text = clean_for_tts(clean_reply)
```

Trong `_speak_sentence()` của `SentenceAudioStreamer` dòng 664:
```python
# Thay:
clean_s = re.sub(r"\[.*?\]", "", sentence).strip()
clean_s = clean_s.replace("(", "").replace(")", "").strip()

# Bằng:
clean_s = clean_for_tts(sentence)
```

### DoD
- LLM trả về response có `**bold**`, `*italic*`, `` `code` `` → TTS không đọc các ký tự markdown đó
- LLM trả về `[emotion:happy]` trong text → không bị đọc thành tiếng
- Kiểm tra: grep `re.sub.*\[.*\]` trong `api/server.py` → **0 kết quả** (tất cả đã dùng `clean_for_tts`)

---

## P0-2 — `_speak_and_notify_proactive` dùng `SentenceAudioStreamer` (30 phút)

### Vấn đề hiện tại

`_speak_and_notify_proactive()` dùng để phát TTS cho proactive messages (screen comments, auto chat). Hiện tại nó gọi `tts.speak(full_text)` một lần cho toàn bộ response — đợi TTS xong mới phát. Không có streaming.

So sánh với chat chính đã dùng `SentenceAudioStreamer` — response dài có thể phát câu 1 trong khi câu 2 đang TTS. Proactive messages cũng có thể dài (screen comment 2-3 câu) — nên áp dụng cùng pattern.

### Sửa

Sửa toàn bộ `_speak_and_notify_proactive()`:

```python
async def _speak_and_notify_proactive(full_reply: str, type_name: str):
    global _ai_busy
    try:
        from persona.dialogue.emotion_parser import EmotionStreamParser
        parser = EmotionStreamParser()
        
        # Parse emotion từ reply
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

        # Dùng SentenceAudioStreamer để stream audio theo từng câu
        audio_chunks = []

        def collect_chunk(chunk):
            """Collector thay vì gửi qua WebSocket — gom audio chunks lại."""
            if chunk.get("type") == "audio":
                audio_chunks.append(chunk)

        from runtime.state.state_store import state_store, CompanionState
        await state_store.transition(CompanionState.SPEAKING)
        
        streamer = SentenceAudioStreamer(tts, collect_chunk)
        
        # Feed từng câu vào streamer
        for sentence in re.split(r"(?<=[.!?])\s+", clean_reply):
            if sentence.strip():
                await streamer.feed_text(sentence + " ")
        
        await streamer.flush()

        # Sau khi tất cả câu được TTS, trigger notification với audio đầu tiên
        # (các câu tiếp theo đã được collect_chunk gom lại)
        first_audio = audio_chunks[0] if audio_chunks else None
        trigger_notification({
            "type": type_name,
            "text": clean_reply,
            "emotion": final_emotion,
            "audio_url": first_audio["audio_url"] if first_audio else None,
            "duration_ms": sum(c.get("duration_ms", 0) for c in audio_chunks),
            # Gửi thêm tất cả audio chunks để frontend phát lần lượt
            "audio_chunks": audio_chunks
        })
        
    except Exception as e:
        logger.warning(f"Proactive TTS speak failed: {e}")
    finally:
        from runtime.state.state_store import state_store, CompanionState
        await state_store.transition(CompanionState.IDLE)
```

**Bước 2 — Cập nhật frontend nhận `audio_chunks`** trong `renderer/overlay/app.js`:

Tìm chỗ xử lý notification `screen_comment` hoặc `proactive`:

```js
// Tìm handler nhận proactive notification, thêm xử lý audio_chunks:
case "screen_comment":
case "proactive": {
  const chunks = data.audio_chunks || [];
  if (chunks.length > 0) {
    // Phát lần lượt từng chunk
    for (const chunk of chunks) {
      await audioPlayer.play(chunk.audio_url);
    }
  } else if (data.audio_url) {
    // Fallback: phát 1 audio như cũ
    await audioPlayer.play(data.audio_url);
  }
  break;
}
```

### DoD
- Proactive message dài 3 câu → câu 1 bắt đầu phát trong ~0.5s (không đợi 3 câu TTS xong)
- Kiểm tra log: xuất hiện `SentenceAudioStreamer` log cho proactive path

---

## P1 — `emotion_roberta` fallback khi LLM không trả về emotion tag (1.5 giờ)

### Vấn đề hiện tại

`EmotionStreamParser` parse `[emotion:happy]` từ LLM output. Khi LLM nhỏ (Ollama local model) hoặc không follow instruction tốt, tag này bị miss → nhân vật stuck ở emotion mặc định.

J.A.I.son dùng `SamLowe/roberta-base-go_emotions` (~66MB) để detect emotion trực tiếp từ text — không phụ thuộc LLM format. DeskAgent đã có `torch` và `sentence-transformers` trong `requirements.txt` → không cần thêm dependency.

### Sửa

**Bước 1 — Tạo file `persona/dialogue/emotion_roberta.py`:**

```python
"""
Fallback emotion detector dùng roberta-base-go_emotions.
Chỉ load model khi cần — lazy singleton.
"""
import logging
from functools import lru_cache

logger = logging.getLogger(__name__)

# Map 28 go_emotions labels → DeskAgent emotion strings
ROBERTA_TO_EMOTION = {
    "joy":          "happy",
    "amusement":    "happy",
    "excitement":   "excited",
    "love":         "smile",
    "gratitude":    "smile",
    "admiration":   "smile",
    "approval":     "smile",
    "caring":       "friendly",
    "pride":        "smile",
    "optimism":     "smile",
    "relief":       "smile",
    "sadness":      "sad",
    "grief":        "sad",
    "disappointment": "sad",
    "remorse":      "sad",
    "anger":        "angry",
    "annoyance":    "angry",
    "disgust":      "angry",
    "fear":         "surprised",
    "nervousness":  "surprised",
    "surprise":     "surprised",
    "confusion":    "thinking",
    "curiosity":    "thinking",
    "realization":  "thinking",
    "embarrassment": "shy",
    "desire":       "smile",
    "neutral":      "normal",
    "disapproval":  "angry",
}

_classifier = None

def _get_classifier():
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline
            import torch
            device = "cuda" if torch.cuda.is_available() else "cpu"
            _classifier = pipeline(
                task="text-classification",
                model="SamLowe/roberta-base-go_emotions",
                top_k=1,
                device=device
            )
            logger.info(f"[EmotionRoberta] Model loaded on {device}")
        except Exception as e:
            logger.warning(f"[EmotionRoberta] Failed to load model: {e}")
            _classifier = False  # Đánh dấu failed, không thử lại
    return _classifier if _classifier else None


def detect_emotion(text: str, min_score: float = 0.4) -> str | None:
    """
    Detect emotion từ text. Trả về DeskAgent emotion string hoặc None nếu không đủ confident.
    
    Args:
        text: Text cần detect (nên là response đã được clean, không có tag)
        min_score: Ngưỡng confidence tối thiểu (0.0–1.0). Dưới ngưỡng → trả về None
    
    Returns:
        Emotion string ("happy", "sad", "angry", "surprised", "thinking", "normal", ...) hoặc None
    """
    if not text or len(text.strip()) < 5:
        return None
    
    classifier = _get_classifier()
    if classifier is None:
        return None
    
    try:
        result = classifier(text[:512])[0][0]  # Giới hạn 512 chars
        label = result["label"]
        score = result["score"]
        
        if score < min_score:
            return None
        
        return ROBERTA_TO_EMOTION.get(label, "normal")
    except Exception as e:
        logger.warning(f"[EmotionRoberta] Inference failed: {e}")
        return None


def preload():
    """Preload model ở startup để tránh latency lần đầu."""
    _get_classifier()
```

**Bước 2 — Tích hợp vào chat handler trong `api/server.py`:**

Tìm đoạn sau khi `full_reply` được build xong (sau `audio_streamer.flush()`), trước `self._send_chunk({"type": "done", ...})`:

```python
# Sau dòng: full_reply = "".join(full_reply_parts).strip()
# Thêm fallback emotion detection nếu LLM không trả về emotion tag:

if current_emotion in ("thinking", initial_emotion):
    # LLM có thể không trả về emotion tag → thử detect từ text
    try:
        from persona.dialogue.emotion_roberta import detect_emotion
        detected = detect_emotion(full_reply)
        if detected and detected != "normal":
            current_emotion = detected
            # Gửi emotion update ra UI
            self._send_chunk({"type": "emotion", "emotion": current_emotion})
    except Exception:
        pass  # Fallback silent — không crash nếu model chưa load
```

**Bước 3 — Preload model ở startup** trong `api/server.py`, trong `async def start()` hoặc `__init__`:

```python
# Trong startup, sau khi init các service:
def _preload_emotion_model():
    """Preload roberta emotion model ở background."""
    try:
        from persona.dialogue.emotion_roberta import preload
        preload()
    except Exception as e:
        logger.warning(f"Emotion model preload skipped: {e}")

import threading
threading.Thread(target=_preload_emotion_model, daemon=True).start()
```

**Bước 4 — Thêm vào `requirements.txt`** (nếu chưa có):

```
transformers>=4.40.0
```

(Kiểm tra trước: `sentence-transformers` đã pull `transformers` vào rồi — nếu vậy không cần thêm)

### DoD
- Dùng Ollama model nhỏ (qwen2:0.5b) không có emotion tag → nhân vật vẫn đổi emotion
- Log xuất hiện `[EmotionRoberta] Model loaded on cpu/cuda` khi startup
- Response text "Tôi rất vui được gặp bạn!" → detect `happy`, nhân vật cười
- Response text "Hmm, để tôi nghĩ xem..." → detect `thinking`, nhân vật pensieve face
- Nếu `transformers` không có → fallback silent, không crash app

---

## P2 — `multiplexor` fan-out: emotion detection song song với TTS (2 giờ)

### Vấn đề hiện tại

Hiện tại chat pipeline trong `api/server.py` chạy tuần tự:

```
LLM stream → parse emotion (tuần tự) → feed SentenceAudioStreamer (tuần tự)
```

Emotion parsing block TTS feed khi parse chậm. J.A.I.son dùng `multiplexor` để fan-out 1 stream đến nhiều consumer chạy song song.

### Giải pháp

Tạo `utils/stream_helpers.py` trong DeskAgent:

```python
"""
Fan-out một async generator đến nhiều consumer song song.
Port từ J.A.I.son multiplexor.py — đơn giản hóa cho DeskAgent use case.
"""
import asyncio
from typing import AsyncGenerator, Callable, List


async def fanout(
    source: AsyncGenerator,
    consumers: List[Callable[[AsyncGenerator], None]]
):
    """
    Broadcast từng item từ source đến tất cả consumers song song.
    
    Args:
        source: AsyncGenerator nguồn (ví dụ: LLM token stream)
        consumers: List các async functions nhận items từ source
    
    Example:
        async def tts_consumer(stream):
            async for item in stream:
                await audio_streamer.feed_text(item["text"])
        
        async def emotion_consumer(stream):
            async for item in stream:
                emotion = detect_emotion(item["text"])
                if emotion: send_chunk({"type": "emotion", "emotion": emotion})
        
        await fanout(llm_stream, [tts_consumer, emotion_consumer])
    """
    # Tạo queue cho mỗi consumer
    queues = [asyncio.Queue() for _ in consumers]
    done_events = [asyncio.Event() for _ in consumers]
    
    # Fan-out task: đọc source và broadcast
    async def broadcast():
        async for item in source:
            for q in queues:
                await q.put(item)
        for event in done_events:
            event.set()
    
    # Wrapper: queue → async generator cho mỗi consumer
    async def queue_to_gen(q: asyncio.Queue, done: asyncio.Event):
        while True:
            try:
                item = q.get_nowait()
                yield item
                q.task_done()
            except asyncio.QueueEmpty:
                if done.is_set() and q.empty():
                    break
                await asyncio.sleep(0)
    
    # Chạy broadcast và tất cả consumers song song
    broadcast_task = asyncio.create_task(broadcast())
    consumer_tasks = [
        asyncio.create_task(consumers[i](queue_to_gen(queues[i], done_events[i])))
        for i in range(len(consumers))
    ]
    
    await asyncio.gather(broadcast_task, *consumer_tasks)
```

**Áp dụng vào `api/server.py`** trong chat streaming handler:

```python
# Thay đoạn hiện tại (parse emotion + feed streamer tuần tự):
#
#   async for chunk in cognition.reason_stream(...):
#       if chunk["type"] == "text":
#           full_reply_parts.append(chunk["text"])
#           self._send_chunk(chunk)
#           if audio_streamer:
#               await audio_streamer.feed_text(chunk["text"])
#
# Bằng fan-out:

from utils.stream_helpers import fanout

text_chunks = []  # Buffer để collect full_reply

async def ui_and_collect_consumer(stream):
    """Consumer 1: gửi text ra UI và collect full reply."""
    async for chunk in stream:
        if chunk["type"] == "text":
            text_chunks.append(chunk["text"])
            self._send_chunk(chunk)

async def tts_consumer(stream):
    """Consumer 2: feed vào SentenceAudioStreamer."""
    if not audio_streamer:
        return
    async for chunk in stream:
        if chunk["type"] == "text" and not chunk.get("thought"):
            await audio_streamer.feed_text(chunk["text"])

async def emotion_consumer(stream):
    """Consumer 3: detect emotion từ chunk (J.A.I.son style)."""
    async for chunk in stream:
        if chunk["type"] == "emotion":
            nonlocal current_emotion
            current_emotion = chunk["emotion"]
            self._send_chunk(chunk)

# Chạy song song
await fanout(
    cognition.reason_stream(text, context, image=image),
    [ui_and_collect_consumer, tts_consumer, emotion_consumer]
)

# Flush sau khi tất cả consumers xong
if audio_streamer:
    await audio_streamer.flush()

full_reply = "".join(text_chunks).strip()
```

### DoD
- Log thời gian: với response 5 câu, câu 1 bắt đầu phát trong <1s sau khi LLM generate câu đầu
- Không có deadlock hay race condition — chạy 10 request liên tiếp không bị treo
- `utils/stream_helpers.py` có unit test đơn giản:
  ```python
  # tests/unit/test_stream_helpers.py
  async def test_fanout():
      items_a = []
      items_b = []
      
      async def source():
          for i in range(5):
              yield {"n": i}
      
      async def consumer_a(stream):
          async for item in stream:
              items_a.append(item["n"])
      
      async def consumer_b(stream):
          async for item in stream:
              items_b.append(item["n"])
      
      await fanout(source(), [consumer_a, consumer_b])
      assert items_a == [0,1,2,3,4]
      assert items_b == [0,1,2,3,4]
  ```

---

## Thứ tự thực thi

```
P0-1  clean_for_tts utility       15 phút   api/server.py
P0-2  proactive dùng streamer     30 phút   api/server.py + renderer/overlay/app.js
P1    emotion_roberta fallback     1.5 giờ  persona/dialogue/emotion_roberta.py + api/server.py
P2    fanout multiplexor           2 giờ    utils/stream_helpers.py + api/server.py
```

## Kiểm tra sau mỗi task

```bash
# Sau P0-1:
# Gõ message → LLM trả về **bold** text → TTS không đọc dấu **
grep -n "re.sub.*\[.*\]" api/server.py  # Phải = 0

# Sau P0-2:
# Trigger screen_comment → câu đầu phát trong <1s (không đợi full response)
# Kiểm tra log: "SentenceAudioStreamer" xuất hiện trong proactive path

# Sau P1:
# Dùng model nhỏ không có emotion tag → vẫn thấy emotion đổi trên avatar
# Log: "[EmotionRoberta] Model loaded"

# Sau P2:
# python -m pytest tests/unit/test_stream_helpers.py -v  → PASS
# Chat dài → câu đầu phát ngay, không đợi hết response
```
