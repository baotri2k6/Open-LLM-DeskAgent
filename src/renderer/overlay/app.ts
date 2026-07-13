import { AvatarController } from "../../live2d/live2d-manager.js";
import { AssetRegistry } from "../../live2d/asset-registry.js";
import { ChatHistory } from "../chat/history.js";
import {
  renderMessage,
  renderChunk,
  renderApprovalCard,
} from "../chat/message.js";
import { AudioPlayer } from "../voice/audio-player.js";
import { VoiceRecorder } from "../voice/recoder.js";



const log = document.getElementById("chatLog") as HTMLDivElement;
const form = document.getElementById("chatForm") as HTMLFormElement;
const input = document.getElementById("chatInput") as HTMLInputElement;
const voiceButton = document.getElementById("voiceButton") as HTMLButtonElement | null;
const statusPill = document.getElementById("serviceStatus") as HTMLSpanElement;
const llmSelect = document.getElementById("llmSelect") as HTMLSelectElement;
const sttSelect = document.getElementById("sttSelect") as HTMLSelectElement;

const attachButton = document.getElementById(
  "attachButton",
) as HTMLButtonElement;
const fileInput = document.getElementById("fileInput") as HTMLInputElement;
const imagePreviewArea = document.getElementById(
  "imagePreviewArea",
) as HTMLDivElement;
const imagePreviewThumbnail = document.getElementById(
  "imagePreviewThumbnail",
) as HTMLImageElement;
const clearImageButton = document.getElementById(
  "clearImageButton",
) as HTMLButtonElement;

const webgpuProgressContainer = document.getElementById(
  "webgpuProgressContainer",
) as HTMLDivElement;
const webgpuProgressText = document.getElementById(
  "webgpuProgressText",
) as HTMLDivElement;
const webgpuProgressPercent = document.getElementById(
  "webgpuProgressPercent",
) as HTMLSpanElement;
const webgpuProgressBar = document.getElementById(
  "webgpuProgressBar",
) as HTMLDivElement;

let attachedImageBase64: string | null = null;
interface IAvatarController {
  readyPromise: Promise<void>;
  changeModel(modelIdOrPath: string): Promise<void>;
  setState(state: { expression?: string; emotion?: string; motion?: string; lipsync?: boolean }): void;
  startLipSync(amp: number): void;
  stopLipSync(): void;
  containsPoint(x: number, y: number): boolean;
}

const avatar = new AvatarController({
  wrap: document.getElementById("avatarWrap")!,
  light: document.getElementById("expressionLight")!,
  img: document.getElementById("avatarImage") as HTMLImageElement,
}) as unknown as IAvatarController;

const history = new ChatHistory();
const audioPlayer = new AudioPlayer();
const recorder = new VoiceRecorder();
let streamEl: HTMLElement | null = null;
let isRecording = false;

let ttsQueue: Array<{ url: string; durationMs: number }> = [];
let ttsPlaying = false;
let chatDone = false;

function setServiceStatus(ok: boolean): void {
  if (statusPill) {
    statusPill.dataset.status = ok ? "ok" : "offline";
    statusPill.textContent = ok ? "Online" : "Offline";
  }
}

async function checkStatus(): Promise<void> {
  try {
    const res = await (window as any).companion.health();
    setServiceStatus(res.status === "ok");
  } catch {
    setServiceStatus(false);
  }
}

function addMessage(role: string, text: string): void {
  const msg = history.add(role, text);
  if (log) {
    log.appendChild(renderMessage(msg));
    log.scrollTop = log.scrollHeight;
  }
}

function setBusy(active: boolean): void {
  if (input) input.disabled = active;
  if (form) {
    const submitBtn = form.querySelector(
      'button[type="submit"]',
    ) as HTMLButtonElement;
    if (submitBtn) submitBtn.disabled = active;
  }
  avatar.setState({
    expression: active ? "thinking" : "smile",
    motion: active ? "thinking" : "idle",
  });
}

checkStatus();
setInterval(checkStatus, 5000);

(window as any).companion.on("python:ready", () => setServiceStatus(true));

(window as any).companion.on("set:emotion", (emotion: string) => {
  avatar.setState({ expression: emotion, emotion, motion: emotion });
});

(window as any).companion.on("set:lipsync", (active: boolean) => {
  if (!active && (ttsPlaying || ttsQueue.length > 0)) {
    return;
  }
  avatar.setState({ lipsync: Boolean(active) });
});

