# Đánh giá kỹ thuật Open LLM DeskAgent
## Dành cho antigravity — nhiệm vụ tiếp theo

> Tài liệu này là kết quả kiểm tra codebase ngày 08/07/2026.
> Mỗi hạng mục có: **trạng thái thực tế**, **vấn đề cụ thể**, **việc cần làm**, **file liên quan**, và **tiêu chí hoàn thành (DoD)**.
> Làm theo thứ tự P0 → P1 → P2. Sau mỗi hạng mục chạy lại `tests/test_phase*.py`.

---

## Bức tranh tổng thể

| Chỉ số | Giá trị |
|--------|---------|
| Test PASS (thực tế, bỏ lỗi pyautogui) | 38/46 |
| Số file trong project | 863 |
| Chỗ dùng `pass` / stub chưa implement | ~119 |
| Mức hoàn thiện tổng thể (ước lượng) | ~60% |

**Kiến trúc tổng thể tốt.** Event-driven qua EventBus, composable modules, lazy import đúng hướng. Vấn đề không phải thiết kế — mà là một số module còn skeleton và một dependency leak nghiêm trọng cần fix trước mọi thứ.

---

## 🔴 FIX TRƯỚC HẾT — pyautogui dependency leak (chặn toàn hệ thống)

### Vấn đề

`llm/manager.py` dòng 18 import thẳng:

```python
from tools.computer_control import mouse_click, mouse_move, keyboard_type, ...
```

`tools/computer_control.py` dòng 8:

```python
import pyautogui  # ← import ngay ở top-level
```

Hậu quả: **bất kỳ module nào import `LLMService` đều fail** ở môi trường không có display (headless, CI, WSL không có Xserver). Đây là nguyên nhân khiến 8 test fail với `No module named 'pyautogui'` — dù pyautogui không liên quan gì đến logic đang test.

### Việc cần làm

**Trong `tools/computer_control.py`:** chuyển toàn bộ import pyautogui sang lazy (chỉ import khi gọi hàm):

```python
# Thay vì:
import pyautogui

def mouse_click(x, y):
    pyautogui.click(x, y)

# Làm thành:
def mouse_click(x, y):
    import pyautogui  # lazy import
    pyautogui.click(x, y)
```

Áp dụng cho tất cả hàm trong file: `mouse_click`, `mouse_move`, `keyboard_type`, `keyboard_press`, `execute_command`, `click_element_by_vision`, `mouse_scroll`, `mouse_drag`.

**Không cần sửa `llm/manager.py`** — chỉ cần fix source của vấn đề.

### DoD

- Chạy `python tests/test_phase2_companion.py` trong môi trường không có display → **13/13 PASS** (không còn lỗi pyautogui).
- Chạy `python tests/test_phase3_agentic.py` → **16/16 PASS**.
- Chạy `python tests/test_milestones_completion.py` → **15/15 PASS**.
- Gọi `from llm.manager import LLMService` trong terminal không có X display không raise exception.

---

## Trục B — Agentic Skill (tiệm cận Claude Code)

### B0. [DONE ✓] Công cụ sửa file dạng patch chính xác

**Trạng thái:** Đã implement đúng và đầy đủ.

`tools/file_edit.py` có `str_replace_file` với validation "xuất hiện đúng 1 lần", `create_file` fail nếu file đã tồn tại. `tools/view_file.py` có số dòng. Đã đăng ký vào `tools/registry.py`. `coding_agent.py` đã dùng patch-based editing, không còn ghi đè toàn bộ file.

**Không cần làm thêm.** Chỉ cần đảm bảo unit test cho 2 edge case tồn tại:

```bash
# Kiểm tra
grep -l "str_replace_file\|create_file" tests/
```

Nếu chưa có test riêng → thêm vào `tests/unit/test_file_edit_tools.py` (file đã có, kiểm tra xem đã cover 2 edge case chưa):
- Patch đúng 1 đoạn trong file 500 dòng, phần còn lại không thay đổi.
- Patch fail an toàn (không sửa gì) khi `old_str` xuất hiện 2 lần.

---

### B1. [DONE ✓] Sandbox thực thi lệnh shell/terminal

**Trạng thái:** Đã implement.

