import { AvatarController } from "../../live2d/live2d-manager.js";
import { AudioPlayer } from "../voice/audio-player.js";
import { VoiceRecorder } from "../voice/recoder.js";

// ─── Lazy-loaded modules (CDN-dependent, must not block avatar rendering) ───
let LocalDB = {
  init: () => Promise.resolve(false),
  addMemory: () => Promise.resolve(null),
  searchMemories: () => Promise.resolve([]),
  syncFromBackend: () => Promise.resolve(),
};
let WebGPUEngine = {
  isInitialized: () => false,
  init: () => Promise.reject(new Error("WebGPU not loaded")),
  chat: () => Promise.reject(new Error("WebGPU not loaded")),
};

// Load CDN-dependent modules asynchronously
(async () => {
  try {
    const mod = await import("../shared/local-db.js");
    LocalDB = mod.LocalDB;
    console.log("[avatar-pet] LocalDB module loaded");
  } catch (err) {
    console.warn("[avatar-pet] LocalDB module failed to load (offline?):", err.message);
  }
  try {
    const mod = await import("../shared/webgpu-engine.js");
    WebGPUEngine = mod.WebGPUEngine;
    console.log("[avatar-pet] WebGPUEngine module loaded");
  } catch (err) {
    console.warn("[avatar-pet] WebGPUEngine module failed to load:", err.message);
  }
})();

const avatarWrap = document.getElementById("avatarWrap");
const petCaption = document.getElementById("petCaption");
const petStatusDot = document.getElementById("petStatusDot");
const petStatusText = document.getElementById("petStatusText");
const petChatForm = document.getElementById("petChatForm");
const petChatInput = document.getElementById("petChatInput");
const petMicButton = document.getElementById("petMicButton");
const petPowerButton = document.getElementById("petPowerButton");

let currentModelPath = "assets/live2d/IceGirl/IceGirl.model3.json"; // default

// Helper to identify character model from path
function getModelKey(modelPath) {
  if (!modelPath) return "icegirl";
  const pathLower = modelPath.toLowerCase();
  if (pathLower.includes("hiyori")) return "hiyori";
  if (pathLower.includes("mao")) return "mao";
  if (pathLower.includes("huohuo")) return "huohuo";
  return "icegirl";
}

const MODEL_ACCESSORIES = {
  icegirl: [
    {
      id: "gamepad",
      label: "🎮 Tay cầm",
      paramId: "ShouBing",
      type: "toggle",
      defaultValue: 0,
      activeValue: 1,
    },
    {
      id: "catears",
      label: "🐱 Tai mèo",
      paramId: "Param53",
      type: "toggle",
      defaultValue: 0,
      activeValue: 1,
    },
    {
      id: "crown",
      label: "👑 Vương miện",
      paramId: "Param40",
      type: "toggle",
      defaultValue: 0,
      activeValue: 1,
    },
    {
      id: "wings",
      label: "🪶 Cánh",
      paramId: "Param41",
      type: "toggle",
      defaultValue: 0,
      activeValue: 1,
    },
    {
      id: "headset",
      label: "🎧 Tai nghe",
      paramId: "JiaJu",
      type: "toggle",
      defaultValue: 0,
      activeValue: 1,
    },
    {
      id: "ponytail",
      label: "💇 Đuôi ngựa",
      paramId: "Param51",
      type: "hair",
      activeValue: 1,
      defaultValue: 0,
    },
    {
      id: "loosehair",
      label: "💇 Tóc xõa",
      paramId: "Param51",
      type: "hair",
      activeValue: 2,
      defaultValue: 0,
    },
  ],
  huohuo: [
    {
      id: "cushion",
      label: "🧸 Gối ôm",
      paramId: ["Param99", "Param119", "Param120", "Param121", "Param122"],
      type: "toggle",
      defaultValue: 0,
      activeValue: 1,
    },
    {
      id: "flag1",
      label: "🚩 Lá cờ 1",
      paramId: "Param63",
      type: "flag",
      activeValue: 1,
      defaultValue: 0,
    },
    {
      id: "flag2",
      label: "🚩 Lá cờ 2",
      paramId: ["Param63", "Param127"],
      type: "flag",
      activeValue: 1,
      defaultValue: 0,
    },
  ],
  mao: [
    {
      id: "exp02",
      label: "😊 Cười",
      expressionName: "exp_02",
      type: "expression",
    },
    {
      id: "exp04",
      label: "😃 Vui vẻ",
      expressionName: "exp_04",
      type: "expression",
    },
    {
      id: "exp05",
      label: "😢 Buồn",
      expressionName: "exp_05",
      type: "expression",
    },
    {
      id: "exp06",
      label: "🤔 Suy nghĩ",
      expressionName: "exp_06",
      type: "expression",
    },
    {
      id: "exp07",
      label: "😮 Ngạc nhiên",
      expressionName: "exp_07",
      type: "expression",
    },
    {
      id: "exp08",
      label: "😠 Tức giận",
      expressionName: "exp_08",
      type: "expression",
    },
  ],
  hiyori: [],
};

