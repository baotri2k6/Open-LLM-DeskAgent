# DeskAgent — Roadmap Hoàn Thiện (dành để giao cho antygravity)

> Tài liệu này liệt kê các hạng mục cụ thể để nâng cấp Open-LLM-DeskAgent theo 2 trục:
> **(A) Companion — tiệm cận Neuro-sama** và **(B) Agentic skill — tiệm cận Claude Code**.
> Mỗi mục có: vấn đề hiện tại, việc cần làm, file/module liên quan, và tiêu chí hoàn thành (DoD)
> để Codex có thể tự chấm được là đã xong hay chưa.

---

## CÁCH DÙNG TÀI LIỆU NÀY

- Làm theo thứ tự ưu tiên **P0 → P1 → P2**. Không nhảy cóc sang P1 khi P0 chưa có test pass.
- Mỗi hạng mục nên là 1 PR/commit riêng, có kèm test.
- Sau mỗi hạng mục lớn, chạy lại bộ test tích hợp hiện có (`tests/test_phase*.py`) để đảm bảo không phá vỡ hệ thống cũ.
- Nếu một hạng mục cần thêm dependency mới, ghi rõ vào `requirements.txt` / `package.json`.

---

## TRỤC B — AGENTIC SKILL (ưu tiên trước vì rủi ro kỹ thuật + an toàn cao nhất)

### B0. [P0] Công cụ sửa file dạng patch chính xác (string-replace / diff-based edit)

**Vấn đề:** `mini_swe_runner.py` và `coding_agent.py` hiện sửa file bằng cách yêu cầu LLM viết lại toàn bộ nội dung file (hoặc chọn file qua JSON list), không có tool patch từng đoạn. Điều này gây: tốn token, dễ mất phần code không liên quan, khó review diff, dễ lỗi khi file dài.

**Việc cần làm:**

1. Tạo `tools/file_edit.py` với 2 tool mới:
   - `str_replace_file(path, old_str, new_str)`: bắt buộc `old_str` xuất hiện **đúng 1 lần** trong file, nếu 0 hoặc >1 lần thì trả lỗi rõ ràng (không đoán mò).
   - `create_file(path, content)`: tạo file mới, fail nếu đã tồn tại.
2. Đăng ký 2 tool này vào `tools/registry.py` (dùng `register_tool`) với JSON schema rõ ràng cho LLM function-calling.
3. Sửa `agents/coding/coding_agent.py` và `agents/coding/mini_swe_runner.py`: thay toàn bộ logic "LLM trả về full file content" bằng luồng gọi `str_replace_file`.
4. Thêm cơ chế **view file có số dòng** (`tools/view_file.py`) để LLM trích đúng `old_str` từ nội dung thật, tránh bịa ra chuỗi không khớp.

**DoD:**

- Unit test: patch đúng 1 đoạn trong file 500 dòng mà không đụng phần còn lại.
- Unit test: patch fail an toàn (không sửa gì) khi `old_str` xuất hiện 2 lần.
- `coding_agent.py` không còn chỗ nào yêu cầu LLM trả về toàn bộ nội dung file để ghi đè.

---

### B1. [P0] Sandbox thực thi lệnh shell/terminal

**Vấn đề:** `execution/terminal/terminal_executor.py` và `execution/filesystem/fs_executor.py` chạy lệnh trực tiếp trên máy thật, chỉ có `ApprovalRegistry` chặn ở tầng ý định — không có cô lập tiến trình thực sự (working dir giới hạn, timeout cứng, whitelist binary, giới hạn network).

**Việc cần làm:**

1. Thêm `execution/sandbox/sandbox_runner.py`:
   - Giới hạn `cwd` vào một thư mục project cụ thể (không cho `cd ..` ra ngoài root đã khai báo).
   - Timeout cứng cho mọi lệnh (mặc định 60s, cấu hình được).
   - Whitelist binary cho phép chạy tự do (git, pytest, npm, python) — lệnh ngoài whitelist bắt buộc qua `ApprovalRegistry`.
   - Capture stdout/stderr, giới hạn output size (tránh log bomb).
2. Route toàn bộ lệnh từ `agents/coding/*` và `execution/terminal/terminal_executor.py` qua `sandbox_runner` thay vì gọi `subprocess` trực tiếp.
3. Log mọi lệnh đã chạy (kể cả bị chặn) vào `runtime/logger.py` với tag riêng để audit sau này.