`execution/sandbox/sandbox_runner.py` có: giới hạn `cwd`, timeout cứng, whitelist binary (git, pytest, npm, python), capture stdout/stderr, path traversal check (`_resolve_target`). `coding_agent.py` route qua sandbox.

**Việc cần confirm:**

```bash
python tests/unit/test_sandbox_runner.py
```

Nếu chưa có test cho trường hợp path traversal (`rm -rf /` bị chặn) và timeout (lệnh treo bị kill) → thêm vào `tests/unit/test_sandbox_runner.py`.

---

### B2. [DONE — cần verify UI] TaskPlan / checklist realtime

**Trạng thái:** Logic đã implement, chưa chắc renderer nhận được event.

`planning/task_graph/task_plan.py` có đủ `TaskPlan`, `TaskPlanStep` với states `pending/in_progress/done/failed`. `coding_agent.py` dòng 26 import và dòng 439–483 sinh TaskPlan trước khi sửa code, emit qua EventBus mỗi khi step đổi trạng thái.

**Vấn đề còn lại:** chưa xác nhận `renderer/chat/` có nhận và hiển thị event `TASK_PLAN_UPDATE` (hoặc tên tương đương) hay không.

**Việc cần làm:**

1. Xác định tên EventType được emit ở dòng 483 của `coding_agent.py`:
   ```bash
   grep -n "TASK_PLAN\|task_plan" agents/coding/coding_agent.py
   grep -n "TASK_PLAN\|task_plan" runtime/events/event_types.py
   ```

2. Tìm trong `renderer/chat/` hoặc `api/server.py` xem có subscriber nào xử lý event này không:
   ```bash
   grep -rn "TASK_PLAN\|task_plan_update\|checklist" renderer/ api/
   ```

3. Nếu chưa có subscriber → thêm handler trong `api/server.py` để forward event qua WebSocket ra frontend, và thêm UI component hiển thị checklist trong `renderer/chat/`.

**DoD:** Chạy 1 task coding thực tế qua IceGirl → trong log server xuất hiện task plan với danh sách bước, và UI chat hiển thị checklist với trạng thái cập nhật realtime (không chỉ "đang xử lý...").

---

### B3. [PARTIAL — cần hoàn thiện] Verification loop dừng sớm khi test pass

**Trạng thái:** Phần lớn đã làm, còn 1 lỗ hổng quan trọng.

`action_verifier.py` có `get_auto_verify_command`. `coding_agent.py` có `break` ở dòng 206 và 299 — có vẻ dừng sớm khi pass. Tuy nhiên:

**Vấn đề cần kiểm tra:**

```bash
grep -n "break\|success.*True\|returncode.*0" agents/coding/coding_agent.py | head -20
```

Cần xác nhận luồng verify thực sự `break` vòng lặp chính khi `success == True`, không chỉ break một inner loop.

Còn một vấn đề chắc chắn tồn tại: khi verify fail, traceback đang bị cắt (`output[:1000]` ở dòng 682) trước khi đưa vào prompt vòng tiếp theo. 1000 ký tự đủ cho lỗi đơn giản nhưng không đủ cho stack trace Python dài. Nên tăng lên `output[:3000]` hoặc lấy phần cuối (thường quan trọng hơn đầu):

```python
# Thay vì:
error_context = f"Lệnh: {verify_cmd}\nOutput:\n{output[:1000]}"

# Làm thành:
tail = output[-3000:] if len(output) > 3000 else output
error_context = f"Lệnh: {verify_cmd}\nOutput (phần cuối):\n{tail}"
```

**DoD:**
- Cố ý đưa 1 bug đơn giản (off-by-one) vào test file → agent tự sửa và dừng ngay vòng lặp khi test pass, log cho thấy số vòng thực tế < MAX_ITER.
- Stack trace đầy đủ (không bị cắt) xuất hiện trong LLM prompt của vòng retry.

---

### B4. [DONE ✓] Multi-agent coordinator: timeout + error isolation

**Trạng thái:** Đã implement đúng và đầy đủ.