function rebuildAccessoryButtons(modelPath) {
  const container = document.getElementById("characterPropsRow");
  if (!container) return;
  container.innerHTML = "";

  const modelKey = getModelKey(modelPath);
  const accessories = MODEL_ACCESSORIES[modelKey] || [];

  if (accessories.length === 0) {
    container.style.display = "none";
    return;
  }
  container.style.display = "flex";

  accessories.forEach((acc) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pose-button";
    btn.textContent = acc.label;
    btn.dataset.id = acc.id;

    btn.addEventListener("click", () => {
      const isActive = btn.classList.toggle("active");

      if (acc.type === "expression") {
        // Expression buttons are mutually exclusive
        if (isActive) {
          container.querySelectorAll(".pose-button").forEach((b) => {
            if (b !== btn) b.classList.remove("active");
          });
          avatar.setState({ expression: acc.expressionName });
        } else {
          avatar.setState({ expression: "normal" });
        }
      } else if (acc.type === "hair") {
        if (isActive) {
          // Deactivate other hair buttons
          accessories.forEach((otherAcc) => {
            if (otherAcc.type === "hair" && otherAcc.id !== acc.id) {
              const otherBtn = container.querySelector(
                `[data-id="${otherAcc.id}"]`,
              );
              if (otherBtn) otherBtn.classList.remove("active");
            }
          });
          avatar.setAccessory(acc.paramId, acc.activeValue);
        } else {
          avatar.setAccessory(acc.paramId, acc.defaultValue);
        }
      } else if (acc.type === "flag") {
        if (isActive) {
          // Deactivate other flag buttons
          accessories.forEach((otherAcc) => {
            if (otherAcc.type === "flag" && otherAcc.id !== acc.id) {
              const otherBtn = container.querySelector(
                `[data-id="${otherAcc.id}"]`,
              );
              if (otherBtn) otherBtn.classList.remove("active");
              // Reset other flag parameters
              if (Array.isArray(otherAcc.paramId)) {
                otherAcc.paramId.forEach((pid) =>
                  avatar.setAccessory(pid, otherAcc.defaultValue),
                );
              } else {
                avatar.setAccessory(otherAcc.paramId, otherAcc.defaultValue);
              }
            }
          });
          // Apply this flag
          if (Array.isArray(acc.paramId)) {
            acc.paramId.forEach((pid) =>
              avatar.setAccessory(pid, acc.activeValue),
            );
          } else {
            avatar.setAccessory(acc.paramId, acc.activeValue);
          }
        } else {
          // Reset this flag parameters
          if (Array.isArray(acc.paramId)) {
            acc.paramId.forEach((pid) =>
              avatar.setAccessory(pid, acc.defaultValue),
            );
          } else {
            avatar.setAccessory(acc.paramId, acc.defaultValue);
          }
        }
      } else {
        // Normal toggle
        const val = isActive ? acc.activeValue : acc.defaultValue;
        avatar.setAccessory(acc.paramId, val);
      }
    });

    container.appendChild(btn);
  });
}

const avatar = new AvatarController({
  wrap: avatarWrap,
  light: document.getElementById("expressionLight"),
  img: document.getElementById("avatarImage"),
});
const recorder = new VoiceRecorder();
const audioPlayer = new AudioPlayer();

let isRecording = false;
let busy = false;
let pointerDrag = null;
let currentReply = "";
let clickResetTimeout = null;

let ttsQueue = [];
let ttsPlaying = false;
let chatDone = false;

const VoiceState = {
  IDLE: "idle",
  LISTENING: "listening",
  USER_SPEAKING: "user_speaking",
  THINKING: "thinking",
  SPEAKING: "speaking",
};
let currentVoiceState = VoiceState.IDLE;
let currentInteractionMode = "streamer";
let streamerLoopActive = false;
let draftInterval = null;
let voiceSequence = 0;
let sttProcessing = false;


function setVoiceState(state) {
  currentVoiceState = state;
  setStatus(state);
}

function setCaption(text) {
  if (!petCaption || !text) return;
  petCaption.textContent = text;
}

function setStatus(status) {
  const label = status || "idle";
  if (petStatusText) petStatusText.textContent = label;
  if (petStatusDot) petStatusDot.dataset.status = label;
  if (petMicButton) {
    const isMicActive =
      label === "listening" ||
      label === "user_speaking" ||
      (currentInteractionMode === "streamer" && streamerLoopActive);
    petMicButton.classList.toggle("active", isMicActive);
  }
}

function setControlsDisabled(disabled) {
  if (petChatInput) petChatInput.disabled = disabled;
  const sendButton = petChatForm?.querySelector('button[type="submit"]');
  if (sendButton) sendButton.disabled = disabled;
}

function setFacing(dx) {
  avatarWrap.classList.toggle("facing-left", dx < 0);
}

function setWalking(active) {
  avatarWrap.classList.toggle("walking", active);
}

function setRecording(active) {
  avatarWrap.classList.toggle("recording", active);
}

async function sleep(ms) {
  await new Promise((resolve) => setTimeout(resolve, ms));
}

