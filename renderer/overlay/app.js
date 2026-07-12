import { AvatarController } from "../../live2d/live2d-manager.js";
import { AssetRegistry } from "../../live2d/asset-registry.js";
import { ChatHistory } from "../chat/history.js";
import {
  renderMessage,
  renderChunk,
  renderApprovalCard
} from "../chat/message.js";
import { AudioPlayer } from "../voice/audio-player.js";
import { VoiceRecorder } from "../voice/recoder.js";
const log = document.getElementById("chatLog");
const form = document.getElementById("chatForm");
const input = document.getElementById("chatInput");
const voiceButton = document.getElementById("voiceButton");
const statusPill = document.getElementById("serviceStatus");
const llmSelect = document.getElementById("llmSelect");
const sttSelect = document.getElementById("sttSelect");
const attachButton = document.getElementById(
  "attachButton"
);
const fileInput = document.getElementById("fileInput");
const imagePreviewArea = document.getElementById(
  "imagePreviewArea"
);
const imagePreviewThumbnail = document.getElementById(
  "imagePreviewThumbnail"
);
const clearImageButton = document.getElementById(
  "clearImageButton"
);
const webgpuProgressContainer = document.getElementById(
  "webgpuProgressContainer"
);
const webgpuProgressText = document.getElementById(
  "webgpuProgressText"
);
const webgpuProgressPercent = document.getElementById(
  "webgpuProgressPercent"
);
const webgpuProgressBar = document.getElementById(
  "webgpuProgressBar"
);
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
    const submitBtn = form.querySelector(
      'button[type="submit"]'
    );
    if (submitBtn) submitBtn.disabled = active;
  }
  avatar.setState({
    expression: active ? "thinking" : "smile",
    motion: active ? "thinking" : "idle"
  });
}
checkStatus();
setInterval(checkStatus, 5e3);
window.companion.on("python:ready", () => setServiceStatus(true));
window.companion.on("set:emotion", (emotion) => {
  avatar.setState({ expression: emotion, emotion, motion: emotion });
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
    const context = {
      locale: "vi-VN"
    };
    const res = await window.companion.chat(
      text,
      imageToSend,
      context
    );
    if (!res?.ok) {
      addMessage(
        "assistant",
        "Backend \u0111ang offline. B\u1EA1n kh\u1EDFi \u0111\u1ED9ng l\u1EA1i Python service gi\xFAp m\xECnh nh\xE9."
      );
      setBusy(false);
      setServiceStatus(false);
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
async function triggerVoiceRecording() {
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
    if (voiceButton) {
      voiceButton.classList.add("active");
      voiceButton.textContent = "Stop";
    }
    avatar.setState({ expression: "focused", motion: "look_side" });
    await recorder.start(() => {
      triggerVoiceRecording();
    });
    return;
  }
  isRecording = false;
  if (voiceButton) {
    voiceButton.classList.remove("active");
    voiceButton.textContent = "Mic";
  }
  setBusy(true);
  const b64 = await recorder.stop();
  if (b64)
    await window.companion.invoke("ai:voice-input", {
      audio_b64: b64
    });
}
if (voiceButton) {
  voiceButton.addEventListener("click", triggerVoiceRecording);
}
window.companion.on("stt:result", (text) => {
  if (input) input.value = text;
  setBusy(false);
});
window.companion.on("voice:listen", (action) => {
  if (action === "start") {
    if (!isRecording) {
      triggerVoiceRecording();
    }
  }
});
window.companion.on(
  "chat:request-approval",
  ({ req_id, action, details }) => {
    avatar.setState({ expression: "focused", motion: "thinking" });
    const approvalEl = renderApprovalCard(req_id, action, details);
    if (log) {
      log.appendChild(approvalEl);
      log.scrollTop = log.scrollHeight;
    }
  }
);
window.companion.on("tts:done", () => avatar.stopLipSync());
window.companion.on("trigger:screenshot", async () => {
  addMessage("user", "[Nhin man hinh]");
  setBusy(true);
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;
  await window.companion.invoke("ai:screenshot", {
    question: "Man hinh dang hien thi gi?"
  });
});
setTimeout(() => {
  addMessage(
    "assistant",
    "Chao ban! Minh la IceGirl. Ban can minh giup gi khong?"
  );
  avatar.setState({ expression: "smile", motion: "idle" });
}, 300);
function updateAvatarBackground(path) {
  const stage = document.querySelector(".avatar-stage");
  if (stage) {
    if (path) {
      let normalizedPath = path.replace(/\\/g, "/");
      let url = "";
      if (normalizedPath.startsWith("http") || normalizedPath.startsWith("file://")) {
        url = normalizedPath;
      } else {
        url = `../../${normalizedPath}`;
      }
      stage.style.backgroundImage = `url('${url}')`;
      stage.style.backgroundSize = "cover";
      stage.style.backgroundPosition = "center";
      stage.style.backgroundRepeat = "no-repeat";
    } else {
      stage.style.backgroundImage = "";
    }
  }
}
function updateAvatarOffset(x, y) {
  const wrap = document.getElementById("avatarWrap");
  if (wrap) {
    wrap.style.transform = `translate(${x || 0}px, ${y || 0}px)`;
  }
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
      if (res.background_image) {
        updateAvatarBackground(res.background_image);
      }
      const posX = res.app?.avatarX || res.avatarX || 0;
      const posY = res.app?.avatarY || res.avatarY || 0;
      updateAvatarOffset(posX, posY);
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
        if (webgpuProgressContainer)
          webgpuProgressContainer.style.display = "flex";
        if (webgpuProgressText)
          webgpuProgressText.textContent = "\u0110ang kh\u1EDFi t\u1EA1o WebGPU...";
        if (webgpuProgressPercent) webgpuProgressPercent.textContent = "0%";
        if (webgpuProgressBar) webgpuProgressBar.style.width = "0%";
        setBusy(true);
        llmSelect.disabled = true;
        try {
          addMessage(
            "system",
            "\u0110ang t\u1EA3i m\xF4 h\xECnh WebGPU Qwen2.5-1.5B (L\u1EA7n \u0111\u1EA7u c\xF3 th\u1EC3 m\u1EA5t v\xE0i ph\xFAt)..."
          );
          await WebGPUEngine.init((text, progress) => {
            if (webgpuProgressText) webgpuProgressText.textContent = text;
            const percent = Math.round(progress * 100);
            if (webgpuProgressPercent)
              webgpuProgressPercent.textContent = `${percent}%`;
            if (webgpuProgressBar)
              webgpuProgressBar.style.width = `${percent}%`;
          });
          addMessage("system", "Kh\u1EDFi t\u1EA1o v\xE0 t\u1EA3i th\xE0nh c\xF4ng m\xF4 h\xECnh WebGPU!");
          if (webgpuProgressContainer)
            webgpuProgressContainer.style.display = "none";
        } catch (err) {
          console.error("WebGPU Init Error:", err);
          addMessage("system", "L\u1ED7i kh\u1EDFi t\u1EA1o WebGPU: " + err.message);
          if (webgpuProgressContainer)
            webgpuProgressContainer.style.display = "none";
          llmSelect.value = "ollama";
          await window.companion.invoke("ai:update-config", {
            key: "llm.provider",
            value: "ollama"
          });
        } finally {
          setBusy(false);
          llmSelect.disabled = false;
        }
      }
    } else {
      const res = await window.companion.invoke("ai:update-config", {
        key: "llm.provider",
        value: provider
      });
      if (res && !res.error) {
        addMessage(
          "system",
          `\u0110\xE3 chuy\u1EC3n sang b\u1ED9 n\xE3o: ${llmSelect.options[llmSelect.selectedIndex].text}`
        );
      }
    }
  });
}
if (sttSelect) {
  sttSelect.addEventListener("change", async () => {
    const model = sttSelect.value;
    const res = await window.companion.invoke("ai:update-config", {
      key: "stt.model",
      value: model
    });
    if (res && !res.error) {
      addMessage(
        "system",
        `\u0110ang t\u1EA3i l\u1EA1i STT sang m\xF4 h\xECnh: ${sttSelect.options[sttSelect.selectedIndex].text}`
      );
    }
  });
}
loadConfig();
if (avatar.readyPromise) {
  avatar.readyPromise.then(() => {
    const loadingBox = document.getElementById("loadingBox");
    if (loadingBox) loadingBox.classList.add("hidden");
    const avatarWrap2 = document.getElementById("avatarWrap");
    if (avatarWrap2) avatarWrap2.style.opacity = "1";
    console.log("[Overlay App] Saved avatar loaded successfully!");
  }).catch((err) => {
    console.error("[Overlay App] Failed to load saved avatar:", err);
    const loadingBox = document.getElementById("loadingBox");
    if (loadingBox) loadingBox.classList.add("hidden");
    const avatarWrap2 = document.getElementById("avatarWrap");
    if (avatarWrap2) avatarWrap2.style.opacity = "1";
  });
} else {
  setTimeout(() => {
    const loadingBox = document.getElementById("loadingBox");
    if (loadingBox) loadingBox.classList.add("hidden");
    const avatarWrap2 = document.getElementById("avatarWrap");
    if (avatarWrap2) avatarWrap2.style.opacity = "1";
  }, 1800);
}
const btnToggleMenu = document.getElementById("btnToggleMenu");
const controlPanel = document.getElementById("controlPanel");
if (btnToggleMenu && controlPanel) {
  btnToggleMenu.addEventListener("click", () => {
    const isActive = controlPanel.classList.toggle("active");
    if (isActive) {
      btnToggleMenu.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"/></svg>`;
    } else {
      btnToggleMenu.innerHTML = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="18 15 12 9 6 15"/></svg>`;
    }
  });
}
const btnToggleMic = document.getElementById("btnToggleMic");
const svgMicNormal = document.getElementById("svgMicNormal");
const svgMicMuted = document.getElementById("svgMicMuted");
if (btnToggleMic && svgMicNormal && svgMicMuted) {
  let isMuted = true;
  btnToggleMic.addEventListener("click", () => {
    isMuted = !isMuted;
    btnToggleMic.classList.toggle("active", !isMuted);
    btnToggleMic.classList.toggle("muted", isMuted);
    svgMicNormal.style.display = isMuted ? "none" : "block";
    svgMicMuted.style.display = isMuted ? "block" : "none";
    window.companion.invoke("voice:toggle-mute", { muted: isMuted }).catch(() => null);
  });
}
const btnToggleChat = document.getElementById("btnToggleChat");
const chatPanel = document.getElementById("chatPanel");
const btnCloseChat = document.getElementById("btnCloseChat");
if (btnToggleChat && chatPanel) {
  btnToggleChat.addEventListener("click", () => {
    const isHidden = chatPanel.style.display === "none" || chatPanel.style.display === "";
    chatPanel.style.display = isHidden ? "flex" : "none";
    btnToggleChat.classList.toggle("active", isHidden);
  });
}
if (btnCloseChat && chatPanel) {
  btnCloseChat.addEventListener("click", () => {
    chatPanel.style.display = "none";
    if (btnToggleChat) btnToggleChat.classList.remove("active");
  });
}
const btnReloadAvatar = document.getElementById("btnReloadAvatar");
if (btnReloadAvatar) {
  btnReloadAvatar.addEventListener("click", () => {
    btnReloadAvatar.classList.add("active");
    const loadingBox = document.getElementById("loadingBox");
    if (loadingBox) loadingBox.classList.remove("hidden");
    setTimeout(() => {
      window.location.reload();
    }, 600);
  });
}
const btnQuickSettings = document.getElementById("btnQuickSettings");
if (btnQuickSettings) {
  btnQuickSettings.addEventListener("click", () => {
    window.companion.invoke("win:open-settings").catch(() => null);
  });
}
const btnPinWindow = document.getElementById("btnPinWindow");
if (btnPinWindow) {
  let isPinned = true;
  btnPinWindow.addEventListener("click", async () => {
    isPinned = !isPinned;
    btnPinWindow.classList.toggle("active", isPinned);
    await window.companion.invoke("win:set-always-on-top", { alwaysOnTop: isPinned }).catch(() => null);
  });
}
const btnHideAvatar = document.getElementById("btnHideAvatar");
const avatarWrap = document.getElementById("avatarWrap");
if (btnHideAvatar && avatarWrap) {
  let isHidden = false;
  btnHideAvatar.addEventListener("click", () => {
    isHidden = !isHidden;
    avatarWrap.style.opacity = isHidden ? "0" : "1";
    avatarWrap.style.pointerEvents = isHidden ? "none" : "auto";
    btnHideAvatar.classList.toggle("active", isHidden);
  });
}
const btnQuitApp = document.getElementById("btnQuitApp");
if (btnQuitApp) {
  btnQuitApp.addEventListener("click", () => {
    if (confirm("Do you want to close DeskAgent?")) {
      window.companion.invoke("win:quit").catch(() => {
        window.close();
      });
    }
  });
}
window.companion.on("config:updated", ({ key, value }) => {
  if (key === "app.avatarX" || key === "app.avatarY") {
    window.companion.invoke("ai:get-config", {}).then((res) => {
      const posX = res.app?.avatarX || res.avatarX || 0;
      const posY = res.app?.avatarY || res.avatarY || 0;
      updateAvatarOffset(posX, posY);
    });
  } else if (key === "app.backgroundImage") {
    updateAvatarBackground(value || "");
  } else if (key === "app.avatarModel") {
    avatar.changeModel(value);
  }
});
const speechBubble = document.getElementById("thoughtBubble");
const speechContent = document.getElementById("thoughtContent");
function setBubbleCaption(msg, expression = "normal") {
  if (speechBubble && speechContent) {
    if (msg) {
      speechContent.textContent = msg;
      speechBubble.classList.remove("hidden");
    } else {
      speechBubble.classList.add("hidden");
    }
  }
  avatar.setState({ expression, emotion: expression, motion: "idle" });
}
let isAppDragging = false;
let isAppBusy = false;
document.addEventListener("dragover", (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (isAppDragging || isAppBusy || isRecording) return;
  isAppDragging = true;
  avatar.setState({ expression: "surprised", emotion: "surprised", motion: "nod" });
  setBubbleCaption("\u1EE6a, c\u1EADu \u0111ang \u0111\u1ECBnh \u0111\u01B0a file g\xEC cho t\u1EDB th\u1EBF? [excited]");
});
document.addEventListener("dragleave", (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (!e.relatedTarget) {
    isAppDragging = false;
    avatar.setState({ expression: "normal", emotion: "normal", motion: "idle" });
    setBubbleCaption("");
  }
});
document.addEventListener("drop", async (e) => {
  e.preventDefault();
  e.stopPropagation();
  isAppDragging = false;
  if (isAppBusy || isRecording) return;
  const files = e.dataTransfer?.files;
  if (files && files.length > 0) {
    const file = files[0];
    const fileName = file.name;
    const filePath = file.path;
    if (fileName.toLowerCase().endsWith(".zip")) {
      try {
        isAppBusy = true;
        setBusy(true);
        avatar.setState({ expression: "thinking", emotion: "thinking", motion: "thinking" });
        setBubbleCaption("\u0110ang ph\xE2n t\xEDch c\u1EA5u tr\xFAc t\u1EC7p ZIP...");
        const scanRes = await window.companion.invoke("avatar:scan-zip", { path: filePath });
        if (scanRes && scanRes.success && scanRes.files && scanRes.files.length > 0) {
          if (scanRes.files.length === 1) {
            await executeOverlayImport(filePath, scanRes.files[0]);
          } else {
            showOverlayZipConfigModal(filePath, scanRes.files);
          }
        } else if (scanRes && !scanRes.success) {
          throw new Error(scanRes.error || "Failed to scan ZIP archive.");
        } else {
          await executeOverlayImport(filePath);
        }
      } catch (err) {
        console.error("Failed to scan Live2D model ZIP:", err);
        setBubbleCaption(`Kh\xF4ng n\u1EA1p \u0111\u01B0\u1EE3c: ${err.message}`);
        avatar.setState({ expression: "sad", emotion: "sad", motion: "shake" });
        isAppBusy = false;
        setBusy(false);
      }
    } else {
      const ext = fileName.substring(fileName.lastIndexOf(".")).toLowerCase();
      const docExtensions = [".pdf", ".docx", ".doc", ".txt", ".md"];
      if (docExtensions.includes(ext)) {
        try {
          isAppBusy = true;
          setBusy(true);
          avatar.setState({ expression: "thinking", emotion: "thinking", motion: "thinking" });
          setBubbleCaption(`\u0110ang \u0111\u1ECDc t\xE0i li\u1EC7u "${fileName}" \u0111\u1EC3 n\u1EA1p ki\u1EBFn th\u1EE9c, c\u1EADu ch\u1EDD t\u1EDB m\u1ED9t x\xEDu nh\xE9...`);
          const res = await window.companion.invoke("system:import-document", { path: filePath });
          if (res && res.success) {
            setBubbleCaption(`T\u1EDB \u0111\xE3 h\u1ECDc xong t\xE0i li\u1EC7u "${fileName}" r\u1ED3i n\xE8! B\xE2y gi\u1EDD c\u1EADu c\xF3 th\u1EC3 h\u1ECFi t\u1EDB b\u1EA5t c\u1EE9 \u0111i\u1EC1u g\xEC v\u1EC1 n\xF3 r\u1ED3i nh\xE9! [happy]`);
            avatar.setState({ expression: "happy", emotion: "happy", motion: "excited" });
            setTimeout(() => {
              if (!isAppBusy && !isRecording) {
                setBubbleCaption("");
                avatar.setState({ expression: "smile", emotion: "smile", motion: "idle" });
              }
            }, 5e3);
          } else {
            throw new Error(res?.error || "Unknown import error");
          }
        } catch (err) {
          console.error("Failed to import document:", err);
          setBubbleCaption(`Kh\xF4ng n\u1EA1p \u0111\u01B0\u1EE3c t\xE0i li\u1EC7u: ${err.message}. C\u1EADu ki\u1EC3m tra l\u1EA1i \u0111\u1ECBnh d\u1EA1ng file nh\xE9.`);
          avatar.setState({ expression: "sad", emotion: "sad", motion: "shake" });
        } finally {
          isAppBusy = false;
          setBusy(false);
        }
      } else {
        setBubbleCaption(`Oa! C\u1EA3m \u01A1n c\u1EADu \u0111\xE3 g\u1EEDi file "${fileName}" cho t\u1EDB nha! [happy]`);
      }
    }
  } else {
    avatar.setState({ expression: "normal", emotion: "normal", motion: "idle" });
    setBubbleCaption("");
  }
});
window.companion.on("avatar:registry-updated", async (newModel) => {
  try {
    await AssetRegistry.load(true);
    setBubbleCaption(`\u2728 \u0110\xE3 th\xEAm nh\xE2n v\u1EADt: ${newModel?.name || "m\u1EDBi"}`);
    setTimeout(() => setBubbleCaption(""), 3e3);
  } catch (e) {
    console.warn("registry-updated reload failed:", e);
  }
});
async function executeOverlayImport(filePath, selectedConfig) {
  try {
    isAppBusy = true;
    setBusy(true);
    avatar.setState({ expression: "thinking", emotion: "thinking", motion: "thinking" });
    setBubbleCaption("\u0110ang gi\u1EA3i n\xE9n v\xE0 n\u1EA1p nh\xE2n v\u1EADt m\u1EDBi...");
    const res = await window.companion.invoke("avatar:import-zip", { path: filePath, selectedConfig });
    if (res && res.success) {
      await AssetRegistry.load(true);
      const modelPath = res.model.path;
      await avatar.changeModel(modelPath);
      await window.companion.invoke("ai:update-config", {
        key: "app.avatarModel",
        value: modelPath
      }).catch(() => null);
      setBubbleCaption(`Oa! \u0110\xE3 n\u1EA1p th\xE0nh c\xF4ng nh\xE2n v\u1EADt m\u1EDBi "${res.model.name}" r\u1ED3i n\xE8! [happy]`);
      avatar.setState({ expression: "happy", emotion: "happy", motion: "excited" });
      window.companion.invoke("ai:broadcast", {
        event: "avatar:registry-updated",
        data: res.model
      }).catch(() => null);
      setTimeout(() => {
        if (!isAppBusy && !isRecording) {
          setBubbleCaption("");
          avatar.setState({ expression: "smile", emotion: "smile", motion: "idle" });
        }
      }, 4e3);
    } else {
      throw new Error(res?.error || "Unknown import error");
    }
  } catch (err) {
    console.error("Failed to import Live2D model ZIP:", err);
    setBubbleCaption(`Kh\xF4ng n\u1EA1p \u0111\u01B0\u1EE3c: ${err.message}`);
    avatar.setState({ expression: "sad", emotion: "sad", motion: "shake" });
  } finally {
    isAppBusy = false;
    setBusy(false);
  }
}
function showOverlayZipConfigModal(filePath, files) {
  const modal = document.getElementById("zipConfigModal");
  const list = document.getElementById("zipConfigList");
  if (!modal || !list) return;
  list.innerHTML = "";
  files.forEach((file) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.style.width = "100%";
    btn.style.textAlign = "left";
    btn.style.padding = "8px 12px";
    btn.style.background = "rgba(255,255,255,0.06)";
    btn.style.color = "#fff";
    btn.style.border = "1px solid rgba(255,255,255,0.1)";
    btn.style.borderRadius = "6px";
    btn.style.cursor = "pointer";
    btn.style.fontSize = "11px";
    btn.style.transition = "background 0.2s";
    btn.textContent = file.split("/").pop() || file;
    btn.title = file;
    btn.addEventListener("mouseover", () => {
      btn.style.background = "rgba(255,255,255,0.12)";
    });
    btn.addEventListener("mouseout", () => {
      btn.style.background = "rgba(255,255,255,0.06)";
    });
    btn.addEventListener("click", async () => {
      modal.style.display = "none";
      await executeOverlayImport(filePath, file);
    });
    list.appendChild(btn);
  });
  modal.style.display = "flex";
}
document.getElementById("zipConfigBtnClose")?.addEventListener("click", () => {
  const modal = document.getElementById("zipConfigModal");
  if (modal) modal.style.display = "none";
  isAppBusy = false;
  setBusy(false);
  setBubbleCaption("");
});
let pointerDrag = false;
const btnDragHandle = document.getElementById("btnDragHandle");
if (btnDragHandle) {
  btnDragHandle.addEventListener("mousedown", () => {
    pointerDrag = true;
  });
  window.addEventListener("mouseup", () => {
    pointerDrag = false;
  });
}
function updateMouseInteractivity(clientX, clientY) {
  if (pointerDrag) {
    if (window.companion && typeof window.companion.setIgnoreMouseEvents === "function") {
      window.companion.setIgnoreMouseEvents(false);
    }
    return;
  }
  let isOverInteractiveElement = false;
  const elementsToCheck = [
    document.getElementById("floatingWifiBtn"),
    document.getElementById("controlPanel"),
    document.getElementById("chatPanel"),
    document.querySelector(".right-floating-stack"),
    document.getElementById("loadingBox")
  ];
  for (const el of elementsToCheck) {
    if (el && el.style.display !== "none" && !el.classList.contains("hidden")) {
      const rect = el.getBoundingClientRect();
      if (clientX >= rect.left && clientX <= rect.right && clientY >= rect.top && clientY <= rect.bottom) {
        isOverInteractiveElement = true;
        break;
      }
    }
  }
  const isOverAvatar = avatar.containsPoint(clientX, clientY);
  const totalInteractive = isOverInteractiveElement || isOverAvatar;
  if (window.companion && typeof window.companion.setIgnoreMouseEvents === "function") {
    if (totalInteractive) {
      window.companion.setIgnoreMouseEvents(false);
    } else {
      window.companion.setIgnoreMouseEvents(true, { forward: true });
    }
  }
}
window.addEventListener("mousemove", (e) => {
  updateMouseInteractivity(e.clientX, e.clientY);
});
window.companion?.on?.("window:cursor-move", (point) => {
  updateMouseInteractivity(point.x, point.y);
});
