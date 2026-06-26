import { AvatarController } from '../../live2d/live2d-manager.js';
import { ChatHistory } from '../chat/history.js';
import { renderMessage, renderChunk, renderApprovalCard } from '../chat/message.js';
import { AudioPlayer } from '../voice/audio-player.js';
import { VoiceRecorder } from '../voice/recoder.js';

// ─── Lazy-loaded modules (CDN-dependent, must not block UI rendering) ───
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

(async () => {
  try {
    const mod = await import('../shared/local-db.js');
    LocalDB = mod.LocalDB;
    console.log("[app] LocalDB module loaded");
  } catch (err) {
    console.warn("[app] LocalDB module failed to load (offline?):", err.message);
  }
  try {
    const mod = await import('../shared/webgpu-engine.js');
    WebGPUEngine = mod.WebGPUEngine;
    console.log("[app] WebGPUEngine module loaded");
  } catch (err) {
    console.warn("[app] WebGPUEngine module failed to load:", err.message);
  }
})();

const log = document.getElementById('chatLog');
const form = document.getElementById('chatForm');
const input = document.getElementById('chatInput');
const voiceButton = document.getElementById('voiceButton');
const statusPill = document.getElementById('serviceStatus');
const llmSelect = document.getElementById('llmSelect');
const sttSelect = document.getElementById('sttSelect');

const attachButton = document.getElementById('attachButton');
const fileInput = document.getElementById('fileInput');
const imagePreviewArea = document.getElementById('imagePreviewArea');
const imagePreviewThumbnail = document.getElementById('imagePreviewThumbnail');
const clearImageButton = document.getElementById('clearImageButton');

// WebGPU DOM elements
const webgpuProgressContainer = document.getElementById('webgpuProgressContainer');
const webgpuProgressText = document.getElementById('webgpuProgressText');
const webgpuProgressPercent = document.getElementById('webgpuProgressPercent');
const webgpuProgressBar = document.getElementById('webgpuProgressBar');

