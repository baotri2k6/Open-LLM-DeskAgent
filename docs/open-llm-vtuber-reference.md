# Open-LLM-VTuber Reference Notes

The user-provided archive was extracted to:

`reference/Open-LLM-VTuber-main/Open-LLM-VTuber-main`

Use it as a reference project, not as a drop-in replacement. This project already has its own Electron shell, Python HTTP service, memory, RAG, desktop tools, and Live2D overlay. The safest path is to migrate features by layer.

## High-Value Pieces To Borrow

1. Provider abstractions
   - Reference: `src/open_llm_vtuber/asr`, `src/open_llm_vtuber/tts`, `src/open_llm_vtuber/agent/stateless_llm`
   - Apply here by turning current single-provider services into small factory-backed services.

2. TTS text preprocessing
   - Reference: `src/open_llm_vtuber/utils/tts_preprocessor.py`
   - Useful for stripping thoughts, brackets, emoji, and non-speakable text before generating voice.

3. Sentence segmentation and faster first response
   - Reference: `src/open_llm_vtuber/conversations/tts_manager.py`, `src/open_llm_vtuber/utils/sentence_divider.py`
   - Useful once this app adds streaming LLM responses.

4. Live2D model registry
   - Reference: `model_dict.json`, `live2d_model.py`, `live2d-models/`
   - Apply here by replacing hardcoded `IceGirl` paths with a character/model registry.

5. Prompt utilities
   - Reference: `prompts/utils/*.txt`
   - Useful for expression tags, tool guidance, proactive speech, and speakable output.

6. MCP/tool pattern
   - Reference: `src/open_llm_vtuber/mcpp`
   - This is a later-stage integration. The current desktop tools are simpler and should stay simple until provider and prompt layers are cleaner.

## Suggested Migration Order

1. Clean window lifecycle and app startup.
2. Add provider factories for LLM, STT, and TTS.
3. Add TTS preprocessing before audio generation.
4. Add character/model registry and multi-character settings.
5. Add streaming response with sentence-based TTS playback.
6. Add MCP-style tools only after the basic local desktop tools are stable.

## First Local Change Made

`electron/main.js` now creates a real chat overlay window using the existing `electron/window/overlay.js`. The tray and `Ctrl+Shift+Space` toggle the chat overlay instead of accidentally hiding/showing the avatar.
