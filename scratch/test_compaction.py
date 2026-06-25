import asyncio
import sys
from pathlib import Path

# Add python-services directory to path
sys.path.append(str(Path(__file__).resolve().parents[1] / "python-services"))

from core.config import config
from services.llm_service import LLMService

async def main():
    sys.stdout.reconfigure(encoding='utf-8')
    print("=== Testing Context Compaction ===")
    
    # Temporarily set context size small to trigger compaction easily
    config.set("llm.context_size", 400) # threshold will be 320 tokens (approx 1280 chars)
    
    llm = LLMService()
    
    # Create large dummy messages
    messages = [
        {"role": "system", "content": "You are a helpful assistant."},
        {"role": "user", "content": "Hello. I need help with coding." * 50}, # ~1500 chars -> ~375 tokens
        {"role": "assistant", "content": "Sure, I can help you with coding. What language?" * 50}, # ~2500 chars -> ~625 tokens
        {"role": "user", "content": "Python please." * 50},
        {"role": "assistant", "content": "Okay, Python it is. What do you want to build?" * 50},
        {"role": "user", "content": "A simple desktop assistant."}
    ]
    
    print(f"Original message count: {len(messages)}")
    estimated = llm._estimate_tokens(messages)
    print(f"Estimated tokens: {estimated}")
    
    provider = config.get("llm.provider")
    api_key = config.get("llm.gemini_api_key")
    model = config.get("llm.gemini_model")
    base_url = "https://generativelanguage.googleapis.com"
    
    compacted = await llm._compact_context_if_needed(messages, provider, api_key, model, base_url)
    print(f"Compacted message count: {len(compacted)}")
    for i, msg in enumerate(compacted):
        print(f"Msg {i} ({msg['role']}): {msg['content'][:150]}...")

if __name__ == "__main__":
    asyncio.run(main())