`agent_coordinator.py` trong `execute_parallel_workflow` đã dùng `asyncio.wait_for` với timeout per-agent (vision 15s, coding 120s, default 60s), `asyncio.gather(*coros, return_exceptions=True)`, và xử lý từng exception riêng lẻ. 1 agent crash không ảnh hưởng kết quả tổng hợp.

**Không cần làm thêm.** Chỉ verify test:

```bash
# Test đã có ở:
python tests/test_phase8_9_multiagent_evolution.py
# Kết quả hiện tại: 6/6 PASS
```

---

### B5. [P2] Skill matching thông minh (không nạp tất cả SKILL.md)

**Trạng thái:** Chưa làm.

**Vấn đề:** `skills/skills_manager.py` hiện nạp tất cả SKILL.md vào context mọi lúc, không filter theo relevance. Với 8+ skill files, đây là token waste không cần thiết.

**Việc cần làm:**

1. Trong `skills/skills_manager.py`, thêm method `find_relevant_skills(task_description: str) -> list[str]`:
   - Đọc frontmatter `description:` từ mỗi SKILL.md (đã có sẵn — các file có `description:` field).
   - So sánh task với description dùng keyword matching đơn giản (không cần embedding).
   - Chỉ trả về skill nào có keyword overlap > 0.

2. Sửa nơi gọi `skills_manager` trong `llm/manager.py` hoặc `cognition/reasoning/cognition.py` để dùng `find_relevant_skills` thay vì load tất cả.

**DoD:** Với 5 task type khác nhau (code, pdf, excel, email, research), log cho thấy chỉ skill liên quan được nạp. Không còn tình trạng prompt engineering skill xuất hiện trong task "viết email".

---

## Trục A — Companion (tiệm cận Neuro-sama)

### A0. [P0] Twitch/stream integration — gap lớn nhất

**Trạng thái:** Skeleton tồn tại nhưng chưa kết nối với response pipeline.

`interaction/chat/twitch_bridge.py` có IRC socket, `_handle_incoming_message`, content moderation, throttle. Test unit cho content_moderator và event publishing đã pass. **Nhưng:** chưa có gì khởi động TwitchBridge từ `api/server.py`, chưa có response pipeline xử lý `VOICE_DETECTED` event từ Twitch, và chưa có demo chạy được.

Đây là **gap lớn nhất** so với Neuro-sama — core identity của Neuro-sama là stream interaction, không phải desktop assistant.

**Việc cần làm:**

**Bước 1 — Kết nối vào server startup** (`api/server.py`):

```python
# Trong startup event của FastAPI/aiohttp:
from interaction.chat.twitch_bridge import TwitchBridge
from config.config import config

twitch_channel = config.get("twitch.channel", "")
if twitch_channel:
    twitch_bridge = TwitchBridge(twitch_channel)
    twitch_bridge.start()  # chạy IRC listener trong background thread
```

**Bước 2 — Xử lý VOICE_DETECTED event từ Twitch** trong `api/server.py` hoặc một `TwitchResponseHandler`:

```python
async def handle_twitch_message(event):
    username = event.payload.get("username", "viewer")
    text = event.payload.get("text", "")
    # Gọi cùng pipeline xử lý message như khi user nhắn trực tiếp
    # nhưng thêm username vào context
    response = await llm_service.chat(
        f"[Twitch chat từ {username}]: {text}",
        context={"source": "twitch", "username": username}
    )
    # Emit response ra WebSocket UI
    await broadcast_ws({"type": "twitch_response", "text": response})

event_bus.subscribe(EventType.VOICE_DETECTED, handle_twitch_message)
```

**Bước 3 — Thêm throttle policy** vào `decision/policy_engine.py`:

```python
def check_twitch_response_policy(
    self,
    messages_per_minute: int,
    channel_size: int,  # ước lượng số viewer
) -> bool:
    """Không spam — chỉ reply khi message rate thấp hoặc message được ưu tiên."""
    if messages_per_minute > 10:
        return random.random() < 0.3  # reply 30% khi chat sôi
    return True
```

**Bước 4 — Config** (`config/companion.config.json`):

```json
{
  "twitch": {
    "channel": "",
    "bot_token": "",
    "response_throttle_per_minute": 5
  }
}
```

