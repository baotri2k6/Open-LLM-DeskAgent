import { AssetRegistry } from "../../live2d/asset-registry.js";
console.log("[settings] settings.ts loaded.");
const saveStatus = document.getElementById("saveStatus");
let toastTimer = null;
function showStatus(msg = "\u0110\xE3 l\u01B0u c\xE0i \u0111\u1EB7t") {
  if (!saveStatus) return;
  saveStatus.textContent = `\u2713  ${msg}`;
  saveStatus.classList.add("visible");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => saveStatus.classList.remove("visible"), 2200);
}
const allPanels = document.querySelectorAll(".view-panel");
const settingsIndex = document.getElementById("settingsIndex");
function navigateTo(targetId) {
  allPanels.forEach((p) => p.classList.remove("active"));
  const targetPanel = document.getElementById(targetId);
  if (targetPanel) {
    targetPanel.classList.add("active");
  }
  if (targetId === "pageModels") loadModelSelectorGrid();
  if (targetId === "pageProviders") renderProviders();
  if (targetId === "pageCard") loadDeskagentCards();
  if (targetId === "pageScenes") loadScenesGallery();
}
document.querySelectorAll(".menu-card").forEach((card) => {
  const target = card.dataset.target || "";
  card.addEventListener("click", () => navigateTo(target));
  card.addEventListener("keydown", (e) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      navigateTo(target);
    }
  });
});
document.querySelectorAll(".back-button").forEach((btn) => {
  btn.addEventListener("click", () => {
    allPanels.forEach((p) => p.classList.remove("active"));
    if (settingsIndex) settingsIndex.classList.add("active");
  });
});
document.querySelectorAll(".accordion-hdr").forEach((hdr) => {
  hdr.addEventListener("click", (e) => {
    if (e.target && e.target.closest("button") && e.target.closest("button") !== hdr) {
      return;
    }
    const accordionId = hdr.dataset.accordion || "";
    const accordionBody = document.querySelector(`#${accordionId} .accordion-body`);
    if (!accordionBody) return;
    const isOpen = hdr.getAttribute("aria-expanded") === "true";
    hdr.setAttribute("aria-expanded", String(!isOpen));
    if (isOpen) {
      accordionBody.style.maxHeight = accordionBody.scrollHeight + "px";
      requestAnimationFrame(() => {
        accordionBody.style.maxHeight = "0";
        accordionBody.style.paddingBottom = "0";
      });
      setTimeout(() => {
        accordionBody.style.display = "none";
        accordionBody.style.maxHeight = "";
        accordionBody.style.paddingBottom = "";
      }, 220);
    } else {
      accordionBody.style.display = "block";
      accordionBody.style.overflow = "hidden";
      accordionBody.style.maxHeight = "0";
      requestAnimationFrame(() => {
        accordionBody.style.maxHeight = accordionBody.scrollHeight + "px";
      });
      setTimeout(() => {
        accordionBody.style.maxHeight = "";
        accordionBody.style.overflow = "";
      }, 220);
    }
  });
});
const slScale = document.getElementById("sliderAvatarScale");
const slLbl = document.getElementById("lblAvatarScaleVal");
const slX = document.getElementById("sliderAvatarX");
const slXLbl = document.getElementById("lblAvatarXVal");
const slY = document.getElementById("sliderAvatarY");
const slYLbl = document.getElementById("lblAvatarYVal");
if (slScale && slLbl) {
  setTimeout(async () => {
    try {
      if (window.companion) {
        const cfg = await window.companion.invoke("ai:get-config", {});
        const val = parseFloat(cfg?.app?.avatarScale);
        if (!isNaN(val) && val > 0) {
          slScale.value = Math.round(val * 100).toString();
          slLbl.textContent = val.toFixed(2) + "x";
        }
        if (slX && slXLbl) {
          const posX = parseInt(cfg?.app?.avatarX || "0");
          slX.value = posX.toString();
          slXLbl.textContent = posX + "px";
        }
        if (slY && slYLbl) {
          const posY = parseInt(cfg?.app?.avatarY || "0");
          slY.value = posY.toString();
          slYLbl.textContent = posY + "px";
        }
        const activeModelPath = cfg?.app?.avatarModel || cfg?.avatar_model || "";
        updateModelTypeLayout(activeModelPath);
      }
    } catch (err) {
      console.error("[settings] Init scale error:", err);
    }
  }, 200);
  slScale.addEventListener("input", async () => {
    const val = (parseInt(slScale.value) / 100).toFixed(2);
    slLbl.textContent = val + "x";
    if (window.companion) {
      await window.companion.invoke("ai:update-config", {
        key: "app.avatarScale",
        value: val
      });
    }
  });
  if (slX && slXLbl) {
    slX.addEventListener("input", async () => {
      const val = slX.value;
      slXLbl.textContent = val + "px";
      if (window.companion) {
        await window.companion.invoke("ai:update-config", {
          key: "app.avatarX",
          value: val
        });
      }
    });
  }
  if (slY && slYLbl) {
    slY.addEventListener("input", async () => {
      const val = slY.value;
      slYLbl.textContent = val + "px";
      if (window.companion) {
        await window.companion.invoke("ai:update-config", {
          key: "app.avatarY",
          value: val
        });
      }
    });
  }
}
function showImportResult(type, msg) {
  const el = document.getElementById("importResult");
  if (!el) return;
  el.className = `import-result import-result-${type}`;
  el.textContent = (type === "success" ? "\u2713 " : "\u2717 ") + msg;
  el.style.display = "block";
  clearTimeout(el._timer);
  el._timer = setTimeout(() => {
    el.style.display = "none";
  }, 5e3);
}
function setImportProgress(visible, label = "Extracting...", pct = null) {
  const bar = document.getElementById("importProgress");
  const fill = document.getElementById("importProgressFill");
  const lbl = document.getElementById("importProgressLabel");
  if (!bar) return;
  bar.style.display = visible ? "block" : "none";
  if (lbl) lbl.textContent = label;
  if (fill) fill.style.width = (pct !== null ? pct : 0) + "%";
}
async function importZipFile(filePath) {
  if (!window.companion) {
    showImportResult("error", "Not connected to desktop backend.");
    return;
  }
  try {
    setImportProgress(true, "Scanning ZIP structure...", 10);
    const scanRes = await window.companion.invoke("avatar:scan-zip", { path: filePath });
    setImportProgress(false);
    if (scanRes && scanRes.success && scanRes.files && scanRes.files.length > 0) {
      if (scanRes.files.length === 1) {
        await executeImport(filePath, scanRes.files[0]);
      } else {
        showZipConfigModal(filePath, scanRes.files);
      }
    } else if (scanRes && !scanRes.success) {
      throw new Error(scanRes.error || "Failed to scan ZIP archive.");
    } else {
      await executeImport(filePath);
    }
  } catch (err) {
    setImportProgress(false);
    showImportResult("error", err.message);
  }
}
async function executeImport(filePath, selectedConfig) {
  setImportProgress(true, "Extracting and registering model...", 30);
  let pct = 30;
  const tick = setInterval(() => {
    pct = Math.min(pct + 8, 85);
    const fill = document.getElementById("importProgressFill");
    if (fill) fill.style.width = pct + "%";
  }, 400);
  try {
    const res = await window.companion.invoke("avatar:import-zip", { path: filePath, selectedConfig });
    clearInterval(tick);
    if (res && res.success) {
      setImportProgress(true, "Done!", 100);
      showImportResult("success", `"${res.model.name}" imported successfully!`);
      setTimeout(() => setImportProgress(false), 1200);
      await AssetRegistry.load(true);
      loadModelSelectorGrid();
      window.companion.invoke("ai:broadcast", {
        event: "avatar:registry-updated",
        data: res.model
      }).catch(() => null);
    } else {
      throw new Error(res?.error || "Unknown import error");
    }
  } catch (err) {
    clearInterval(tick);
    setImportProgress(false);
    showImportResult("error", err.message);
  }
}
function showZipConfigModal(filePath, files) {
  const modal = document.getElementById("zipConfigModal");
  const list = document.getElementById("zipConfigList");
  if (!modal || !list) return;
  list.innerHTML = "";
  files.forEach((file) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "pick-btn";
    btn.style.width = "100%";
    btn.style.textAlign = "left";
    btn.style.justifyContent = "flex-start";
    btn.style.padding = "10px 14px";
    btn.style.height = "auto";
    btn.style.background = "rgba(255,255,255,0.06)";
    btn.style.color = "#fff";
    btn.style.border = "1px solid rgba(255,255,255,0.1)";
    btn.style.borderRadius = "8px";
    btn.style.cursor = "pointer";
    btn.style.transition = "background 0.2s";
    btn.textContent = file;
    btn.addEventListener("mouseover", () => {
      btn.style.background = "rgba(255,255,255,0.12)";
    });
    btn.addEventListener("mouseout", () => {
      btn.style.background = "rgba(255,255,255,0.06)";
    });
    btn.addEventListener("click", async () => {
      modal.classList.remove("active");
      await executeImport(filePath, file);
    });
    list.appendChild(btn);
  });
  modal.classList.add("active");
}
document.getElementById("zipConfigBtnClose")?.addEventListener("click", () => {
  document.getElementById("zipConfigModal")?.classList.remove("active");
});
document.getElementById("btnBrowseZip")?.addEventListener("click", async () => {
  if (!window.companion) {
    showImportResult("error", "Not connected.");
    return;
  }
  const fp = await window.companion.showOpenDialog({
    title: "Select ZIP",
    filters: [{ name: "ZIP Archives", extensions: ["zip"] }]
  });
  if (fp) await importZipFile(fp);
});
document.getElementById("btnSelectModel")?.addEventListener("click", () => {
  const modal = document.getElementById("modelSelectorModal");
  if (modal) {
    modal.classList.add("active");
    loadModelSelectorGrid();
  }
});
document.getElementById("modalBtnClose")?.addEventListener("click", () => {
  document.getElementById("modelSelectorModal")?.classList.remove("active");
});
document.getElementById("modalBtnImport")?.addEventListener("click", async () => {
  if (!window.companion) {
    showImportResult("error", "Not connected.");
    return;
  }
  const fp = await window.companion.showOpenDialog({
    title: "Select model",
    filters: [
      { name: "Model files", extensions: ["zip", "vrm"] },
      { name: "All files", extensions: ["*"] }
    ]
  });
  if (fp) {
    await importZipFile(fp);
    loadModelSelectorGrid();
  }
});
document.getElementById("btnRefreshModels")?.addEventListener("click", () => {
  loadModelSelectorGrid();
});
document.addEventListener("dragover", (e) => {
  const panel = document.getElementById("pageModels");
  if (panel && panel.classList.contains("active")) {
    e.preventDefault();
    document.getElementById("modelsDropOverlay")?.classList.add("visible");
  }
});
document.addEventListener("dragleave", (e) => {
  const panel = document.getElementById("pageModels");
  if (panel && !panel.contains(e.relatedTarget)) {
    document.getElementById("modelsDropOverlay")?.classList.remove("visible");
  }
});
document.addEventListener("drop", async (e) => {
  const panel = document.getElementById("pageModels");
  if (!panel || !panel.classList.contains("active")) return;
  e.preventDefault();
  document.getElementById("modelsDropOverlay")?.classList.remove("visible");
  const file = e.dataTransfer?.files?.[0];
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".zip")) {
    showImportResult("error", "Please drop a .zip file.");
    return;
  }
  await importZipFile(file.path);
});
async function loadModelSelectorGrid() {
  const grid = document.getElementById("modalSelectorGrid");
  if (!grid) return;
  grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-3); padding: 30px;">Loading models...</div>';
  try {
    let activePath = "assets/live2d/IceGirl/IceGirl.model3.json";
    if (window.companion) {
      const resConfig = await window.companion.invoke("ai:get-config", {});
      activePath = resConfig?.avatar_model || "assets/live2d/IceGirl/IceGirl.model3.json";
    }
    const res = await fetch("../../assets/live2d/models.json?t=" + Date.now());
    const data = await res.json();
    const models = data.models || [];
    if (!models.length) {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-3); padding: 30px;">No models installed.</div>';
      return;
    }
    grid.innerHTML = "";
    const emojis = { icegirl: "\u{1F9CA}", hiyori: "\u{1F338}", mao: "\u{1F431}", huohuo: "\u{1F98B}" };
    models.forEach((m) => {
      const isActive = m.path === activePath;
      const card = document.createElement("div");
      card.className = "selector-card" + (isActive ? " active" : "");
      const emoji = emojis[m.id] || "\u2728";
      const isVrm = m.path.toLowerCase().endsWith(".vrm") || m.id.toLowerCase().includes("vrm");
      const typeLabel = isVrm ? "VRM" : "Live2D";
      const typeIcon = isVrm ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/></svg>` : `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="21" y1="9" x2="3" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>`;
      card.innerHTML = `
        <div class="selector-card-thumb-wrap">
          <button class="selector-thumb-action" type="button" title="Info">\u2022\u2022\u2022</button>
          ${m.thumbnail ? `<img src="../../${m.thumbnail}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/><span class="mre" style="display:none">${emoji}</span>` : `<span class="mre" style="font-size: 48px;">${emoji}</span>`}
        </div>
        <div class="selector-card-info">
          <div class="selector-title-row">
            <span class="selector-name" title="${m.name}">${m.name}</span>
            <button class="selector-btn-edit" type="button" title="Rename">\u270F</button>
            ${isActive ? "" : '<button class="selector-btn-delete" type="button" title="Delete">\u{1F5D1}\uFE0F</button>'}
          </div>
          <span class="selector-badge">
            ${typeIcon}
            ${typeLabel}
          </span>
          <button class="pick-btn" type="button">
            ${isActive ? '<span class="pick-btn-active-text">Picked</span>' : "Pick"}
          </button>
        </div>
      `;
      card.querySelector(".pick-btn")?.addEventListener("click", async () => {
        if (isActive) return;
        if (window.companion) {
          const resUpdate = await window.companion.invoke("ai:update-config", {
            key: "app.avatarModel",
            value: m.path
          });
          if (resUpdate && !resUpdate.error) {
            showStatus(`Changed character to ${m.name}`);
            updateModelTypeLayout(m.path);
            loadModelSelectorGrid();
          }
        }
      });
      card.querySelector(".selector-btn-edit")?.addEventListener("click", async (e) => {
        e.stopPropagation();
        const newName = prompt(`Rename "${m.name}" to:`, m.name);
        if (newName && newName.trim() && newName.trim() !== m.name) {
          showStatus(`Renamed to ${newName}`);
        }
      });
      card.querySelector(".selector-btn-delete")?.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Are you sure you want to delete "${m.name}"?
(This action cannot be undone)`)) return;
        if (window.companion) {
          const r = await window.companion.deleteCharacter(m.id);
          if (r?.success) {
            card.remove();
            showStatus(`Deleted "${m.name}"`);
            loadModelSelectorGrid();
          } else {
            showStatus(r?.error || "Failed to delete.");
          }
        }
      });
      card.querySelector(".selector-thumb-action")?.addEventListener("click", (e) => {
        e.stopPropagation();
        alert(`Model details:

ID: ${m.id}
Name: ${m.name}
Path: ${m.path}
Description: ${m.description || "No description"}`);
      });
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-3); padding: 30px;">Error loading: ${err.message}</div>`;
  }
}
const PROVIDERS = [
  // CHAT PROVIDERS
  { id: "official", name: "Official Provider", desc: "Official AI provider by AIRI.", tags: ["RECOMMENDED", "PAID", "CLOUD"], icon: "\u2B50", category: "chat" },
  { id: "openrouter", name: "OpenRouter", desc: "openrouter.ai", tags: ["PAID", "CLOUD"], icon: "\u25C0", category: "chat" },
  { id: "aihubmix", name: "AIHubMix", desc: "https://aihubmix.com (10% off)", tags: ["PAID", "CLOUD"], icon: "\u{1F310}", category: "chat" },
  { id: "azure", name: "Azure OpenAI", desc: "Azure OpenAI API", tags: ["PAID", "CLOUD"], icon: "A", category: "chat" },
  { id: "ollama", name: "Ollama", desc: "ollama.ai", tags: ["FREE", "LOCAL"], icon: "\u{1F999}", category: "chat" },
  { id: "lmstudio", name: "LM Studio", desc: "lmstudio.ai", tags: ["FREE", "LOCAL"], icon: "\u2261", category: "chat" },
  { id: "deepseek", name: "DeepSeek", desc: "deepseek.com", tags: ["PAID", "CLOUD"], icon: "\u{1F40B}", category: "chat" },
  { id: "openai-compat", name: "OpenAI Compatible", desc: "OpenAI Compatible", tags: ["CLOUD"], icon: "\u2699", category: "chat" },
  { id: "xiaomi", name: "Xiaomi MiMo", desc: "api.xiaomimimo.com", tags: ["PAID", "CLOUD"], icon: "M", category: "chat" },
  { id: "openai", name: "OpenAI", desc: "openai.com", tags: ["PAID", "CLOUD"], icon: "\u25CE", category: "chat" },
  { id: "anthropic", name: "Anthropic", desc: "anthropic.com", tags: ["PAID", "CLOUD"], icon: "\u2B21", category: "chat" },
  { id: "gemini", name: "Google Gemini", desc: "ai.google.dev", tags: ["PAID", "CLOUD"], icon: "\u2726", category: "chat" },
  // VISION PROVIDERS (Screenshot 1)
  { id: "official-vision", name: "Official Provider", desc: "Official AI provider by deskagent.", tags: ["RECOMMENDED", "PAID", "CLOUD"], icon: "\u2B50", category: "vision" },
  { id: "openrouter-vision", name: "OpenRouter", desc: "openrouter.ai", tags: ["PAID", "CLOUD"], icon: "\u25C0", category: "vision" },
  { id: "aihubmix-vision", name: "AIHubMix", desc: "https://aihubmix.com (10% off)", tags: ["PAID", "CLOUD"], icon: "\u{1F310}", category: "vision" },
  { id: "azure-vision", name: "Azure OpenAI", desc: "Azure OpenAI API", tags: ["PAID", "CLOUD"], icon: "A", category: "vision" },
  { id: "ollama-vision", name: "Ollama", desc: "ollama.ai", tags: ["FREE", "LOCAL"], icon: "\u{1F999}", category: "vision" },
  { id: "lmstudio-vision", name: "LM Studio", desc: "lmstudio.ai", tags: ["FREE", "LOCAL"], icon: "\u2261", category: "vision" },
  // SPEECH PROVIDERS (Screenshot 2)
  { id: "official-speech", name: "Official Speech Provider", desc: "Official text-to-speech provider by AIRI.", tags: ["RECOMMENDED", "PAID", "CLOUD"], icon: "\u2B50", category: "speech" },
  { id: "official-streaming-speech", name: "Official Streaming Speech Provider", desc: "Official low-latency text-to-speech provider by AIRI (bidirectional WebSocket).", tags: ["RECOMMENDED", "PAID", "CLOUD"], icon: "\u2B50", category: "speech" },
  { id: "app-local-speech", name: "App (Local)", desc: "https://github.com/moeru-ai/xsai-transformers", tags: ["FREE", "LOCAL"], icon: "\u2261", category: "speech" },
  { id: "openai-speech", name: "OpenAI", desc: "openai.com", tags: ["PAID", "CLOUD"], icon: "\u25CE", category: "speech" },
  { id: "openai-compat-speech", name: "OpenAI Compatible", desc: "OpenAI Compatible", tags: ["CLOUD"], icon: "\u2699", category: "speech" },
  { id: "elevenlabs", name: "ElevenLabs", desc: "elevenlabs.io", tags: ["PAID", "CLOUD"], icon: "\u2B21", category: "speech" },
  // TRANSCRIPTION PROVIDERS (Screenshot 3)
  { id: "official-transcription", name: "Official Transcription Provider", desc: "Official speech-to-text provider by AIRI.", tags: ["CLOUD"], icon: "\u2B50", category: "transcription" },
  { id: "app-local-transcription", name: "App (Local)", desc: "https://github.com/moeru-ai/xsai-transformers", tags: ["FREE", "LOCAL"], icon: "\u2261", category: "transcription" },
  { id: "openai-transcription", name: "OpenAI", desc: "openai.com", tags: ["PAID", "CLOUD"], icon: "\u25CE", category: "transcription" },
  { id: "openai-compat-transcription", name: "OpenAI Compatible", desc: "OpenAI Compatible", tags: ["CLOUD"], icon: "\u2699", category: "transcription" },
  { id: "aliyun-nls", name: "Aliyun NLS", desc: "Aliyun NLS", tags: ["PAID", "CLOUD"], icon: "[-]", category: "transcription" },
  { id: "comet-api", name: "Comet API", desc: "CometAPI.com", tags: ["PAID", "CLOUD"], icon: "\u{1FA90}", category: "transcription" },
  // ARTISTRY PROVIDERS (Screenshot 4)
  { id: "comfyui", name: "ComfyUI", desc: "Local image generation runner.", tags: ["RECOMMENDED", "FREE", "LOCAL"], icon: "\u{1F3A8}", category: "artistry" },
  { id: "replicate", name: "Replicate", desc: "Cloud-based model inference service.", tags: ["PAID", "CLOUD"], icon: "\u2B21", category: "artistry" },
  { id: "nano-banana", name: "Nano Banana", desc: "Google AI Studio Image Preview.", tags: ["FREE", "CLOUD"], icon: "\u{1F34C}", category: "artistry" }
];
const HEADERS = {
  chat: {
    icon: "\u{1F4AC}",
    title: "Chat",
    desc: "Chat model providers for thinking, and behaving."
  },
  vision: {
    icon: "\u{1F441}\uFE0F",
    title: "Vision",
    desc: "Vision model providers for image understanding."
  },
  speech: {
    icon: "\u{1F5E3}\uFE0F",
    title: "Speech",
    desc: "Speech (text-to-speech) model providers. e.g. ElevenLabs, Azure Speech."
  },
  transcription: {
    icon: "\u{1F399}\uFE0F",
    title: "Transcription",
    desc: "Transcription (speech-to-text) model providers. e.g. Whisper.cpp, OpenAI, Azure Speech"
  },
  artistry: {
    icon: "\u{1F3A8}",
    title: "Artistry",
    desc: "Image generation and design model providers. e.g. ComfyUI, Replicate."
  }
};
let activeProviderTab = "chat";
let activePricingFilter = "all";
let activeDeploymentFilter = "all";
let providersInitialized = false;
const PROVIDER_CONFIG_MAP = {
  "openai": { key: "llm.openai_api_key" },
  "gemini": { key: "llm.gemini_api_key" },
  "deepseek": { key: "llm.deepseek_api_key", url: "llm.deepseek_base_url", urlPlaceholder: "https://api.deepseek.com/v1" },
  "glm": { key: "llm.glm_api_key", url: "llm.glm_base_url", urlPlaceholder: "https://open.bigmodel.cn/api/paas/v4" },
  "qwen": { key: "llm.qwen_api_key", url: "llm.qwen_base_url", urlPlaceholder: "https://dashscope.aliyuncs.com/compatible-mode/v1" },
  // Vision
  "gemini-vision": { key: "llm.gemini_api_key" },
  "openai-vision": { key: "llm.openai_api_key" },
  // Speech
  "fish-audio": { key: "tts.fish_audio_api_key" },
  "openai-speech": { key: "llm.openai_api_key" },
  // Transcription
  "openai-transcription": { key: "llm.openai_api_key" },
  // Azure / OpenAI compatible / local
  "azure": { key: "llm.openai_compatible_api_key", url: "llm.openai_compatible_base_url", urlPlaceholder: "https://.openai.azure.com/" },
  "openrouter": { key: "llm.openai_compatible_api_key", url: "llm.openai_compatible_base_url", urlPlaceholder: "https://openrouter.ai/api/v1" },
  "aihubmix": { key: "llm.openai_compatible_api_key", url: "llm.openai_compatible_base_url", urlPlaceholder: "https://aihubmix.com/v1" },
  "openai-compat": { key: "llm.openai_compatible_api_key", url: "llm.openai_compatible_base_url", urlPlaceholder: "https://api.your-provider.com/v1" },
  // Local
  "ollama": { url: "llm.host", urlPlaceholder: "http://localhost:11434", urlLabel: "Host URL" },
  "lmstudio": { url: "llm.host", urlPlaceholder: "http://localhost:1234/v1", urlLabel: "Host URL" },
  "ollama-vision": { url: "llm.host", urlPlaceholder: "http://localhost:11434", urlLabel: "Host URL" }
};
let currentDetailProviderId = "";
let providerDetailInitialized = false;
function validateProviderConfig(providerId, apiKeyValue) {
  const banner = document.getElementById("validationBanner");
  const errorText = document.getElementById("validationErrorText");
  if (!banner || !errorText) return;
  const mapping = PROVIDER_CONFIG_MAP[providerId];
  if (mapping && mapping.key && !apiKeyValue) {
    errorText.textContent = "API key is required.";
    banner.style.display = "block";
  } else {
    banner.style.display = "none";
  }
}
async function openProviderDetail(providerId) {
  currentDetailProviderId = providerId;
  const p = PROVIDERS.find((item) => item.id === providerId);
  if (!p) return;
  const titleEl = document.getElementById("lblProviderDetailTitle");
  const keyDescEl = document.getElementById("lblApiKeyDesc");
  if (titleEl) titleEl.textContent = p.name;
  if (keyDescEl) keyDescEl.textContent = `API Key for ${p.name}`;
  let config = {};
  if (window.companion) {
    try {
      config = await window.companion.invoke("ai:get-config", {});
    } catch (err) {
      console.error(err);
    }
  }
  const mapping = PROVIDER_CONFIG_MAP[providerId];
  const basicCard = document.getElementById("providerBasicCard");
  const basicTitle = document.getElementById("lblApiKeyTitle");
  const keyInput = document.getElementById("txtProviderApiKey");
  if (mapping && mapping.key) {
    if (basicCard) basicCard.style.display = "block";
    if (basicTitle) basicTitle.style.display = "block";
    let savedKey = "";
    const k = mapping.key;
    if (k === "llm.gemini_api_key") savedKey = config?.gemini_key || "";
    else if (k === "llm.openai_api_key") savedKey = config?.openai_key || "";
    else if (k === "llm.deepseek_api_key") savedKey = config?.deepseek_key || "";
    else if (k === "llm.glm_api_key") savedKey = config?.glm_key || "";
    else if (k === "llm.qwen_api_key") savedKey = config?.qwen_key || "";
    else if (k === "llm.openai_compatible_api_key") savedKey = config?.openai_compatible_key || "";
    else if (k === "tts.fish_audio_api_key") savedKey = config?.fish_api_key || "";
    if (keyInput) {
      keyInput.value = savedKey;
      keyInput.type = "password";
    }
    validateProviderConfig(providerId, savedKey);
  } else {
    if (basicCard) basicCard.style.display = "none";
    const banner = document.getElementById("validationBanner");
    if (banner) banner.style.display = "none";
  }
  const advancedCard = document.getElementById("accordionAdvanced");
  const urlLabel = document.getElementById("lblBaseUrlTitle");
  const urlDesc = document.getElementById("lblBaseUrlDesc");
  const urlInput = document.getElementById("txtProviderBaseUrl");
  if (mapping && (mapping.url || providerId === "openai")) {
    if (advancedCard) advancedCard.style.display = "block";
    if (urlLabel) urlLabel.textContent = mapping.urlLabel || "Base URL";
    if (urlDesc) urlDesc.textContent = mapping.urlLabel ? `Custom host server address` : `Custom base URL (optional)`;
    if (urlInput) {
      urlInput.placeholder = mapping.urlPlaceholder || "https://api.openai.com/v1";
      let savedUrl = "";
      if (providerId === "openai") {
        savedUrl = config?.openai_base_url || "https://api.openai.com/v1";
      } else if (mapping.url === "llm.deepseek_base_url") {
        savedUrl = config?.deepseek_base_url || "";
      } else if (mapping.url === "llm.glm_base_url") {
        savedUrl = config?.glm_base_url || "";
      } else if (mapping.url === "llm.qwen_base_url") {
        savedUrl = config?.qwen_base_url || "";
      } else if (mapping.url === "llm.openai_compatible_base_url") {
        savedUrl = config?.openai_compatible_base_url || "";
      } else if (mapping.url === "llm.host") {
        savedUrl = config?.host || "";
      }
      urlInput.value = savedUrl;
    }
  } else {
    if (advancedCard) advancedCard.style.display = "none";
  }
  navigateTo("pageProviderDetail");
  if (providerDetailInitialized) return;
  providerDetailInitialized = true;
  document.getElementById("btnBackToProviders")?.addEventListener("click", () => {
    navigateTo("pageProviders");
    renderProviders();
  });
  document.getElementById("btnToggleProviderKeyVis")?.addEventListener("click", () => {
    if (keyInput) {
      const isPass = keyInput.type === "password";
      keyInput.type = isPass ? "text" : "password";
      const btn = document.getElementById("btnToggleProviderKeyVis");
      if (btn) btn.textContent = isPass ? "\u{1F512}" : "\u{1F441}";
    }
  });
  keyInput?.addEventListener("change", async () => {
    if (!currentDetailProviderId || !window.companion) return;
    const mapping2 = PROVIDER_CONFIG_MAP[currentDetailProviderId];
    if (mapping2 && mapping2.key) {
      const val = keyInput.value.trim();
      await window.companion.invoke("ai:update-config", {
        key: mapping2.key,
        value: val
      });
      showStatus("API credential saved");
      validateProviderConfig(currentDetailProviderId, val);
    }
  });
  urlInput?.addEventListener("change", async () => {
    if (!currentDetailProviderId || !window.companion) return;
    const mapping2 = PROVIDER_CONFIG_MAP[currentDetailProviderId];
    const val = urlInput.value.trim();
    let configKey = "";
    if (currentDetailProviderId === "openai") {
      configKey = "llm.openai_base_url";
    } else if (mapping2 && mapping2.url) {
      configKey = mapping2.url;
    }
    if (configKey) {
      await window.companion.invoke("ai:update-config", {
        key: configKey,
        value: val
      });
      showStatus("Base URL updated");
    }
  });
  document.getElementById("btnContinueAnyway")?.addEventListener("click", () => {
    const banner = document.getElementById("validationBanner");
    if (banner) banner.style.display = "none";
  });
}
function renderProviders() {
  const grid = document.getElementById("providerGrid");
  if (!grid) return;
  const headerEl = document.getElementById("providerHeader");
  if (headerEl) {
    const info = HEADERS[activeProviderTab];
    headerEl.innerHTML = `
      <div style="display: flex; align-items: center; gap: 10px; margin-top: 14px; margin-bottom: 6px; font-family: var(--font);">
        <span style="font-size: 26px; line-height: 1;">${info.icon}</span>
        <h2 style="font-size: 22px; font-weight: 700; margin: 0; color: var(--text-1);">${info.title}</h2>
      </div>
      <span style="font-size: 12px; color: var(--text-3); font-weight: 500; display: block; margin-left: 2px; font-family: var(--font);">${info.desc}</span>
    `;
  }
  const loader = document.getElementById("providerLoadingState");
  if (loader) loader.style.display = "inline";
  grid.style.opacity = "0.5";
  setTimeout(async () => {
    grid.innerHTML = "";
    grid.style.opacity = "1";
    if (loader) loader.style.display = "none";
    const filtered = PROVIDERS.filter((p) => {
      if (p.category !== activeProviderTab) return false;
      if (activePricingFilter !== "all") {
        const isFree = p.tags.includes("FREE");
        const isPaid = p.tags.includes("PAID");
        if (activePricingFilter === "free" && !isFree) return false;
        if (activePricingFilter === "paid" && !isPaid) return false;
      }
      if (activeDeploymentFilter !== "all") {
        const isLocal = p.tags.includes("LOCAL");
        const isCloud = p.tags.includes("CLOUD");
        if (activeDeploymentFilter === "local" && !isLocal) return false;
        if (activeDeploymentFilter === "cloud" && !isCloud) return false;
      }
      return true;
    });
    if (filtered.length === 0) {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-3); padding: 30px; font-size: 13px;">No providers match selected filters.</div>';
      return;
    }
    let activeId = "";
    try {
      if (window.companion) {
        const cfg = await window.companion.invoke("ai:get-config", {});
        if (activeProviderTab === "chat") activeId = cfg?.llm_provider || "ollama";
        else if (activeProviderTab === "speech") activeId = cfg?.tts_backend || "edge";
      }
    } catch (_) {
    }
    filtered.forEach((p) => {
      const card = document.createElement("div");
      card.className = "provider-card";
      card.dataset.id = p.id;
      const tagsHtml = p.tags.map((t) => `<span class="provider-tag provider-tag-${t.toLowerCase()}">${t}</span>`).join("");
      const isSelected = activeId === p.id;
      card.innerHTML = `
        <div class="provider-card-top">
          <div class="provider-card-info">
            <span class="provider-card-name">${p.name}</span>
            <span class="provider-card-desc">${p.desc}</span>
          </div>
          <div class="provider-card-logo">${p.icon}</div>
        </div>
        ${p.tags.length ? `<div class="provider-tags">${tagsHtml}</div>` : ""}
        <label class="provider-radio">
          <input type="radio" name="provider_${activeProviderTab}" value="${p.id}" ${isSelected ? "checked" : ""}/>
          <span class="radio-dot"></span>
        </label>
      `;
      card.addEventListener("click", () => {
        const radio2 = card.querySelector('input[type="radio"]');
        if (radio2 && !radio2.checked) {
          radio2.checked = true;
          radio2.dispatchEvent(new Event("change"));
        }
        openProviderDetail(p.id);
      });
      const radio = card.querySelector('input[type="radio"]');
      radio?.addEventListener("change", async () => {
        if (radio.checked && window.companion) {
          let configKey = "llm.provider";
          if (activeProviderTab === "speech") configKey = "tts.backend";
          const res = await window.companion.invoke("ai:update-config", {
            key: configKey,
            value: p.id
          });
          if (res && !res.error) showStatus(`Provider changed to ${p.name}`);
        }
      });
      grid.appendChild(card);
    });
  }, 200);
  if (providersInitialized) return;
  providersInitialized = true;
  document.querySelectorAll(".provider-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".provider-tab-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeProviderTab = btn.dataset.tab;
      renderProviders();
    });
  });
  document.querySelectorAll("#filterPricing .filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#filterPricing .filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activePricingFilter = btn.dataset.val;
      renderProviders();
    });
  });
  document.querySelectorAll("#filterDeployment .filter-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll("#filterDeployment .filter-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      activeDeploymentFilter = btn.dataset.val;
      renderProviders();
    });
  });
}
function loadAiriCards() {
  const container = document.getElementById("airiExistingCards");
  if (!container || container.children.length > 0) return;
  container.innerHTML = "";
  const personas = [
    {
      name: "ReLU",
      desc: "(from Neko Ayaka) Good morning! You are finally awake. Your name is AIRI, pronounced as /\u02C8e\u026Atri\u02D0/, it the word A.I. companion. Your creator is Neko Ayaka.",
      version: "v1.0.0",
      active: true
    }
  ];
  personas.forEach((p) => {
    const card = document.createElement("div");
    card.className = "deskagent-persona-card" + (p.active ? " deskagent-persona-card-active" : "");
    card.innerHTML = `
      <div class="apc-header">
        <span class="apc-name">${p.name}</span>
        <div class="apc-actions">
          <button class="apc-btn-edit" title="Edit">\u270F</button>
          ${p.active ? '<span class="apc-active-dot"></span>' : ""}
        </div>
      </div>
      <p class="apc-desc">${p.desc}</p>
      <div class="apc-footer">
        <span class="apc-version">${p.version}</span>
        <div class="apc-badges">
          <span class="apc-badge">\u{1F4C4} default</span>
          <span class="apc-badge">\u{1F50A} default</span>
        </div>
      </div>
      ${p.active ? '<div class="apc-bottom-active"><span class="apc-active-check">\u2713</span></div>' : ""}
    `;
    container.appendChild(card);
  });
}
document.getElementById("btnOpenDataFolder")?.addEventListener("click", () => {
  if (window.companion) {
    window.companion.invoke("system:open-data-folder", {}).catch(() => {
    });
  }
});
document.getElementById("btnMoveToCenter")?.addEventListener("click", async () => {
  if (window.companion) {
    try {
      const bounds = await window.companion.invoke("pet:get-bounds");
      if (bounds && bounds.workArea) {
        const { x, y, width: sw, height: sh } = bounds.workArea;
        const targetX = x + (sw - bounds.width) / 2;
        const targetY = y + (sh - bounds.height) / 2;
        await window.companion.invoke("pet:move-to", { x: targetX, y: targetY });
      } else {
        await window.companion.invoke("pet:move-to", { x: 600, y: 400 });
      }
    } catch (e) {
      console.error("Failed to move avatar to center:", e);
    }
  }
});
async function loadScenesGallery() {
  const gallery = document.getElementById("scenesGallery");
  if (!gallery) return;
  gallery.innerHTML = "";
  if (!window.companion) {
    gallery.innerHTML = '<div class="scene-empty">Not connected to companion.</div>';
    return;
  }
  try {
    const list = await window.companion.invoke("avatar:get-backgrounds");
    const cfg = await window.companion.invoke("ai:get-config");
    const activeBg = cfg?.background_image || "";
    if (!list || list.length === 0) {
      gallery.innerHTML = '<div class="scene-empty">No backgrounds uploaded yet.</div>';
      return;
    }
    list.forEach((bgPath) => {
      const thumb = document.createElement("div");
      const isActive = activeBg === bgPath;
      thumb.className = "scene-thumb" + (isActive ? " scene-thumb-active" : "");
      const fileName = bgPath.split(/[\\/]/).pop() || "";
      thumb.innerHTML = `
        <img src="../../${bgPath}" alt="Background" />
        <span class="scene-thumb-label">${fileName}</span>
        ${isActive ? '<div class="scene-active-check">\u2713</div>' : ""}
      `;
      thumb.addEventListener("click", async () => {
        const targetValue = isActive ? "" : bgPath;
        await window.companion.invoke("ai:update-config", {
          key: "app.backgroundImage",
          value: targetValue
        });
        showStatus(isActive ? "Background cleared" : "Background set successfully");
        loadScenesGallery();
      });
      gallery.appendChild(thumb);
    });
  } catch (err) {
    console.error("Failed to load scenes gallery:", err);
    gallery.innerHTML = '<div class="scene-empty">Failed to load gallery images.</div>';
  }
}
document.getElementById("btnUploadBackground")?.addEventListener("click", async () => {
  if (!window.companion) return;
  try {
    const fp = await window.companion.showOpenDialog({
      title: "Select background image",
      filters: [{ name: "Images", extensions: ["jpg", "jpeg", "png", "gif", "webp"] }]
    });
    if (!fp) return;
    const res = await window.companion.invoke("avatar:upload-background", { filePath: fp });
    if (res && res.success) {
      await window.companion.invoke("ai:update-config", {
        key: "app.backgroundImage",
        value: res.path
      });
      showStatus("Background uploaded and applied!");
      loadScenesGallery();
    } else {
      showStatus(res?.error || "Failed to copy background image");
    }
  } catch (err) {
    console.error("Upload background error:", err);
    showStatus(err.message);
  }
});
async function updateSystemStatus() {
  const statusBackend = document.getElementById("status-backend");
  const statusLlm = document.getElementById("status-llm");
  const statusTts = document.getElementById("status-tts");
  const statusStt = document.getElementById("status-stt");
  const statusMemory = document.getElementById("status-memory");
  try {
    if (!window.companion) return;
    const res = await window.companion.health();
    if (res && res.status === "ok" && res.checks) {
      const checks = res.checks;
      if (statusBackend) {
        statusBackend.textContent = "Online";
        statusBackend.style.color = "var(--accent)";
      }
      if (statusLlm) {
        statusLlm.textContent = `${checks.llm.status} (${checks.llm.provider})`;
        statusLlm.style.color = checks.llm.status === "Online" ? "var(--accent)" : "var(--danger)";
      }
      if (statusTts) {
        statusTts.textContent = `${checks.tts.status} (${checks.tts.backend})`;
        statusTts.style.color = checks.tts.status === "Online" ? "var(--accent)" : "var(--danger)";
      }
      if (statusStt) {
        statusStt.textContent = `${checks.stt.status} (${checks.stt.model})`;
        statusStt.style.color = checks.stt.status === "Online" ? "var(--accent)" : "var(--danger)";
      }
      if (statusMemory) {
        statusMemory.textContent = checks.memory.status;
        statusMemory.style.color = checks.memory.status === "Online" ? "var(--accent)" : "var(--danger)";
      }
    } else {
      throw new Error("offline");
    }
  } catch (err) {
    const offlineList = [statusBackend, statusLlm, statusTts, statusStt, statusMemory];
    offlineList.forEach((el) => {
      if (el) {
        el.textContent = "Offline";
        el.style.color = "var(--danger)";
      }
    });
  }
}
if (window.companion) {
  window.companion.on("python:ready", () => {
    updateSystemStatus();
  });
  updateSystemStatus();
  setInterval(updateSystemStatus, 4e3);
  setTimeout(async () => {
    try {
      if (window.companion) {
        const cfg = await window.companion.invoke("ai:get-config", {});
        const wsAddr = cfg?.["connection.ws_address"] || "ws://localhost:6121/ws";
        const wsInput = document.getElementById("txtWsAddress");
        if (wsInput) wsInput.value = wsAddr;
        const secureWss = cfg?.["connection.secure_wss"] === true || cfg?.["connection.secure_wss"] === "true";
        const secureInput = document.getElementById("chkSecureWs");
        if (secureInput) secureInput.checked = secureWss;
        const netExpose = cfg?.["connection.network_expose"] || "local";
        const segBtns = document.querySelectorAll("#networkExposure .segment-btn");
        segBtns.forEach((btn) => {
          if (btn.dataset.value === netExpose) {
            segBtns.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
          }
        });
        const authToken = cfg?.["connection.auth_token"] || "q7x9w2v8k4m3n5p6r8t2y1u9i8o7p6a5";
        const tokenInput = document.getElementById("txtAuthToken");
        if (tokenInput) tokenInput.value = authToken;
      }
    } catch (err) {
      console.error("[settings] Init connection config error:", err);
    }
  }, 250);
  const txtAuthToken = document.getElementById("txtAuthToken");
  const btnToggleTokenVis = document.getElementById("btnToggleTokenVis");
  if (txtAuthToken && btnToggleTokenVis) {
    btnToggleTokenVis.addEventListener("click", () => {
      const isPass = txtAuthToken.type === "password";
      txtAuthToken.type = isPass ? "text" : "password";
      btnToggleTokenVis.setAttribute("title", isPass ? "Hide Token" : "Show Token");
      btnToggleTokenVis.style.opacity = isPass ? "1" : "0.5";
    });
  }
  const btnCopyToken = document.getElementById("btnCopyToken");
  if (btnCopyToken && txtAuthToken) {
    btnCopyToken.addEventListener("click", async () => {
      try {
        await navigator.clipboard.writeText(txtAuthToken.value);
        showStatus("Copied token to clipboard!");
      } catch (err) {
        showStatus("Failed to copy token.");
      }
    });
  }
  const segButtons = document.querySelectorAll("#networkExposure .segment-btn");
  segButtons.forEach((btn) => {
    btn.addEventListener("click", async () => {
      segButtons.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const val = btn.dataset.value || "local";
      await window.companion.invoke("ai:update-config", {
        key: "connection.network_expose",
        value: val
      });
      showStatus(`Expose network set to: ${btn.textContent}`);
    });
  });
  const chkSecureWs = document.getElementById("chkSecureWs");
  if (chkSecureWs) {
    chkSecureWs.addEventListener("change", async () => {
      await window.companion.invoke("ai:update-config", {
        key: "connection.secure_wss",
        value: chkSecureWs.checked
      });
      showStatus(chkSecureWs.checked ? "Secure WSS enabled" : "Secure WSS disabled");
    });
  }
  const txtWsAddress = document.getElementById("txtWsAddress");
  if (txtWsAddress) {
    txtWsAddress.addEventListener("change", async () => {
      await window.companion.invoke("ai:update-config", {
        key: "connection.ws_address",
        value: txtWsAddress.value.trim()
      });
      showStatus("WebSocket server address saved");
    });
  }
  if (txtAuthToken) {
    txtAuthToken.addEventListener("change", async () => {
      await window.companion.invoke("ai:update-config", {
        key: "connection.auth_token",
        value: txtAuthToken.value.trim()
      });
      showStatus("Connection auth token updated");
    });
  }
  setTimeout(async () => {
    try {
      if (window.companion) {
        const cfg = await window.companion.invoke("ai:get-config", {});
        const bindVal = (id, lblId, val, divisor = 1) => {
          const el = document.getElementById(id);
          const lbl = document.getElementById(lblId);
          if (el && val !== void 0) {
            const num = parseFloat(val);
            el.value = Math.round(num * divisor).toString();
            if (lbl) {
              if (divisor === 1e4 || divisor === 100) {
                lbl.textContent = num.toFixed(4);
              } else {
                lbl.textContent = num.toString();
              }
            }
          }
        };
        const bindSelect = (id, val) => {
          const el = document.getElementById(id);
          if (el && val !== void 0) el.value = val;
        };
        const bindColor = (id, val) => {
          const el = document.getElementById(id);
          if (el && val !== void 0) {
            el.value = val.slice(0, 7);
          }
        };
        const config3d = cfg?.["3d"] || {};
        bindVal("slider3DPosX", "lbl3DPosXVal", config3d.pos_x ?? "0.0000", 1e4);
        bindVal("slider3DPosY", "lbl3DPosYVal", config3d.pos_y ?? "0.0000", 1e4);
        bindVal("slider3DPosZ", "lbl3DPosZVal", config3d.pos_z ?? "0.0000", 1e4);
        bindVal("slider3DFov", "lbl3DFovVal", config3d.fov ?? "40", 1);
        bindVal("slider3DDist", "lbl3DDistVal", config3d.distance ?? "1.4513", 100);
        bindVal("slider3DRotY", "lbl3DRotYVal", config3d.rotation_y ?? "0", 1);
        bindSelect("select3DLookAt", config3d.look_at ?? "mouse");
        bindVal("slider3DLightRotX", "lbl3DLightRotXVal", config3d.light_rot_x ?? "0", 1);
        bindVal("slider3DLightRotY", "lbl3DLightRotYVal", config3d.light_rot_y ?? "0", 1);
        bindColor("cp3DLightColor", config3d.light_color ?? "#fffbf5ff");
        bindVal("slider3DLightIntensity", "lbl3DLightIntensityVal", config3d.light_intensity ?? "2.02", 100);
        bindVal("slider3DAmbientIntensity", "lbl3DAmbientIntensityVal", config3d.ambient_intensity ?? "0.60", 100);
        bindColor("cp3DAmbientColor", config3d.ambient_color ?? "#ffffffff");
        bindSelect("select3DEnvironment", config3d.environment ?? "hemisphere");
        bindVal("slider3DHemiIntensity", "lbl3DHemiIntensityVal", config3d.hemi_intensity ?? "0.40", 100);
        bindColor("cp3DHemiSkyColor", config3d.hemi_sky_color ?? "#ffffffff");
        bindColor("cp3DHemiGroundColor", config3d.hemi_ground_color ?? "#222222ff");
      }
    } catch (err) {
      console.error("[settings] Init 3d config error:", err);
    }
  }, 200);
  const setup3DListener = (id, lblId, configKey, factor = 1) => {
    const el = document.getElementById(id);
    const lbl = document.getElementById(lblId);
    if (el) {
      el.addEventListener("input", async () => {
        const raw = parseFloat(el.value);
        const val = (raw / factor).toFixed(4);
        if (lbl) {
          if (factor === 1) {
            lbl.textContent = Math.round(raw).toString();
          } else {
            lbl.textContent = parseFloat(val).toFixed(4);
          }
        }
        await window.companion.invoke("ai:update-config", {
          key: configKey,
          value: val
        });
      });
    }
  };
  const setup3DColorListener = (id, configKey) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", async () => {
        await window.companion.invoke("ai:update-config", {
          key: configKey,
          value: el.value + "ff"
          // append standard alpha
        });
      });
    }
  };
  const setup3DSelectListener = (id, configKey) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", async () => {
        await window.companion.invoke("ai:update-config", {
          key: configKey,
          value: el.value
        });
      });
    }
  };
  setup3DListener("slider3DPosX", "lbl3DPosXVal", "3d.pos_x", 1e4);
  setup3DListener("slider3DPosY", "lbl3DPosYVal", "3d.pos_y", 1e4);
  setup3DListener("slider3DPosZ", "lbl3DPosZVal", "3d.pos_z", 1e4);
  setup3DListener("slider3DFov", "lbl3DFovVal", "3d.fov", 1);
  setup3DListener("slider3DDist", "lbl3DDistVal", "3d.distance", 100);
  setup3DListener("slider3DRotY", "lbl3DRotYVal", "3d.rotation_y", 1);
  setup3DSelectListener("select3DLookAt", "3d.look_at");
  setup3DListener("slider3DLightRotX", "lbl3DLightRotXVal", "3d.light_rot_x", 1);
  setup3DListener("slider3DLightRotY", "lbl3DLightRotYVal", "3d.light_rot_y", 1);
  setup3DColorListener("cp3DLightColor", "3d.light_color");
  setup3DListener("slider3DLightIntensity", "lbl3DLightIntensityVal", "3d.light_intensity", 100);
  setup3DListener("slider3DAmbientIntensity", "lbl3DAmbientIntensityVal", "3d.ambient_intensity", 100);
  setup3DColorListener("cp3DAmbientColor", "3d.ambient_color");
  setup3DSelectListener("select3DEnvironment", "3d.environment");
  setup3DListener("slider3DHemiIntensity", "lbl3DHemiIntensityVal", "3d.hemi_intensity", 100);
  setup3DColorListener("cp3DHemiSkyColor", "3d.hemi_sky_color");
  setup3DColorListener("cp3DHemiGroundColor", "3d.hemi_ground_color");
  setTimeout(async () => {
    try {
      if (window.companion) {
        const cfg = await window.companion.invoke("ai:get-config", {});
        const anim = cfg?.animation || {};
        const chkMouse = document.getElementById("chkMouseTracking");
        if (chkMouse) chkMouse.checked = anim.mouse_tracking !== false;
        const slEyeOffset2 = document.getElementById("sliderEyeOffset");
        const lblEyeOffset2 = document.getElementById("lblEyeOffsetVal");
        if (slEyeOffset2 && anim.eye_offset !== void 0) {
          slEyeOffset2.value = Math.round(parseFloat(anim.eye_offset) * 100).toString();
          if (lblEyeOffset2) lblEyeOffset2.textContent = (parseFloat(anim.eye_offset) * 100).toFixed(2) + "%";
        }
        const chkIdleEye = document.getElementById("chkIdleEyeMovement");
        if (chkIdleEye) chkIdleEye.checked = anim.idle_eye_movement !== false;
        const chkBlink = document.getElementById("chkBlink");
        if (chkBlink) chkBlink.checked = anim.enable_blink !== false;
        const selBlink = document.getElementById("selectBlinkMode");
        if (selBlink) selBlink.value = anim.blink_mode || "auto";
        const selIdle = document.getElementById("selectIdleAnimation");
        if (selIdle) selIdle.value = anim.idle_animation || "idle";
        const params = cfg?.params || {};
        const slRenderScale2 = document.getElementById("sliderRenderScale");
        const lblRenderScale2 = document.getElementById("lblRenderScaleVal");
        if (slRenderScale2 && params.render_scale !== void 0) {
          slRenderScale2.value = Math.round(parseFloat(params.render_scale) * 100).toString();
          if (lblRenderScale2) lblRenderScale2.textContent = parseFloat(params.render_scale).toFixed(2) + "x";
        }
        const chkShadow = document.getElementById("chkDropShadow");
        if (chkShadow) chkShadow.checked = params.drop_shadow === true;
        const fpsVal = params.fps_limit || "30";
        const fpsBtns2 = document.querySelectorAll("#fpsLimitSegment .segment-btn");
        fpsBtns2.forEach((btn) => {
          if (btn.dataset.value === fpsVal) {
            fpsBtns2.forEach((b) => b.classList.remove("active"));
            btn.classList.add("active");
          }
        });
        const chkExpr = document.getElementById("chkExpressionSystem");
        if (chkExpr) chkExpr.checked = cfg?.expressions?.enabled !== false;
        const paramVals = params.values || {};
        const bindParam = (id, lblId, val, isMultiplier = false) => {
          const el = document.getElementById(id);
          const lbl = document.getElementById(lblId);
          if (el && val !== void 0) {
            const num = parseFloat(val);
            el.value = isMultiplier ? Math.round(num * 100).toString() : num.toString();
            if (lbl) lbl.textContent = num.toFixed(isMultiplier ? 2 : 0);
          }
        };
        bindParam("sliderParamAngleX", "lblParamAngleXVal", paramVals.angle_x ?? "0");
        bindParam("sliderParamAngleY", "lblParamAngleYVal", paramVals.angle_y ?? "0");
        bindParam("sliderParamAngleZ", "lblParamAngleZVal", paramVals.angle_z ?? "0");
        bindParam("sliderParamEyeLOpen", "lblParamEyeLOpenVal", paramVals.eye_l_open ?? "1.0", true);
        bindParam("sliderParamEyeROpen", "lblParamEyeROpenVal", paramVals.eye_r_open ?? "1.0", true);
        bindParam("sliderParamEyeLSmile", "lblParamEyeLSmileVal", paramVals.eye_l_smile ?? "0.0", true);
        bindParam("sliderParamEyeRSmile", "lblParamEyeRSmileVal", paramVals.eye_r_smile ?? "0.0", true);
        bindParam("sliderParamBrowLX", "lblParamBrowLXVal", paramVals.brow_l_x ?? "0.0", true);
        bindParam("sliderParamBrowRX", "lblParamBrowRXVal", paramVals.brow_r_x ?? "0.0", true);
        bindParam("sliderParamBrowLY", "lblParamBrowLYVal", paramVals.brow_l_y ?? "0.0", true);
        bindParam("sliderParamBrowRY", "lblParamBrowRYVal", paramVals.brow_r_y ?? "0.0", true);
        bindParam("sliderParamMouthOpen", "lblParamMouthOpenVal", paramVals.mouth_open ?? "0.0", true);
        bindParam("sliderParamMouthForm", "lblParamMouthFormVal", paramVals.mouth_form ?? "0.0", true);
        bindParam("sliderParamBodyX", "lblParamBodyXVal", paramVals.body_x ?? "0");
        bindParam("sliderParamBreath", "lblParamBreathVal", paramVals.breath ?? "0.0", true);
      }
    } catch (err) {
      console.error("[settings] Init 2d config error:", err);
    }
  }, 200);
  const setup2DCheckbox = (id, configKey) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", async () => {
        await window.companion.invoke("ai:update-config", {
          key: configKey,
          value: el.checked
        });
      });
    }
  };
  const setup2DSelect = (id, configKey) => {
    const el = document.getElementById(id);
    if (el) {
      el.addEventListener("change", async () => {
        await window.companion.invoke("ai:update-config", {
          key: configKey,
          value: el.value
        });
      });
    }
  };
  setup2DCheckbox("chkMouseTracking", "animation.mouse_tracking");
  setup2DCheckbox("chkIdleEyeMovement", "animation.idle_eye_movement");
  setup2DCheckbox("chkBlink", "animation.enable_blink");
  setup2DSelect("selectBlinkMode", "animation.blink_mode");
  setup2DSelect("selectIdleAnimation", "animation.idle_animation");
  const slEyeOffset = document.getElementById("sliderEyeOffset");
  const lblEyeOffset = document.getElementById("lblEyeOffsetVal");
  if (slEyeOffset) {
    slEyeOffset.addEventListener("input", async () => {
      const pct = parseInt(slEyeOffset.value);
      const val = (pct / 100).toFixed(4);
      if (lblEyeOffset) lblEyeOffset.textContent = pct.toFixed(2) + "%";
      await window.companion.invoke("ai:update-config", {
        key: "animation.eye_offset",
        value: val
      });
    });
  }
  const slRenderScale = document.getElementById("sliderRenderScale");
  const lblRenderScale = document.getElementById("lblRenderScaleVal");
  if (slRenderScale) {
    slRenderScale.addEventListener("input", async () => {
      const pct = parseInt(slRenderScale.value);
      const val = (pct / 100).toFixed(2);
      if (lblRenderScale) lblRenderScale.textContent = val + "x";
      await window.companion.invoke("ai:update-config", {
        key: "params.render_scale",
        value: val
      });
    });
  }
  const fpsBtns = document.querySelectorAll("#fpsLimitSegment .segment-btn");
  fpsBtns.forEach((btn) => {
    btn.addEventListener("click", async () => {
      fpsBtns.forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      const val = btn.dataset.value || "30";
      await window.companion.invoke("ai:update-config", {
        key: "params.fps_limit",
        value: val
      });
    });
  });
  setup2DCheckbox("chkDropShadow", "params.drop_shadow");
  setup2DCheckbox("chkExpressionSystem", "expressions.enabled");
  const setupParamSlider = (id, lblId, paramKey, isMultiplier = false) => {
    const el = document.getElementById(id);
    const lbl = document.getElementById(lblId);
    if (el) {
      el.addEventListener("input", async () => {
        const raw = parseFloat(el.value);
        const val = isMultiplier ? (raw / 100).toFixed(2) : raw.toString();
        if (lbl) lbl.textContent = parseFloat(val).toFixed(isMultiplier ? 2 : 0);
        await window.companion.invoke("ai:update-config", {
          key: `params.values.${paramKey}`,
          value: val
        });
      });
    }
  };
  setupParamSlider("sliderParamAngleX", "lblParamAngleXVal", "angle_x");
  setupParamSlider("sliderParamAngleY", "lblParamAngleYVal", "angle_y");
  setupParamSlider("sliderParamAngleZ", "lblParamAngleZVal", "angle_z");
  setupParamSlider("sliderParamEyeLOpen", "lblParamEyeLOpenVal", "eye_l_open", true);
  setupParamSlider("sliderParamEyeROpen", "lblParamEyeROpenVal", "eye_r_open", true);
  setupParamSlider("sliderParamEyeLSmile", "lblParamEyeLSmileVal", "eye_l_smile", true);
  setupParamSlider("sliderParamEyeRSmile", "lblParamEyeRSmileVal", "eye_r_smile", true);
  setupParamSlider("sliderParamBrowLX", "lblParamBrowLXVal", "brow_l_x", true);
  setupParamSlider("sliderParamBrowRX", "lblParamBrowRXVal", "brow_r_x", true);
  setupParamSlider("sliderParamBrowLY", "lblParamBrowLYVal", "brow_l_y", true);
  setupParamSlider("sliderParamBrowRY", "lblParamBrowRYVal", "brow_r_y", true);
  setupParamSlider("sliderParamMouthOpen", "lblParamMouthOpenVal", "mouth_open", true);
  setupParamSlider("sliderParamMouthForm", "lblParamMouthFormVal", "mouth_form", true);
  setupParamSlider("sliderParamBodyX", "lblParamBodyXVal", "body_x");
  setupParamSlider("sliderParamBreath", "lblParamBreathVal", "breath", true);
  document.getElementById("btnResetParams")?.addEventListener("click", async () => {
    if (!confirm("Reset all 2D model parameters to default?")) return;
    const defaults = {
      angle_x: "0",
      angle_y: "0",
      angle_z: "0",
      eye_l_open: "1.00",
      eye_r_open: "1.00",
      eye_l_smile: "0.00",
      eye_r_smile: "0.00",
      brow_l_x: "0.00",
      brow_r_x: "0.00",
      brow_l_y: "0.00",
      brow_r_y: "0.00",
      mouth_open: "0.00",
      mouth_form: "0.00",
      body_x: "0",
      breath: "0.00"
    };
    const setUI = (id, lblId, val, isMultiplier = false) => {
      const el = document.getElementById(id);
      const lbl = document.getElementById(lblId);
      if (el) el.value = isMultiplier ? Math.round(parseFloat(val) * 100).toString() : val;
      if (lbl) lbl.textContent = val;
    };
    setUI("sliderParamAngleX", "lblParamAngleXVal", "0");
    setUI("sliderParamAngleY", "lblParamAngleYVal", "0");
    setUI("sliderParamAngleZ", "lblParamAngleZVal", "0");
    setUI("sliderParamEyeLOpen", "lblParamEyeLOpenVal", "1.00", true);
    setUI("sliderParamEyeROpen", "lblParamEyeROpenVal", "1.00", true);
    setUI("sliderParamEyeLSmile", "lblParamEyeLSmileVal", "0.00", true);
    setUI("sliderParamEyeRSmile", "lblParamEyeRSmileVal", "0.00", true);
    setUI("sliderParamBrowLX", "lblParamBrowLXVal", "0.00", true);
    setUI("sliderParamBrowRX", "lblParamBrowRXVal", "0.00", true);
    setUI("sliderParamBrowLY", "lblParamBrowLYVal", "0.00", true);
    setUI("sliderParamBrowRY", "lblParamBrowRYVal", "0.00", true);
    setUI("sliderParamMouthOpen", "lblParamMouthOpenVal", "0.00", true);
    setUI("sliderParamMouthForm", "lblParamMouthFormVal", "0.00", true);
    setUI("sliderParamBodyX", "lblParamBodyXVal", "0");
    setUI("sliderParamBreath", "lblParamBreathVal", "0.00", true);
    for (const key of Object.keys(defaults)) {
      await window.companion.invoke("ai:update-config", {
        key: `params.values.${key}`,
        value: defaults[key]
      });
    }
    showStatus("Parameters reset to default!");
  });
  document.getElementById("btnClearCache")?.addEventListener("click", () => {
    showStatus("Model rendering cache cleared successfully!");
  });
}
function updateModelTypeLayout(modelPath) {
  const isVrm = modelPath.toLowerCase().endsWith(".vrm") || modelPath.toLowerCase().includes("vrm");
  const acc3DVrm = document.getElementById("accordion3DVrm");
  const accExpressions = document.getElementById("accordionExpressions");
  const accParams = document.getElementById("accordionParams");
  const accAnimation = document.getElementById("accordionAnimation");
  if (acc3DVrm) {
    acc3DVrm.style.display = isVrm ? "block" : "none";
  }
  if (accExpressions) {
    accExpressions.style.display = isVrm ? "none" : "block";
  }
  if (accParams) {
    accParams.style.display = isVrm ? "none" : "block";
  }
  if (accAnimation) {
    accAnimation.style.display = isVrm ? "none" : "block";
  }
}
window.companion?.on?.("avatar:registry-updated", async () => {
  try {
    await AssetRegistry.load(true);
    loadModelSelectorGrid();
  } catch (e) {
    console.warn("[settings] Failed to reload model selector:", e);
  }
});
export {
  updateModelTypeLayout
};