let attachedImageBase64 = null;
const avatar = new AvatarController({
  wrap: document.getElementById('avatarWrap'),
  light: document.getElementById('expressionLight'),
  img: document.getElementById('avatarImage'),
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
  statusPill.dataset.status = ok ? 'ok' : 'offline';
  statusPill.textContent = ok ? 'Online' : 'Offline';
}

async function checkStatus() {
  try {
    const res = await window.companion.health();
    setServiceStatus(res.status === 'ok');
  } catch {
    setServiceStatus(false);
  }
}

function addMessage(role, text) {
  const msg = history.add(role, text);
  log.appendChild(renderMessage(msg));
  log.scrollTop = log.scrollHeight;
}

function setBusy(active) {
  input.disabled = active;
  form.querySelector('button[type="submit"]').disabled = active;
  avatar.setState({ expression: active ? 'thinking' : 'smile', motion: active ? 'thinking' : 'idle' });
}

checkStatus();
setInterval(checkStatus, 5000);

window.companion.on('python:ready', () => setServiceStatus(true));

window.companion.on('set:emotion', emotion => {
  avatar.setState({ expression: emotion, motion: emotion === 'excited' ? 'excited' : 'idle' });
});

window.companion.on('set:lipsync', active => {
  if (!active && (ttsPlaying || ttsQueue.length > 0)) {
    return;
  }
  avatar.setState({ lipsync: Boolean(active) });
});

window.companion.on('chat:chunk', chunk => {
  if (!streamEl) {
    streamEl = renderChunk();
    log.appendChild(streamEl);
  }
  streamEl.querySelector('.msg-body').textContent += chunk;
  log.scrollTop = log.scrollHeight;
});

async function processTtsQueue() {
  if (ttsPlaying) return;
  if (ttsQueue.length === 0) {
    if (chatDone) {
      avatar.stopLipSync();
      window.companion.setLipsync(false);
      setBusy(false);
      input.focus();
    }
    return;
  }

  ttsPlaying = true;
  const { url } = ttsQueue.shift();

  window.companion.setLipsync(true);
  try {
    await audioPlayer.play(url, amp => avatar.startLipSync(amp));
  } catch (err) {
    console.warn('[tts] audio playback failed:', err);
  } finally {
    avatar.stopLipSync();
    ttsPlaying = false;
    setTimeout(processTtsQueue, 50);
  }
}

window.companion.on('chat:done', reply => {
  if (streamEl) {
    const text = streamEl.querySelector('.msg-body').textContent || reply || '';
    history.add('assistant', text);
    streamEl = null;
  } else if (reply) {
    addMessage('assistant', reply);
  }
  chatDone = true;
  if (!ttsPlaying && ttsQueue.length === 0) {
    avatar.stopLipSync();
    window.companion.setLipsync(false);
    setBusy(false);
    input.focus();
  }
});

window.companion.on('tts:audio', async ({ url, duration_ms: durationMs } = {}) => {
  if (!url) return;
  ttsQueue.push({ url, durationMs });
  processTtsQueue();
});

form.addEventListener('submit', async event => {
  event.preventDefault();
  const text = input.value.trim();
  if (!text && !attachedImageBase64) return;

  const imageToSend = attachedImageBase64;

  input.value = '';
  attachedImageBase64 = null;
  if (fileInput) fileInput.value = '';
  if (imagePreviewArea) imagePreviewArea.style.display = 'none';
  if (imagePreviewThumbnail) imagePreviewThumbnail.src = '';

  streamEl = null;
  
  const displayMsg = imageToSend ? `${text ? text + ' ' : ''}![image](${imageToSend})` : text;
  addMessage('user', displayMsg);
  setBusy(true);

  // Reset audio queue state
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;

  // Search memories in PGlite WASM
  let memoryContext = [];
  try {
    const memories = await LocalDB.searchMemories(text);
    memoryContext = memories.map(m => ({ text: m.text }));
  } catch (err) {
    console.warn("Failed to query LocalDB:", err);
  }

  if (llmSelect && llmSelect.value === 'webgpu') {
    // ----------------------------------------------------
    // Run Local WebGPU Inference
    // ----------------------------------------------------
    const systemPrompt = "Bạn là IceGirl, trợ lý ảo cá nhân 2.5D cực kỳ đáng yêu, thân thiện và thông minh. Hãy trả lời người dùng một cách tự nhiên, ngắn gọn và thêm các thẻ cảm xúc như [smile], [happy], [excited], [thinking], [sad] phù hợp.\n" +
      (memoryContext.length > 0 ? "Thông tin đã ghi nhớ về người dùng: " + memoryContext.map(m => m.text).join("; ") : "");

    const chatHistory = history.all().map(h => ({
      role: h.role === 'user' ? 'user' : 'assistant',
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
      log.appendChild(streamEl);

      // Trigger start event for OBS
      window.companion.broadcast('start', { emotion: 'normal', motion: 'thinking' });
      window.companion.setLipsync(true);

      const onChunk = (token) => {
        parserBuffer += token;
        
        // Match emotion tag
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
          currentResponseText += textToYield;
          streamEl.querySelector('.msg-body').textContent += textToYield;
          window.companion.broadcast('chat_chunk', textToYield);
          log.scrollTop = log.scrollHeight;
        }
      };

      await WebGPUEngine.chat(messages, onChunk);
      
      // Flush remaining
      if (parserBuffer) {
        streamEl.querySelector('.msg-body').textContent += parserBuffer;
        currentResponseText += parserBuffer;
        window.companion.broadcast('chat_chunk', parserBuffer);
      }

      window.companion.broadcast('chat_done', currentResponseText);

      // Save user prompt to local database
      await LocalDB.addMemory(text);

      // Synthesize TTS
      const ttsRes = await window.companion.invoke("ai:tts", { text: currentResponseText });
      if (ttsRes && ttsRes.ok && ttsRes.response.audio_url) {
        ttsQueue.push({ url: ttsRes.response.audio_url, durationMs: ttsRes.response.duration_ms });
        processTtsQueue();
      } else {
        avatar.setState({ expression: 'smile', motion: 'idle', lipsync: false });
        window.companion.setLipsync(false);
        setBusy(false);
        input.focus();
      }

      history.add('assistant', currentResponseText);
      streamEl = null;
      chatDone = true;

    } catch (err) {
      console.error("WebGPU Chat Generation Error:", err);
      addMessage('assistant', 'Lỗi suy luận WebGPU: ' + err.message);
      setBusy(false);
    }

  } else {
    // ----------------------------------------------------
    // Run normal HTTP Chat over Python Server
    // ----------------------------------------------------
    const context = {
      locale: 'vi-VN',
      memory: memoryContext
    };

    const res = await window.companion.chat(text, imageToSend, context);
    if (!res?.ok) {
      addMessage('assistant', 'Backend đang offline. Bạn khởi động lại Python service giúp mình nhé.');
      setBusy(false);
      setServiceStatus(false);
    } else {
      // Auto save memory context locally too
      await LocalDB.addMemory(text);
    }
  }
});

// Đính kèm ảnh từ máy tính
attachButton?.addEventListener('click', () => {
  fileInput?.click();
});

fileInput?.addEventListener('change', event => {
  const file = event.target.files[0];
  if (!file) return;

  const reader = new FileReader();
  reader.onload = e => {
    attachedImageBase64 = e.target.result;
    if (imagePreviewThumbnail) imagePreviewThumbnail.src = attachedImageBase64;
    if (imagePreviewArea) imagePreviewArea.style.display = 'flex';
  };
  reader.readAsDataURL(file);
});

clearImageButton?.addEventListener('click', () => {
  attachedImageBase64 = null;
  if (fileInput) fileInput.value = '';
  if (imagePreviewArea) imagePreviewArea.style.display = 'none';
  if (imagePreviewThumbnail) imagePreviewThumbnail.src = '';
});

voiceButton.addEventListener('click', async () => {
  if (!isRecording) {
    isRecording = true;
    voiceButton.classList.add('active');
    voiceButton.textContent = 'Stop';
    avatar.setState({ expression: 'focused', motion: 'look_side' });
    await recorder.start();
    return;
  }

  isRecording = false;
  voiceButton.classList.remove('active');
  voiceButton.textContent = 'Mic';
  setBusy(true);
  const b64 = await recorder.stop();
  if (b64) await window.companion.invoke('ai:voice-input', { audio_b64: b64 });
});

window.companion.on('stt:result', text => {
  input.value = text;
  setBusy(false);
});

window.companion.on('chat:request-approval', ({ req_id, action, details }) => {
  avatar.setState({ expression: 'focused', motion: 'thinking' });
  const approvalEl = renderApprovalCard(req_id, action, details);
  log.appendChild(approvalEl);
  log.scrollTop = log.scrollHeight;
});

window.companion.on('tts:done', () => avatar.stopLipSync());

window.companion.on('trigger:screenshot', async () => {
  addMessage('user', '[Nhin man hinh]');
  setBusy(true);

  // Reset audio queue state
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;

  await window.companion.invoke('ai:screenshot', { question: 'Man hinh dang hien thi gi?' });
});

setTimeout(() => {
  addMessage('assistant', 'Chao ban! Minh la IceGirl. Ban can minh giup gi khong?');
  avatar.setState({ expression: 'smile', motion: 'idle' });
}, 300);

// Khởi động lưu trữ Vector DB ký ức cục bộ IndexedDB
try {
  LocalDB.init().then(() => {
    console.log("[App] Local Vector DB initialized");
  });
} catch (err) {
  console.warn("[App] Failed to initialize Local Vector DB:", err);
}

async function loadConfig() {
  try {
    const res = await window.companion.invoke('ai:get-config');
    if (res && !res.error) {
      if (llmSelect) {
        const val = res.llm_provider || 'ollama';
        llmSelect.value = val;
        if (val === 'webgpu') {
          llmSelect.dispatchEvent(new Event('change'));
        }
      }
      if (sttSelect) sttSelect.value = res.stt_model || 'base';
    }
  } catch (err) {
    console.warn('[config] Failed to load initial configuration:', err);
  }
}

if (llmSelect) {
  llmSelect.addEventListener('change', async () => {
    const provider = llmSelect.value;
    
    if (provider === 'webgpu') {
      if (!WebGPUEngine.isInitialized()) {
        webgpuProgressContainer.style.display = 'flex';
        webgpuProgressText.textContent = "Đang khởi tạo WebGPU...";
        webgpuProgressPercent.textContent = "0%";
        webgpuProgressBar.style.width = "0%";
        
        setBusy(true);
        llmSelect.disabled = true;
        
        try {
          addMessage('system', 'Đang tải mô hình WebGPU Qwen2.5-1.5B (Lần đầu có thể mất vài phút)...');
          await WebGPUEngine.init((text, progress) => {
            webgpuProgressText.textContent = text;
            const percent = Math.round(progress * 100);
            webgpuProgressPercent.textContent = `${percent}%`;
            webgpuProgressBar.style.width = `${percent}%`;
          });
          
          addMessage('system', 'Khởi tạo và tải thành công mô hình WebGPU!');
          webgpuProgressContainer.style.display = 'none';
        } catch (err) {
          console.error("WebGPU Init Error:", err);
          addMessage('system', 'Lỗi khởi tạo WebGPU: ' + err.message);
          webgpuProgressContainer.style.display = 'none';
          llmSelect.value = 'ollama';
          await window.companion.invoke('ai:update-config', { key: 'llm.provider', value: 'ollama' });
        } finally {
          setBusy(false);
          llmSelect.disabled = false;
        }
      }
    } else {
      const res = await window.companion.invoke('ai:update-config', { key: 'llm.provider', value: provider });
      if (res && !res.error) {
        addMessage('system', `Đã chuyển sang bộ não: ${llmSelect.options[llmSelect.selectedIndex].text}`);
      }
    }
  });
}

if (sttSelect) {
  sttSelect.addEventListener('change', async () => {
    const model = sttSelect.value;
    const res = await window.companion.invoke('ai:update-config', { key: 'stt.model', value: model });
    if (res && !res.error) {
      addMessage('system', `Đang tải lại STT sang mô hình: ${sttSelect.options[sttSelect.selectedIndex].text}`);
    }
  });
}

loadConfig();