**DoD:**
- Thêm `twitch.channel = "your_test_channel"` vào config → chạy `npm start` → gõ message vào kênh Twitch → trong vòng 3 giây companion phản hồi trong UI.
- Toxic message bị filter, không có response.
- Khi chat sôi (>10 msg/min) chỉ reply khoảng 30% message, không spam.

---

### A1. [P1] Life Loop — hoạt động trong môi trường không có display

**Trạng thái:** Kiến trúc đúng, phụ thuộc nặng vào pyautogui cho screen capture.

`life/life_loop.py` có async loop đúng. Nhưng `life/observe/observer.py` gọi screen capture → pyautogui → crash headless. Companion không thể "sống" mà không quan sát màn hình, nhưng cũng không nên crash khi không có display.

**Việc cần làm:**

Trong `life/observe/observer.py`, wrap screen capture bằng try/except và fallback sang "blind observation":

```python
async def observe(self) -> ContextPacket:
    try:
        screenshot = _capture_screen()  # pyautogui
        ocr_text = _ocr(screenshot)
        active_window = _get_active_window()
    except Exception:
        # Fallback: observe mà không có màn hình
        ocr_text = ""
        active_window = "unknown"
        screenshot = None

    return ContextPacket(
        ocr_text=ocr_text,
        active_window=active_window,
        idle_seconds=_get_idle_seconds(),
        activity=_infer_activity(active_window, ocr_text),
        has_screen=screenshot is not None,
    )
```

Companion sẽ vẫn chạy Life Loop (Feel → Think → Decide → Act) ngay cả khi không thấy màn hình — chỉ thiếu context màn hình, không crash.

**DoD:** Chạy `python -c "from life.life_loop import LifeLoop; ll = LifeLoop(); ll.start()"` trong môi trường headless — không crash, log cho thấy life loop đang chạy với `has_screen=False`.

---

### A2. [P1] Proactive messenger — có nội dung thực sự

**Trạng thái:** `life/act/proactive_messenger.py` có infrastructure nhưng chưa rõ sinh nội dung gì để chủ động nói.

**Vấn đề:** Khi `decision_engine` quyết định "nên lên tiếng" (proactive speak allowed), companion cần có gì đó để nói. Hiện tại chưa có `ProactiveContentGenerator` rõ ràng.

**Việc cần làm:**

Trong `life/act/proactive_messenger.py`, thêm method `_generate_proactive_message` dựa trên context hiện tại:

```python
async def _generate_proactive_message(self, context: LifeContext) -> str:
    """Sinh nội dung chủ động dựa trên context. Dùng LLM, không hardcode."""
    from llm.manager import LLMService
    llm = LLMService()

    # Chọn prompt template dựa trên motivation hiện tại
    if context.motivation == "curiosity":
        prompt = f"Bạn đang nhìn thấy màn hình: '{context.ocr_text[:200]}'. Đặt 1 câu hỏi thú vị."
    elif context.motivation == "boredom":
        prompt = "User đang idle. Chủ động bắt chuyện ngắn gọn, vui vẻ."
    else:
        prompt = "Bình luận ngắn về những gì bạn đang quan sát trên màn hình."

    return await llm.generate(prompt, max_tokens=80)
```

**DoD:** Sau 10 phút idle (hoặc set `proactive_interval_seconds = 60` để test), companion tự nói 1 câu. Nội dung khác nhau mỗi lần (không hardcode). Silence Policy vẫn block khi user đang code.

---

### A3. [P1] Spontaneity parameter — tính ngẫu hứng có kiểm soát

**Trạng thái:** Chưa có.

**Vấn đề:** Companion hiện tại quá ổn định — mọi response đều follow prompt template. Neuro-sama hấp dẫn vì có yếu tố bất ngờ: bình luận ngoài kịch bản, phản ứng không đoán trước.

**Việc cần làm:**

1. Thêm `spontaneity: float` (0.0–1.0) vào `config/persona.config.json` cho từng nhân vật:
   ```json
   {
     "IceGirl": { "spontaneity": 0.3 },
     "Hiyori":  { "spontaneity": 0.5 },
     "Mao":     { "spontaneity": 0.2 },
     "Huohuo":  { "spontaneity": 0.1 }
   }
   ```

