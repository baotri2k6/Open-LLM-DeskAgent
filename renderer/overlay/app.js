import { AvatarController } from "../../live2d/live2d-manager.js";
import { ChatHistory } from "../chat/history.js";
import { renderMessage, renderChunk, renderApprovalCard } from "../chat/message.js";
import { AudioPlayer } from "../voice/audio-player.js";
import { VoiceRecorder } from "../voice/recoder.js";
let LocalDB = {
  init: () => Promise.resolve(false),
  addMemory: () => Promise.resolve(null),
  searchMemories: () => Promise.resolve([]),
  syncFromBackend: () => Promise.resolve()
};
let WebGPUEngine = {
  isInitialized: () => false,
  init: () => Promise.reject(new Error("WebGPU not loaded")),
  chat: () => Promise.reject(new Error("WebGPU not loaded"))
};
(async () => {
  try {
    const mod = await import("../shared/local-db.js");
    LocalDB = mod.LocalDB;
    console.log("[app] LocalDB module loaded");
  } catch (err) {
    console.warn("[app] LocalDB module failed to load (offline?):", err.message);
  }
  try {
    const mod = await import("../shared/webgpu-engine.js");
    WebGPUEngine = mod.WebGPUEngine;
    console.log("[app] WebGPUEngine module loaded");
  } catch (err) {
    console.warn("[app] WebGPUEngine module failed to load:", err.message);
  }
})();
const log = document.getElementById("chatLog");
const form = document.getElementById("chatForm");
const input = document.getElementById("chatInput");
const voiceButton = document.getElementById("voiceButton");
const statusPill = document.getElementById("serviceStatus");
const llmSelect = document.getElementById("llmSelect");
const sttSelect = document.getElementById("sttSelect");
const attachButton = document.getElementById("attachButton");
const fileInput = document.getElementById("fileInput");
const imagePreviewArea = document.getElementById("imagePreviewArea");
const imagePreviewThumbnail = document.getElementById("imagePreviewThumbnail");
const clearImageButton = document.getElementById("clearImageButton");
const webgpuProgressContainer = document.getElementById("webgpuProgressContainer");
const webgpuProgressText = document.getElementById("webgpuProgressText");
const webgpuProgressPercent = document.getElementById("webgpuProgressPercent");
const webgpuProgressBar = document.getElementById("webgpuProgressBar");
let attachedImageBase64 = null;
const avatar = new AvatarController({
  wrap: document.getElementById("avatarWrap"),
  light: document.getElementById("expressionLight"),
  img: document.getElementById("avatarImage")
});
const history = new ChatHistory();
const audioPlayer = new AudioPlayer();
const recorder = new VoiceRecorder();
let streamEl = null;
let isRecording = false;
let ttsQueue = [];
let ttsPlaying = false;
let chatDone = false;
function setServiceStatus(ok) {
  if (statusPill) {
    statusPill.dataset.status = ok ? "ok" : "offline";
    statusPill.textContent = ok ? "Online" : "Offline";
  }
}
async function checkStatus() {
  try {
    const res = await window.companion.health();
    setServiceStatus(res.status === "ok");
  } catch {
    setServiceStatus(false);
  }
}
function addMessage(role, text) {
  const msg = history.add(role, text);
  if (log) {
    log.appendChild(renderMessage(msg));
    log.scrollTop = log.scrollHeight;
  }
}
function setBusy(active) {
  if (input) input.disabled = active;
  if (form) {
    const submitBtn = form.querySelector('button[type="submit"]');
    if (submitBtn) submitBtn.disabled = active;
  }
  avatar.setState({ expression: active ? "thinking" : "smile", motion: active ? "thinking" : "idle" });
}
checkStatus();
setInterval(checkStatus, 5e3);
window.companion.on("python:ready", () => setServiceStatus(true));
window.companion.on("set:emotion", (emotion) => {
  avatar.setState({ expression: emotion, motion: emotion === "excited" ? "excited" : "idle" });
});
window.companion.on("set:lipsync", (active) => {
  if (!active && (ttsPlaying || ttsQueue.length > 0)) {
    return;
  }
  avatar.setState({ lipsync: Boolean(active) });
});
window.companion.on("chat:chunk", (chunk) => {
  if (!streamEl) {
    streamEl = renderChunk();
    if (log) log.appendChild(streamEl);
  }
  const body = streamEl.querySelector(".msg-body");
  if (body) body.textContent += chunk;
  if (log) log.scrollTop = log.scrollHeight;
});
async function processTtsQueue() {
  if (ttsPlaying) return;
  if (ttsQueue.length === 0) {
    if (chatDone) {
      avatar.stopLipSync();
      window.companion.setLipsync(false);
      setBusy(false);
      if (input) input.focus();
    }
    return;
  }
  ttsPlaying = true;
  const item = ttsQueue.shift();
  if (item) {
    const { url } = item;
    window.companion.setLipsync(true);
    try {
      await audioPlayer.play(url, (amp) => avatar.startLipSync(amp));
    } catch (err) {
      console.warn("[tts] audio playback failed:", err);
    } finally {
      avatar.stopLipSync();
      ttsPlaying = false;
      setTimeout(processTtsQueue, 50);
    }
  }
}
window.companion.on("chat:done", (reply) => {
  if (streamEl) {
    const body = streamEl.querySelector(".msg-body");
    const text = (body ? body.textContent : "") || reply || "";
    history.add("assistant", text);
    streamEl = null;
  } else if (reply) {
    addMessage("assistant", reply);
  }
  chatDone = true;
  if (!ttsPlaying && ttsQueue.length === 0) {
    avatar.stopLipSync();
    window.companion.setLipsync(false);
    setBusy(false);
    if (input) input.focus();
  }
});
window.companion.on("tts:audio", async (data = {}) => {
  const url = data?.url;
  if (!url) return;
  ttsQueue.push({ url, durationMs: data.duration_ms || 0 });
  processTtsQueue();
});
if (form) {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (!input) return;
    const text = input.value.trim();
    if (!text && !attachedImageBase64) return;
    const imageToSend = attachedImageBase64;
    input.value = "";
    attachedImageBase64 = null;
    if (fileInput) fileInput.value = "";
    if (imagePreviewArea) imagePreviewArea.style.display = "none";
    if (imagePreviewThumbnail) imagePreviewThumbnail.src = "";
    streamEl = null;
    const displayMsg = imageToSend ? `${text ? text + " " : ""}![image](${imageToSend})` : text;
    addMessage("user", displayMsg);
    setBusy(true);
    ttsQueue = [];
    ttsPlaying = false;
    chatDone = false;
    audioPlayer.stop();
    avatar.stopLipSync();
    window.companion.invoke("ai:cancel-chat").catch((err) => {
      console.warn("Failed to cancel active generation:", err);
    });
    let memoryContext = [];
    try {
      const memories = await LocalDB.searchMemories(text);
      memoryContext = memories.map((m) => ({ text: m.text }));
    } catch (err) {
      console.warn("Failed to query LocalDB:", err);
    }
    if (llmSelect && llmSelect.value === "webgpu") {
      const systemPrompt = "B\u1EA1n l\xE0 IceGirl, tr\u1EE3 l\xFD \u1EA3o c\xE1 nh\xE2n 2.5D c\u1EF1c k\u1EF3 \u0111\xE1ng y\xEAu, th\xE2n thi\u1EC7n v\xE0 th\xF4ng minh. H\xE3y tr\u1EA3 l\u1EDDi ng\u01B0\u1EDDi d\xF9ng m\u1ED9t c\xE1ch t\u1EF1 nhi\xEAn, ng\u1EAFn g\u1ECDn v\xE0 th\xEAm c\xE1c th\u1EBB c\u1EA3m x\xFAc nh\u01B0 [smile], [happy], [excited], [thinking], [sad] ph\xF9 h\u1EE3p.\n" + (memoryContext.length > 0 ? "Th\xF4ng tin \u0111\xE3 ghi nh\u1EDB v\u1EC1 ng\u01B0\u1EDDi d\xF9ng: " + memoryContext.map((m) => m.text).join("; ") : "");
      const chatHistory = history.all().map((h) => ({
        role: h.role === "user" ? "user" : "assistant",
        content: h.text
      }));
      const messages = [
        { role: "system", content: systemPrompt },
        ...chatHistory
      ];
      let currentResponseText = "";
      let parserBuffer = "";
      const EMOTION_REGEX = /\[(normal|neutral|smile|friendly|happy|excited|focused|thinking|sad|angry|surprised|wink|tongue|money)\]/i;
      try {
        streamEl = renderChunk();
        if (log) log.appendChild(streamEl);
        window.companion.broadcast("start", { emotion: "normal", motion: "thinking" });
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
          const idx = parserBuffer.indexOf("[");
          const idxAngle = parserBuffer.indexOf("<");
          let textToYield = "";
          if (idx === -1 && idxAngle === -1) {
            textToYield = parserBuffer;
            parserBuffer = "";
          } else {
            const indices = [idx, idxAngle].filter((i) => i !== -1);
            const firstIdx = Math.min(...indices);
            if (firstIdx > 0) {
              textToYield = parserBuffer.substring(0, firstIdx);
              parserBuffer = parserBuffer.substring(firstIdx);
            }
          }
          if (textToYield && streamEl) {
            currentResponseText += textToYield;
            const body = streamEl.querySelector(".msg-body");
            if (body) body.textContent += textToYield;
            window.companion.broadcast("chat_chunk", textToYield);
            if (log) log.scrollTop = log.scrollHeight;
          }
        };
        await WebGPUEngine.chat(messages, onChunk);
        if (parserBuffer && streamEl) {
          const body = streamEl.querySelector(".msg-body");
          if (body) body.textContent += parserBuffer;
          currentResponseText += parserBuffer;
          window.companion.broadcast("chat_chunk", parserBuffer);
        }
        window.companion.broadcast("chat_done", currentResponseText);
        await LocalDB.addMemory(text);
        const ttsRes = await window.companion.invoke("ai:tts", { text: currentResponseText });
        if (ttsRes && ttsRes.ok && ttsRes.response.audio_url) {
          ttsQueue.push({ url: ttsRes.response.audio_url, durationMs: ttsRes.response.duration_ms });
          processTtsQueue();
        } else {
          avatar.setState({ expression: "smile", motion: "idle", lipsync: false });
          window.companion.setLipsync(false);
          setBusy(false);
          if (input) input.focus();
        }
        history.add("assistant", currentResponseText);
        streamEl = null;
        chatDone = true;
      } catch (err) {
        console.error("WebGPU Chat Generation Error:", err);
        addMessage("assistant", "L\u1ED7i suy lu\u1EADn WebGPU: " + err.message);
        setBusy(false);
      }
    } else {
      const context = {
        locale: "vi-VN",
        memory: memoryContext
      };
      const res = await window.companion.chat(text, imageToSend, context);
      if (!res?.ok) {
        addMessage("assistant", "Backend \u0111ang offline. B\u1EA1n kh\u1EDFi \u0111\u1ED9ng l\u1EA1i Python service gi\xFAp m\xECnh nh\xE9.");
        setBusy(false);
        setServiceStatus(false);
      } else {
        await LocalDB.addMemory(text);
      }
    }
  });
}
attachButton?.addEventListener("click", () => {
  fileInput?.click();
});
fileInput?.addEventListener("change", (event) => {
  const file = event.target.files[0];
  if (!file) return;
  const reader = new FileReader();
  reader.onload = (e) => {
    attachedImageBase64 = e.target?.result;
    if (imagePreviewThumbnail) imagePreviewThumbnail.src = attachedImageBase64;
    if (imagePreviewArea) imagePreviewArea.style.display = "flex";
  };
  reader.readAsDataURL(file);
});
clearImageButton?.addEventListener("click", () => {
  attachedImageBase64 = null;
  if (fileInput) fileInput.value = "";
  if (imagePreviewArea) imagePreviewArea.style.display = "none";
  if (imagePreviewThumbnail) imagePreviewThumbnail.src = "";
});
voiceButton.addEventListener("click", async () => {
  if (!isRecording) {
    ttsQueue = [];
    ttsPlaying = false;
    chatDone = true;
    audioPlayer.stop();
    avatar.stopLipSync();
    window.companion.invoke("ai:cancel-chat").catch((err) => {
      console.warn("Failed to cancel active generation:", err);
    });
    isRecording = true;
    voiceButton.classList.add("active");
    voiceButton.textContent = "Stop";
    avatar.setState({ expression: "focused", motion: "look_side" });
    await recorder.start(() => {
      voiceButton.click();
    });
    return;
  }
  isRecording = false;
  voiceButton.classList.remove("active");
  voiceButton.textContent = "Mic";
  setBusy(true);
  const b64 = await recorder.stop();
  if (b64) await window.companion.invoke("ai:voice-input", { audio_b64: b64 });
});
window.companion.on("stt:result", (text) => {
  if (input) input.value = text;
  setBusy(false);
});
window.companion.on("chat:request-approval", ({ req_id, action, details }) => {
  avatar.setState({ expression: "focused", motion: "thinking" });
  const approvalEl = renderApprovalCard(req_id, action, details);
  if (log) {
    log.appendChild(approvalEl);
    log.scrollTop = log.scrollHeight;
  }
});
window.companion.on("tts:done", () => avatar.stopLipSync());
window.companion.on("trigger:screenshot", async () => {
  addMessage("user", "[Nhin man hinh]");
  setBusy(true);
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;
  await window.companion.invoke("ai:screenshot", { question: "Man hinh dang hien thi gi?" });
});
setTimeout(() => {
  addMessage("assistant", "Chao ban! Minh la IceGirl. Ban can minh giup gi khong?");
  avatar.setState({ expression: "smile", motion: "idle" });
}, 300);
try {
  LocalDB.init().then(() => {
    console.log("[App] Local Vector DB initialized");
  });
} catch (err) {
  console.warn("[App] Failed to initialize Local Vector DB:", err);
}
async function loadConfig() {
  try {
    const res = await window.companion.invoke("ai:get-config", {});
    if (res && !res.error) {
      if (llmSelect) {
        const val = res.llm_provider || "ollama";
        llmSelect.value = val;
        if (val === "webgpu") {
          llmSelect.dispatchEvent(new Event("change"));
        }
      }
      if (sttSelect) sttSelect.value = res.stt_model || "base";
    }
  } catch (err) {
    console.warn("[config] Failed to load initial configuration:", err);
  }
}
if (llmSelect) {
  llmSelect.addEventListener("change", async () => {
    const provider = llmSelect.value;
    if (provider === "webgpu") {
      if (!WebGPUEngine.isInitialized()) {
        if (webgpuProgressContainer) webgpuProgressContainer.style.display = "flex";
        if (webgpuProgressText) webgpuProgressText.textContent = "\u0110ang kh\u1EDFi t\u1EA1o WebGPU...";
        if (webgpuProgressPercent) webgpuProgressPercent.textContent = "0%";
        if (webgpuProgressBar) webgpuProgressBar.style.width = "0%";
        setBusy(true);
        llmSelect.disabled = true;
        try {
          addMessage("system", "\u0110ang t\u1EA3i m\xF4 h\xECnh WebGPU Qwen2.5-1.5B (L\u1EA7n \u0111\u1EA7u c\xF3 th\u1EC3 m\u1EA5t v\xE0i ph\xFAt)...");
          await WebGPUEngine.init((text, progress) => {
            if (webgpuProgressText) webgpuProgressText.textContent = text;
            const percent = Math.round(progress * 100);
            if (webgpuProgressPercent) webgpuProgressPercent.textContent = `${percent}%`;
            if (webgpuProgressBar) webgpuProgressBar.style.width = `${percent}%`;
          });
          addMessage("system", "Kh\u1EDFi t\u1EA1o v\xE0 t\u1EA3i th\xE0nh c\xF4ng m\xF4 h\xECnh WebGPU!");
          if (webgpuProgressContainer) webgpuProgressContainer.style.display = "none";
        } catch (err) {
          console.error("WebGPU Init Error:", err);
          addMessage("system", "L\u1ED7i kh\u1EDFi t\u1EA1o WebGPU: " + err.message);
          if (webgpuProgressContainer) webgpuProgressContainer.style.display = "none";
          llmSelect.value = "ollama";
          await window.companion.invoke("ai:update-config", { key: "llm.provider", value: "ollama" });
        } finally {
          setBusy(false);
          llmSelect.disabled = false;
        }
      }
    } else {
      const res = await window.companion.invoke("ai:update-config", { key: "llm.provider", value: provider });
      if (res && !res.error) {
        addMessage("system", `\u0110\xE3 chuy\u1EC3n sang b\u1ED9 n\xE3o: ${llmSelect.options[llmSelect.selectedIndex].text}`);
      }
    }
  });
}
if (sttSelect) {
  sttSelect.addEventListener("change", async () => {
    const model = sttSelect.value;
    const res = await window.companion.invoke("ai:update-config", { key: "stt.model", value: model });
    if (res && !res.error) {
      addMessage("system", `\u0110ang t\u1EA3i l\u1EA1i STT sang m\xF4 h\xECnh: ${sttSelect.options[sttSelect.selectedIndex].text}`);
    }
  });
}
loadConfig();