(window as any).companion.on("chat:chunk", (chunk: string) => {
  if (!streamEl) {
    streamEl = renderChunk();
    if (log) log.appendChild(streamEl);
  }
  const body = streamEl.querySelector(".msg-body");
  if (body) body.textContent += chunk;
  if (log) log.scrollTop = log.scrollHeight;
});

async function processTtsQueue(): Promise<void> {
  if (ttsPlaying) return;
  if (ttsQueue.length === 0) {
    if (chatDone) {
      avatar.stopLipSync();
      (window as any).companion.setLipsync(false);
      setBusy(false);
      if (input) input.focus();
    }
    return;
  }

  ttsPlaying = true;
  const item = ttsQueue.shift();
  if (item) {
    const { url } = item;
    (window as any).companion.setLipsync(true);
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

(window as any).companion.on("chat:done", (reply: string) => {
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
    (window as any).companion.setLipsync(false);
    setBusy(false);
    if (input) input.focus();
  }
});

(window as any).companion.on("tts:audio", async (data: any = {}) => {
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

    const displayMsg = imageToSend
      ? `${text ? text + " " : ""}![image](${imageToSend})`
      : text;
    addMessage("user", displayMsg);
    setBusy(true);

    // Barge-in: Clear queue, stop active speech playback, and cancel backend LLM stream
    ttsQueue = [];
    ttsPlaying = false;
    chatDone = false;
    audioPlayer.stop();
    avatar.stopLipSync();
    (window as any).companion.invoke("ai:cancel-chat").catch((err: any) => {
      console.warn("Failed to cancel active generation:", err);
    });

    const context = {
      locale: "vi-VN"
    };

    const res = await (window as any).companion.chat(
      text,
      imageToSend,
      context,
    );
    if (!res?.ok) {
      addMessage(
        "assistant",
        "Backend đang offline. Bạn khởi động lại Python service giúp mình nhé.",
      );
      setBusy(false);
      setServiceStatus(false);
    }
  });
}

attachButton?.addEventListener("click", () => {
  fileInput?.click();
});