async function ask(text) {
  const clean = text.trim();
  if (!clean) return;

  busy = true;
  currentReply = "";
  setCaption(clean);
  setStatus("thinking");
  setControlsDisabled(true);
  setWalking(false);
  avatar.setState({ expression: "thinking", motion: "thinking" });

  // Reset audio queue state
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;

  // Search memories in PGlite WASM
  let memoryContext = [];
  try {
    const memories = await LocalDB.searchMemories(clean);
    memoryContext = memories.map(m => ({ text: m.text }));
  } catch (err) {
    console.warn("Failed to query LocalDB:", err);
  }

  // Get current LLM provider config
  let provider = "ollama";
  try {
    const config = await window.companion.invoke('ai:get-config');
    if (config && !config.error) {
      provider = config.llm_provider || "ollama";
    }
  } catch (err) {
    console.warn("Failed to get config:", err);
  }

  if (provider === 'webgpu') {
    // ----------------------------------------------------
    // Run Local WebGPU Inference in Pet Window
    // ----------------------------------------------------
    if (!WebGPUEngine.isInitialized()) {
      setCaption("Mô hình WebGPU chưa được tải. Vui lòng mở bảng Chat và chọn bộ não WebGPU để tải mô hình.");
      setStatus("error");
      avatar.setState({ expression: "sad", motion: "shake", lipsync: false });
      busy = false;
      setControlsDisabled(false);
      return;
    }

    const systemPrompt = "Bạn là IceGirl, trợ lý ảo cá nhân 2.5D cực kỳ đáng yêu, thân thiện và thông minh. Hãy trả lời người dùng một cách tự nhiên, ngắn gọn và thêm các thẻ cảm xúc như [smile], [happy], [excited], [thinking], [sad] phù hợp.\n" +
      (memoryContext.length > 0 ? "Thông tin đã ghi nhớ về người dùng: " + memoryContext.map(m => m.text).join("; ") : "");

    const messages = [
      { role: "system", content: systemPrompt },
      { role: "user", content: clean }
    ];

    let parserBuffer = "";
    const EMOTION_REGEX = /\[(normal|neutral|smile|friendly|happy|excited|focused|thinking|sad|angry|surprised|wink|tongue|money)\]/i;

    try {
      setStatus("speaking");
      window.companion.broadcast('start', { emotion: 'normal', motion: 'thinking' });
      window.companion.setLipsync(true);

      const onChunk = (token) => {
        parserBuffer += token;
        
        const match = parserBuffer.match(EMOTION_REGEX);
        if (match) {
          const tag = match[0];
          const emotion = match[1].toLowerCase();
          parserBuffer = parserBuffer.replace(tag, "");
          avatar.setState({ expression: emotion });
          window.companion.setEmotion(emotion);
        }
        
        const idx = parserBuffer.indexOf('[');
        const idxAngle = parserBuffer.indexOf('<');
        
        let textToYield = "";
        if (idx === -1 && idxAngle === -1) {
          textToYield = parserBuffer;
          parserBuffer = "";
        } else {
          const indices = [idx, idxAngle].filter(i => i !== -1);
          const firstIdx = Math.min(...indices);
          if (firstIdx > 0) {
            textToYield = parserBuffer.substring(0, firstIdx);
            parserBuffer = parserBuffer.substring(firstIdx);
          }
        }
        
        if (textToYield) {
          currentReply += textToYield;
          setCaption(currentReply);
          window.companion.broadcast('chat_chunk', textToYield);
        }
      };

      await WebGPUEngine.chat(messages, onChunk);
      
      if (parserBuffer) {
        currentReply += parserBuffer;
        setCaption(currentReply);
        window.companion.broadcast('chat_chunk', parserBuffer);
      }

      window.companion.broadcast('chat_done', currentReply);
      await LocalDB.addMemory(clean);

      // Synthesize TTS
      const ttsRes = await window.companion.invoke("ai:tts", { text: currentReply });
      if (ttsRes && ttsRes.ok && ttsRes.response.audio_url) {
        ttsQueue.push({ url: ttsRes.response.audio_url, durationMs: ttsRes.response.duration_ms });
        processTtsQueue();
      } else {
        avatar.setState({ expression: "smile", motion: "idle", lipsync: false });
        window.companion.setLipsync(false);
        busy = false;
        setControlsDisabled(false);
      }
      chatDone = true;

    } catch (err) {
      console.error("WebGPU Chat Generation Error (Pet):", err);
      setCaption("Lỗi suy luận WebGPU: " + err.message);
      setStatus("error");
      busy = false;
      setControlsDisabled(false);
    }

  } else {
    // ----------------------------------------------------
    // Run normal HTTP Chat over Python Server
    // ----------------------------------------------------
    const context = {
      locale: "vi-VN",
      mode: "voice",
      memory: memoryContext
    };

    const res = await window.companion.chat(clean, context);
    if (!res?.ok) {
      setCaption("Backend đang offline. Khởi động lại Python service nhé.");
      setStatus("error");
      avatar.setState({ expression: "sad", motion: "shake", lipsync: false });
      busy = false;
      setControlsDisabled(false);
    } else {
      await LocalDB.addMemory(clean);
    }
  }
}

