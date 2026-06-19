console.log("[settings] settings.js script loaded.");

const llmSelect = document.getElementById("llmSelect");
const sttSelect = document.getElementById("sttSelect");
const avatarSelect = document.getElementById("avatarSelect");
const chkScreenAwareness = document.getElementById("chkScreenAwareness");
const chkTwitchMode = document.getElementById("chkTwitchMode");
const txtTwitchChannel = document.getElementById("txtTwitchChannel");
const radModeStreamer = document.getElementById("radModeStreamer");
const radModeAssistant = document.getElementById("radModeAssistant");
const saveStatus = document.getElementById("saveStatus");

function showStatus() {
  if (!saveStatus) return;
  saveStatus.classList.add("visible");
  setTimeout(() => {
    saveStatus.classList.remove("visible");
  }, 2000);
}

async function loadConfig() {
  console.log("[settings] Starting loadConfig()...");
  if (!window.companion) {
    console.error("[settings] window.companion is undefined! Preload script might not have loaded.");
    return;
  }
  try {
    const res = await window.companion.invoke('ai:get-config');
    console.log("[settings] Received configuration:", res);
    if (res && !res.error) {
      if (llmSelect) llmSelect.value = res.llm_provider || 'ollama';
      if (sttSelect) sttSelect.value = res.stt_model || 'base';
      if (avatarSelect) avatarSelect.value = res.avatar_model || 'assets/live2d/IceGirl/IceGirl.model3.json';
      if (chkScreenAwareness) chkScreenAwareness.checked = Boolean(res.screen_awareness);
      if (chkTwitchMode) chkTwitchMode.checked = Boolean(res.twitch_mode);
      if (txtTwitchChannel) txtTwitchChannel.value = res.twitch_channel || '';
      
      if (radModeStreamer && radModeAssistant) {
        if (res.interaction_mode === 'streamer') {
          radModeStreamer.checked = true;
          console.log("[settings] Checked streamer mode");
        } else {
          radModeAssistant.checked = true;
          console.log("[settings] Checked assistant mode");
        }
      }
    } else {
      console.warn("[settings] Config response empty or has error:", res?.error);
    }
  } catch (err) {
    console.error('[settings] Failed to load configuration:', err);
  }
}

if (!window.companion) {
  console.error("[settings] window.companion is undefined! Preload script might not have loaded.");
} else {
  if (llmSelect) {
    llmSelect.addEventListener('change', async () => {
      console.log("[settings] llm provider changed:", llmSelect.value);
      const res = await window.companion.invoke('ai:update-config', { key: 'llm.provider', value: llmSelect.value });
      if (res && !res.error) showStatus();
    });
  }

  if (avatarSelect) {
    avatarSelect.addEventListener('change', async () => {
      console.log("[settings] avatar model changed:", avatarSelect.value);
      const res = await window.companion.invoke('ai:update-config', { key: 'app.avatarModel', value: avatarSelect.value });
      if (res && !res.error) showStatus();
    });
  }

  if (sttSelect) {
    sttSelect.addEventListener('change', async () => {
      console.log("[settings] stt model changed:", sttSelect.value);
      const res = await window.companion.invoke('ai:update-config', { key: 'stt.model', value: sttSelect.value });
      if (res && !res.error) showStatus();
    });
  }

  if (chkScreenAwareness) {
    chkScreenAwareness.addEventListener('change', async () => {
      console.log("[settings] screen awareness changed:", chkScreenAwareness.checked);
      const res = await window.companion.invoke('ai:update-config', { key: 'features.screenAwareness', value: chkScreenAwareness.checked });
      if (res && !res.error) showStatus();
    });
  }

  if (chkTwitchMode) {
    chkTwitchMode.addEventListener('change', async () => {
      console.log("[settings] twitch mode changed:", chkTwitchMode.checked);
      const res = await window.companion.invoke('ai:update-config', { key: 'features.twitchMode', value: chkTwitchMode.checked });
      if (res && !res.error) showStatus();
    });
  }

  if (txtTwitchChannel) {
    const saveChannel = async () => {
      const channel = txtTwitchChannel.value.trim();
      console.log("[settings] twitch channel changed:", channel);
      const res = await window.companion.invoke('ai:update-config', { key: 'twitch.channel', value: channel });
      if (res && !res.error) showStatus();
    };
    txtTwitchChannel.addEventListener('blur', saveChannel);
    txtTwitchChannel.addEventListener('keypress', (e) => {
      if (e.key === 'Enter') {
        e.preventDefault();
        saveChannel();
        txtTwitchChannel.blur();
      }
    });
  }

  document.querySelectorAll('input[name="interactionMode"]').forEach(rad => {
    rad.addEventListener('change', async () => {
      if (rad.checked) {
        console.log("[settings] interactionMode radio checked:", rad.value);
        const res = await window.companion.invoke('ai:update-config', { key: 'app.interactionMode', value: rad.value });
        console.log("[settings] update interactionMode response:", res);
        if (res && !res.error) showStatus();
      }
    });
  });

  window.companion.on('python:ready', () => {
    console.log("[settings] Python service is ready. Reloading configuration...");
    loadConfig();
  });

  loadConfig();
}
