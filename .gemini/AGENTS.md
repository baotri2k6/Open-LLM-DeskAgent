# DeskAgent Gemini/Antigravity Developer Rules

These are the rules and guidelines specific to the Gemini/Antigravity AI coding assistant working on the DeskAgent codebase.

## 1. Project Architecture
The DeskAgent workspace is a hybrid Node/Python workspace organized as follows:
- `desktop/`: Main process files (Electron).
- `renderer/`: Renderer process files (HTML/CSS/JS/Live2D/Spine).
- `src/`: Shared TypeScript/JavaScript code.
- `agents/`: Core LLM agents (Desktop, Browser, Planner, Vision).
- `api/`: Local server interface (`server.py`).
- `life/`: Autonomous Life Loop.
- `memory/`: Multi-tiered storage facade.
- `tools/`: System execution tools.

## 2. Core Coding Rules
1. **Strict Modular Separation**: Do NOT write UI logic in the backend, and do NOT run native OS commands from the renderer.
2. **Safety**: All dangerous operations must check with `PermissionManager` first. Respect the workspace bounds.
3. **Click-through Optimization**: Always maintain `preserveDrawingBuffer: true` for WebGL canvases.
4. **Token Efficiency & Lazy Loading**: Keep startup under 5 seconds by lazy loading models.
5. **Data Contracts**: Always use `ContextPacket` when passing unified snapshots.
6. **Portability**: Do NOT use hardcoded absolute workspace paths. Always use relative/dynamic paths.
