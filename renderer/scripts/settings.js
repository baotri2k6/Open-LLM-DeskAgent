console.log("[settings] settings.js loaded.");

// ─── Element refs ────────────────────────────────────────────
const llmSelect = document.getElementById("llmSelect");
const sttSelect = document.getElementById("sttSelect");
const chkTwitchMode = document.getElementById("chkTwitchMode");
const txtTwitchChannel = document.getElementById("txtTwitchChannel");
const twitchChannelWrap = document.getElementById("twitchChannelWrap");
const radModeStreamer = document.getElementById("radModeStreamer");
const radModeAssistant = document.getElementById("radModeAssistant");
const saveStatus = document.getElementById("saveStatus");

// ─── Toast ───────────────────────────────────────────────────
let toastTimer = null;
function showStatus(msg = "Đã lưu cài đặt") {
  if (!saveStatus) return;
  saveStatus.textContent = `✓  ${msg}`;
  saveStatus.classList.add("visible");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => saveStatus.classList.remove("visible"), 2200);
}

// ─── Twitch channel toggle ────────────────────────────────────
function syncTwitchWrap(checked) {
  if (twitchChannelWrap) {
    twitchChannelWrap.classList.toggle("visible", checked);
  }
}

// ─── Load config ─────────────────────────────────────────────
async function loadConfig() {
  if (!window.companion) return;
  try {
    const res = await window.companion.invoke("ai:get-config");
    if (!res || res.error) return;

    if (llmSelect) llmSelect.value = res.llm_provider || "ollama";
    if (sttSelect) sttSelect.value = res.stt_model || "base";
    if (chkTwitchMode) chkTwitchMode.checked = Boolean(res.twitch_mode);
    if (txtTwitchChannel) txtTwitchChannel.value = res.twitch_channel || "";

    syncTwitchWrap(Boolean(res.twitch_mode));

    // Avatar radio
    const avatarVal =
      res.avatar_model || "assets/live2d/IceGirl/IceGirl.model3.json";
    const avatarRadios = document.querySelectorAll('input[name="avatarModel"]');
    avatarRadios.forEach((r) => {
      r.checked = r.value === avatarVal;
    });

    // Mode radio
    if (radModeStreamer && radModeAssistant) {
      if (res.interaction_mode === "streamer") radModeStreamer.checked = true;
      else radModeAssistant.checked = true;
    }
  } catch (err) {
    console.error("[settings] loadConfig error:", err);
  }
}

// ─── Wire up controls ─────────────────────────────────────────
if (!window.companion) {
  console.error("[settings] window.companion undefined!");
} else {
  llmSelect?.addEventListener("change", async () => {
    const res = await window.companion.invoke("ai:update-config", {
      key: "llm.provider",
      value: llmSelect.value,
    });
    if (res && !res.error) showStatus();
  });

  sttSelect?.addEventListener("change", async () => {
    const res = await window.companion.invoke("ai:update-config", {
      key: "stt.model",
      value: sttSelect.value,
    });
    if (res && !res.error) showStatus();
  });

  // Avatar radio cards
  document.querySelectorAll('input[name="avatarModel"]').forEach((radio) => {
    radio.addEventListener("change", async () => {
      if (!radio.checked) return;
      const res = await window.companion.invoke("ai:update-config", {
        key: "app.avatarModel",
        value: radio.value,
      });
      if (res && !res.error) showStatus("Đã đổi nhân vật");
    });
  });

  // Mode radio cards
  document
    .querySelectorAll('input[name="interactionMode"]')
    .forEach((radio) => {
      radio.addEventListener("change", async () => {
        if (!radio.checked) return;
        const res = await window.companion.invoke("ai:update-config", {
          key: "app.interactionMode",
          value: radio.value,
        });
        if (res && !res.error) showStatus("Đã đổi chế độ");
      });
    });

  chkTwitchMode?.addEventListener("change", async () => {
    syncTwitchWrap(chkTwitchMode.checked);
    const res = await window.companion.invoke("ai:update-config", {
      key: "features.twitchMode",
      value: chkTwitchMode.checked,
    });
    if (res && !res.error)
      showStatus(chkTwitchMode.checked ? "Twitch đã bật" : "Twitch đã tắt");
  });

  const saveChannel = async () => {
    const channel = txtTwitchChannel?.value.trim() || "";
    const res = await window.companion.invoke("ai:update-config", {
      key: "twitch.channel",
      value: channel,
    });
    if (res && !res.error) showStatus(`Kênh: ${channel}`);
  };

  txtTwitchChannel?.addEventListener("blur", saveChannel);
  txtTwitchChannel?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveChannel();
      txtTwitchChannel.blur();
    }
  });

  window.companion.on("python:ready", loadConfig);
  loadConfig();
}