async function handleBargeIn() {
  console.log("[Barge-in] User interrupted the AI!");
  setVoiceState(VoiceState.USER_SPEAKING);

  // Cancel active LLM/TTS streams on backend
  window.companion.invoke("ai:cancel-chat").catch(() => null);

  // Abort local playback and lipsync
  audioPlayer.stop();
  avatar.stopLipSync();

  // Clear audio player queue
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;

  // Reset recorder's sample buffer
  recorder.clearBuffer();
  voiceSequence = 0;
  setCaption("Đang nghe...");
  avatar.setState({ expression: "focused", motion: "nod" });
}

async function startRecording() {
  try {
    busy = true;
    setVoiceState(VoiceState.LISTENING);
    setCaption("Đang nghe...");
    setWalking(false);
    window.companion.invoke("ai:interact").catch(() => null);

    voiceSequence = 0;

    // Bind VAD callbacks with intelligent energy threshold for barge-in
    recorder.onSpeechStartCallback = (rms) => {
      if (currentVoiceState === VoiceState.SPEAKING) {
        const BARGE_IN_ENERGY_THRESHOLD = 0.05; // ignore background noise / speaker echo
        if (rms >= BARGE_IN_ENERGY_THRESHOLD) {
          handleBargeIn();
        } else {
          console.log(
            `[Barge-in] Ignored voice activity below threshold: ${rms.toFixed(4)} < ${BARGE_IN_ENERGY_THRESHOLD}`,
          );
          recorder.resetSpeakingState();
        }
      } else {
        setVoiceState(VoiceState.USER_SPEAKING);
      }
    };

    await recorder.start(() => {
      console.log("[VAD] Silence/Timeout detected, auto stopping.");
      stopRecording();
    });

    isRecording = true;
    setRecording(true);
    avatar.setState({ expression: "focused", motion: "look_side" });
  } catch (err) {
    console.error("[startRecording] error:", err);
    busy = false;
    setVoiceState(VoiceState.IDLE);
    avatar.setState({ expression: "sad", motion: "shake" });
  }
}

async function stopRecording() {
  if (draftInterval) {
    clearInterval(draftInterval);
    draftInterval = null;
  }

  isRecording = false;
  setRecording(false);
  setVoiceState(VoiceState.THINKING);
  setCaption("Đang xử lý giọng nói...");
  avatar.setState({ expression: "thinking", motion: "thinking" });

  const b64 = await recorder.stop();
  if (!b64) {
    busy = false;
    setVoiceState(VoiceState.IDLE);
    setControlsDisabled(false);
    avatar.setState({ expression: "normal", motion: "idle" });
    return;
  }

  const res = await window.companion.invoke("ai:voice-input", {
    audio_b64: b64,
    is_draft: false,
    sequence: ++voiceSequence,
    timestamp: Date.now(),
  });

  if (!res?.ok) {
    busy = false;
    setVoiceState(VoiceState.IDLE);
    setCaption("Mình chưa nghe rõ. Thử lại nhé.");
    setControlsDisabled(false);
    avatar.setState({ expression: "sad", motion: "shake" });
  }
}

petChatForm?.addEventListener("submit", (event) => {
  event.preventDefault();
  const text = petChatInput?.value.trim() || "";
  if (!text || busy) return;
  petChatInput.value = "";
  window.companion.invoke("ai:interact").catch(() => null);
  ask(text);
});

function toggleMic() {
  if (currentInteractionMode === "streamer") {
    streamerLoopActive = !streamerLoopActive;
    if (streamerLoopActive) {
      startRecording();
    } else {
      isRecording = false;
      busy = false;
      setRecording(false);
      setVoiceState(VoiceState.IDLE);
      setControlsDisabled(false);

      window.companion.invoke("ai:cancel-chat").catch(() => null);
      audioPlayer.stop();
      avatar.stopLipSync();
      ttsQueue = [];
      ttsPlaying = false;
      chatDone = false;

      recorder.stop().catch(() => null);
      if (draftInterval) {
        clearInterval(draftInterval);
        draftInterval = null;
      }
      setCaption("Đã dừng nghe.");
      avatar.setState({ expression: "smile", motion: "idle" });
    }
  } else {
    if (isRecording) stopRecording();
    else if (!busy) startRecording();
  }
}

const petCodeButton = document.getElementById("petCodeButton");
petCodeButton?.addEventListener("click", () => {
  window.companion.openCoding();
});

petMicButton?.addEventListener("click", () => {
  toggleMic();
});

petPowerButton?.addEventListener("click", () => {
  window.companion.hideAvatar();
});

avatarWrap.addEventListener("pointerdown", async (event) => {
  event.preventDefault();
  window.companion.invoke("ai:interact").catch(() => null);
  const bounds = await window.companion.petBounds();
  if (!bounds) return;
  pointerDrag = {
    id: event.pointerId,
    screenX: event.screenX,
    screenY: event.screenY,
    startX: bounds.x,
    startY: bounds.y,
    moved: false,
  };
  avatarWrap.setPointerCapture(event.pointerId);
});

