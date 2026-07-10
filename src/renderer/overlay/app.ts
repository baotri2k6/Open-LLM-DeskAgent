import { AvatarController } from "../../live2d/live2d-manager.js";
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
const voiceButton = document.getElementById("voiceButton") as HTMLButtonElement;
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
const avatar = new AvatarController({
  wrap: document.getElementById("avatarWrap"),
  light: document.getElementById("expressionLight"),
  img: document.getElementById("avatarImage") as HTMLImageElement,
});

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

voiceButton.addEventListener("click", async () => {
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
    voiceButton.classList.add("active");
    voiceButton.textContent = "Stop";
    avatar.setState({ expression: "focused", motion: "look_side" });
    await recorder.start(() => {
      // Silence trigger callback
      voiceButton.click();
    });
    return;
  }

  isRecording = false;
  voiceButton.classList.remove("active");
  voiceButton.textContent = "Mic";
  setBusy(true);
  const b64 = await recorder.stop();
  if (b64)
    await (window as any).companion.invoke("ai:voice-input", {
      audio_b64: b64,
    });
});

(window as any).companion.on("stt:result", (text: string) => {
  if (input) input.value = text;
  setBusy(false);
});

(window as any).companion.on("voice:listen", (action: string) => {
  if (action === "start") {
    if (!isRecording) {
      voiceButton.click();
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
