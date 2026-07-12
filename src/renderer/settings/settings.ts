// @ts-ignore
import { AssetRegistry } from "../../live2d/asset-registry.js";

console.log("[settings] settings.ts loaded.");

// ─── Interfaces ──────────────────────────────────────────────
interface ModelItem {
  id: string;
  name: string;
  path: string;
  thumbnail?: string;
  description?: string;
  default?: boolean;
}

interface PersonaItem {
  name: string;
  desc: string;
  version: string;
  active: boolean;
}

interface ProviderItem {
  id: string;
  name: string;
  desc: string;
  tags: string[];
  icon: string;
}

// ─── Elements ────────────────────────────────────────────────
const saveStatus = document.getElementById("saveStatus") as HTMLDivElement;
let toastTimer: any = null;

function showStatus(msg: string = "Đã lưu cài đặt"): void {
  if (!saveStatus) return;
  saveStatus.textContent = `✓  ${msg}`;
  saveStatus.classList.add("visible");
  if (toastTimer) clearTimeout(toastTimer);
  toastTimer = setTimeout(() => saveStatus.classList.remove("visible"), 2200);
}

// ─── Navigation ──────────────────────────────────────────────
const allPanels = document.querySelectorAll(".view-panel") as NodeListOf<HTMLDivElement>;
const settingsIndex = document.getElementById("settingsIndex") as HTMLDivElement;

function navigateTo(targetId: string): void {
  allPanels.forEach(p => p.classList.remove("active"));
  const targetPanel = document.getElementById(targetId);
  if (targetPanel) {
    targetPanel.classList.add("active");
  }
  
  // Dynamic page load hooks
  if (targetId === "pageModels") loadModelSelectorGrid();
  if (targetId === "pageProviders") renderProviders();
  if (targetId === "pageCard") loadAiriCards();
}

document.querySelectorAll(".menu-card").forEach(card => {
  const target = (card as HTMLElement).dataset.target || "";
  card.addEventListener("click", () => navigateTo(target));
  card.addEventListener("keydown", (e: any) => {
    if (e.key === "Enter" || e.key === " ") {
      e.preventDefault();
      navigateTo(target);
    }
  });
});

document.querySelectorAll(".back-button").forEach(btn => {
  btn.addEventListener("click", () => {
    allPanels.forEach(p => p.classList.remove("active"));
    if (settingsIndex) settingsIndex.classList.add("active");
  });
});

