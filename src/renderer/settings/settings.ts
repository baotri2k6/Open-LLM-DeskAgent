console.log("[settings] settings.ts loaded.");

// ─── Element refs ────────────────────────────────────────────
const llmSelect = document.getElementById("llmSelect") as HTMLSelectElement;
const sttSelect = document.getElementById("sttSelect") as HTMLSelectElement;
const chkTwitchMode = document.getElementById("chkTwitchMode") as HTMLInputElement;
const txtTwitchChannel = document.getElementById("txtTwitchChannel") as HTMLInputElement;
const twitchChannelWrap = document.getElementById("twitchChannelWrap") as HTMLDivElement;
const radModeStreamer = document.getElementById("radModeStreamer") as HTMLInputElement;
const radModeAssistant = document.getElementById("radModeAssistant") as HTMLInputElement;
const saveStatus = document.getElementById("saveStatus") as HTMLDivElement;

// ─── Toast ───────────────────────────────────────────────────
let toastTimer: any = null;
function showStatus(msg: string = "Đã lưu cài đặt"): void {
  if (!saveStatus) return;
  saveStatus.textContent = `✓  ${msg}`;
  saveStatus.classList.add("visible");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => saveStatus.classList.remove("visible"), 2200);
}

// ─── Twitch channel toggle ────────────────────────────────────
function syncTwitchWrap(checked: boolean): void {
  if (twitchChannelWrap) {
    twitchChannelWrap.classList.toggle("visible", checked);
  }
}

// ─── Toggle LLM config containers ─────────────────────────────
function toggleLLMSubConfigs(provider: string): void {
  document.querySelectorAll(".llm-sub-config").forEach((block) => {
    (block as HTMLElement).style.display = "none";
  });
  const activeBlock = document.getElementById(`config-${provider}`);
  if (activeBlock) {
    activeBlock.style.display = "block";
  }
}

// ─── Load config ─────────────────────────────────────────────
async function loadConfig(): Promise<void> {
  if (!(window as any).companion) return;
  try {
    const res = await (window as any).companion.invoke("ai:get-config", {});
    if (!res || res.error) return;

    if (llmSelect) {
      llmSelect.value = res.llm_provider || "ollama";
      toggleLLMSubConfigs(res.llm_provider || "ollama");
    }
    
    // Populate subconfig inputs
    const setVal = (id: string, val: string) => {
      const el = document.getElementById(id) as HTMLInputElement;
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
      if (block) block.style.display = (sttSelect.value === "funasr") ? "block" : "none";
    }
    setVal("sttFunasrModelInput", res.stt_funasr_model || "");
    if (chkTwitchMode) chkTwitchMode.checked = Boolean(res.twitch_mode);
    if (txtTwitchChannel) txtTwitchChannel.value = res.twitch_channel || "";

    syncTwitchWrap(Boolean(res.twitch_mode));

    // Avatar radio
    const avatarVal = res.avatar_model || "assets/live2d/IceGirl/IceGirl.model3.json";
    const avatarRadios = document.querySelectorAll('input[name="avatarModel"]');
    avatarRadios.forEach((r) => {
      (r as HTMLInputElement).checked = (r as HTMLInputElement).value === avatarVal;
    });

    // Avatar scale
    const avatarScaleSelect = document.getElementById("avatarScaleSelect") as HTMLSelectElement;
    if (avatarScaleSelect) {
      avatarScaleSelect.value = res.avatar_scale || "1.0";
    }

    // Mode radio
    if (radModeStreamer && radModeAssistant) {
      if (res.interaction_mode === "streamer") radModeStreamer.checked = true;
      else radModeAssistant.checked = true;
    }

    // Memory toggle checkbox status
    const chkMemoryMode = document.getElementById("chkMemoryMode") as HTMLInputElement;
    if (chkMemoryMode) {
      chkMemoryMode.checked = res.memory !== false;
    }

    loadMemories();
  } catch (err) {
    console.error("[settings] loadConfig error:", err);
  }
}