avatarWrap.addEventListener("pointermove", (event) => {
  if (!pointerDrag || pointerDrag.id !== event.pointerId) return;
  const dx = event.screenX - pointerDrag.screenX;
  const dy = event.screenY - pointerDrag.screenY;
  if (Math.hypot(dx, dy) > 5) pointerDrag.moved = true;
  setFacing(dx);
  window.companion.petMoveTo({
    x: pointerDrag.startX + dx,
    y: pointerDrag.startY + dy,
  });
});

avatarWrap.addEventListener("pointerup", (event) => {
  if (!pointerDrag || pointerDrag.id !== event.pointerId) return;
  const wasClick = !pointerDrag.moved;
  pointerDrag = null;
  avatarWrap.releasePointerCapture(event.pointerId);

  if (wasClick) {
    // Play a gentle reaction instead of starting voice recording
    if (!busy && !isRecording) {
      // Calculate coordinates relative to the wrapper bounds
      const rect = avatarWrap.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;

      avatar.handleTap(x, y);

      // NÂNG CẤP: Theo dõi click chuột liên tục để kích hoạt tương tác vật lý
      trackClickForMicroInteraction();

      if (clickResetTimeout) clearTimeout(clickResetTimeout);
      clickResetTimeout = setTimeout(() => {
        if (!busy && !isRecording) {
          avatar.setState({ expression: "normal", motion: "idle" });
        }
      }, 3000);
    }
  }
});

window.addEventListener("keydown", (event) => {
  if (event.target === petChatInput) return;
  if (event.code === "Space") {
    event.preventDefault();
    toggleMic();
  }
});

window.companion.on("python:ready", () => {
  setStatus("idle");
  avatar.setState({ expression: "smile", motion: "nod" });
  applyInitialMode();
});

window.companion.on("set:emotion", (emotion) => {
  avatar.setState({
    expression: emotion,
    motion: emotion === "excited" ? "excited" : "idle",
  });
});

window.companion.on("set:lipsync", (active) => {
  if (!active && (ttsPlaying || ttsQueue.length > 0)) {
    return;
  }
  avatar.setState({ lipsync: Boolean(active) });
});

window.companion.on("stt:result", (text) => {
  if (text) ask(text);
  else {
    busy = false;
    setStatus("error");
    setCaption("Minh chua nghe ro. Thu lai nhe.");
    setControlsDisabled(false);
    avatar.setState({ expression: "sad", motion: "shake" });
  }
});

window.companion.on("chat:chunk", (chunk) => {
  if (chunk) {
    currentReply += chunk;
    setCaption(currentReply);
  }
});

async function processTtsQueue() {
  if (ttsPlaying) return;
  if (ttsQueue.length === 0) {
    if (chatDone) {
      avatar.setState({ expression: "smile", motion: "idle", lipsync: false });
      busy = false;

      if (currentInteractionMode === "streamer") {
        setTimeout(() => {
          if (currentInteractionMode === "streamer" && streamerLoopActive) {
            startRecording();
          } else {
            setVoiceState(VoiceState.IDLE);
            setControlsDisabled(false);
          }
        }, 500);
      } else {
        setVoiceState(VoiceState.IDLE);
        setControlsDisabled(false);
      }
    }
    return;
  }

  ttsPlaying = true;
  const { url } = ttsQueue.shift();
  const absoluteUrl = url.startsWith("http")
    ? url
    : `http://127.0.0.1:8765${url}`;

  try {
    busy = true;
    setVoiceState(VoiceState.SPEAKING);
    await audioPlayer.play(absoluteUrl, (amp) => avatar.startLipSync(amp));
  } catch (err) {
    console.warn("[tts] pet audio playback failed:", err);
  } finally {
    avatar.stopLipSync();
    ttsPlaying = false;
    setTimeout(processTtsQueue, 50);
  }
}

window.companion.on("chat:done", (reply) => {
  if (!currentReply && reply) setCaption(reply);
  chatDone = true;
  if (!ttsPlaying && ttsQueue.length === 0) {
    avatar.setState({ expression: "smile", motion: "idle", lipsync: false });
    busy = false;
    if (currentInteractionMode === "streamer") {
      setTimeout(() => {
        if (currentInteractionMode === "streamer" && streamerLoopActive) {
          startRecording();
        } else {
          setVoiceState(VoiceState.IDLE);
          setControlsDisabled(false);
        }
      }, 500);
    } else {
      setVoiceState(VoiceState.IDLE);
      setControlsDisabled(false);
    }
  }
});

window.companion.on("tts:audio", async ({ url } = {}) => {
  if (!url) return;
  ttsQueue.push({ url });
  processTtsQueue();
});

window.companion.on("tts:done", () => {
  ttsPlaying = false;
  busy = false;
  if (currentInteractionMode !== "streamer") {
    setVoiceState(VoiceState.IDLE);
    setControlsDisabled(false);
  }
  avatar.stopLipSync();
});

