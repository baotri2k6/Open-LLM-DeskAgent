import { AvatarController } from './avatar/live2d-manager.js';
import { ChatHistory } from './chat/history.js';
import { renderMessage, renderChunk, renderApprovalCard } from './chat/message.js';
import { AudioPlayer } from './voice/audio-player.js';
import { VoiceRecorder } from './voice/recoder.js';

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
  
  // Hiển thị ảnh xem trước trực tiếp trong bong bóng chat của người dùng
  const displayMsg = imageToSend ? `${text ? text + ' ' : ''}![image](${imageToSend})` : text;
  addMessage('user', displayMsg);
  setBusy(true);

  // Reset audio queue state
  ttsQueue = [];
  ttsPlaying = false;
  chatDone = false;

  const res = await window.companion.chat(text, imageToSend, { locale: 'vi-VN' });
  if (!res?.ok) {
    addMessage('assistant', 'Backend dang offline. Ban khoi dong lai Python service giup minh nhe.');
    setBusy(false);
    setServiceStatus(false);
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

async function loadConfig() {
  try {
    const res = await window.companion.invoke('ai:get-config');
    if (res && !res.error) {
      if (llmSelect) llmSelect.value = res.llm_provider || 'ollama';
      if (sttSelect) sttSelect.value = res.stt_model || 'base';
    }
  } catch (err) {
    console.warn('[config] Failed to load initial configuration:', err);
  }
}

if (llmSelect) {
  llmSelect.addEventListener('change', async () => {
    const provider = llmSelect.value;
    const res = await window.companion.invoke('ai:update-config', { key: 'llm.provider', value: provider });
    if (res && !res.error) {
      addMessage('system', `Đã chuyển sang bộ não: ${llmSelect.options[llmSelect.selectedIndex].text}`);
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
