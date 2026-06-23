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

// ─── Toggle LLM config containers ─────────────────────────────
function toggleLLMSubConfigs(provider) {
  document.querySelectorAll(".llm-sub-config").forEach((block) => {
    block.style.display = "none";
  });
  const activeBlock = document.getElementById(`config-${provider}`);
  if (activeBlock) {
    activeBlock.style.display = "block";
  }
}

// ─── Load config ─────────────────────────────────────────────
async function loadConfig() {
  if (!window.companion) return;
  try {
    const res = await window.companion.invoke("ai:get-config");
    if (!res || res.error) return;

    if (llmSelect) {
      llmSelect.value = res.llm_provider || "ollama";
      toggleLLMSubConfigs(res.llm_provider || "ollama");
    }
    
    // Populate subconfig inputs
    if (document.getElementById("geminiKeyInput")) document.getElementById("geminiKeyInput").value = res.gemini_key || "";
    if (document.getElementById("geminiModelInput")) document.getElementById("geminiModelInput").value = res.gemini_model || "";
    if (document.getElementById("openaiKeyInput")) document.getElementById("openaiKeyInput").value = res.openai_key || "";
    if (document.getElementById("openaiModelInput")) document.getElementById("openaiModelInput").value = res.openai_model || "";
    if (document.getElementById("deepseekKeyInput")) document.getElementById("deepseekKeyInput").value = res.deepseek_key || "";
    if (document.getElementById("deepseekModelInput")) document.getElementById("deepseekModelInput").value = res.deepseek_model || "";
    if (document.getElementById("glmKeyInput")) document.getElementById("glmKeyInput").value = res.glm_key || "";
    if (document.getElementById("glmModelInput")) document.getElementById("glmModelInput").value = res.glm_model || "";
    if (document.getElementById("qwenKeyInput")) document.getElementById("qwenKeyInput").value = res.qwen_key || "";
    if (document.getElementById("qwenModelInput")) document.getElementById("qwenModelInput").value = res.qwen_model || "";
    if (document.getElementById("openaiCompatibleKeyInput")) document.getElementById("openaiCompatibleKeyInput").value = res.openai_compatible_key || "";
    if (document.getElementById("openaiCompatibleModelInput")) document.getElementById("openaiCompatibleModelInput").value = res.openai_compatible_model || "";
    if (document.getElementById("openaiCompatibleBaseUrlInput")) document.getElementById("openaiCompatibleBaseUrlInput").value = res.openai_compatible_base_url || "";

    if (sttSelect) {
      sttSelect.value = res.stt_model || "base";
      const block = document.getElementById("stt-funasr-config");
      if (block) block.style.display = (sttSelect.value === "funasr") ? "block" : "none";
    }
    if (document.getElementById("sttFunasrModelInput")) {
      document.getElementById("sttFunasrModelInput").value = res.stt_funasr_model || "";
    }
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

    // Avatar scale
    const avatarScaleSelect = document.getElementById("avatarScaleSelect");
    if (avatarScaleSelect) {
      avatarScaleSelect.value = res.avatar_scale || "1.0";
    }

    // Mode radio
    if (radModeStreamer && radModeAssistant) {
      if (res.interaction_mode === "streamer") radModeStreamer.checked = true;
      else radModeAssistant.checked = true;
    }

    // Memory toggle checkbox status
    const chkMemoryMode = document.getElementById("chkMemoryMode");
    if (chkMemoryMode) {
      chkMemoryMode.checked = res.memory !== false;
    }
    
    // Load memories list
    loadMemories();
  } catch (err) {
    console.error("[settings] loadConfig error:", err);
  }
}

async function loadMemories() {
  const memoryList = document.getElementById("memoryList");
  if (!memoryList) return;
  try {
    const res = await window.companion.invoke("ai:get-memories");
    if (!res || res.error) {
      memoryList.innerHTML = `<div style="text-align: center; color: var(--text-3); padding: 20px;">Lỗi tải ký ức: ${res ? res.error : "Không có phản hồi"}</div>`;
      return;
    }
    const memories = res.memories || [];
    if (memories.length === 0) {
      memoryList.innerHTML = `<div style="text-align: center; color: var(--text-3); padding: 20px;">Chưa lưu ký ức nào.</div>`;
      return;
    }
    
    memoryList.innerHTML = "";
    memories.forEach((mem) => {
      const item = document.createElement("div");
      item.className = "memory-item";
      
      const input = document.createElement("input");
      input.type = "text";
      input.className = "memory-text";
      input.value = mem.text;
      
      // Save on blur or Enter
      const saveEdit = async () => {
        const val = input.value.trim();
        if (val && val !== mem.text) {
          const updateRes = await window.companion.invoke("ai:update-memory", { id: mem.id, text: val });
          if (updateRes && !updateRes.error && updateRes.success) {
            mem.text = val;
            showStatus("Đã cập nhật ký ức");
          } else {
            input.value = mem.text;
            showStatus("Lỗi cập nhật ký ức");
          }
        }
      };
      
      input.addEventListener("blur", saveEdit);
      input.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          saveEdit();
          input.blur();
        }
      });
      
      const actions = document.createElement("div");
      actions.className = "memory-actions";
      
      const delBtn = document.createElement("button");
      delBtn.className = "memory-btn delete";
      delBtn.innerHTML = "🗑️";
      delBtn.title = "Xóa ký ức";
      delBtn.addEventListener("click", async () => {
        if (confirm("Bạn có chắc chắn muốn xóa ký ức này không?")) {
          const delRes = await window.companion.invoke("ai:delete-memory", { id: mem.id });
          if (delRes && !delRes.error && delRes.success) {
            item.remove();
            showStatus("Đã xóa ký ức");
            if (memoryList.children.length === 0) {
              memoryList.innerHTML = `<div style="text-align: center; color: var(--text-3); padding: 20px;">Chưa lưu ký ức nào.</div>`;
            }
          } else {
            showStatus("Lỗi khi xóa ký ức");
          }
        }
      });
      
      actions.appendChild(delBtn);
      item.appendChild(input);
      item.appendChild(actions);
      memoryList.appendChild(item);
    });
  } catch (err) {
    console.error("[settings] loadMemories error:", err);
  }
}

