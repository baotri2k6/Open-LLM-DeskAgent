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
  if (targetId === "pageModels") loadModelGrid();
  if (targetId === "pageProviders") renderProviders();
  if (targetId === "pageCard") loadAiriCards();
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
  setImportProgress(true, "Extracting and registering model...", 30);
  let pct = 30;
  const tick = setInterval(() => {
    pct = Math.min(pct + 8, 85);
    const fill = document.getElementById("importProgressFill");
    if (fill) fill.style.width = pct + "%";
  }, 400);
  try {
    const res = await window.companion.invoke("avatar:import-zip", { path: filePath });
    clearInterval(tick);
    if (res && res.success) {
      setImportProgress(true, "Done!", 100);
      showImportResult("success", `"${res.model.name}" imported successfully!`);
      setTimeout(() => setImportProgress(false), 1200);
      loadModelGrid();
    } else {
      throw new Error(res?.error || "Unknown import error");
    }
  } catch (err) {
    clearInterval(tick);
    setImportProgress(false);
    showImportResult("error", err.message);
  }
}
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
  loadModelGrid();
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
            loadModelSelectorGrid();
            loadModelGrid();
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
async function loadModelGrid() {
  const grid = document.getElementById("modelGrid");
  if (!grid) return;
  grid.innerHTML = '<div class="model-grid-empty">Loading...</div>';
  try {
    const res = await fetch("../../assets/live2d/models.json?t=" + Date.now());
    const data = await res.json();
    const models = data.models || [];
    if (!models.length) {
      grid.innerHTML = '<div class="model-grid-empty">No models installed.</div>';
      return;
    }
    grid.innerHTML = "";
    const emojis = { icegirl: "\u{1F9CA}", hiyori: "\u{1F338}", mao: "\u{1F431}", huohuo: "\u{1F98B}" };
    models.forEach((m) => {
      const card = document.createElement("div");
      card.className = "model-row";
      card.dataset.id = m.id;
      const emoji = emojis[m.id] || "\u2728";
      card.innerHTML = `
        <div class="model-row-thumb">
          ${m.thumbnail ? `<img src="../../${m.thumbnail}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/><span class="mre" style="display:none">${emoji}</span>` : `<span class="mre">${emoji}</span>`}
        </div>
        <div class="model-row-info">
          <span class="model-row-name">${m.name}</span>
          <span class="model-row-desc">${m.description || m.path.split("/").pop()}</span>
        </div>
        <div class="model-row-actions">
          ${m.default ? '<span class="model-badge-default">Default</span>' : `<button class="model-del-btn" data-id="${m.id}" title="Remove"><svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.2"><polyline points="3 6 5 6 21 6"/><path d="M19 6l-1 14H6L5 6"/><path d="M10 11v6"/><path d="M14 11v6"/><path d="M9 6V4h6v2"/></svg></button>`}
        </div>
      `;
      card.querySelector(".model-del-btn")?.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Remove "${m.name}" from the list?
(Files won't be deleted from disk)`)) return;
        if (window.companion) {
          const r = await window.companion.deleteCharacter(m.id);
          if (r?.success) {
            card.remove();
            showImportResult("success", `"${m.name}" removed.`);
          } else {
            showImportResult("error", r?.error || "Failed to remove.");
          }
        }
      });
      grid.appendChild(card);
    });
  } catch (err) {
    grid.innerHTML = `<div class="model-grid-empty">Error: ${err.message}</div>`;
  }
}
const PROVIDERS = [
  { id: "official", name: "Official Provider", desc: "Official AI provider by AIRI.", tags: ["RECOMMENDED", "PAID", "CLOUD"], icon: "\u2B50" },
  { id: "openrouter", name: "OpenRouter", desc: "openrouter.ai", tags: ["PAID", "CLOUD"], icon: "\u25C0" },
  { id: "aihubmix", name: "AIHubMix", desc: "https://aihubmix.com (10% off)", tags: ["PAID", "CLOUD"], icon: "\u{1F310}" },
  { id: "azure", name: "Azure OpenAI", desc: "Azure OpenAI API", tags: ["PAID", "CLOUD"], icon: "A" },
  { id: "ollama", name: "Ollama", desc: "ollama.ai", tags: ["FREE", "LOCAL"], icon: "\u{1F999}" },
  { id: "lmstudio", name: "LM Studio", desc: "lmstudio.ai", tags: ["FREE", "LOCAL"], icon: "\u2261" },
  { id: "deepseek", name: "DeepSeek", desc: "deepseek.com", tags: ["PAID", "CLOUD"], icon: "\u{1F40B}" },
  { id: "openai-compat", name: "OpenAI Compatible", desc: "OpenAI Compatible", tags: [], icon: "\u2699" },
  { id: "xiaomi", name: "Xiaomi MiMo", desc: "api.xiaomimimo.com", tags: ["PAID", "CLOUD"], icon: "M" },
  { id: "openai", name: "OpenAI", desc: "openai.com", tags: ["PAID", "CLOUD"], icon: "\u25CE" },
  { id: "anthropic", name: "Anthropic", desc: "anthropic.com", tags: ["PAID", "CLOUD"], icon: "\u2B21" },
  { id: "gemini", name: "Google Gemini", desc: "ai.google.dev", tags: ["PAID", "CLOUD"], icon: "\u2726" }
];
function renderProviders() {
  const grid = document.getElementById("providerGrid");
  if (!grid || grid.children.length > 0) return;
  grid.innerHTML = "";
  PROVIDERS.forEach((p) => {
    const card = document.createElement("div");
    card.className = "provider-card";
    card.dataset.id = p.id;
    const tagsHtml = p.tags.map((t) => `<span class="provider-tag provider-tag-${t.toLowerCase()}">${t}</span>`).join("");
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
        <input type="radio" name="provider" value="${p.id}"/>
        <span class="radio-dot"></span>
      </label>
    `;
    card.addEventListener("click", () => {
      const radio2 = card.querySelector('input[type="radio"]');
      if (radio2 && !radio2.checked) {
        radio2.checked = true;
        radio2.dispatchEvent(new Event("change"));
      }
    });
    const radio = card.querySelector('input[type="radio"]');
    radio?.addEventListener("change", async () => {
      if (radio.checked && window.companion) {
        const res = await window.companion.invoke("ai:update-config", {
          key: "llm.provider",
          value: p.id
        });
        if (res && !res.error) showStatus(`Provider changed to ${p.name}`);
      }
    });
    grid.appendChild(card);
  });
  setTimeout(async () => {
    try {
      if (window.companion) {
        const cfg = await window.companion.invoke("ai:get-config", {});
        const currentProvider = cfg?.llm_provider || "ollama";
        const targetRadio = grid.querySelector(`input[name="provider"][value="${currentProvider}"]`);
        if (targetRadio) targetRadio.checked = true;
      }
    } catch (_) {
    }
  }, 100);
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
    card.className = "airi-persona-card" + (p.active ? " airi-persona-card-active" : "");
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
document.getElementById("btnMoveToCenter")?.addEventListener("click", () => {
  if (window.companion) {
    window.companion.invoke("pet:move-to", { x: 0, y: 0 }).catch(() => {
    });
  }
});
document.getElementById("btnUploadBackground")?.addEventListener("click", async () => {
  if (!window.companion) return;
  const fp = await window.companion.showOpenDialog({
    title: "Select background image",
    filters: [{ name: "Images", extensions: ["jpg", "jpeg", "png", "gif", "webp"] }]
  });
  if (!fp) return;
  const gallery = document.getElementById("scenesGallery");
  const empty = gallery?.querySelector(".scene-empty");
  if (empty) empty.remove();
  const thumb = document.createElement("div");
  thumb.className = "scene-thumb";
  thumb.innerHTML = `
    <img src="file://${fp}" alt="Background" />
    <span class="scene-thumb-label">${fp.split(/[\\/]/).pop()}</span>
  `;
  gallery?.appendChild(thumb);
  showStatus("Background uploaded successfully");
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
}
