# Contributing to DeskAgent

Thank you for contributing to DeskAgent! To maintain code quality and clean project structure, please follow these guidelines.

---

## 1. Local Environment Setup

1.  **Backend Setup**:
    *   Create a virtual environment: `python -m venv venv`
    *   Activate it: `.\venv\Scripts\activate` (Windows) or `source venv/bin/activate` (Linux/Mac)
    *   Install dependencies: `pip install -r requirements.txt`
    *   Start Python server: `npm run python` (or `python backend/server.py`)

2.  **Desktop App Setup**:
    *   Install Node dependencies: `npm install`
    *   Start the Electron application: `npm run dev`

---

## 2. Creating Skills

Skills are modular, self-contained markdown manuals instructing the agent how to perform specific tasks.
*   Place new skills in `skills/<skill_name>/SKILL.md`.
*   Every `SKILL.md` must start with a YAML frontmatter section containing `name` and `description`:
    ```yaml
    ---
    name: your-skill-name
    description: A brief description of what this skill allows the agent to do.
    ---
    ```
*   Keep the instruction body concise and actionable.

---

## 3. Creating Plugins

Plugins extend the agent's capabilities with custom Python functions and schemas.
*   Place new plugins in `plugins/<plugin_name>/`.
*   Include a `plugin.json` definition and the corresponding Python code.
*   Ensure all database or state files created by plugins are stored in the local `cache/` or `data/` directories to prevent workspace clutter.