**DoD:**

- Test: lệnh `rm -rf /` hoặc thao tác ra ngoài `cwd` bị chặn, có log rõ lý do.
- Test: lệnh hợp lệ (`pytest`) chạy được, có timeout hoạt động (mock lệnh treo → bị kill đúng giờ).

---

### B2. [P1] Todo-list / Task tracking tường minh trong vòng lặp coding agent

**Vấn đề:** `coding_agent.py` có `MAX_ITER` nhưng không có danh sách bước công việc tường minh (todo list) để người dùng theo dõi tiến độ như Claude Code — hiện chỉ emit event chung chung.

**Việc cần làm:**

1. Thêm dataclass `TaskPlan` trong `planning/task_graph/` (đã có thư mục sẵn) với các state: `pending / in_progress / done / failed`.
2. `coding_agent.py`: trước khi sửa code, bắt buộc LLM sinh ra danh sách bước (3–8 bước) dưới dạng `TaskPlan`, lưu vào state, emit qua EventBus mỗi khi 1 bước đổi trạng thái.
3. Renderer (`renderer/chat/`) hiển thị todo list này realtime (giống Claude Code hiển thị checklist khi làm việc).

**DoD:**

- Khi chạy 1 task coding thực tế, UI/log hiển thị được danh sách bước và trạng thái cập nhật theo thời gian thực, không chỉ "đang xử lý...".

---

### B3. [P1] Cơ chế tự kiểm chứng (verification loop) chặt hơn

**Vấn đề:** `action_verifier.py` tồn tại nhưng chưa rõ có bắt buộc chạy test/lint sau mỗi lần sửa code hay không; `MAX_ITER = 5` cứng nhưng không có tiêu chí dừng sớm khi test đã pass.

**Việc cần làm:**

1. Chuẩn hoá `execution/verifier/action_verifier.py`: sau mỗi patch, tự động chạy (theo thứ tự ưu tiên) — test suite dự án nếu phát hiện được (`pytest`, `npm test`) → nếu không có, chạy `python -m py_compile` / `node --check` để ít nhất bắt lỗi cú pháp.
2. Vòng lặp trong `coding_agent.py` dừng ngay khi verify pass, không chạy hết `MAX_ITER` một cách máy móc.
3. Khi verify fail, đưa nguyên văn traceback/lỗi vào prompt vòng lặp kế tiếp (không tóm tắt lại bằng lời).

**DoD:**

- Test tích hợp: cố tình đưa 1 bug đơn giản (ví dụ off-by-one), agent tự sửa và dừng đúng vòng lặp khi test pass, không chạy dư vòng lặp.

---

### B4. [P2] Multi-agent coordinator: xử lý lỗi & timeout giữa các subagent

**Vấn đề:** `agent_coordinator.py` (91 dòng) dùng `asyncio.gather` đơn giản, chưa rõ xử lý khi 1 subagent lỗi/treo — có thể làm treo cả `gather`.

**Việc cần làm:**

1. Bọc từng subagent call bằng `asyncio.wait_for` với timeout riêng theo loại agent (vision nhanh, coding chậm hơn).
2. Dùng `asyncio.gather(..., return_exceptions=True)`, log lỗi từng subagent riêng thay vì để 1 lỗi làm crash toàn bộ kết quả tổng hợp.
3. Thêm test giả lập 1 subagent raise exception → xác nhận các subagent khác vẫn trả kết quả bình thường.

**DoD:** Test coordinator với 3 subagent (1 lỗi, 1 timeout, 1 thành công) → kết quả tổng hợp vẫn có phần thành công, có báo lỗi rõ cho 2 cái còn lại.

---

### B5. [P2] SKILL.md → skill có thể đánh giá được (không chỉ là prompt tĩnh)

**Vấn đề:** Các file `skills/*/SKILL.md` là hướng dẫn tĩnh, không có cơ chế nạp động theo ngữ cảnh hay đánh giá hiệu quả skill (khác với ý tưởng skill triggering có kiểm chứng).

**Việc cần làm:**

