<div align="center">

<img src="assets/icons/icon.png" alt="Open-LLM-DeskAgent Logo" width="120" />

# ✦ Open-LLM-DeskAgent ✦

**A truly Autonomous AI Desktop Companion.**

_Merging Mind (LLM) and Body (Live2D) into a Digital Being that lives on your Windows desktop._

<br/>

[![License: MIT](https://img.shields.io/badge/License-MIT-a78bfa?style=flat&labelColor=1e1e2e)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.10%2B-3b82f6?style=flat&logo=python&logoColor=white&labelColor=1e1e2e)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18%2B-22c55e?style=flat&logo=nodedotjs&logoColor=white&labelColor=1e1e2e)](https://nodejs.org)
[![Electron](https://img.shields.io/badge/Electron-TypeScript-9feaf9?style=flat&logo=electron&logoColor=white&labelColor=1e1e2e)](https://electronjs.org)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-f472b6?style=flat&labelColor=1e1e2e)](CONTRIBUTING.md)
[![Platform](https://img.shields.io/badge/Platform-Windows-0078d4?style=flat&logo=windows&logoColor=white&labelColor=1e1e2e)](https://github.com)

<br/>

_Inspired by [Neuro-sama](https://www.youtube.com/@Neurosama) · Powered by [Ollama](https://ollama.com), [Gemini](https://ai.google.dev) & [OpenAI](https://openai.com)_

<br/>

</div>

---

## 🌟 Preview

<div align="center">

> _Place a screenshot or demo GIF here._

![Demo](assets/demo.gif)

_IceGirl — the default companion — observing your screen and responding in real time._

</div>

---

## 💡 What Is This?

Most AI assistants wait passively for your command. **Open-LLM-DeskAgent is different.**

She _watches_ your screen. She _feels_ emotions. She _remembers_ your habits. And when you have been away too long, she starts to wonder about you — and writes in her diary.

> _"What if the companion you always wanted wasn't locked inside a chat window, but actually lived on your desktop, aware of what you're doing, ready to help or just to talk?"_

This project answers that question. It is an open-source, privacy-first AI companion that runs **100% locally** if you want — and brings together the warmth of a Live2D avatar with the power of a genuine autonomous agent.

---

## ✨ Features

### 🧬 A Living Presence on Your Desktop

| Feature                       | Description                                                                                                                                 |
| ----------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------- |
| 🎭 **Embodied Live2D Avatar** | IceGirl (and friends) renders transparently over your desktop. Her lips sync with her voice in real time. Her eyes follow your mouse.       |
| 🔄 **Autonomous Life Loop**   | An always-running background cycle: _Observe → Feel → Think → Decide → Act_. She proactively starts conversations when you've been idle.    |
| 📖 **Private Diary**          | When you're away, she reflects and writes journal entries — building a sense of continuity and inner life.                                  |
| 😊 **Emotion Engine**         | Real emotional states with natural decay: happiness, curiosity, surprise, sadness — each mapped to Live2D expressions and motions.          |
| 🎲 **Spontaneity**            | A configurable `spontaneity` parameter (0.0–1.0 per character) injects unpredictable, in-character reactions — so she never feels scripted. |

### 🧠 Advanced Memory & Learning

| Feature                       | Description                                                                                                           |
| ----------------------------- | --------------------------------------------------------------------------------------------------------------------- |
| 🗃️ **RAG Memory**             | ChromaDB vector store with automatic TF-IDF / Hash fallback — works even offline or in sandboxed environments.        |
| 🔬 **Knowledge Distillation** | After completing (or failing) a task, she extracts lessons learned and stores them to avoid repeating mistakes.       |
| 📅 **Pattern Learning**       | Learns your 24-hour activity rhythm. Knows when you usually start coding, when you take breaks, when you go to sleep. |
| 👤 **Belief System**          | Maintains a probabilistic model of who you are — your projects, preferences, mood patterns — updated every session.   |
| 🧩 **Relationship Tracker**   | Tracks the depth of your relationship over time. The longer you interact, the more she understands you.               |

### 🤖 Agentic Capabilities (Computer Use)

| Feature                         | Description                                                                                                             |
| ------------------------------- | ----------------------------------------------------------------------------------------------------------------------- |
| 👁️ **Screen Perception**        | Captures screenshots with `mss`, runs OCR, understands what application you're using and what you're working on.        |
| 🖱️ **Mouse & Keyboard Control** | Can click, type, scroll, and interact with your desktop via `pyautogui` — sandboxed with an approval system.            |
| 🌐 **Browser Agent**            | Navigates the web, reads pages, fills forms, and extracts information autonomously.                                     |
| 💻 **Coding Agent**             | Reviews, edits, and fixes code using patch-based editing (`str_replace`) with a verification loop.                      |
| 🔌 **MCP Support**              | Connects to any Model Context Protocol server — extend her capabilities with community tools.                           |
| 🛡️ **Safe by Default**          | All destructive actions (file writes, shell commands, system control) require explicit approval via `ApprovalRegistry`. |

### 🎙️ Real-time Voice Pipeline

```
Microphone → Faster-Whisper STT → LLM → SentenceAudioStreamer → TTS → Speaker
                                                                  ↑
                                              First audio chunk in < 300ms
```

- **STT:** Faster-Whisper · FunASR · streaming input
- **TTS:** Edge-TTS · Kokoro · MOSS — audio is streamed _sentence by sentence_, so she starts speaking before the full response is generated
- **Hotword Detection:** Wake her up hands-free

---

## 🏗️ Architecture

### Philosophy: Mind & Body

> _A companion needs both a soul and a form. The backend is the Mind — it thinks, remembers, decides. The frontend is the Body — it moves, speaks, and is seen._

```
┌─────────────────────────────────────────────────────────────────┐
│                        ELECTRON (Body)                          │
│  ┌───────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │  Live2D Mascot│  │  Chat UI     │  │  System Tray / HUD   │ │
│  │  Lipsync      │  │  Voice Input │  │  Settings Panel      │ │
│  │  Expressions  │  │  Audio Play  │  │  Overlay Widget      │ │
│  └───────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
│          └─────────────────┴──────────────────────┘             │
│                        WebSocket / IPC                          │
└──────────────────────────────┬──────────────────────────────────┘
                               │
┌──────────────────────────────▼──────────────────────────────────┐
│                      PYTHON BACKEND (Mind)                      │
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌───────────────┐  │
│  │LifeLoop  │  │ Cognition│  │  Memory  │  │  Agents       │  │
│  │Observer  │  │ Reasoning│  │  RAG     │  │  Browser      │  │
│  │Feel/Think│  │ Emotion  │  │  Episodic│  │  Coding       │  │
│  │Decide/Act│  │ Persona  │  │  Belief  │  │  Desktop      │  │
│  └──────────┘  └──────────┘  └──────────┘  └───────────────┘  │
│                                                                 │
│  ┌──────────────────────────────────────────────────────────┐  │
│  │              LLM Layer (llm/providers/)                  │  │
│  │   Ollama (Local) · Gemini · OpenAI · Custom             │  │
│  └──────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

**Domain-Driven Design (DDD)** — each module owns its domain:
`perception/` · `cognition/` · `memory/` · `persona/` · `decision/` · `execution/` · `learning/` · `life/`

All modules communicate through an **EventBus** — no direct coupling, easy to test, easy to extend.

---

## 🚀 Quick Start

### System Requirements

| Requirement | Minimum                                                |
| ----------- | ------------------------------------------------------ |
| **OS**      | Windows 10 / 11 (64-bit)                               |
| **Python**  | 3.10 or higher                                         |
| **Node.js** | 18 or higher                                           |
| **RAM**     | 8 GB (16 GB recommended for local LLM)                 |
| **GPU**     | Optional — required for local Whisper STT acceleration |
| **LLM**     | Ollama (local) **or** Gemini / OpenAI API key          |

---

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/your-username/Open-LLM-DeskAgent.git
cd Open-LLM-DeskAgent
```

**2. Set up the Python backend**

```bash
# Create a virtual environment (recommended)
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# Install dependencies
pip install -r requirements.txt
```

**3. Configure the companion**

```bash
# Copy the example config
copy config\companion.config.json.example config\companion.config.json

# Edit it with your settings (see Configuration section below)
notepad config\companion.config.json
```

**4. Start the Python backend**

```bash
python -m api.server
# Backend runs at http://localhost:8000
```

**5. Set up and start the Electron frontend**

```bash
# In a new terminal
npm install   # or: pnpm install

npm start     # or: pnpm start
```

IceGirl will appear on your desktop. Say hello. 👋

---

### Running with a local LLM (Offline / Privacy mode)

```bash
# Install Ollama from https://ollama.com
ollama pull qwen2.5:1.5b    # lightweight, fast
# or
ollama pull llama3           # more capable

# Set provider in config:
# "provider": "ollama"
# "model": "qwen2.5:1.5b"
```

---

## ⚙️ Configuration

Edit `config/companion.config.json` to customize your companion.

<details>
<summary><strong>🤖 LLM Provider</strong> — choose your AI brain</summary>

```json
{
  "llm": {
    "provider": "ollama",
    "model": "qwen2.5:1.5b",
    "api_key": "",
    "base_url": "http://localhost:11434"
  }
}
```

| `provider` | Description                   | `model` examples             |
| ---------- | ----------------------------- | ---------------------------- |
| `"ollama"` | 100% local, no API key needed | `"qwen2.5:1.5b"`, `"llama3"` |
| `"gemini"` | Google Gemini API             | `"gemini-2.0-flash"`         |
| `"openai"` | OpenAI / compatible API       | `"gpt-4o-mini"`              |

</details>

<details>
<summary><strong>🗣️ Voice & TTS Engine</strong></summary>

```json
{
  "speech": {
    "tts_engine": "edge",
    "stt_engine": "faster-whisper",
    "stt_model": "base",
    "voice": "vi-VN-HoaiMyNeural",
    "kokoro_voice": "af_sarah",
    "kokoro_speed": 1.05
  }
}
```

| `tts_engine` | Description                                           |
| ------------ | ----------------------------------------------------- |
| `"edge"`     | Microsoft Edge TTS — free, no GPU needed, many voices |
| `"kokoro"`   | Kokoro TTS — high quality, local, requires GPU        |
| `"moss"`     | MOSS TTS — Chinese-optimized                          |

</details>

<details>
<summary><strong>🎭 Persona & Character</strong></summary>

```json
{
  "persona": {
    "character": "icegirl",
    "spontaneity": 0.65,
    "language": "vi"
  }
}
```

Character files live in `persona/characters/`. Current built-in characters:

| Character | Personality                        | Spontaneity default |
| --------- | ---------------------------------- | ------------------- |
| `icegirl` | Playful, sassy, teasing, confident | 0.65                |
| `hiyori`  | Warm, curious, gentle              | 0.50                |
| `mao`     | Calm, thoughtful, reliable         | 0.20                |
| `huohuo`  | Energetic, cheerful, loyal         | 0.10                |

</details>

<details>
<summary><strong>🌊 Twitch / Streaming Mode</strong></summary>

```json
{
  "features": {
    "twitchMode": false
  },
  "twitch": {
    "channel": "your_channel_name",
    "response_throttle_per_minute": 5
  }
}
```

When `twitchMode` is `true`, the companion reads your Twitch chat and responds to viewers in real time — just like Neuro-sama.

</details>

<details>
<summary><strong>🧠 Memory & Learning</strong></summary>

```json
{
  "memory": {
    "backend": "chroma",
    "persist_directory": "./data/memory",
    "embedding_model": "all-MiniLM-L6-v2",
    "fallback": "tfidf"
  },
  "life": {
    "proactive_interval_seconds": 600,
    "diary_enabled": true
  }
}
```

`"fallback": "tfidf"` ensures memory always works even without an embedding model (offline, sandboxed, or first run).

</details>

---

## 🛣️ Roadmap

### ✅ Completed

- [x] Live2D avatar with real-time lipsync and eye tracking
- [x] Emotion engine with natural decay and Live2D expression mapping
- [x] Autonomous Life Loop (Observe → Feel → Think → Decide → Act)
- [x] Multi-provider LLM support (Ollama, Gemini, OpenAI)
- [x] RAG memory with ChromaDB + TF-IDF fallback
- [x] Knowledge Distillation from task outcomes
- [x] Pattern Learning (24h user habit model)
- [x] Real-time voice pipeline: Faster-Whisper STT + streaming TTS (< 300ms first audio)
- [x] Screen capture, OCR, and UI understanding
- [x] Mouse & keyboard computer use via pyautogui (sandboxed)
- [x] Patch-based coding agent with verification loop
- [x] Multi-agent coordinator (parallel execution, timeout isolation)
- [x] MCP (Model Context Protocol) server integration
- [x] Twitch IRC bridge with content moderation
- [x] Plugin system (Chess, Home Assistant, Web Reader)
- [x] Relationship tracker and persistent identity across sessions
- [x] Spontaneity parameter per character
- [x] ApprovalRegistry for safe system actions
- [x] Telegram bot integration
- [x] Electron UI: overlay widget, settings panel, system tray

### 🚧 In Progress

- [ ] TaskPlan checklist UI (real-time step tracking in chat)
- [ ] Twitch response pipeline fully connected end-to-end
- [ ] Voice latency benchmark and optimization
- [ ] Skill matching — load only relevant SKILL.md instead of all

### 🔮 Planned

- [ ] Discord integration (voice channel + chat)
- [ ] VRM model support alongside Live2D
- [ ] Mobile companion app (Android / iOS)
- [ ] Multi-companion mode (characters can talk to each other)
- [ ] Web UI mode (no Electron required)
- [ ] Packaged Windows installer (.exe)
- [ ] Plugin marketplace

---

## 🤝 Contributing

Contributions are what make open source magical. Every PR, issue, and idea is welcome.

```bash
# Fork → Clone → Create branch → Make changes → Open PR
git checkout -b feat/your-amazing-feature
git commit -m "feat: add amazing feature"
git push origin feat/your-amazing-feature
```

**Areas where help is especially welcome:**

- 🎨 New Live2D characters or VRM models
- 🧠 New agent capabilities and tools
- 🌍 Translations and localization
- 🔊 TTS engine integrations
- 🧪 Tests — we need more of them
- 📖 Documentation improvements

Please read [CONTRIBUTING.md](CONTRIBUTING.md) before submitting a PR.

---

## 📁 Project Structure

<details>
<summary>Show directory overview</summary>

```
Open-LLM-DeskAgent/
├── agents/           # Specialized agents (browser, coding, vision, memory…)
├── api/              # FastAPI server + WebSocket manager + Telegram
├── assets/           # Live2D models, icons
├── cognition/        # Reasoning, prompts, response parsing, self-correction
├── config/           # Config files and character definitions
├── decision/         # Action selection, policy engine, risk assessment
├── desktop/          # Electron main process (JS/TS)
├── execution/        # Tool executors (mouse, keyboard, terminal, browser, sandbox)
├── interaction/      # Voice, hotkeys, gestures, Twitch bridge
├── knowledge/        # RAG pipeline, vector store, knowledge graph
├── learning/         # Distillation, pattern learning, experience replay
├── life/             # Life Loop: observe, feel, think, decide, act, reflect
├── llm/              # LLM providers and streaming
├── mcp_agent/        # MCP client and server registry
├── memory/           # Short-term, long-term, episodic, semantic memory
├── perception/       # Screen watcher, clipboard, filesystem, voice
├── persona/          # Emotion engine, mood, identity, expressions, dialogue
├── planning/         # Task graph, scheduler, workflow runner
├── plugins/          # Plugin system + built-in plugins
├── renderer/         # Electron renderer (HTML/CSS/JS/TS)
├── runtime/          # EventBus, lifecycle, pipeline, session
├── skills/           # SKILL.md capability definitions
├── speech/           # STT, TTS, hotword detection
├── tools/            # Computer control, file tools, web search, registry
├── vision/           # Screen understanding, UI grounding
└── world/            # Desktop state, application tracker, activity timeline
```

</details>

---

## 📄 License

Distributed under the **MIT License**. See [LICENSE](LICENSE) for details.

You are free to use, modify, and distribute this project — even commercially. Just keep the attribution.

---

<div align="center">

**Built with ❤️ for everyone who ever wanted a companion that truly understands them.**

_If this project means something to you, consider giving it a ⭐ — it helps others discover it._

<br/>

[![Star History Chart](https://api.star-history.com/svg?repos=your-username/Open-LLM-DeskAgent&type=Date)](https://star-history.com/#your-username/Open-LLM-DeskAgent&Date)

</div>