2. Trong `cognition/reasoning/cognition.py`, trước khi gọi LLM, với xác suất `spontaneity` thêm instruction vào system prompt:
   ```python
   import random
   if random.random() < persona.spontaneity:
       extra = random.choice([
           "Phản ứng bất ngờ, ra ngoài kịch bản một chút.",
           "Bình luận về điều gì đó không liên quan mà bạn vừa 'để ý'.",
           "Trêu chọc nhẹ user về việc họ đang làm.",
       ])
       system_prompt += f"\n[Spontaneous mode]: {extra}"
   ```

**DoD:** Log 20 response liên tiếp ở `spontaneity=0.0` vs `spontaneity=0.5` — nhận ra sự khác biệt bằng mắt thường. Không có response nào bị break (companion vẫn coherent, chỉ thêm yếu tố bất ngờ).

---

### A4. [P2] Voice latency — benchmark và optimize

**Trạng thái:** Chưa đo.

Neuro-sama phản hồi trong khoảng 500–800ms (streaming TTS + LLM). DeskAgent chưa có benchmark nào cho end-to-end latency (STT nhận xong → TTS bắt đầu phát).

**Việc cần làm:**

Thêm `scripts/benchmark_voice_latency.py`:

```python
import asyncio, time
from speech.stt.stt_service import STTService
from llm.manager import LLMService
from speech.tts.tts_service import TTSService

async def benchmark():
    stt = STTService()
    llm = LLMService()
    tts = TTSService()

    test_audio = open("tests/fixtures/sample_voice.wav", "rb").read()

    t0 = time.perf_counter()
    text = await stt.transcribe(test_audio)
    t1 = time.perf_counter()
    response = await llm.chat(text)
    t2 = time.perf_counter()
    audio_chunk = await tts.synthesize_first_chunk(response)
    t3 = time.perf_counter()

    print(f"STT: {(t1-t0)*1000:.0f}ms")
    print(f"LLM: {(t2-t1)*1000:.0f}ms")
    print(f"TTS first chunk: {(t3-t2)*1000:.0f}ms")
    print(f"Total to first audio: {(t3-t0)*1000:.0f}ms")

asyncio.run(benchmark())
```

**DoD:** Có số liệu cụ thể. Nếu total > 2000ms → investigate bottleneck và tối ưu phần chậm nhất (thường là LLM cold start với Ollama hoặc TTS không streaming).

---

## Không làm (out of scope)

- Không build multi-viewer streaming stack (donation alerts, subscriber events) — ngoài phạm vi "companion cá nhân".
- Không tự chế LLM/VLM riêng — tiếp tục dùng Ollama/Gemini/OpenAI.
- Không refactor lại EventBus hay kiến trúc module hiện tại — chỉ bổ sung, không đập đi xây lại.
- Không thêm Discord integration trong vòng này — Twitch trước.

---

## Thứ tự thực thi đề xuất

```
Fix pyautogui leak          → 1–2 giờ   → unblock toàn bộ test suite
B3 verify early stop        → 1 giờ     → cần B0 đã xong (đã xong)
B2 renderer checklist       → 2–3 giờ   → confirm UI nhận event, thêm component
A0 Twitch pipeline          → 4–6 giờ   → kết nối bridge vào server, thêm handler
A1 Life Loop headless safe  → 1 giờ     → wrap try/except trong observer
A2 Proactive content        → 2 giờ     → thêm content generator
A3 Spontaneity              → 1 giờ     → thêm param + inject vào prompt
B5 Skill matching           → 2 giờ     → keyword filter trong skills_manager
A4 Voice latency benchmark  → 1 giờ     → thêm script, không cần optimize ngay
```

Tổng ước lượng: **~20 giờ dev** để hoàn thiện từ 60% → 85%.

---

## Kiểm tra nhanh sau mỗi hạng mục

```bash
# Chạy sau mỗi thay đổi để đảm bảo không phá vỡ gì cũ:
python tests/test_phase2_companion.py
python tests/test_phase3_agentic.py
python tests/test_phase7_lifeloop.py
python tests/test_phase8_9_multiagent_evolution.py

# Mục tiêu sau khi fix pyautogui leak:
# Tất cả 4 file trên: 0 FAIL
```