async function loadMemories(): Promise<void> {
  const memoryList = document.getElementById("memoryList");
  if (!memoryList) return;
  try {
    const res = await (window as any).companion.invoke("ai:get-memories", {});
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
    memories.forEach((mem: any) => {
      const item = document.createElement("div");
      item.className = "memory-item";
      
      const inp = document.createElement("input");
      inp.type = "text";
      inp.className = "memory-text";
      inp.value = mem.text;
      
      const saveEdit = async () => {
        const val = inp.value.trim();
        if (val && val !== mem.text) {
          const updateRes = await (window as any).companion.invoke("ai:update-memory", { id: mem.id, text: val });
          if (updateRes && !updateRes.error && updateRes.success) {
            mem.text = val;
            showStatus("Đã cập nhật ký ức");
          } else {
            inp.value = mem.text;
            showStatus("Lỗi cập nhật ký ức");
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
      delBtn.innerHTML = "🗑️";
      delBtn.title = "Xóa ký ức";
      delBtn.addEventListener("click", async () => {
        if (confirm("Bạn có chắc chắn muốn xóa ký ức này không?")) {
          const delRes = await (window as any).companion.invoke("ai:delete-memory", { id: mem.id });
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
      item.appendChild(inp);
      item.appendChild(actions);
      memoryList.appendChild(item);
    });
  } catch (err) {
    console.error("[settings] loadMemories error:", err);
  }
}

// ─── Wire up controls ─────────────────────────────────────────
if (!(window as any).companion) {
  console.error("[settings] window.companion undefined!");
} else {
  llmSelect?.addEventListener("change", async () => {
    toggleLLMSubConfigs(llmSelect.value);
    const res = await (window as any).companion.invoke("ai:update-config", {
      key: "llm.provider",
      value: llmSelect.value,
    });
    if (res && !res.error) showStatus();
  });

  const bindConfigInput = (elemId: string, configKey: string, label: string) => {
    const elem = document.getElementById(elemId) as HTMLInputElement;
    elem?.addEventListener("change", async () => {
      const res = await (window as any).companion.invoke("ai:update-config", {
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

    const res = await (window as any).companion.invoke("ai:update-config", {
      key: "stt.model",
      value: sttSelect.value,
    });
    if (res && !res.error) showStatus();
  });

  document.querySelectorAll('input[name="avatarModel"]').forEach((radio) => {
    radio.addEventListener("change", async () => {
      const r = radio as HTMLInputElement;
      if (!r.checked) return;
      const res = await (window as any).companion.invoke("ai:update-config", {
        key: "app.avatarModel",
        value: r.value,
      });
      if (res && !res.error) showStatus("Đã đổi nhân vật");
    });
  });

  const avatarScaleSelect = document.getElementById("avatarScaleSelect") as HTMLSelectElement;
  avatarScaleSelect?.addEventListener("change", async () => {
    const res = await (window as any).companion.invoke("ai:update-config", {
      key: "app.avatarScale",
      value: avatarScaleSelect.value,
    });
    if (res && !res.error) showStatus("Đã lưu tỷ lệ nhân vật");
  });

  document.querySelectorAll('input[name="interactionMode"]').forEach((radio) => {
    radio.addEventListener("change", async () => {
      const r = radio as HTMLInputElement;
      if (!r.checked) return;
      const res = await (window as any).companion.invoke("ai:update-config", {
        key: "app.interactionMode",
        value: r.value,
      });
      if (res && !res.error) showStatus("Đã đổi chế độ");
    });
  });

  chkTwitchMode?.addEventListener("change", async () => {
    syncTwitchWrap(chkTwitchMode.checked);
    const res = await (window as any).companion.invoke("ai:update-config", {
      key: "features.twitchMode",
      value: chkTwitchMode.checked,
    });
    if (res && !res.error)
      showStatus(chkTwitchMode.checked ? "Twitch đã bật" : "Twitch đã tắt");
  });

  const saveChannel = async () => {
    const channel = txtTwitchChannel?.value.trim() || "";
    const res = await (window as any).companion.invoke("ai:update-config", {
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

  const chkMemoryMode = document.getElementById("chkMemoryMode") as HTMLInputElement;
  chkMemoryMode?.addEventListener("change", async () => {
    const res = await (window as any).companion.invoke("ai:update-config", {
      key: "features.memory",
      value: chkMemoryMode.checked,
    });
    if (res && !res.error) {
      showStatus(chkMemoryMode.checked ? "Đã bật ghi nhớ dài hạn" : "Đã tắt ghi nhớ dài hạn");
    }
  });

  const txtNewMemory = document.getElementById("txtNewMemory") as HTMLInputElement;
  const btnAddMemory = document.getElementById("btnAddMemory") as HTMLButtonElement;
  const handleAddMemory = async () => {
    const text = txtNewMemory?.value.trim() || "";
    if (!text) return;
    const res = await (window as any).companion.invoke("ai:add-memory", { text });
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

  async function updateSystemStatus(): Promise<void> {
    const statusBackend = document.getElementById("status-backend");
    const statusLlm = document.getElementById("status-llm");
    const statusTts = document.getElementById("status-tts");
    const statusStt = document.getElementById("status-stt");
    const statusMemory = document.getElementById("status-memory");

    try {
      const res = await (window as any).companion.health();
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
      offlineList.forEach(el => {
        if (el) {
          el.textContent = "Offline";
          el.style.color = "#ef4444";
        }
      });
    }
  }

  (window as any).companion.on("python:ready", () => {
    loadConfig();
    updateSystemStatus();
  });
  
  loadConfig();
  updateSystemStatus();
  setInterval(updateSystemStatus, 4000);
}