// ─── Wire up controls ─────────────────────────────────────────
if (!window.companion) {
  console.error("[settings] window.companion undefined!");
} else {
  llmSelect?.addEventListener("change", async () => {
    toggleLLMSubConfigs(llmSelect.value);
    const res = await window.companion.invoke("ai:update-config", {
      key: "llm.provider",
      value: llmSelect.value,
    });
    if (res && !res.error) showStatus();
  });

  const bindConfigInput = (elemId, configKey, label) => {
    const elem = document.getElementById(elemId);
    elem?.addEventListener("change", async () => {
      const res = await window.companion.invoke("ai:update-config", {
        key: configKey,
        value: elem.value,
      });
      if (res && !res.error) showStatus(`Đã lưu ${label}`);
    });
  };

  bindConfigInput("geminiKeyInput", "llm.gemini_api_key", "Gemini Key");
  bindConfigInput("geminiModelInput", "llm.gemini_model", "Gemini Model");
  bindConfigInput("openaiKeyInput", "llm.openai_api_key", "OpenAI Key");
  bindConfigInput("openaiModelInput", "llm.openai_model", "OpenAI Model");
  bindConfigInput("deepseekKeyInput", "llm.deepseek_api_key", "DeepSeek Key");
  bindConfigInput("deepseekModelInput", "llm.deepseek_model", "DeepSeek Model");
  bindConfigInput("glmKeyInput", "llm.glm_api_key", "GLM Key");
  bindConfigInput("glmModelInput", "llm.glm_model", "GLM Model");
  bindConfigInput("qwenKeyInput", "llm.qwen_api_key", "Qwen Key");
  bindConfigInput("qwenModelInput", "llm.qwen_model", "Qwen Model");
  bindConfigInput("openaiCompatibleKeyInput", "llm.openai_compatible_api_key", "Custom Key");
  bindConfigInput("openaiCompatibleModelInput", "llm.openai_compatible_model", "Custom Model");
  bindConfigInput("openaiCompatibleBaseUrlInput", "llm.openai_compatible_base_url", "Custom Base URL");
  bindConfigInput("sttFunasrModelInput", "stt.funasr_model", "FunASR Model");
 
  sttSelect?.addEventListener("change", async () => {
    const block = document.getElementById("stt-funasr-config");
    if (block) block.style.display = (sttSelect.value === "funasr") ? "block" : "none";

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

  // Avatar scale change
  const avatarScaleSelect = document.getElementById("avatarScaleSelect");
  avatarScaleSelect?.addEventListener("change", async () => {
    const res = await window.companion.invoke("ai:update-config", {
      key: "app.avatarScale",
      value: avatarScaleSelect.value,
    });
    if (res && !res.error) showStatus("Đã lưu tỷ lệ nhân vật");
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

  // Memory manager bindings
  const chkMemoryMode = document.getElementById("chkMemoryMode");
  chkMemoryMode?.addEventListener("change", async () => {
    const res = await window.companion.invoke("ai:update-config", {
      key: "features.memory",
      value: chkMemoryMode.checked,
    });
    if (res && !res.error) {
      showStatus(chkMemoryMode.checked ? "Đã bật ghi nhớ dài hạn" : "Đã tắt ghi nhớ dài hạn");
    }
  });

  const txtNewMemory = document.getElementById("txtNewMemory");
  const btnAddMemory = document.getElementById("btnAddMemory");
  const handleAddMemory = async () => {
    const text = txtNewMemory?.value.trim() || "";
    if (!text) return;
    const res = await window.companion.invoke("ai:add-memory", { text });
    if (res && !res.error && res.success) {
      txtNewMemory.value = "";
      showStatus("Đã thêm ký ức mới");
      loadMemories();
    } else {
      showStatus("Lỗi thêm ký ức");
    }
  };
  btnAddMemory?.addEventListener("click", handleAddMemory);
  txtNewMemory?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddMemory();
    }
  });

  window.companion.on("python:ready", loadConfig);
  loadConfig();
}
