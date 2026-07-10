"""EventType — registry of all event type constants.

Tất cả event type strings được định nghĩa tập trung ở đây.
Không hardcode string "VoiceDetected" ở nhiều nơi.
"""

from __future__ import annotations


class EventType:
    """Constants cho tất cả event types trong hệ thống."""

    # ── Perception ─────────────────────────────────────────────────────────
    VOICE_DETECTED          = "VoiceDetected"
    SPEECH_RECOGNIZED       = "SpeechRecognized"       # payload: {text, confidence, lang}
    SCREEN_CAPTURED         = "ScreenCaptured"          # payload: {image_path, timestamp}
    CLIPBOARD_CHANGED       = "ClipboardChanged"        # payload: {content, content_type}
    CONTEXT_CREATED         = "ContextCreated"          # payload: {context_packet}
    WINDOW_CHANGED          = "WindowChanged"           # payload: {title, process, path}

    # ── Memory ─────────────────────────────────────────────────────────────
    MEMORY_RETRIEVED        = "MemoryRetrieved"         # payload: {memories, query}
    MEMORY_WRITEBACK        = "MemoryWritebackStarted"
    MEMORY_SAVED            = "MemoryWritebackFinished" # payload: {memory_id, type}

    # ── Cognition / LLM ────────────────────────────────────────────────────
    INTENT_DETECTED         = "IntentDetected"          # payload: {intent, confidence, entities}
    LLM_STARTED             = "LLMStarted"              # payload: {model, prompt_tokens}
    TOKEN_STREAMED          = "TokenStreamed"            # payload: {token, accumulated}
    EMOTION_DETECTED        = "EmotionDetected"         # payload: {emotion, intensity, source}
    TOOL_REQUESTED          = "ToolRequested"           # payload: {tool_name, arguments}
    LLM_FINISHED            = "LLMFinished"             # payload: {full_text, total_tokens}

    # ── Execution ──────────────────────────────────────────────────────────
    TOOL_STARTED            = "ToolStarted"             # payload: {tool_name, arguments}
    TOOL_FINISHED           = "ToolFinished"            # payload: {tool_name, result, success}
    TOOL_FAILED             = "ToolFailed"              # payload: {tool_name, error, retry_count}
    APPROVAL_REQUESTED      = "ExecutionApprovalRequested"  # payload: {action, risk_level}
    APPROVAL_GRANTED        = "ExecutionApprovalGranted"
    APPROVAL_DENIED         = "ExecutionApprovalDenied"

    # ── Planning ───────────────────────────────────────────────────────────
    PLAN_CREATED            = "PlanCreated"             # payload: {goal, steps}
    PLAN_STEP_STARTED       = "PlanStepStarted"         # payload: {step_index, description}
    PLAN_STEP_FINISHED      = "PlanStepFinished"        # payload: {step_index, success}
    PLAN_FINISHED           = "PlanFinished"            # payload: {goal, success, duration}
    PLAN_FAILED             = "PlanFailed"              # payload: {goal, reason, retry}

    # ── Persona ────────────────────────────────────────────────────────────
    EXPRESSION_CHANGED      = "ExpressionChanged"       # payload: {expression, intensity}
    MOOD_UPDATED            = "MoodUpdated"             # payload: {mood, energy, valence}
    EMOTION_UPDATED         = "EmotionUpdated"          # payload: {emotion, intensity}
    RELATIONSHIP_UPDATED    = "RelationshipUpdated"     # payload: {level, delta, dimension}
    GOAL_COMPLETED          = "GoalCompleted"           # payload: {goal_id, goal_text}
    HABIT_TRIGGERED         = "HabitTriggered"          # payload: {habit_name, context}

    # ── Motivation ─────────────────────────────────────────────────────────
    BOREDOM_TRIGGERED       = "BoredomTriggered"        # payload: {idle_minutes, level}
    CURIOSITY_TRIGGERED     = "CuriosityTriggered"      # payload: {topic, question}
    DRIVE_ACTIVATED         = "DriveActivated"          # payload: {drive_name, intensity}

    # ── Speech / Avatar ────────────────────────────────────────────────────
    TTS_STARTED             = "TTSStarted"              # payload: {text, voice}
    TTS_FINISHED            = "TTSFinished"
    AUDIO_CHUNK_READY       = "AudioChunkReady"         # payload: {chunk_index, audio_b64}
    LIPSYNC_UPDATED         = "LipsyncUpdated"          # payload: {mouth_open, phoneme}
    MOTION_TRIGGERED        = "MotionTriggered"         # payload: {motion_name, priority}
    RESPONSE_FINISHED       = "ResponseFinished"        # payload: {text, duration_ms}

    # ── Life Loop ──────────────────────────────────────────────────────────
    LIFE_CYCLE_STARTED      = "LifeCycleStarted"
    LIFE_CYCLE_FINISHED     = "LifeCycleFinished"       # payload: {action_taken, reason}
    PROACTIVE_TRIGGERED     = "ProactiveTriggered"      # payload: {reason, message}
    SILENCE_DECISION        = "SilenceDecision"         # payload: {reason} — companion stays silent

    # ── Companion State ────────────────────────────────────────────────────
    STATE_CHANGED           = "StateChanged"            # payload: {from, to}

    # ── Lifecycle ──────────────────────────────────────────────────────────
    SYSTEM_READY            = "SystemReady"
    SYSTEM_SHUTDOWN         = "SystemShutdown"
    SESSION_STARTED         = "SessionStarted"          # payload: {session_id}
    SESSION_ENDED           = "SessionEnded"            # payload: {session_id, duration}
    ERROR_OCCURRED          = "ErrorOccurred"           # payload: {error_type, message, recoverable}
    PLUGIN_LOADED           = "PluginLoaded"            # payload: {plugin_name}
    PLUGIN_ERROR            = "PluginError"             # payload: {plugin_name, error}

    # ── OBS / External ────────────────────────────────────────────────────
    OBS_BROADCAST           = "OBSBroadcast"            # payload: {type, data}