window.companion.on(
  "chat:request-approval",
  async ({ req_id, action, details }) => {
    avatar.setState({ expression: "focused", motion: "thinking" });
    const approved = confirm(
      `IceGirl muốn thực hiện hành động:\n${action}\n\nChi tiết:\n${JSON.stringify(details, null, 2)}\n\nBạn có đồng ý không?`,
    );
    await window.companion.invoke("ai:submit-approval", { req_id, approved });
  },
);

window.companion.on("trigger:screenshot", async () => {
  busy = true;
  setStatus("thinking");
  setControlsDisabled(true);
  await window.companion.invoke("ai:screenshot", {
    question: "Man hinh dang hien thi gi?",
  });
});

function toggleConsole() {
  const petConsole = document.getElementById("petConsole");
  const avatarStage = document.querySelector(".avatar-stage");
  if (petConsole) {
    const isHidden = petConsole.classList.toggle("hidden");
    if (avatarStage) {
      avatarStage.classList.toggle("console-hidden", isHidden);
    }
  }
}

// Double click on avatar to toggle console
avatarWrap?.addEventListener("dblclick", (event) => {
  event.stopPropagation();
  toggleConsole();
});

// Listen from Electron IPC
window.companion.on("toggle:console", () => {
  toggleConsole();
});

window.companion.health().catch(() => null);
setInterval(() => window.companion.health().catch(() => null), 5000);

// Listen to config updates from the options window
window.companion.on("config:updated", ({ key, value }) => {
  if (key === "llm.provider") {
    const names = {
      ollama: "Ollama (Local)",
      gemini: "Gemini API",
      openai: "OpenAI API",
    };
    setCaption(`Bộ não đã được đổi sang: ${names[value] || value}`);
  } else if (key === "features.screenAwareness") {
    setCaption(`Tự động nhận thức màn hình đã: ${value ? "BẬT" : "TẮT"}`);
  } else if (key === "features.twitchMode") {
    setCaption(`Đọc chat livestream Twitch đã: ${value ? "BẬT" : "TẮT"}`);
  } else if (key === "twitch.channel") {
    setCaption(`Đã lưu kênh Twitch: ${value}`);
  } else if (key === "app.interactionMode") {
    currentInteractionMode = value;
    const petConsole = document.getElementById("petConsole");
    const avatarStage = document.querySelector(".avatar-stage");
    if (petConsole) {
      const isStreamer = value === "streamer";
      petConsole.classList.toggle("hidden", isStreamer);
      if (avatarStage) {
        avatarStage.classList.toggle("console-hidden", isStreamer);
      }
    }
    setCaption(
      `Chế độ tương tác: ${value === "streamer" ? "Streamer (Neuro-Sama)" : "Trợ lý (Chat Box)"}`,
    );
    if (value === "streamer") {
      streamerLoopActive = true;
      startRecording();
    } else if (streamerLoopActive) {
      streamerLoopActive = false;
      toggleMic();
    }
  } else if (key === "app.avatarModel") {
    avatar.changeModel(value);
    currentModelPath = value;
    rebuildAccessoryButtons(value);
    setCaption(`Đã đổi nhân vật thành công!`);

  }
});

// Notifications polling and handling
async function handleNotification(note) {
  if (note.type === "screen_comment" || note.type === "twitch_comment") {
    busy = true;
    currentReply = note.text;
    setCaption(note.text);

    setStatus("speaking");
    if (note.emotion) {
      avatar.setState({ expression: note.emotion, motion: "nod" });
    }

    // Clear and play TTS
    ttsQueue = [];
    ttsPlaying = false;
    chatDone = true;

    if (note.audio_url) {
      ttsQueue.push({ url: note.audio_url });
      processTtsQueue();
    } else {
      await sleep(3500);
      avatar.setState({ expression: "smile", motion: "idle", lipsync: false });
      busy = false;
      setStatus("idle");
    }
  }
}

setInterval(async () => {
  if (busy || isRecording) return;
  try {
    const res = await window.companion.invoke("ai:get-notifications");
    if (res && res.notifications && res.notifications.length > 0) {
      for (const note of res.notifications) {
        await handleNotification(note);
      }
    }
  } catch (err) {
    console.warn("[notifications] Failed to fetch notifications:", err);
  }
}, 3000);

let initialModeApplied = false;

async function applyInitialMode() {
  if (initialModeApplied) return;
  try {
    const res = await window.companion.invoke("ai:get-config");
    if (res && !res.error) {
      initialModeApplied = true;
      currentInteractionMode = res.interaction_mode || "streamer";
      const petConsole = document.getElementById("petConsole");
      const avatarStage = document.querySelector(".avatar-stage");
      if (petConsole) {
        const isStreamer = currentInteractionMode === "streamer";
        petConsole.classList.toggle("hidden", isStreamer);
        if (avatarStage) {
          avatarStage.classList.toggle("console-hidden", isStreamer);
        }
      }
      if (res.avatar_model) {
        if (currentModelPath !== res.avatar_model) {
          currentModelPath = res.avatar_model;
          avatar.changeModel(res.avatar_model);
        }
      }

      rebuildAccessoryButtons(currentModelPath);
      if (currentInteractionMode === "streamer") {
        streamerLoopActive = true;
        startRecording();
      }
    }
  } catch (err) {
    console.warn("[config] Failed to apply initial interaction mode:", err);
  }
}
applyInitialMode();