1. `skills/skills_manager.py`: thêm cơ chế match skill theo mô tả nhiệm vụ (embedding-based hoặc keyword-based) trước khi nạp toàn bộ nội dung SKILL.md vào context — tránh nhồi tất cả skill vào prompt.
2. Thêm trường `description` ngắn (dùng để match) tách biệt khỏi nội dung chi tiết (giống frontmatter hiện có, nhưng dùng thực sự để filter thay vì chỉ đọc tất cả).
3. (Tùy chọn nâng cao) Thêm log "skill nào được dùng cho task nào" để sau này đánh giá skill nào hữu ích, skill nào không.

**DoD:** Với 5 loại task khác nhau, chỉ đúng skill liên quan được nạp vào context (verify qua log), không nạp cả 8 SKILL.md mỗi lần.

---

## TRỤC A — COMPANION (tiệm cận Neuro-sama)

### A1. [P1] Đọc/tương tác chat trực tiếp (Twitch/Discord) — tối thiểu ở mức cắm được

**Vấn đề:** Không có tích hợp đọc chat livestream nào, dù đây là đặc trưng cốt lõi của Neuro-sama.

**Việc cần làm:**

1. Thêm `interaction/chat/twitch_bridge.py` dùng `twitchio` hoặc IRC WebSocket của Twitch, chỉ cần đọc message trong 1 channel + gửi vào EventBus như một nguồn perception mới (tương tự cách `perception/` đang nhận voice/screen).
2. Thêm policy trong `decision/` để quyết định khi nào react với chat (tránh spam trả lời mọi message — cần throttle/priority giống `Silence Engine` đã có sẵn cho user chính).
3. Không bắt buộc làm Discord ngay — ưu tiên Twitch trước vì đã có nhắc trong `config/` và `content_moderator.py`.

**DoD:** Chạy demo: gõ message vào kênh Twitch test → companion phản hồi trong log/UI trong vài giây, có throttle không trả lời mọi dòng chat.

---

### A2. [P1] Tăng độ "ngẫu hứng" có kiểm soát trong phản hồi

**Vấn đề:** Kiến trúc hiện tại thiên về ổn định/nhất quán (đúng cho companion cá nhân) nhưng thiếu biến thiên bất ngờ làm nội dung thú vị để xem/tương tác.

**Việc cần làm:**

1. Thêm tham số "spontaneity" vào `persona/` — xác suất chèn phản ứng ngoài kịch bản (trêu chọc, bình luận bất ngờ về màn hình/hoạt động) dựa trên `world_model` hiện có, không cần thêm model mới.
2. Expose tham số này ra `config/persona.config.json` để chỉnh theo từng nhân vật (IceGirl vs Hiyori có mức độ khác nhau).

**DoD:** So sánh 20 phản hồi liên tiếp ở spontaneity thấp vs cao — có thể phân biệt rõ bằng mắt thường qua log hội thoại.

---

### A3. [P2] Tài liệu hoá rõ ràng: đây KHÔNG phải mục tiêu thay thế Neuro-sama's streaming stack

Đã có sẵn trong `COMPANION_ROADMAP.md` — chỉ cần giữ nguyên định hướng, không cần việc kỹ thuật thêm, ghi chú lại để Codex không tự ý build tính năng streaming quy mô lớn (multi-viewer chat, donation alerts...) ngoài phạm vi cá nhân.

---

## KHÔNG LÀM (out of scope cho vòng này)

- Không xây dựng hệ thống streaming đa người xem/donation/subscriber alert — ngoài phạm vi "companion cá nhân".
- Không tự chế LLM/VLM riêng — tiếp tục dùng provider hiện có (Ollama/Gemini/OpenAI).
- Không đổi kiến trúc EventBus/module hiện tại — chỉ bổ sung, không refactor toàn bộ.

---

## THỨ TỰ THỰC THI ĐỀ XUẤT CHO CODEX

1. B0 (file edit chính xác) — nền tảng cho mọi việc sửa code sau này.
2. B1 (sandbox) — bắt buộc trước khi cho agent chạy lệnh thật nhiều hơn.
3. B3 (verification loop) — cần B0 xong trước.
4. B2 (todo list) — cải thiện trải nghiệm, không chặn các mục khác.
5. B4 (coordinator lỗi/timeout).
6. B5 (skill matching).
7. A1 → A2 → A3.

Sau mỗi bước B0–B3, chạy lại toàn bộ `tests/test_phase*.py` để đảm bảo chưa phá vỡ gì.
