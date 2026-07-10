import sys
import os

# Thêm python-services vào sys.path để import các module dịch vụ
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "python-services"))

from services.memory_service import MemoryService
from core.config import config

def main():
    print("=== Testing Memory CRUD Operations ===")
    
    # Khởi tạo MemoryService
    service = MemoryService()
    
    # 1. Lấy danh sách ban đầu
    memories = service.get_all_memories()
    initial_count = len(memories)
    print(f"Initial memory count: {initial_count}")
    
    # 2. Thêm một ký ức thủ công
    test_text = "Test memory for CRUD validation"
    fact = service.remember(test_text, category="test")
    print(f"Added memory: {fact}")
    
    # Lấy lại danh sách để tìm ID mới
    memories = service.get_all_memories()
    assert len(memories) == initial_count + 1, "Count should increase by 1"
    
    new_fact = memories[-1]
    fact_id = new_fact.get("id")
    print(f"New fact ID: {fact_id}")
    assert fact_id is not None, "Fact should have a unique ID"
    assert new_fact["text"] == test_text, "Fact text mismatch"
    
    # 3. Cập nhật ký ức
    updated_text = "Updated memory text for validation"
    success_update = service.update_memory(fact_id, updated_text)
    print(f"Update operation success: {success_update}")
    assert success_update is True, "Update should return True"
    
    # Kiểm tra xem văn bản đã được cập nhật chưa
    memories = service.get_all_memories()
    updated_fact = [f for f in memories if f.get("id") == fact_id][0]
    print(f"Updated memory text: {updated_fact['text']}")
    assert updated_fact["text"] == updated_text, "Text was not updated successfully"
    
    # 4. Xóa ký ức
    success_delete = service.delete_memory(fact_id)
    print(f"Delete operation success: {success_delete}")
    assert success_delete is True, "Delete should return True"
    
    # Kiểm tra xem danh sách đã về ban đầu chưa
    memories = service.get_all_memories()
    assert len(memories) == initial_count, "Memory count should return to initial"
    
    print("\n=== All Memory CRUD Operations Passed Successfully! ===")

if __name__ == "__main__":
    main()
