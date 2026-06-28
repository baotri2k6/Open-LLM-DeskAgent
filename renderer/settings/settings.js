console.log("[settings] settings.ts loaded.");
const llmSelect = document.getElementById("llmSelect");
const sttSelect = document.getElementById("sttSelect");
const chkTwitchMode = document.getElementById("chkTwitchMode");
const txtTwitchChannel = document.getElementById("txtTwitchChannel");
const twitchChannelWrap = document.getElementById("twitchChannelWrap");
const radModeStreamer = document.getElementById("radModeStreamer");
const radModeAssistant = document.getElementById("radModeAssistant");
const saveStatus = document.getElementById("saveStatus");
let toastTimer = null;
function showStatus(msg = "\u0110\xE3 l\u01B0u c\xE0i \u0111\u1EB7t") {
  if (!saveStatus) return;
  saveStatus.textContent = `\u2713  ${msg}`;
  saveStatus.classList.add("visible");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => saveStatus.classList.remove("visible"), 2200);
}
function syncTwitchWrap(checked) {
  if (twitchChannelWrap) {
    twitchChannelWrap.classList.toggle("visible", checked);
  }
}
function toggleLLMSubConfigs(provider) {
  document.querySelectorAll(".llm-sub-config").forEach((block) => {
    block.style.display = "none";
  });
  const activeBlock = document.getElementById(`config-${provider}`);
  if (activeBlock) {
    activeBlock.style.display = "block";
  }
}
async function loadConfig() {
  if (!window.companion) return;
  try {
    const res = await window.companion.invoke("ai:get-config", {});
    if (!res || res.error) return;
    if (llmSelect) {
      llmSelect.value = res.llm_provider || "ollama";
      toggleLLMSubConfigs(res.llm_provider || "ollama");
    }
    const setVal = (id, val) => {
      const el = document.getElementById(id);
      if (el) el.value = val;
    };
    setVal("geminiKeyInput", res.gemini_key || "");
    setVal("geminiModelInput", res.gemini_model || "");
    setVal("openaiKeyInput", res.openai_key || "");
    setVal("openaiModelInput", res.openai_model || "");
    setVal("deepseekKeyInput", res.deepseek_key || "");
    setVal("deepseekModelInput", res.deepseek_model || "");
    setVal("glmKeyInput", res.glm_key || "");
    setVal("glmModelInput", res.glm_model || "");
    setVal("qwenKeyInput", res.qwen_key || "");
    setVal("qwenModelInput", res.qwen_model || "");
    setVal("openaiCompatibleKeyInput", res.openai_compatible_key || "");
    setVal("openaiCompatibleModelInput", res.openai_compatible_model || "");
    setVal("openaiCompatibleBaseUrlInput", res.openai_compatible_base_url || "");
    if (sttSelect) {
      sttSelect.value = res.stt_model || "base";
      const block = document.getElementById("stt-funasr-config");
      if (block) block.style.display = sttSelect.value === "funasr" ? "block" : "none";
    }
    setVal("sttFunasrModelInput", res.stt_funasr_model || "");
    if (chkTwitchMode) chkTwitchMode.checked = Boolean(res.twitch_mode);
    if (txtTwitchChannel) txtTwitchChannel.value = res.twitch_channel || "";
    syncTwitchWrap(Boolean(res.twitch_mode));
    const avatarVal = res.avatar_model || "assets/live2d/IceGirl/IceGirl.model3.json";
    const avatarRadios = document.querySelectorAll('input[name="avatarModel"]');
    avatarRadios.forEach((r) => {
      r.checked = r.value === avatarVal;
    });
    const avatarScaleSelect = document.getElementById("avatarScaleSelect");
    if (avatarScaleSelect) {
      avatarScaleSelect.value = res.avatar_scale || "1.0";
    }
    if (radModeStreamer && radModeAssistant) {
      if (res.interaction_mode === "streamer") radModeStreamer.checked = true;
      else radModeAssistant.checked = true;
    }
    const chkMemoryMode = document.getElementById("chkMemoryMode");
    if (chkMemoryMode) {
      chkMemoryMode.checked = res.memory !== false;
    }
    loadMemories();
  } catch (err) {
    console.error("[settings] loadConfig error:", err);
  }
}
async function loadMemories() {
  const memoryList = document.getElementById("memoryList");
  if (!memoryList) return;
  try {
    const res = await window.companion.invoke("ai:get-memories", {});
    if (!res || res.error) {
      memoryList.innerHTML = `<div style="text-align: center; color: var(--text-3); padding: 20px;">L\u1ED7i t\u1EA3i k\xFD \u1EE9c: ${res ? res.error : "Kh\xF4ng c\xF3 ph\u1EA3n h\u1ED3i"}</div>`;
      return;
    }
    const memories = res.memories || [];
    if (memories.length === 0) {
      memoryList.innerHTML = `<div style="text-align: center; color: var(--text-3); padding: 20px;">Ch\u01B0a l\u01B0u k\xFD \u1EE9c n\xE0o.</div>`;
      return;
    }
    memoryList.innerHTML = "";
    memories.forEach((mem) => {
      const item = document.createElement("div");
      item.className = "memory-item";
      const inp = document.createElement("input");
      inp.type = "text";
      inp.className = "memory-text";
      inp.value = mem.text;
      const saveEdit = async () => {
        const val = inp.value.trim();
        if (val && val !== mem.text) {
          const updateRes = await window.companion.invoke("ai:update-memory", { id: mem.id, text: val });
          if (updateRes && !updateRes.error && updateRes.success) {
            mem.text = val;
            showStatus("\u0110\xE3 c\u1EADp nh\u1EADt k\xFD \u1EE9c");
          } else {
            inp.value = mem.text;
            showStatus("L\u1ED7i c\u1EADp nh\u1EADt k\xFD \u1EE9c");
          }
        }
      };
      inp.addEventListener("blur", saveEdit);
      inp.addEventListener("keypress", (e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          saveEdit();
          inp.blur();
        }
      });
      const actions = document.createElement("div");
      actions.className = "memory-actions";
      const delBtn = document.createElement("button");
      delBtn.className = "memory-btn delete";
      delBtn.innerHTML = "\u{1F5D1}\uFE0F";
      delBtn.title = "X\xF3a k\xFD \u1EE9c";
      delBtn.addEventListener("click", async () => {
        if (confirm("B\u1EA1n c\xF3 ch\u1EAFc ch\u1EAFn mu\u1ED1n x\xF3a k\xFD \u1EE9c n\xE0y kh\xF4ng?")) {
          const delRes = await window.companion.invoke("ai:delete-memory", { id: mem.id });
          if (delRes && !delRes.error && delRes.success) {
            item.remove();
            showStatus("\u0110\xE3 x\xF3a k\xFD \u1EE9c");
            if (memoryList.children.length === 0) {
              memoryList.innerHTML = `<div style="text-align: center; color: var(--text-3); padding: 20px;">Ch\u01B0a l\u01B0u k\xFD \u1EE9c n\xE0o.</div>`;
            }
          } else {
            showStatus("L\u1ED7i khi x\xF3a k\xFD \u1EE9c");
          }
        }
      });
      actions.appendChild(delBtn);
      item.appendChild(inp);
      item.appendChild(actions);
      memoryList.appendChild(item);
    });
  } catch (err) {
    console.error("[settings] loadMemories error:", err);
  }
}
if (!window.companion) {
  console.error("[settings] window.companion undefined!");
} else {
  llmSelect?.addEventListener("change", async () => {
    toggleLLMSubConfigs(llmSelect.value);
    const res = await window.companion.invoke("ai:update-config", {
      key: "llm.provider",
      value: llmSelect.value
    });
    if (res && !res.error) showStatus();
  });
  const bindConfigInput = (elemId, configKey, label) => {
    const elem = document.getElementById(elemId);
    elem?.addEventListener("change", async () => {
      const res = await window.companion.invoke("ai:update-config", {
        key: configKey,
        value: elem.value
      });
      if (res && !res.error) showStatus(`\u0110\xE3 l\u01B0u ${label}`);
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
    if (block) block.style.display = sttSelect.value === "funasr" ? "block" : "none";
    const res = await window.companion.invoke("ai:update-config", {
      key: "stt.model",
      value: sttSelect.value
    });
    if (res && !res.error) showStatus();
  });
  document.querySelectorAll('input[name="avatarModel"]').forEach((radio) => {
    radio.addEventListener("change", async () => {
      const r = radio;
      if (!r.checked) return;
      const res = await window.companion.invoke("ai:update-config", {
        key: "app.avatarModel",
        value: r.value
      });
      if (res && !res.error) showStatus("\u0110\xE3 \u0111\u1ED5i nh\xE2n v\u1EADt");
    });
  });
  const avatarScaleSelect = document.getElementById("avatarScaleSelect");
  avatarScaleSelect?.addEventListener("change", async () => {
    const res = await window.companion.invoke("ai:update-config", {
      key: "app.avatarScale",
      value: avatarScaleSelect.value
    });
    if (res && !res.error) showStatus("\u0110\xE3 l\u01B0u t\u1EF7 l\u1EC7 nh\xE2n v\u1EADt");
  });
  document.querySelectorAll('input[name="interactionMode"]').forEach((radio) => {
    radio.addEventListener("change", async () => {
      const r = radio;
      if (!r.checked) return;
      const res = await window.companion.invoke("ai:update-config", {
        key: "app.interactionMode",
        value: r.value
      });
      if (res && !res.error) showStatus("\u0110\xE3 \u0111\u1ED5i ch\u1EBF \u0111\u1ED9");
    });
  });
  chkTwitchMode?.addEventListener("change", async () => {
    syncTwitchWrap(chkTwitchMode.checked);
    const res = await window.companion.invoke("ai:update-config", {
      key: "features.twitchMode",
      value: chkTwitchMode.checked
    });
    if (res && !res.error)
      showStatus(chkTwitchMode.checked ? "Twitch \u0111\xE3 b\u1EADt" : "Twitch \u0111\xE3 t\u1EAFt");
  });
  const saveChannel = async () => {
    const channel = txtTwitchChannel?.value.trim() || "";
    const res = await window.companion.invoke("ai:update-config", {
      key: "twitch.channel",
      value: channel
    });
    if (res && !res.error) showStatus(`K\xEAnh: ${channel}`);
  };
  txtTwitchChannel?.addEventListener("blur", saveChannel);
  txtTwitchChannel?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      saveChannel();
      txtTwitchChannel.blur();
    }
  });
  const chkMemoryMode = document.getElementById("chkMemoryMode");
  chkMemoryMode?.addEventListener("change", async () => {
    const res = await window.companion.invoke("ai:update-config", {
      key: "features.memory",
      value: chkMemoryMode.checked
    });
    if (res && !res.error) {
      showStatus(chkMemoryMode.checked ? "\u0110\xE3 b\u1EADt ghi nh\u1EDB d\xE0i h\u1EA1n" : "\u0110\xE3 t\u1EAFt ghi nh\u1EDB d\xE0i h\u1EA1n");
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
      showStatus("\u0110\xE3 th\xEAm k\xFD \u1EE9c m\u1EDBi");
      loadMemories();
    } else {
      showStatus("L\u1ED7i th\xEAm k\xFD \u1EE9c");
    }
  };
  btnAddMemory?.addEventListener("click", handleAddMemory);
  txtNewMemory?.addEventListener("keypress", (e) => {
    if (e.key === "Enter") {
      e.preventDefault();
      handleAddMemory();
    }
  });
  async function updateSystemStatus() {
    const statusBackend = document.getElementById("status-backend");
    const statusLlm = document.getElementById("status-llm");
    const statusTts = document.getElementById("status-tts");
    const statusStt = document.getElementById("status-stt");
    const statusMemory = document.getElementById("status-memory");
    try {
      const res = await window.companion.health();
      if (res && res.status === "ok" && res.checks) {
        const checks = res.checks;
        if (statusBackend) {
          statusBackend.textContent = "Online";
          statusBackend.style.color = "var(--accent)";
        }
        if (statusLlm) {
          statusLlm.textContent = `${checks.llm.status} (${checks.llm.provider})`;
          statusLlm.style.color = checks.llm.status === "Online" ? "var(--accent)" : "#ef4444";
        }
        if (statusTts) {
          statusTts.textContent = `${checks.tts.status} (${checks.tts.backend})`;
          statusTts.style.color = checks.tts.status === "Online" ? "var(--accent)" : "#ef4444";
        }
        if (statusStt) {
          statusStt.textContent = `${checks.stt.status} (${checks.stt.model})`;
          statusStt.style.color = checks.stt.status === "Online" ? "var(--accent)" : "#ef4444";
        }
        if (statusMemory) {
          statusMemory.textContent = checks.memory.status;
          statusMemory.style.color = checks.memory.status === "Online" ? "var(--accent)" : "#ef4444";
        }
      } else {
        throw new Error("offline");
      }
    } catch (err) {
      const offlineList = [statusBackend, statusLlm, statusTts, statusStt, statusMemory];
      offlineList.forEach((el) => {
        if (el) {
          el.textContent = "Offline";
          el.style.color = "#ef4444";
        }
      });
    }
  }
  window.companion.on("python:ready", () => {
    loadConfig();
    updateSystemStatus();
  });
  loadConfig();
  updateSystemStatus();
  setInterval(updateSystemStatus, 4e3);
}
