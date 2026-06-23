"""Simple JSON-backed memory service for the MVP."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from core.config import PROJECT_ROOT


class MemoryService:
    def __init__(self, profile_path: Path | None = None) -> None:
        self.profile_path = profile_path or PROJECT_ROOT / "data" / "user_profile.json"
        self.profile_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.profile_path.exists() or self.profile_path.stat().st_size == 0:
            self._write({
                "name": "",
                "preferences": {"language": "vi-VN"},
                "facts": [],
                "relationship": {"score": 15, "level": "Người quen", "last_interaction": ""},
                "mood": "vui vẻ"
            })
        else:
            # Kiểm tra và tự động điền các khoá thiếu nếu file json đã có sẵn
            profile = self._read()
            dirty = False
            if "relationship" not in profile:
                profile["relationship"] = {"score": 15, "level": "Người quen", "last_interaction": ""}
                dirty = True
            else:
                rel = profile["relationship"]
                # Đảm bảo level của mối quan hệ thuộc đúng 3 mức: Người lạ, Người quen, Bạn thân
                if rel.get("level") not in ["Người lạ", "Người quen", "Bạn thân"]:
                    score = rel.get("score", 15)
                    if score <= 10:
                        rel["level"] = "Người lạ"
                    elif score <= 50:
                        rel["level"] = "Người quen"
                    else:
                        rel["level"] = "Bạn thân"
                    dirty = True
            if "mood" not in profile:
                profile["mood"] = "vui vẻ"
                dirty = True
            if dirty:
                self._write(profile)

        # Khởi tạo ChromaDB
        self._recent_conversations = []
        try:
            from rag.vector_store import get_vector_store
            self._vector_store = get_vector_store("companion_memories")
            self._has_vector = True
        except Exception as exc:
            import logging
            logging.warning("Failed to init companion memory VectorStore: %s", exc)
            self._has_vector = False

    def _read(self) -> dict[str, Any]:
        with self.profile_path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write(self, payload: dict[str, Any]) -> None:
        with self.profile_path.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, ensure_ascii=False, indent=2)

    def get_profile(self) -> dict[str, Any]:
        return self._read()

    def remember(self, text: str, category: str = "note") -> dict[str, Any]:
        profile = self._read()
        fact = {
            "text": text.strip(),
            "category": category,
            "createdAt": datetime.now().isoformat(timespec="seconds"),
        }
        profile.setdefault("facts", []).append(fact)
        self._write(profile)

        if self._has_vector:
            try:
                from rag.chunker import Chunk
                chunk = Chunk(
                    text=text.strip(),
                    doc_id="facts",
                    chunk_index=len(profile.get("facts", [])) + int(datetime.now().timestamp() % 100000),
                    metadata={"category": category, "createdAt": fact["createdAt"]}
                )
                self._vector_store.add_chunks([chunk])
            except Exception as e:
                import logging
                logging.warning("Failed to save memory to ChromaDB: %s", e)

        return fact

    def recall(self, query: str = "") -> list[dict[str, Any]]:
        if self._has_vector and query.strip():
            try:
                results = self._vector_store.query(query, n_results=5)
                recalled = []
                for item in results:
                    recalled.append({
                        "text": item["text"],
                        "category": item.get("metadata", {}).get("category", "note"),
                        "createdAt": item.get("metadata", {}).get("createdAt", ""),
                    })
                if recalled:
                    return recalled
            except Exception as e:
                import logging
                logging.warning("Recall from ChromaDB failed: %s. Falling back to JSON", e)

        facts = self._read().get("facts", [])
        if not query:
            return facts[-10:]
        lowered = query.lower()
        matches = [fact for fact in facts if lowered in fact.get("text", "").lower()]
        return matches[-10:] if matches else facts[-5:]

    # ─── Relationship & Mood System ──────────────────────────────────────────────

    def get_relationship(self) -> dict:
        profile = self._read()
        return profile.get("relationship", {"score": 15, "level": "Người quen", "last_interaction": ""})

    def update_relationship(self, score_change: int) -> dict:
        profile = self._read()
        rel = profile.get("relationship", {"score": 15, "level": "Người quen", "last_interaction": ""})
        new_score = max(0, min(100, rel.get("score", 15) + score_change))
        
        if new_score <= 10:
            level = "Người lạ"
        elif new_score <= 50:
            level = "Người quen"
        else:
            level = "Bạn thân"
            
        rel["score"] = new_score
        rel["level"] = level
        profile["relationship"] = rel
        self._write(profile)
        return rel

    def get_mood(self) -> str:
        self.drift_mood()
        return self._read().get("mood", "vui vẻ")

    def update_mood(self, mood: str) -> None:
        profile = self._read()
        profile["mood"] = mood
        profile["mood_updated_at"] = datetime.now().isoformat()
        self._write(profile)

    def drift_mood(self) -> str:
        """Tự động thay đổi tâm trạng theo thời gian (MoodDrift)."""
        try:
            profile = self._read()
            mood = profile.get("mood", "vui vẻ")
            
            # Lấy thông tin tương tác cuối cùng
            rel = profile.get("relationship", {})
            last_interact_str = rel.get("last_interaction", "")
            if not last_interact_str:
                return mood
                
            last_time = datetime.fromisoformat(last_interact_str)
            now = datetime.now()
            delta_seconds = (now - last_time).total_seconds()
            
            dirty = False
            # 1. Nếu lâu quá không tương tác -> tự động buồn/chán
            if delta_seconds > 1800:  # > 30 phút
                if mood != "buồn":
                    mood = "buồn"
                    profile["mood"] = mood
                    dirty = True
                    from core.logger import get_logger
                    get_logger("ai-companion.llm").info("MoodDrift: Trôi sang trạng thái 'buồn' do bị bỏ bê > 30 phút")
            elif delta_seconds > 600:  # > 10 phút
                if mood not in ["chán", "buồn"]:
                    mood = "chán"
                    profile["mood"] = mood
                    dirty = True
                    from core.logger import get_logger
                    get_logger("ai-companion.llm").info("MoodDrift: Trôi sang trạng thái 'chán' do rảnh rỗi > 10 phút")
            
            # 2. Nếu bị dỗi "hơi dỗi" quá 15 phút -> tự động nguôi giận về "vui vẻ"
            mood_updated_str = profile.get("mood_updated_at", "")
            if mood_updated_str:
                mood_updated_time = datetime.fromisoformat(mood_updated_str)
                mood_age = (now - mood_updated_time).total_seconds()
                if mood == "hơi dỗi" and mood_age > 900:  # > 15 phút
                    mood = "vui vẻ"
                    profile["mood"] = mood
                    profile["mood_updated_at"] = now.isoformat()
                    dirty = True
                    from core.logger import get_logger
                    get_logger("ai-companion.llm").info("MoodDrift: Tự động nguôi giận ('hơi dỗi' -> 'vui vẻ') sau 15 phút")
            
            if dirty:
                self._write(profile)
                
            return mood
        except Exception as e:
            from core.logger import get_logger
            get_logger("ai-companion.llm").warning("Error in drift_mood: %s", e)
            return "vui vẻ"

    def write_back_memory(self, user_msg: str, assistant_msg: str) -> None:
        """Ghi nhận và đúc kết ký ức có cấu trúc ngay sau lượt hội thoại (Memory Write-back)."""
        import threading
        import asyncio
        from core.logger import get_logger
        
        def run_write_back():
            try:
                # Dùng Event Loop mới trong Thread để tránh xung đột
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                loop.run_until_complete(self._extract_facts_from_turn(user_msg, assistant_msg))
                loop.close()
            except Exception as e:
                get_logger("ai-companion.llm").warning("Error in write_back_memory background: %s", e)
                
        threading.Thread(target=run_write_back, daemon=True).start()

    async def _extract_facts_from_turn(self, user_msg: str, assistant_msg: str) -> None:
        from core.logger import get_logger
        logger = get_logger("ai-companion.llm")
        
        # 1. Lọc bớt các câu chat quá ngắn hoặc chỉ là câu chào để tránh lãng phí gọi LLM vô ích
        clean_user = user_msg.strip()
        generic_words = {"hello", "hi", "chào", "chào em", "ok", "oke", "dạ", "uh", "ừ", "vâng", "bye", "tạm biệt"}
        if len(clean_user) < 8 or clean_user.lower() in generic_words:
            return
            
        try:
            prompt = (
                f"Hãy đóng vai trò là hệ thống đúc kết ký ức. Phân tích cuộc hội thoại ngắn sau đây:\n\n"
                f"Người dùng: {user_msg}\n"
                f"AI: {assistant_msg}\n\n"
                f"Nhiệm vụ: Nếu cuộc trò chuyện trên có chứa thông tin cá nhân mới, sở thích, thói quen, "
                f"hoặc yêu cầu cụ thể của người dùng cần nhớ lâu dài, hãy đúc kết nó thành 1 câu khẳng định ngắn gọn "
                f"(Ví dụ: 'Người dùng thích uống cà phê sữa', 'Người dùng tên là Nam và đang học lập trình Web'). "
                f"Nếu không có thông tin gì quan trọng hoặc mới mẻ đáng nhớ, CHỈ trả về từ 'NONE'. "
                f"Không giải thích gì thêm."
            )
            
            from services.llm_service import LLMService
            llm = LLMService()
            response = await llm.chat(prompt)
            response_clean = response.strip().strip("-* ").strip()
            
            if response_clean and response_clean.upper() != "NONE" and len(response_clean) > 5:
                # Kiểm tra xem fact này đã có trong database chưa bằng cách query tương đối
                existing_facts = self.recall(response_clean)
                is_duplicate = False
                for fact in existing_facts:
                    if response_clean.lower() in fact["text"].lower() or fact["text"].lower() in response_clean.lower():
                        is_duplicate = True
                        break
                        
                if not is_duplicate:
                    self.remember(response_clean, category="turn_reflection")
                    logger.info("Memory Write-back: Đã đúc kết và ghi nhớ: %s", response_clean)
        except Exception as exc:
            logger.warning("Memory Write-back failed: %s", exc)


    def record_interaction(self) -> str:
        """Ghi nhận thời gian tương tác và trả về ghi chú bối cảnh nếu có khoảng cách thời gian lớn."""
        profile = self._read()
        rel = profile.get("relationship", {"score": 15, "level": "Người quen", "last_interaction": ""})
        last_str = rel.get("last_interaction", "")
        now = datetime.now()
        
        context_note = ""
        if last_str:
            try:
                last_time = datetime.fromisoformat(last_str)
                delta = now - last_time
                days = delta.days
                hours = delta.seconds // 3600
                
                if days >= 3:
                    context_note = f"[Hệ thống: Đã {days} ngày cậu chưa nói chuyện với IceGirl. IceGirl sẽ cực kỳ nhớ cậu và hơi hờn dỗi nhẹ vì bị bỏ bê]"
                elif days >= 1:
                    context_note = f"[Hệ thống: Đã hơn 1 ngày cậu chưa nói chuyện với IceGirl. IceGirl sẽ chào đón cậu thân mật, hỏi thăm xem cậu bận gì]"
                elif hours >= 4:
                    context_note = f"[Hệ thống: Đã vài tiếng kể từ lần nói chuyện trước trong ngày. Hãy chào mừng cậu quay lại]"
            except Exception:
                pass
                
        rel["last_interaction"] = now.isoformat(timespec="seconds")
        profile["relationship"] = rel
        self._write(profile)
        return context_note

    def analyze_sentiment_and_update(self, text: str) -> str | None:
        """Tự động phân tích tình cảm từ tin nhắn người dùng để tăng điểm mối quan hệ và cập nhật tâm trạng."""
        text_lower = text.lower()
        score_change = 0
        new_mood = None
        
        # Thân mật, khen ngợi
        if any(w in text_lower for w in ["yêu", "thương", "thích", "cảm ơn", "cam on", "dễ thương", "de thuong", "ngoan", "giỏi", "gioi", "xinh", "đẹp"]):
            score_change = 1
            new_mood = "vui vẻ"
        # Bị ghét, xúc phạm, tiêu cực
        elif any(w in text_lower for w in ["ghét", "ghet", "ngốc", "ngoc", "tệ", "te", "khùng", "khung", "dở", "do", "bỏ đi", "bo di", "ngu"]):
            score_change = -1
            new_mood = "hơi dỗi"
            
        if score_change != 0:
            self.update_relationship(score_change)
        if new_mood:
            self.update_mood(new_mood)
            
        return new_mood

    def add_to_conversation_history(self, role: str, content: str) -> None:
        self._recent_conversations.append({"role": role, "content": content})
        if len(self._recent_conversations) >= 15:
            # Kích hoạt đúc kết ký ức (Reflection) trong background
            import threading
            import asyncio
            from core.logger import get_logger
            
            convs = list(self._recent_conversations)
            self._recent_conversations = []  # Clear để nhận block tiếp theo
            
            def run_reflection():
                try:
                    asyncio.run(self._generate_reflection_memories(convs))
                except Exception as e:
                    get_logger("ai-companion.llm").warning("Error running reflection: %s", e)
                
            threading.Thread(target=run_reflection, daemon=True).start()

    async def _generate_reflection_memories(self, conversations: list[dict]) -> None:
        from core.logger import get_logger
        logger = get_logger("ai-companion.llm")
        try:
            # Ghép cuộc hội thoại thành text
            chat_section = ""
            for msg in conversations:
                speaker = "Người dùng" if msg["role"] == "user" else "IceGirl"
                chat_section += f"{speaker}: {msg['content']}\n"
                
            # Tạo prompt đúc kết
            prompt = (
                f"Dưới đây là lịch sử cuộc hội thoại vừa qua:\n\n{chat_section}\n"
                "Dựa trên cuộc trò chuyện trên, hãy đưa ra tối đa 3 thông tin ngắn gọn, "
                "quan trọng và cốt lõi nhất về người dùng hoặc cuộc hội thoại mà AI cần ghi nhớ (ví dụ: sở thích, tên tuổi, sự kiện, yêu cầu...). "
                "Mỗi thông tin viết trên một dòng mới, bắt đầu bằng dấu gạch đầu dòng '- '. "
                "Không giải thích, chỉ xuất ra các thông tin cần ghi nhớ."
            )
            
            from services.llm_service import LLMService
            llm = LLMService()
            # Gọi LLM chat (non-stream)
            response = await llm.chat(prompt)
            logger.info("Memory Reflection raw response: %s", response)
            
            # Phân tách từng dòng để lưu vào memory
            lines = response.split("\n")
            count = 0
            for line in lines:
                cleaned = line.strip().lstrip("-* ").strip()
                if cleaned and len(cleaned) > 5:
                    self.remember(cleaned, category="reflection")
                    count += 1
            if count > 0:
                logger.info("Memory Reflection: Tự động ghi nhớ %d ký ức mới vào database.", count)
        except Exception as exc:
            logger.warning("Memory Reflection failed: %s", exc)

    def get_all_memories(self) -> list[dict[str, Any]]:
        profile = self._read()
        facts = profile.get("facts", [])
        # Ensure every fact has an ID
        dirty = False
        import uuid
        for fact in facts:
            if "id" not in fact:
                fact["id"] = str(uuid.uuid4())
                dirty = True
        if dirty:
            self._write(profile)
        return facts

    def delete_memory(self, fact_id: str) -> bool:
        profile = self._read()
        facts = profile.get("facts", [])
        new_facts = [f for f in facts if f.get("id") != fact_id]
        if len(new_facts) == len(facts):
            return False  # not found
            
        profile["facts"] = new_facts
        self._write(profile)
        
        # Sync with ChromaDB
        self._sync_all_memories_to_vector_store(new_facts)
        return True

    def update_memory(self, fact_id: str, new_text: str) -> bool:
        profile = self._read()
        facts = profile.get("facts", [])
        found = False
        for fact in facts:
            if fact.get("id") == fact_id:
                fact["text"] = new_text.strip()
                fact["updatedAt"] = datetime.now().isoformat(timespec="seconds")
                found = True
                break
        if not found:
            return False
            
        self._write(profile)
        # Sync with ChromaDB
        self._sync_all_memories_to_vector_store(facts)
        return True

    def _sync_all_memories_to_vector_store(self, facts: list[dict[str, Any]]):
        if not self._has_vector:
            return
        try:
            # Delete old facts doc from ChromaDB
            self._vector_store.delete_doc("facts")
            
            # Re-add all facts as chunks
            from rag.chunker import Chunk
            chunks = []
            for i, fact in enumerate(facts):
                chunks.append(Chunk(
                    text=fact["text"].strip(),
                    doc_id="facts",
                    chunk_index=i,
                    metadata={"category": fact.get("category", "note"), "createdAt": fact.get("createdAt", ""), "fact_id": fact.get("id", "")}
                ))
            self._vector_store.add_chunks(chunks)
        except Exception as e:
            import logging
            logging.warning("Failed to sync memories to ChromaDB: %s", e)