fileInput?.addEventListener("change", (event: any) => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = (e) => {
    attachedImageBase64 = e.target?.result as string;
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
    // Barge-in: Stop active speech and cancel current generation on mic activation
    ttsQueue = [];
    ttsPlaying = false;
    chatDone = true;
    audioPlayer.stop();
    avatar.stopLipSync();
    (window as any).companion.invoke("ai:cancel-chat").catch((err: any) => {
      console.warn("Failed to cancel active generation:", err);
    });

    isRecording = true;
    if (voiceButton) {
      voiceButton.classList.add("active");
      voiceButton.textContent = "Stop";
    }
    avatar.setState({ expression: "focused", motion: "look_side" });
    await recorder.start(() => {
      // Silence trigger callback
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
    await (window as any).companion.invoke("ai:voice-input", {
      audio_b64: b64,
    });
}

if (voiceButton) {
  voiceButton.addEventListener("click", triggerVoiceRecording);
}

(window as any).companion.on("stt:result", (text: string) => {
  if (input) input.value = text;
  setBusy(false);
});

(window as any).companion.on("voice:listen", (action: string) => {
  if (action === "start") {
    if (!isRecording) {
      triggerVoiceRecording();
    }
  }
});

(window as any).companion.on(
  "chat:request-approval",
  ({ req_id, action, details }: any) => {
    avatar.setState({ expression: "focused", motion: "thinking" });
    const approvalEl = renderApprovalCard(req_id, action, details);
    if (log) {
      log.appendChild(approvalEl);
      log.scrollTop = log.scrollHeight;
    }
  },
);

(window as any).companion.on("tts:done", () => avatar.stopLipSync());

(window as any).companion.on("trigger:screenshot", async () => {
  addMessage("user", "[Nhin man hinh]");
  setBusy(true);

  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;

  await (window as any).companion.invoke("ai:screenshot", {
    question: "Man hinh dang hien thi gi?",
  });
});

setTimeout(() => {
  addMessage(
    "assistant",
    "Chao ban! Minh la IceGirl. Ban can minh giup gi khong?",
  );
  avatar.setState({ expression: "smile", motion: "idle" });
}, 300);



function updateAvatarBackground(path: string) {
  const stage = document.querySelector(".avatar-stage") as HTMLElement;
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

function updateAvatarOffset(x: string | number, y: string | number) {
  const wrap = document.getElementById("avatarWrap");
  if (wrap) {
    wrap.style.transform = `translate(${x || 0}px, ${y || 0}px)`;
  }
}

async function loadConfig(): Promise<void> {
  try {
    const res = await (window as any).companion.invoke("ai:get-config", {});
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

      // Load avatar position offsets
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
          webgpuProgressText.textContent = "Đang khởi tạo WebGPU...";
        if (webgpuProgressPercent) webgpuProgressPercent.textContent = "0%";
        if (webgpuProgressBar) webgpuProgressBar.style.width = "0%";

        setBusy(true);
        llmSelect.disabled = true;

        try {
          addMessage(
            "system",
            "Đang tải mô hình WebGPU Qwen2.5-1.5B (Lần đầu có thể mất vài phút)...",
          );
          await WebGPUEngine.init((text: string, progress: number) => {
            if (webgpuProgressText) webgpuProgressText.textContent = text;
            const percent = Math.round(progress * 100);
            if (webgpuProgressPercent)
              webgpuProgressPercent.textContent = `${percent}%`;
            if (webgpuProgressBar)
              webgpuProgressBar.style.width = `${percent}%`;
          });

          addMessage("system", "Khởi tạo và tải thành công mô hình WebGPU!");
          if (webgpuProgressContainer)
            webgpuProgressContainer.style.display = "none";
        } catch (err: any) {
          console.error("WebGPU Init Error:", err);
          addMessage("system", "Lỗi khởi tạo WebGPU: " + err.message);
          if (webgpuProgressContainer)
            webgpuProgressContainer.style.display = "none";
          llmSelect.value = "ollama";
          await (window as any).companion.invoke("ai:update-config", {
            key: "llm.provider",
            value: "ollama",
          });
        } finally {
          setBusy(false);
          llmSelect.disabled = false;
        }
      }
    } else {
      const res = await (window as any).companion.invoke("ai:update-config", {
        key: "llm.provider",
        value: provider,
      });
      if (res && !res.error) {
        addMessage(
          "system",
          `Đã chuyển sang bộ não: ${llmSelect.options[llmSelect.selectedIndex].text}`,
        );
      }
    }
  });
}

if (sttSelect) {
  sttSelect.addEventListener("change", async () => {
    const model = sttSelect.value;
    const res = await (window as any).companion.invoke("ai:update-config", {
      key: "stt.model",
      value: model,
    });
    if (res && !res.error) {
      addMessage(
        "system",
        `Đang tải lại STT sang mô hình: ${sttSelect.options[sttSelect.selectedIndex].text}`,
      );
    }
  });
}

loadConfig();

// ─── Floating Widgets UI Logic ──────────────────────────────────
// Hide loading box and fade in avatar after it is fully loaded
if (avatar.readyPromise) {
  avatar.readyPromise.then(() => {
    const loadingBox = document.getElementById("loadingBox");
    if (loadingBox) loadingBox.classList.add("hidden");
    const avatarWrap = document.getElementById("avatarWrap");
    if (avatarWrap) avatarWrap.style.opacity = "1";
    console.log("[Overlay App] Saved avatar loaded successfully!");
  }).catch((err: any) => {
    console.error("[Overlay App] Failed to load saved avatar:", err);
    const loadingBox = document.getElementById("loadingBox");
    if (loadingBox) loadingBox.classList.add("hidden");
    const avatarWrap = document.getElementById("avatarWrap");
    if (avatarWrap) avatarWrap.style.opacity = "1";
  });
} else {
  setTimeout(() => {
    const loadingBox = document.getElementById("loadingBox");
    if (loadingBox) loadingBox.classList.add("hidden");
    const avatarWrap = document.getElementById("avatarWrap");
    if (avatarWrap) avatarWrap.style.opacity = "1";
  }, 1800);
}

// Toggle Control Panel (Chevron button)
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

// Toggle Mic (Mute/Unmute)
const btnToggleMic = document.getElementById("btnToggleMic");
const svgMicNormal = document.getElementById("svgMicNormal");
const svgMicMuted = document.getElementById("svgMicMuted");
if (btnToggleMic && svgMicNormal && svgMicMuted) {
  let isMuted = true; // default starting state
  btnToggleMic.addEventListener("click", () => {
    isMuted = !isMuted;
    btnToggleMic.classList.toggle("active", !isMuted);
    btnToggleMic.classList.toggle("muted", isMuted);
    svgMicNormal.style.display = isMuted ? "none" : "block";
    svgMicMuted.style.display = isMuted ? "block" : "none";
    (window as any).companion.invoke("voice:toggle-mute", { muted: isMuted }).catch(() => null);
  });
}

// Toggle Chat Panel visibility (Chat button in Grid)
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

// Reload character model (Reload button in Grid)
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

// Quick Settings (Open settings window)
const btnQuickSettings = document.getElementById("btnQuickSettings");
if (btnQuickSettings) {
  btnQuickSettings.addEventListener("click", () => {
    (window as any).companion.invoke("win:open-settings").catch(() => null);
  });
}

// Pin Window Toggle (Pin button in Footer)
const btnPinWindow = document.getElementById("btnPinWindow");
if (btnPinWindow) {
  let isPinned = true;
  btnPinWindow.addEventListener("click", async () => {
    isPinned = !isPinned;
    btnPinWindow.classList.toggle("active", isPinned);
    await (window as any).companion.invoke("win:set-always-on-top", { alwaysOnTop: isPinned }).catch(() => null);
  });
}

// Hide Avatar (Hide button in Footer)
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

// Quit Application (Quit button in Footer)
const btnQuitApp = document.getElementById("btnQuitApp");
if (btnQuitApp) {
  btnQuitApp.addEventListener("click", () => {
    if (confirm("Do you want to close DeskAgent?")) {
      (window as any).companion.invoke("win:quit").catch(() => {
        window.close();
      });
    }
  });
}

// Listen to configuration updates from the main process
(window as any).companion.on("config:updated", ({ key, value }: { key: string; value: any }) => {
  if (key === "app.avatarX" || key === "app.avatarY") {
    (window as any).companion.invoke("ai:get-config", {}).then((res: any) => {
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

// Speech bubble helpers
const speechBubble = document.getElementById("thoughtBubble"); // Use thoughtBubble as display caption bubble
const speechContent = document.getElementById("thoughtContent");
function setBubbleCaption(msg: string, expression: string = "normal") {
  if (speechBubble && speechContent) {
    if (msg) {
      speechContent.textContent = msg;
      speechBubble.classList.remove("hidden");
    } else {
      speechBubble.classList.add("hidden");
    }
  }
  avatar.setState({ expression: expression, emotion: expression, motion: "idle" });
}

let isAppDragging = false;
let isAppBusy = false;

document.addEventListener("dragover", (e) => {
  e.preventDefault();
  e.stopPropagation();
  if (isAppDragging || isAppBusy || isRecording) return;
  isAppDragging = true;
  avatar.setState({ expression: "surprised", emotion: "surprised", motion: "nod" });
  setBubbleCaption("Ủa, cậu đang định đưa file gì cho tớ thế? [excited]");
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
    const filePath = (file as any).path;

    if (fileName.toLowerCase().endsWith(".zip")) {
      try {
        isAppBusy = true;
        setBusy(true);
        avatar.setState({ expression: "thinking", emotion: "thinking", motion: "thinking" });
        setBubbleCaption("Đang phân tích cấu trúc tệp ZIP...");

        const scanRes = await (window as any).companion.invoke("avatar:scan-zip", { path: filePath });
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
      } catch (err: any) {
        console.error("Failed to scan Live2D model ZIP:", err);
        setBubbleCaption(`Không nạp được: ${err.message}`);
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
          setBubbleCaption(`Đang đọc tài liệu "${fileName}" để nạp kiến thức, cậu chờ tớ một xíu nhé...`);

          const res = await (window as any).companion.invoke("system:import-document", { path: filePath });

          if (res && res.success) {
            setBubbleCaption(`Tớ đã học xong tài liệu "${fileName}" rồi nè! Bây giờ cậu có thể hỏi tớ bất cứ điều gì về nó rồi nhé! [happy]`);
            avatar.setState({ expression: "happy", emotion: "happy", motion: "excited" });

            setTimeout(() => {
              if (!isAppBusy && !isRecording) {
                setBubbleCaption("");
                avatar.setState({ expression: "smile", emotion: "smile", motion: "idle" });
              }
            }, 5000);
          } else {
            throw new Error(res?.error || "Unknown import error");
          }
        } catch (err: any) {
          console.error("Failed to import document:", err);
          setBubbleCaption(`Không nạp được tài liệu: ${err.message}. Cậu kiểm tra lại định dạng file nhé.`);
          avatar.setState({ expression: "sad", emotion: "sad", motion: "shake" });
        } finally {
          isAppBusy = false;
          setBusy(false);
        }
      } else {
        setBubbleCaption(`Oa! Cảm ơn cậu đã gửi file "${fileName}" cho tớ nha! [happy]`);
      }
    }
  } else {
    avatar.setState({ expression: "normal", emotion: "normal", motion: "idle" });
    setBubbleCaption("");
  }
});

(window as any).companion.on("avatar:registry-updated", async (newModel: any) => {
  try {
    await AssetRegistry.load(true);
    setBubbleCaption(`✨ Đã thêm nhân vật: ${newModel?.name || "mới"}`);
    setTimeout(() => setBubbleCaption(""), 3000);
  } catch (e) {
    console.warn("registry-updated reload failed:", e);
  }
});

async function executeOverlayImport(filePath: string, selectedConfig?: string) {
  try {
    isAppBusy = true;
    setBusy(true);
    avatar.setState({ expression: "thinking", emotion: "thinking", motion: "thinking" });
    setBubbleCaption("Đang giải nén và nạp nhân vật mới...");

    const res = await (window as any).companion.invoke("avatar:import-zip", { path: filePath, selectedConfig });

    if (res && res.success) {
      await AssetRegistry.load(true);
      const modelPath = res.model.path;
      await avatar.changeModel(modelPath);

      await (window as any).companion.invoke("ai:update-config", {
        key: "app.avatarModel",
        value: modelPath
      }).catch(() => null);

      setBubbleCaption(`Oa! Đã nạp thành công nhân vật mới "${res.model.name}" rồi nè! [happy]`);
      avatar.setState({ expression: "happy", emotion: "happy", motion: "excited" });

      // Notify other windows (like settings window) to refresh
      (window as any).companion.invoke("ai:broadcast", {
        event: "avatar:registry-updated",
        data: res.model
      }).catch(() => null);

      setTimeout(() => {
        if (!isAppBusy && !isRecording) {
          setBubbleCaption("");
          avatar.setState({ expression: "smile", emotion: "smile", motion: "idle" });
        }
      }, 4000);
    } else {
      throw new Error(res?.error || "Unknown import error");
    }
  } catch (err: any) {
    console.error("Failed to import Live2D model ZIP:", err);
    setBubbleCaption(`Không nạp được: ${err.message}`);
    avatar.setState({ expression: "sad", emotion: "sad", motion: "shake" });
  } finally {
    isAppBusy = false;
    setBusy(false);
  }
}

function showOverlayZipConfigModal(filePath: string, files: string[]) {
  const modal = document.getElementById("zipConfigModal");
  const list = document.getElementById("zipConfigList");
  if (!modal || !list) return;

  list.innerHTML = "";
  files.forEach(file => {
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

    // Show filename only or relative path
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

// Close Zip Config Modal listener in overlay
document.getElementById("zipConfigBtnClose")?.addEventListener("click", () => {
  const modal = document.getElementById("zipConfigModal");
  if (modal) modal.style.display = "none";
  isAppBusy = false;
  setBusy(false);
  setBubbleCaption("");
});

// ─── Click-through Optimization (Chạm xuyên qua khoảng trống) ───
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

function updateMouseInteractivity(clientX: number, clientY: number) {
  if (pointerDrag) {
    if ((window as any).companion && typeof (window as any).companion.setIgnoreMouseEvents === "function") {
      (window as any).companion.setIgnoreMouseEvents(false);
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
    if (el && (el as HTMLElement).style.display !== "none" && !el.classList.contains("hidden")) {
      const rect = el.getBoundingClientRect();
      if (
        clientX >= rect.left &&
        clientX <= rect.right &&
        clientY >= rect.top &&
        clientY <= rect.bottom
      ) {
        isOverInteractiveElement = true;
        break;
      }
    }
  }

  const isOverAvatar = avatar.containsPoint(clientX, clientY);
  const totalInteractive = isOverInteractiveElement || isOverAvatar;

  if ((window as any).companion && typeof (window as any).companion.setIgnoreMouseEvents === "function") {
    if (totalInteractive) {
      (window as any).companion.setIgnoreMouseEvents(false);
    } else {
      (window as any).companion.setIgnoreMouseEvents(true, { forward: true });
    }
  }
}

window.addEventListener("mousemove", (e) => {
  updateMouseInteractivity(e.clientX, e.clientY);
});

(window as any).companion?.on?.("window:cursor-move", (point: { x: number; y: number }) => {
  updateMouseInteractivity(point.x, point.y);
});