// ─── Accordion Toggles ────────────────────────────────────────
document.querySelectorAll(".accordion-hdr").forEach(hdr => {
  hdr.addEventListener("click", (e: Event) => {
    // Avoid triggering when inner elements like refresh button are clicked
    if (e.target && (e.target as HTMLElement).closest("button") && (e.target as HTMLElement).closest("button") !== hdr) {
      return;
    }
    const accordionId = (hdr as HTMLElement).dataset.accordion || "";
    const accordionBody = document.querySelector(`#${accordionId} .accordion-body`) as HTMLElement;
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

// ─── Models Page: Scale & Position ───────────────────────────
const slScale = document.getElementById("sliderAvatarScale") as HTMLInputElement;
const slLbl = document.getElementById("lblAvatarScaleVal") as HTMLSpanElement;

if (slScale && slLbl) {
  // Init scale
  setTimeout(async () => {
    try {
      if ((window as any).companion) {
        const cfg = await (window as any).companion.invoke("ai:get-config", {});
        const val = parseFloat(cfg?.app?.avatarScale);
        if (!isNaN(val) && val > 0) {
          slScale.value = Math.round(val * 100).toString();
          slLbl.textContent = val.toFixed(2) + "x";
        }
        
        // Dynamic layout toggle for 2D/3D
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
    if ((window as any).companion) {
      await (window as any).companion.invoke("ai:update-config", {
        key: "app.avatarScale",
        value: val
      });
    }
  });
}

// ─── Models Page: Import ZIP ──────────────────────────────────
function showImportResult(type: "success" | "error", msg: string): void {
  const el = document.getElementById("importResult");
  if (!el) return;
  el.className = `import-result import-result-${type}`;
  el.textContent = (type === "success" ? "✓ " : "✗ ") + msg;
  el.style.display = "block";
  
  // @ts-ignore
  clearTimeout(el._timer);
  // @ts-ignore
  el._timer = setTimeout(() => {
    el.style.display = "none";
  }, 5000);
}

function setImportProgress(visible: boolean, label: string = "Extracting...", pct: number | null = null): void {
  const bar = document.getElementById("importProgress");
  const fill = document.getElementById("importProgressFill");
  const lbl = document.getElementById("importProgressLabel");
  if (!bar) return;
  bar.style.display = visible ? "block" : "none";
  if (lbl) lbl.textContent = label;
  if (fill) fill.style.width = (pct !== null ? pct : 0) + "%";
}

async function importZipFile(filePath: string): Promise<void> {
  if (!(window as any).companion) {
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
    const res = await (window as any).companion.invoke("avatar:import-zip", { path: filePath });
    clearInterval(tick);
    if (res && res.success) {
      setImportProgress(true, "Done!", 100);
      showImportResult("success", `"${res.model.name}" imported successfully!`);
      setTimeout(() => setImportProgress(false), 1200);
      loadModelSelectorGrid();
    } else {
      throw new Error(res?.error || "Unknown import error");
    }
  } catch (err: any) {
    clearInterval(tick);
    setImportProgress(false);
    showImportResult("error", err.message);
  }
}

document.getElementById("btnBrowseZip")?.addEventListener("click", async () => {
  if (!(window as any).companion) {
    showImportResult("error", "Not connected.");
    return;
  }
  const fp = await (window as any).companion.showOpenDialog({
    title: "Select ZIP",
    filters: [{ name: "ZIP Archives", extensions: ["zip"] }]
  });
  if (fp) await importZipFile(fp);
});

// Select model button -> opens custom Modal Selector Dialog
document.getElementById("btnSelectModel")?.addEventListener("click", () => {
  const modal = document.getElementById("modelSelectorModal");
  if (modal) {
    modal.classList.add("active");
    loadModelSelectorGrid();
  }
});

// Close modal button
document.getElementById("modalBtnClose")?.addEventListener("click", () => {
  document.getElementById("modelSelectorModal")?.classList.remove("active");
});

// Import button inside modal selector
document.getElementById("modalBtnImport")?.addEventListener("click", async () => {
  if (!(window as any).companion) {
    showImportResult("error", "Not connected.");
    return;
  }
  const fp = await (window as any).companion.showOpenDialog({
    title: "Select model",
    filters: [
      { name: "Model files", extensions: ["zip", "vrm"] },
      { name: "All files", extensions: ["*"] }
    ]
  });
  if (fp) {
    await importZipFile(fp);
    // Refresh modal selector grid after import
    loadModelSelectorGrid();
  }
});

document.getElementById("btnRefreshModels")?.addEventListener("click", () => {
  loadModelSelectorGrid();
});

// Page-level drag and drop on pageModels
document.addEventListener("dragover", e => {
  const panel = document.getElementById("pageModels");
  if (panel && panel.classList.contains("active")) {
    e.preventDefault();
    document.getElementById("modelsDropOverlay")?.classList.add("visible");
  }
});

document.addEventListener("dragleave", e => {
  const panel = document.getElementById("pageModels");
  if (panel && !panel.contains(e.relatedTarget as Node)) {
    document.getElementById("modelsDropOverlay")?.classList.remove("visible");
  }
});

document.addEventListener("drop", async e => {
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

// ─── Models Page: Model Selector Grid inside Modal ─────────────
async function loadModelSelectorGrid(): Promise<void> {
  const grid = document.getElementById("modalSelectorGrid");
  if (!grid) return;
  grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-3); padding: 30px;">Loading models...</div>';
  try {
    let activePath = "assets/live2d/IceGirl/IceGirl.model3.json";
    if ((window as any).companion) {
      const resConfig = await (window as any).companion.invoke("ai:get-config", {});
      activePath = resConfig?.avatar_model || "assets/live2d/IceGirl/IceGirl.model3.json";
    }

    const res = await fetch("../../assets/live2d/models.json?t=" + Date.now());
    const data = await res.json();
    const models: ModelItem[] = data.models || [];
    if (!models.length) {
      grid.innerHTML = '<div style="grid-column: 1/-1; text-align: center; color: var(--text-3); padding: 30px;">No models installed.</div>';
      return;
    }
    grid.innerHTML = "";
    const emojis: Record<string, string> = { icegirl: "🧊", hiyori: "🌸", mao: "🐱", huohuo: "🦋" };

    models.forEach(m => {
      const isActive = m.path === activePath;
      const card = document.createElement("div");
      card.className = "selector-card" + (isActive ? " active" : "");
      const emoji = emojis[m.id] || "✨";
      
      const isVrm = m.path.toLowerCase().endsWith(".vrm") || m.id.toLowerCase().includes("vrm");
      const typeLabel = isVrm ? "VRM" : "Live2D";
      const typeIcon = isVrm 
        ? `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="8" r="4"/><path d="M6 20v-2a4 4 0 0 1 4-4h4a4 4 0 0 1 4 4v2"/></svg>`
        : `<svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="3" width="18" height="18" rx="2"/><line x1="21" y1="9" x2="3" y2="9"/><line x1="9" y1="21" x2="9" y2="9"/></svg>`;

      card.innerHTML = `
        <div class="selector-card-thumb-wrap">
          <button class="selector-thumb-action" type="button" title="Info">•••</button>
          ${m.thumbnail 
            ? `<img src="../../${m.thumbnail}" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"/><span class="mre" style="display:none">${emoji}</span>` 
            : `<span class="mre" style="font-size: 48px;">${emoji}</span>`
          }
        </div>
        <div class="selector-card-info">
          <div class="selector-title-row">
            <span class="selector-name" title="${m.name}">${m.name}</span>
            <button class="selector-btn-edit" type="button" title="Rename">✏</button>
            ${isActive ? "" : '<button class="selector-btn-delete" type="button" title="Delete">🗑️</button>'}
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

      // Pick action button listener
      card.querySelector(".pick-btn")?.addEventListener("click", async () => {
        if (isActive) return;
        if ((window as any).companion) {
          const resUpdate = await (window as any).companion.invoke("ai:update-config", {
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

      // Rename action button listener
      card.querySelector(".selector-btn-edit")?.addEventListener("click", async (e) => {
        e.stopPropagation();
        const newName = prompt(`Rename "${m.name}" to:`, m.name);
        if (newName && newName.trim() && newName.trim() !== m.name) {
          // Note: In local DeskAgent manifest, renaming can be saved back
          showStatus(`Renamed to ${newName}`);
        }
      });

      // Delete action button listener (only if not active)
      card.querySelector(".selector-btn-delete")?.addEventListener("click", async (e) => {
        e.stopPropagation();
        if (!confirm(`Are you sure you want to delete "${m.name}"?\n(This action cannot be undone)`)) return;
        if ((window as any).companion) {
          const r = await (window as any).companion.deleteCharacter(m.id);
          if (r?.success) {
            card.remove();
            showStatus(`Deleted "${m.name}"`);
            loadModelSelectorGrid();
          } else {
            showStatus(r?.error || "Failed to delete.");
          }
        }
      });

      // Options click listener
      card.querySelector(".selector-thumb-action")?.addEventListener("click", (e) => {
        e.stopPropagation();
        alert(`Model details:\n\nID: ${m.id}\nName: ${m.name}\nPath: ${m.path}\nDescription: ${m.description || "No description"}`);
      });

      grid.appendChild(card);
    });
  } catch (err: any) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--text-3); padding: 30px;">Error loading: ${err.message}</div>`;
  }
}




// ─── Providers Page: Grid & Actions ───────────────────────────
const PROVIDERS: ProviderItem[] = [
  { id: "official", name: "Official Provider", desc: "Official AI provider by AIRI.", tags: ["RECOMMENDED", "PAID", "CLOUD"], icon: "⭐" },
  { id: "openrouter", name: "OpenRouter", desc: "openrouter.ai", tags: ["PAID", "CLOUD"], icon: "◀" },
  { id: "aihubmix", name: "AIHubMix", desc: "https://aihubmix.com (10% off)", tags: ["PAID", "CLOUD"], icon: "🌐" },
  { id: "azure", name: "Azure OpenAI", desc: "Azure OpenAI API", tags: ["PAID", "CLOUD"], icon: "A" },
  { id: "ollama", name: "Ollama", desc: "ollama.ai", tags: ["FREE", "LOCAL"], icon: "🦙" },
  { id: "lmstudio", name: "LM Studio", desc: "lmstudio.ai", tags: ["FREE", "LOCAL"], icon: "≡" },
  { id: "deepseek", name: "DeepSeek", desc: "deepseek.com", tags: ["PAID", "CLOUD"], icon: "🐋" },
  { id: "openai-compat", name: "OpenAI Compatible", desc: "OpenAI Compatible", tags: [], icon: "⚙" },
  { id: "xiaomi", name: "Xiaomi MiMo", desc: "api.xiaomimimo.com", tags: ["PAID", "CLOUD"], icon: "M" },
  { id: "openai", name: "OpenAI", desc: "openai.com", tags: ["PAID", "CLOUD"], icon: "◎" },
  { id: "anthropic", name: "Anthropic", desc: "anthropic.com", tags: ["PAID", "CLOUD"], icon: "⬡" },
  { id: "gemini", name: "Google Gemini", desc: "ai.google.dev", tags: ["PAID", "CLOUD"], icon: "✦" },
];

function renderProviders(): void {
  const grid = document.getElementById("providerGrid");
  if (!grid || grid.children.length > 0) return;
  grid.innerHTML = "";

  PROVIDERS.forEach(p => {
    const card = document.createElement("div");
    card.className = "provider-card";
    card.dataset.id = p.id;
    const tagsHtml = p.tags.map(t => `<span class="provider-tag provider-tag-${t.toLowerCase()}">${t}</span>`).join("");
    
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

    // Click card to check radio
    card.addEventListener("click", () => {
      const radio = card.querySelector('input[type="radio"]') as HTMLInputElement;
      if (radio && !radio.checked) {
        radio.checked = true;
        radio.dispatchEvent(new Event("change"));
      }
    });

    const radio = card.querySelector('input[type="radio"]') as HTMLInputElement;
    radio?.addEventListener("change", async () => {
      if (radio.checked && (window as any).companion) {
        const res = await (window as any).companion.invoke("ai:update-config", {
          key: "llm.provider",
          value: p.id
        });
        if (res && !res.error) showStatus(`Provider changed to ${p.name}`);
      }
    });

    grid.appendChild(card);
  });

  // Sync state with config
  setTimeout(async () => {
    try {
      if ((window as any).companion) {
        const cfg = await (window as any).companion.invoke("ai:get-config", {});
        const currentProvider = cfg?.llm_provider || "ollama";
        const targetRadio = grid.querySelector(`input[name="provider"][value="${currentProvider}"]`) as HTMLInputElement;
        if (targetRadio) targetRadio.checked = true;
      }
    } catch (_) {}
  }, 100);
}

// ─── AIRI Card Page: Load list ────────────────────────────────
function loadAiriCards(): void {
  const container = document.getElementById("airiExistingCards");
  if (!container || container.children.length > 0) return;
  container.innerHTML = "";

  // Mock persona card matching screenshot
  const personas: PersonaItem[] = [
    {
      name: "ReLU",
      desc: "(from Neko Ayaka) Good morning! You are finally awake. Your name is AIRI, pronounced as /ˈeɪtriː/, it the word A.I. companion. Your creator is Neko Ayaka.",
      version: "v1.0.0",
      active: true
    }
  ];

  personas.forEach(p => {
    const card = document.createElement("div");
    card.className = "airi-persona-card" + (p.active ? " airi-persona-card-active" : "");
    card.innerHTML = `
      <div class="apc-header">
        <span class="apc-name">${p.name}</span>
        <div class="apc-actions">
          <button class="apc-btn-edit" title="Edit">✏</button>
          ${p.active ? '<span class="apc-active-dot"></span>' : ""}
        </div>
      </div>
      <p class="apc-desc">${p.desc}</p>
      <div class="apc-footer">
        <span class="apc-version">${p.version}</span>
        <div class="apc-badges">
          <span class="apc-badge">📄 default</span>
          <span class="apc-badge">🔊 default</span>
        </div>
      </div>
      ${p.active ? '<div class="apc-bottom-active"><span class="apc-active-check">✓</span></div>' : ""}
    `;

    container.appendChild(card);
  });
}

// ─── Data Page Actions ────────────────────────────────────────
document.getElementById("btnOpenDataFolder")?.addEventListener("click", () => {
  if ((window as any).companion) {
    (window as any).companion.invoke("system:open-data-folder", {}).catch(() => {});
  }
});

document.getElementById("btnMoveToCenter")?.addEventListener("click", () => {
  if ((window as any).companion) {
    (window as any).companion.invoke("pet:move-to", { x: 0, y: 0 }).catch(() => {});
  }
});

// ─── Scenes: Upload Background ───────────────────────────────
document.getElementById("btnUploadBackground")?.addEventListener("click", async () => {
  if (!(window as any).companion) return;
  const fp = await (window as any).companion.showOpenDialog({
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

// ─── System / Diagnostics ────────────────────────────────────
async function updateSystemStatus(): Promise<void> {
  const statusBackend = document.getElementById("status-backend");
  const statusLlm = document.getElementById("status-llm");
  const statusTts = document.getElementById("status-tts");
  const statusStt = document.getElementById("status-stt");
  const statusMemory = document.getElementById("status-memory");

  try {
    if (!(window as any).companion) return;
    const res = await (window as any).companion.health();
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
    offlineList.forEach(el => {
      if (el) {
        el.textContent = "Offline";
        el.style.color = "var(--danger)";
      }
    });
  }
}

// ─── App state sync ──────────────────────────────────────────
if ((window as any).companion) {
  (window as any).companion.on("python:ready", () => {
    updateSystemStatus();
  });
  
  updateSystemStatus();
  setInterval(updateSystemStatus, 4000);

  // Load and populate Connection settings on startup
  setTimeout(async () => {
    try {
      if ((window as any).companion) {
        const cfg = await (window as any).companion.invoke("ai:get-config", {});
        
        // 1. WebSocket Server Address
        const wsAddr = cfg?.["connection.ws_address"] || "ws://localhost:6121/ws";
        const wsInput = document.getElementById("txtWsAddress") as HTMLInputElement;
        if (wsInput) wsInput.value = wsAddr;

        // 2. Secure WebSocket (WSS)
        const secureWss = cfg?.["connection.secure_wss"] === true || cfg?.["connection.secure_wss"] === "true";
        const secureInput = document.getElementById("chkSecureWs") as HTMLInputElement;
        if (secureInput) secureInput.checked = secureWss;

        // 3. Network Exposure Segment
        const netExpose = cfg?.["connection.network_expose"] || "local";
        const segBtns = document.querySelectorAll("#networkExposure .segment-btn") as NodeListOf<HTMLButtonElement>;
        segBtns.forEach(btn => {
          if (btn.dataset.value === netExpose) {
            segBtns.forEach(b => b.classList.remove("active"));
            btn.classList.add("active");
          }
        });

        // 4. Auth Token
        const authToken = cfg?.["connection.auth_token"] || "q7x9w2v8k4m3n5p6r8t2y1u9i8o7p6a5";
        const tokenInput = document.getElementById("txtAuthToken") as HTMLInputElement;
        if (tokenInput) tokenInput.value = authToken;
      }
    } catch (err) {
      console.error("[settings] Init connection config error:", err);
    }
  }, 250);

  // ─── Connection Page: Show / Hide Auth Token ─────────────────
  const txtAuthToken = document.getElementById("txtAuthToken") as HTMLInputElement;
  const btnToggleTokenVis = document.getElementById("btnToggleTokenVis");
  if (txtAuthToken && btnToggleTokenVis) {
    btnToggleTokenVis.addEventListener("click", () => {
      const isPass = txtAuthToken.type === "password";
      txtAuthToken.type = isPass ? "text" : "password";
      btnToggleTokenVis.setAttribute("title", isPass ? "Hide Token" : "Show Token");
      // Change icon opacity
      (btnToggleTokenVis as HTMLElement).style.opacity = isPass ? "1" : "0.5";
    });
  }

  // ─── Connection Page: Copy Auth Token ────────────────────────
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

  // ─── Connection Page: Segment Control Expose On Network ──────
  const segButtons = document.querySelectorAll("#networkExposure .segment-btn") as NodeListOf<HTMLButtonElement>;
  segButtons.forEach(btn => {
    btn.addEventListener("click", async () => {
      segButtons.forEach(b => b.classList.remove("active"));
      btn.classList.add("active");
      const val = btn.dataset.value || "local";
      
      // Save network mode to config
      await (window as any).companion.invoke("ai:update-config", {
        key: "connection.network_expose",
        value: val
      });
      showStatus(`Expose network set to: ${btn.textContent}`);
    });
  });

  // ─── Connection Page: WSS Toggle switch ──────────────────────
  const chkSecureWs = document.getElementById("chkSecureWs") as HTMLInputElement;
  if (chkSecureWs) {
    chkSecureWs.addEventListener("change", async () => {
      await (window as any).companion.invoke("ai:update-config", {
        key: "connection.secure_wss",
        value: chkSecureWs.checked
      });
      showStatus(chkSecureWs.checked ? "Secure WSS enabled" : "Secure WSS disabled");
    });
  }

  // ─── Connection Page: Server Address input ──────────────────
  const txtWsAddress = document.getElementById("txtWsAddress") as HTMLInputElement;
  if (txtWsAddress) {
    txtWsAddress.addEventListener("change", async () => {
      await (window as any).companion.invoke("ai:update-config", {
        key: "connection.ws_address",
        value: txtWsAddress.value.trim()
      });
      showStatus("WebSocket server address saved");
    });
  }

  // ─── Connection Page: Auth Token change input ────────────────
  if (txtAuthToken) {
    txtAuthToken.addEventListener("change", async () => {
      await (window as any).companion.invoke("ai:update-config", {
        key: "connection.auth_token",
        value: txtAuthToken.value.trim()
      });
      showStatus("Connection auth token updated");
    });
  }

  // ─── 3D VRM Page: Camera Height slider ───────────────────────
  const slider3DHeight = document.getElementById("slider3DCameraHeight") as HTMLInputElement;
  const lbl3DHeight = document.getElementById("lbl3DCameraHeightVal") as HTMLSpanElement;
  if (slider3DHeight && lbl3DHeight) {
    slider3DHeight.addEventListener("input", async () => {
      const val = (parseInt(slider3DHeight.value) / 100).toFixed(2);
      lbl3DHeight.textContent = val + "m";
      await (window as any).companion.invoke("ai:update-config", {
        key: "3d.camera_height",
        value: val
      });
    });
  }

  // ─── 3D VRM Page: Camera Zoom slider ─────────────────────────
  const slider3DZoom = document.getElementById("slider3DCameraZoom") as HTMLInputElement;
  const lbl3DZoom = document.getElementById("lbl3DCameraZoomVal") as HTMLSpanElement;
  if (slider3DZoom && lbl3DZoom) {
    slider3DZoom.addEventListener("input", async () => {
      const val = (parseInt(slider3DZoom.value) / 100).toFixed(2);
      lbl3DZoom.textContent = val + "x";
      await (window as any).companion.invoke("ai:update-config", {
        key: "3d.camera_zoom",
        value: val
      });
    });
  }

  // ─── 3D VRM Page: Light Intensity slider ─────────────────────
  const slider3DLight = document.getElementById("slider3DLight") as HTMLInputElement;
  const lbl3DLight = document.getElementById("lbl3DLightVal") as HTMLSpanElement;
  if (slider3DLight && lbl3DLight) {
    slider3DLight.addEventListener("input", async () => {
      const val = slider3DLight.value;
      lbl3DLight.textContent = val + "%";
      await (window as any).companion.invoke("ai:update-config", {
        key: "3d.light_intensity",
        value: val
      });
    });
  }

  // ─── 3D VRM Page: Face Tracking webcam button ────────────────
  const btnStartTracking = document.getElementById("btnStartTracking");
  if (btnStartTracking) {
    let isTracking = false;
    btnStartTracking.addEventListener("click", () => {
      isTracking = !isTracking;
      btnStartTracking.textContent = isTracking ? "Stop Tracking" : "Start Tracking";
      btnStartTracking.classList.toggle("data-btn-accent", isTracking);
      showStatus(isTracking ? "Face tracking started" : "Face tracking stopped");
    });
  }
}

// ─── Shared helper: Toggle 2D vs 3D accordions based on model ──
export function updateModelTypeLayout(modelPath: string): void {
  const isVrm = modelPath.toLowerCase().endsWith(".vrm") || modelPath.toLowerCase().includes("vrm");
  const acc3DVrm = document.getElementById("accordion3DVrm");
  const accExpressions = document.getElementById("accordionExpressions");
  const accParams = document.getElementById("accordionParams");
  
  if (acc3DVrm) {
    acc3DVrm.style.display = isVrm ? "block" : "none";
  }
  if (accExpressions) {
    accExpressions.style.display = isVrm ? "none" : "block";
  }
  if (accParams) {
    accParams.style.display = isVrm ? "none" : "block";
  }
}

