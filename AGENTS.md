# DeskAgent Developer Specifications & Rules

Welcome! If you are an AI coding assistant (like Antigravity) working on the DeskAgent repository, you must adhere to the following rules, standards, and architecture specifications.

---

## 1. Project Architecture

The DeskAgent workspace is a hybrid Node/Python workspace organized as follows:
*   **Electron UI Application (Frontend)**:
    *   `desktop/`: Main process files (window management, ipc routing, websocket overlay server).
    *   `renderer/`: Renderer process files (HTML/CSS/JS interface, WebGL canvas renderers for Live2D/Spine).
    *   `src/`: Shared TypeScript/JavaScript code for the desktop application.
*   **Python AI Backend Services**:
    *   `agents/`: Core LLM agents (DesktopAgent, BrowserAgent, PlannerAgent, VisionAgent).
    *   `api/`: Local server interface (`server.py` FastAPI/WebSocket app).
    *   `cognition/`: Cognitive layers (`reasoning/` for CognitionEngine, `context/` for ContextManager, `prompts/` for prompt builders and templates).
    *   `motivation/`: Companion needs, drives, curiosity systems, and `motivation_manager.py`.
    *   `life/`: Autonomous Life Loop orchestrator (`life_loop.py`, `feel_engine.py`, `reflect_engine.py`, `life_learner.py`).
    *   `social/`: Interpersonal features including relationship tracking and `empathy_engine.py`.
    *   `memory/`: Multi-tiered storage facade (`memory_manager.py`, `memory_service.py`, `vectorstore/` for ChromaDB memory store, semantic/episodic/procedural memory).
    *   `execution/`: Core system actions (`mouse/`, `keyboard/`, `filesystem/`, `terminal/`, `approval/` permissions checks).
    *   `tools/`: System execution tools (`computer_control.py`, `screen_reader.py`).
*   **Extendable Plugins & Skills**:
    *   `plugins/`: Additional extendable plugins (e.g. chess, homeassistant).
    *   `skills/`: Reusable markdown instructions for specific agent workflows.
    *   `scripts/`: Dev & build tools.

---

## 2. Core Coding Rules

1.  **Strict Modular Separation**: 
    *   Do NOT write UI logic in the backend, and do NOT run native Python/OS shell commands from the renderer process.
    *   All communication between the desktop application and the Python backend must go through the standard HTTP/WebSocket APIs.
2.  **Safety & Permission System**:
    *   All dangerous operations (such as running shell commands or modifying files outside the project scope) must check with `PermissionManager` first.
    *   Respect the workspace bounds. Never edit or overwrite critical user configuration files without explicit user consent.
3.  **Click-through Optimization**:
    *   Always maintain the `preserveDrawingBuffer: true` configuration for WebGL canvases in Live2D and Spine.
    *   The `containsPoint` methods must check pixel alpha values to allow users to interact with background applications through transparent areas.
4.  **Token Efficiency & Lazy Loading**:
    *   Use lazy loading for heavy machine learning model initializations to ensure startup times remain under 5 seconds.
    *   Use progressive disclosure of skills: let the agent call `read_skill` only when they need to execute it, keeping context usage light.
5.  **Data Contracts & Portability**:
    *   Always use the dataclass `ContextPacket` (defined in `runtime/context/context_packet.py`) when passing unified snapshots between perception, cognition, and execution layers.
    *   Never use hardcoded workspace paths like `'d:/Open LLM DeskAgent'` in tests or code; always use relative or dynamic paths via `Path(__file__).resolve()` to ensure machine-portability and CI/CD compatibility.
