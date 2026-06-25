# DeskAgent Developer Specifications & Rules

Welcome! If you are an AI coding assistant (like Antigravity) working on the DeskAgent repository, you must adhere to the following rules, standards, and architecture specifications.

---

## 1. Project Architecture

The DeskAgent workspace is organized as follows:
*   `apps/desktop/`: The Electron user interface application.
    *   `main/`: Main process files (ipc routing, window management, websocket overlay server).
    *   `renderer/`: Renderer process files (HTML/CSS/JS interface, Canvas renderers for Live2D/Spine).
*   `backend/`: Python backend engine.
    *   `agents/`: Core LLM agents (DesktopAgent, BrowserAgent, PlannerAgent).
    *   `core/`: Core mechanisms (SkillsManager, PluginManager, EmotionParser, cognition).
    *   `services/`: Background services (LLM, Memory, STT, TTS).
    *   `tools/`: System and OS execution tools.
    *   `utils/`: Core utilities (e.g. PermissionManager).
*   `plugins/`: Additional extendable plugins.
*   `skills/`: Reusable markdown instructions for specific agent workflows.
*   `scripts/`: Dev & build tools.

---

## 2. Core Coding Rules

1.  **Strict Modular Separation**: 
    *   Do NOT write UI logic in the backend (`backend/`), and do NOT run native Python/OS shell commands from the renderer process.
    *   All communication between the desktop application and the Python backend must go through the standard HTTP/WebSocket APIs.
2.  **Safety & Permission System**:
    *   All dangerous operations (such as running shell commands or modifying files outside the project scope) must check with `PermissionManager` first.
    *   Respect the workspace bounds. Never edit or overwrite critical user configuration files without explicit user consent.
3.  **Click-through Optimization**:
    *   Always maintain the `preserveDrawingBuffer: true` configuration for WebGL canvases in Live2D and Spine.
    *   The `containsPoint` methods must check pixel alpha values to allow users to interact with background applications through transparent areas.
4.  **Token Efficiency & Lazy Loading**:
    *   Use lazy loading for heavy machine learning model initializations (STT, Embeddings, LLM workers) to ensure startup times remain under 5 seconds.
    *   Use progressive disclosure of skills through system prompts: let the agent call `read_skill` only when they need to execute it, keeping context usage light.