setTimeout(() => {
  if (
    currentInteractionMode !== "streamer" &&
    currentVoiceState === VoiceState.IDLE
  ) {
    setStatus("idle");
    avatar.setState({ expression: "smile", motion: "idle" });
  }
}, 500);

window.addEventListener("mousemove", (e) => {
  if (pointerDrag) {
    if (
      window.companion &&
      typeof window.companion.setIgnoreMouseEvents === "function"
    ) {
      window.companion.setIgnoreMouseEvents(false);
    }
    return;
  }

  const petConsole = document.getElementById("petConsole");
  let isOverConsole = false;
  if (petConsole && !petConsole.classList.contains("hidden")) {
    const rect = petConsole.getBoundingClientRect();
    isOverConsole =
      e.clientX >= rect.left &&
      e.clientX <= rect.right &&
      e.clientY >= rect.top &&
      e.clientY <= rect.bottom;
  }

  const isOverAvatar = avatar.containsPoint(e.clientX, e.clientY);
  const isOverInteractive = isOverAvatar || isOverConsole;

  if (
    window.companion &&
    typeof window.companion.setIgnoreMouseEvents === "function"
  ) {
    if (isOverInteractive) {
      window.companion.setIgnoreMouseEvents(false);
    } else {
      window.companion.setIgnoreMouseEvents(true, { forward: true });
    }
  }
});

// ─── Size controls ───────────────────────────────────────────
(function initSizeControls() {
  const btns = document.querySelectorAll(".size-btn");
  if (!btns.length) return;

  // Restore saved scale
  const saved = parseFloat(localStorage.getItem("avatar_scale") || "1.0");
  if (saved && saved !== 1.0) _applyScale(saved, false);

  btns.forEach((btn) => {
    btn.addEventListener("click", () => {
      const scale = parseFloat(btn.dataset.scale);
      if (scale) _applyScale(scale, true);
    });
  });

  async function _applyScale(scale, save) {
    // Update active button
    document
      .querySelectorAll(".size-btn")
      .forEach((b) =>
        b.classList.toggle("active", parseFloat(b.dataset.scale) === scale),
      );
    // Resize Electron window
    try {
      await window.companion.petSetSize(scale);
    } catch (e) {}
    // Save preference
    if (save) localStorage.setItem("avatar_scale", String(scale));
    // Caption feedback
    const labels = { 0.6: "Nhỏ", 1.0: "Mặc định", 1.5: "Lớn", 2.0: "Rất lớn" };
    setCaption(`Cỡ nhân vật: ${labels[scale] || scale + "x"}`);
    setTimeout(() => {
      if (!busy) setCaption("");
    }, 1800);
  }
})();

// ─── Tương tác Vật lý: Kéo thả file & Click liên tục ──────────────────
let clickCount = 0;
let clickTimer = null;
let isDragging = false;

function trackClickForMicroInteraction() {
  clickCount++;
  if (clickTimer) clearTimeout(clickTimer);
  
  clickTimer = setTimeout(() => {
    clickCount = 0;
  }, 2000);

  if (clickCount >= 3) {
    clickCount = 0;
    if (clickTimer) clearTimeout(clickTimer);
    triggerMultiClickReaction();
  }
}

async function triggerMultiClickReaction() {
  try {
    const res = await fetch("http://127.0.0.1:8765/memory/profile");
    const profile = await res.json();
    const name = (profile.name || "IceGirl").toLowerCase();
    const rel = profile.relationship || { score: 15, level: "Người quen" };
    const level = rel.level || "Người quen";
    
    let reactionText = "";
    let emotion = "angry";
    
    if (name.includes("hiyori")) {
      if (level === "Bạn thân") {
        const quotes = [
          "Hì hì, nhột tớ quá nè! Cậu nghịch ghê á! [smile]",
          "Ơ kìa cậu! Trêu tớ là tớ nhột đó nha! [excited]",
          "Hí hí! Đừng chọc tớ mà, buồn cười quá! [happy]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "happy";
      } else if (level === "Người lạ") {
        reactionText = "Ủa... cậu đừng nhấp liên tục vào người tớ như vậy chứ, tớ hơi ngại á... [sad]";
        emotion = "sad";
      } else {
        const quotes = [
          "A! Cậu làm gì thế? Tớ nhột đó nha! [surprised]",
          "Nè nha, chọc tớ là tớ chọc lại đó hihi! [wink]",
          "Đừng bấm lung tung vào tớ mà, tập trung học đi nào! [focused]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "surprised";
      }
    } else if (name.includes("mao")) {
      if (level === "Bạn thân") {
        const quotes = [
          "Nè, chọc tôi vui lắm hả? Đồ ngốc này! [tongue]",
          "Tay cậu ngứa ngáy à? Muốn tôi phạt không? [angry]",
          "Hừm, nghịch tóc tôi là tôi bắt đền cafe đó nhé! [wink]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "wink";
      } else if (level === "Người lạ") {
        reactionText = "Hạn chế đụng vào tôi đi nhé, chúng ta chưa thân thiết đâu. [angry]";
        emotion = "angry";
      } else {
        const quotes = [
          "Cậu rảnh quá hả? Không có việc gì làm à? [focused]",
          "Đừng có nhấp chuột bừa bãi vào tôi nữa coi! [angry]",
          "Nhột đó! Tránh xa tôi ra một chút xem nào. [sad]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "angry";
      }
    } else if (name.includes("huohuo")) {
      if (level === "Bạn thân") {
        const quotes = [
          "Oa... cậu đừng làm thế, Anh Đuôi sẽ giận mắng cậu đó! [sad]",
          "Dạ... nhột quá à... cậu đừng chọc em nữa mà... [happy]",
          "Ơ... cậu cứ nghịch thế này làm em sợ ghê... [surprised]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "sad";
      } else if (level === "Người lạ") {
        reactionText = "Á! Ma cứu... ơ, hoá ra là cậu... Đừng hù em sợ mà... [surprised]";
        emotion = "surprised";
      } else {
        const quotes = [
          "Dạ... cậu đừng bấm liên tục vào em thế, em xin lỗi mà... [sad]",
          "Ơ kìa... có chuyện gì gấp hả cậu? Em đang nghe đây... [focused]",
          "Hu hu, đừng bắt nạt phán quan tập sự mà cậu... [sad]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "sad";
      }
    } else {
      if (level === "Bạn thân") {
        const quotes = [
          "Nè! Chọc tớ nhột lắm đó nha! Đồ nghịch ngợm! [tongue]",
          "Tay cậu nhanh hơn não rồi đấy à? [wink]",
          "Hihi! Nhột quá đi mất, dừng lại mau! [happy]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "happy";
      } else if (level === "Người lạ") {
        reactionText = "Cậu làm gì vậy? Đừng có gõ liên tục vào tớ chứ! [angry]";
        emotion = "angry";
      } else {
        const quotes = [
          "Nè nha! Đừng có nghịch chuột lung tung vào tớ chứ! [angry]",
          "Ui da! Cậu nhấn mạnh tay thế, đau tớ đấy! [sad]",
          "Bấm nữa là tớ cắn cho một miếng bây giờ! [tongue]"
        ];
        reactionText = quotes[Math.floor(Math.random() * quotes.length)];
        emotion = "angry";
      }
    }

    speakQuickReaction(reactionText, emotion);
  } catch (e) {
    console.error("Failed to trigger multi-click reaction:", e);
  }
}

async function speakQuickReaction(text, emotion) {
  window.companion.invoke("ai:cancel-chat").catch(() => null);
  audioPlayer.stop();
  avatar.stopLipSync();
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = true;

  if (emotion) {
    avatar.setState({ expression: emotion });
    window.companion.setEmotion(emotion);
  }
  setCaption(text);

  try {
    busy = true;
    setVoiceState(VoiceState.SPEAKING);
    const ttsRes = await window.companion.invoke("ai:tts", { text: text });
    if (ttsRes && ttsRes.ok && ttsRes.response.audio_url) {
      ttsQueue.push({ url: ttsRes.response.audio_url, durationMs: ttsRes.response.duration_ms });
      processTtsQueue();
    } else {
      busy = false;
      setVoiceState(VoiceState.IDLE);
    }
  } catch (e) {
    console.error("Failed to play quick reaction TTS:", e);
    busy = false;
    setVoiceState(VoiceState.IDLE);
  }
}

// Drag and drop events
document.addEventListener("dragover", (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (isDragging || busy || isRecording) return;
  isDragging = true;
  avatar.setState({ expression: "surprised", motion: "nod" });
  setCaption("Ủa, cậu đang định đưa file gì cho tớ thế? [excited]");
});

document.addEventListener("dragleave", (e) => {
  e.preventDefault();
  e.stopPropagation();
  // Drag leaves the window
  if (!e.relatedTarget) {
    isDragging = false;
    avatar.setState({ expression: "normal", motion: "idle" });
    setCaption("");
  }
});

document.addEventListener("drop", (e) => {
  e.preventDefault();
  e.stopPropagation();
  isDragging = false;
  if (busy || isRecording) return;

  const files = e.dataTransfer.files;
  if (files && files.length > 0) {
    const file = files[0];
    const fileName = file.name;
    const filePath = file.path; // Electron exposes absolute path
    const msg = `Oa! Cậu vừa thả thư mục hoặc tệp "${fileName}" vào tớ! Để tớ mở giao diện Coding Agent lên làm việc nhé! [happy]`;
    speakQuickReaction(msg, "happy");
    window.companion.openCoding(filePath);
  } else {
    avatar.setState({ expression: "normal", motion: "idle" });
    setCaption("");
  }
});
