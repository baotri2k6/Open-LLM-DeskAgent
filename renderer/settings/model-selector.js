/**
 * renderer/settings/model-selector.js
 *
 * Module độc lập cho Model Selector Grid trong Settings.
 * Drop-in vào renderer/settings/settings.js — import hoặc paste vào cuối file.
 *
 * Cần trong settings.html:
 *   #modalSelectorGrid    — container grid cho model cards
 *   #modelSelectorModal   — modal overlay
 *   #modalBtnImport       — nút "Import ZIP"
 *   #zipConfigModal       — modal chọn config khi ZIP có nhiều model3.json
 *   #zipConfigList        — list bên trong zipConfigModal
 *   #importProgress       — progress bar container
 *   #importProgressFill   — progress bar fill element
 *   #importProgressLabel  — label text
 *   #importResult         — kết quả import (success/error)
 */

"use strict";

// ── Constants ─────────────────────────────────────────────────────────────────
const GRID_COLS = 3; // số cột trong grid
const CARD_ASPECT = "4/5"; // tỉ lệ ảnh thumbnail

// ── State ─────────────────────────────────────────────────────────────────────
let _currentModelId = null;
let _pendingZipPath = null; // lưu path khi đang chờ user chọn config trong ZIP

// ── Main: load và render grid ─────────────────────────────────────────────────

/**
 * Load danh sách model từ backend/registry và render grid.
 * Gọi khi user mở trang Models, sau khi import thành công.
 */
async function loadModelSelectorGrid() {
  const grid = document.getElementById("modalSelectorGrid");
  if (!grid) return;

  // Loading state
  grid.innerHTML = `
    <div style="grid-column:1/-1;display:flex;flex-direction:column;align-items:center;
      gap:10px;padding:32px;color:rgba(255,255,255,0.4);font-size:13px">
      <div style="width:32px;height:32px;border-radius:50%;border:2px solid rgba(255,255,255,0.1);
        border-top-color:rgba(255,255,255,0.5);animation:spin 0.8s linear infinite"></div>
      Đang tải danh sách model…
    </div>`;

  try {
    // Lấy model hiện tại từ config
    if (window.companion) {
      const cfg = await window.companion
        .invoke("ai:get-config", {})
        .catch(() => null);
      const currentPath = cfg?.avatar_model || cfg?.app?.avatarModel || "";
      _currentModelId = _pathToModelId(currentPath);
    }

    // Lấy danh sách model
    const models = await _fetchModels();

    if (!models.length) {
      grid.innerHTML = `
        <div style="grid-column:1/-1;text-align:center;padding:40px 20px;
          color:rgba(255,255,255,0.35);font-size:13px">
          Chưa có model nào. Hãy import một file ZIP Live2D.
        </div>`;
      return;
    }

    // Render cards
    grid.innerHTML = "";
    models.forEach((model) => {
      const card = _buildModelCard(model);
      grid.appendChild(card);
    });
  } catch (err) {
    console.error("[model-selector] loadModelSelectorGrid error:", err);
    grid.innerHTML = `
      <div style="grid-column:1/-1;text-align:center;padding:32px;
        color:rgba(255,100,100,0.8);font-size:13px">
        ✕ Không thể tải danh sách model: ${err.message}
      </div>`;
  }
}

// ── Fetch models ──────────────────────────────────────────────────────────────

async function _fetchModels() {
  // Ưu tiên IPC (Electron)
  if (window.companion) {
    const res = await window.companion
      .invoke("avatar:list-models", {})
      .catch(() => null);
    if (res?.success && Array.isArray(res.models)) return res.models;
  }

  // Fallback: AssetRegistry (nếu đã load)
  if (typeof AssetRegistry !== "undefined") {
    await AssetRegistry.load().catch(() => null);
    const all = AssetRegistry.getAll?.() ?? [];
    if (all.length) return all;
  }

  // Fallback cuối: fetch trực tiếp models.json
  try {
    const res = await fetch("../../assets/live2d/models.json");
    if (res.ok) {
      const data = await res.json();
      return Array.isArray(data.models)
        ? data.models
        : Array.isArray(data)
          ? data
          : [];
    }
  } catch {}

  return [];
}

function _pathToModelId(filePath) {
  if (!filePath) return null;
  const lower = filePath.toLowerCase();
  // Lấy tên thư mục model từ path
  const parts = lower.replace(/\\/g, "/").split("/");
  const live2dIdx = parts.indexOf("live2d");
  if (live2dIdx !== -1 && parts[live2dIdx + 1]) {
    return parts[live2dIdx + 1];
  }
  return null;
}

// ── Build model card ──────────────────────────────────────────────────────────

function _buildModelCard(model) {
  const isActive =
    model.id === _currentModelId || (model.default && !_currentModelId);
  const isDefault = !!model.default;

  const card = document.createElement("div");
  card.className = "model-card" + (isActive ? " model-card--active" : "");
  card.dataset.modelId = model.id;
  card.setAttribute("role", "button");
  card.setAttribute("tabindex", "0");
  card.setAttribute("aria-pressed", String(isActive));
  card.title = model.description || model.name;

  // Thumbnail
  const thumbSrc = model.thumbnail
    ? `../../${model.thumbnail}`
    : _generatePlaceholderSvg(model.name);
  const isDataUrl = thumbSrc.startsWith("data:");

  // Tags
  const tags = (model.tags || []).filter((t) => t !== "imported").slice(0, 2);

  card.innerHTML = `
    <div class="model-card__thumb-wrap" style="aspect-ratio:${CARD_ASPECT};position:relative;overflow:hidden;border-radius:10px;background:rgba(255,255,255,0.04)">
      ${
        isDataUrl
          ? `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center">${thumbSrc}</div>`
          : `<img
            src="${thumbSrc}"
            alt="${model.name}"
            loading="lazy"
            onerror="this.parentElement.innerHTML='<div style=\\'width:100%;height:100%;display:flex;align-items:center;justify-content:center;font-size:36px;opacity:.3\\'>✦</div>'"
            style="width:100%;height:100%;object-fit:cover;object-position:top center;display:block"
          />`
      }
      ${
        isActive
          ? `<div class="model-card__active-badge" style="
        position:absolute;top:8px;right:8px;
        background:rgba(124,58,237,0.9);color:#fff;
        font-size:10px;font-weight:600;padding:3px 8px;
        border-radius:99px;backdrop-filter:blur(8px);
      ">✓ Đang dùng</div>`
          : ""
      }
      ${
        isDefault
          ? `<div style="
        position:absolute;top:8px;left:8px;
        background:rgba(0,0,0,0.55);color:rgba(255,255,255,0.7);
        font-size:9px;font-weight:500;padding:2px 6px;
        border-radius:99px;backdrop-filter:blur(8px);
      ">Default</div>`
          : ""
      }
    </div>

    <div class="model-card__info" style="padding:8px 2px 4px">
      <div style="display:flex;align-items:center;justify-content:space-between;gap:6px">
        <span style="font-size:13px;font-weight:500;color:#f1f5f9;
          overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1">
          ${_escHtml(model.name || model.id)}
        </span>
        ${
          !isDefault
            ? `<button class="model-card__delete" data-model-id="${model.id}"
          title="Xóa khỏi danh sách"
          style="flex-shrink:0;width:22px;height:22px;border-radius:5px;border:none;
            background:transparent;color:rgba(255,255,255,0.3);cursor:pointer;
            font-size:13px;display:flex;align-items:center;justify-content:center;
            transition:all .15s">✕</button>`
            : ""
        }
      </div>
      ${
        tags.length
          ? `<div style="display:flex;gap:4px;margin-top:4px;flex-wrap:wrap">
        ${tags
          .map(
            (
              t,
            ) => `<span style="font-size:10px;padding:1px 6px;border-radius:99px;
          background:rgba(255,255,255,0.06);color:rgba(255,255,255,0.45)">${t}</span>`,
          )
          .join("")}
      </div>`
          : ""
      }
    </div>`;

  // Click card → set model
  card.addEventListener("click", (e) => {
    if (e.target.closest(".model-card__delete")) return;
    _selectModel(model);
  });
  card.addEventListener("keydown", (e) => {
    if (
      (e.key === "Enter" || e.key === " ") &&
      !e.target.closest(".model-card__delete")
    ) {
      e.preventDefault();
      _selectModel(model);
    }
  });

  // Delete button
  const delBtn = card.querySelector(".model-card__delete");
  if (delBtn) {
    delBtn.addEventListener("click", (e) => {
      e.stopPropagation();
      _confirmDeleteModel(model);
    });
    delBtn.addEventListener("mouseenter", () => {
      delBtn.style.background = "rgba(248,113,113,0.15)";
      delBtn.style.color = "rgba(248,113,113,0.9)";
    });
    delBtn.addEventListener("mouseleave", () => {
      delBtn.style.background = "transparent";
      delBtn.style.color = "rgba(255,255,255,0.3)";
    });
  }

  return card;
}

/** SVG placeholder khi không có thumbnail */
function _generatePlaceholderSvg(name) {
  const initial = (name || "?")[0].toUpperCase();
  return `data:image/svg+xml,${encodeURIComponent(
    `<svg xmlns="http://www.w3.org/2000/svg" width="200" height="250" viewBox="0 0 200 250">
      <defs><linearGradient id="g" x1="0%" y1="0%" x2="100%" y2="100%">
        <stop offset="0%" style="stop-color:#3d1d77"/>
        <stop offset="100%" style="stop-color:#0e7490"/>
      </linearGradient></defs>
      <rect width="200" height="250" fill="url(#g)"/>
      <text x="100" y="140" font-family="system-ui" font-size="72" font-weight="300"
        text-anchor="middle" fill="rgba(255,255,255,0.6)">${initial}</text>
    </svg>`,
  )}`;
}

// ── Select / Switch model ─────────────────────────────────────────────────────

async function _selectModel(model) {
  if (model.id === _currentModelId) return; // already active

  if (!window.companion) {
    showImportResult?.("error", "Cần chạy trong Electron để đổi model");
    return;
  }

  // Optimistic UI: update active card ngay lập tức
  _currentModelId = model.id;
  document.querySelectorAll(".model-card").forEach((c) => {
    const active = c.dataset.modelId === model.id;
    c.classList.toggle("model-card--active", active);
    c.setAttribute("aria-pressed", String(active));
    const badge = c.querySelector(".model-card__active-badge");
    if (active && !badge) {
      const thumb = c.querySelector(".model-card__thumb-wrap");
      if (thumb) {
        const b = document.createElement("div");
        b.className = "model-card__active-badge";
        b.style.cssText =
          "position:absolute;top:8px;right:8px;background:rgba(124,58,237,0.9);color:#fff;font-size:10px;font-weight:600;padding:3px 8px;border-radius:99px;backdrop-filter:blur(8px)";
        b.textContent = "✓ Đang dùng";
        thumb.appendChild(b);
      }
    } else if (!active && badge) {
      badge.remove();
    }
  });

  try {
    const res = await window.companion.invoke("avatar:set-model", {
      modelId: model.id,
      modelPath: model.path,
    });
    if (!res?.success) {
      console.warn("[model-selector] set-model failed:", res?.error);
      showImportResult?.("error", res?.error || "Không thể đổi model");
    }
  } catch (err) {
    console.error("[model-selector] _selectModel error:", err);
    showImportResult?.("error", String(err));
  }
}

// ── Delete model ──────────────────────────────────────────────────────────────

async function _confirmDeleteModel(model) {
  // Simple confirm — có thể thay bằng custom modal sau
  const ok = confirm(
    `Xóa "${model.name}" khỏi danh sách?\n\nFile trên disk sẽ không bị xóa.`,
  );
  if (!ok) return;

  if (!window.companion) {
    showImportResult?.("error", "Cần chạy trong Electron");
    return;
  }
  try {
    const res = await window.companion.invoke("avatar:delete-model", {
      modelId: model.id,
    });
    if (res?.success) {
      showImportResult?.("success", `Đã xóa "${model.name}" khỏi danh sách`);
      loadModelSelectorGrid();
    } else {
      showImportResult?.("error", res?.error || "Không thể xóa");
    }
  } catch (err) {
    showImportResult?.("error", String(err));
  }
}

// ── Import ZIP flow ───────────────────────────────────────────────────────────

/** Mở dialog chọn file ZIP */
async function triggerZipImport() {
  if (!window.companion) {
    alert("Tính năng import cần chạy trong Electron app");
    return;
  }
  try {
    const filePath = await window.companion.invoke("system:open-file-dialog", {
      title: "Chọn file Live2D ZIP",
      filters: [{ name: "ZIP Archive", extensions: ["zip"] }],
    });
    if (!filePath) return; // user cancelled

    await importZipFile(filePath);
  } catch (err) {
    showImportResult?.("error", "Không thể mở dialog: " + err.message);
  }
}

/**
 * Pipeline import:
 *   1. Scan ZIP → lấy danh sách config files
 *   2. Nếu 1 config → import thẳng
 *   3. Nếu nhiều config → hiển thị modal cho user chọn
 */
async function importZipFile(filePath) {
  if (!window.companion) {
    showImportResult?.("error", "Không kết nối được Electron backend");
    return;
  }
  try {
    _setImportProgress(true, "Đang scan cấu trúc ZIP…", 10);

    const scanRes = await window.companion.invoke("avatar:scan-zip", {
      path: filePath,
    });
    _setImportProgress(false);

    if (!scanRes?.success) {
      throw new Error(scanRes?.error || "Không thể đọc file ZIP");
    }

    const files = scanRes.files ?? [];

    if (files.length === 0) {
      // Không tìm thấy config → thử import luôn, để backend tự xử lý
      await _executeImport(filePath, null);
    } else if (files.length === 1) {
      // Chỉ có 1 config → import thẳng
      await _executeImport(filePath, files[0]);
    } else {
      // Nhiều config → show modal cho user chọn
      _showZipConfigModal(filePath, files);
    }
  } catch (err) {
    _setImportProgress(false);
    showImportResult?.("error", err.message);
  }
}

async function _executeImport(filePath, selectedConfig) {
  _setImportProgress(true, "Đang giải nén và đăng ký model…", 30);

  // Animate progress bar
  let pct = 30;
  const tick = setInterval(() => {
    pct = Math.min(pct + 7, 88);
    const fill = document.getElementById("importProgressFill");
    if (fill) fill.style.width = pct + "%";
  }, 500);

  try {
    const res = await window.companion.invoke("avatar:import-zip", {
      path: filePath,
      selectedConfig: selectedConfig || "",
    });
    clearInterval(tick);

    if (res?.success) {
      _setImportProgress(true, "Hoàn tất!", 100);
      showImportResult?.(
        "success",
        `✓ Đã thêm "${res.model?.name ?? "model"}" vào danh sách`,
      );
      setTimeout(() => _setImportProgress(false), 1200);

      // Reload registry và grid
      if (typeof AssetRegistry !== "undefined") {
        await AssetRegistry.load(true).catch(() => null);
      }
      await loadModelSelectorGrid();
    } else {
      throw new Error(res?.error || "Import thất bại");
    }
  } catch (err) {
    clearInterval(tick);
    _setImportProgress(false);
    showImportResult?.("error", err.message);
  }
}

// ── ZIP Config Modal ──────────────────────────────────────────────────────────

function _showZipConfigModal(filePath, files) {
  _pendingZipPath = filePath;

  const modal = document.getElementById("zipConfigModal");
  const list = document.getElementById("zipConfigList");

  if (!modal || !list) {
    // Fallback nếu không có modal — dùng file đầu tiên
    console.warn(
      "[model-selector] zipConfigModal not found, using first config",
    );
    _executeImport(filePath, files[0]);
    return;
  }

  // Render danh sách config files
  list.innerHTML = files
    .map(
      (f, i) => `
      <button
        class="zip-config-item"
        data-config="${_escHtml(f)}"
        style="
          display:flex;align-items:center;gap:10px;width:100%;
          padding:10px 13px;border-radius:8px;border:1px solid rgba(255,255,255,0.08);
          background:rgba(255,255,255,0.03);cursor:pointer;
          text-align:left;transition:all .15s;margin-bottom:5px;
          color:rgba(255,255,255,0.8);font-size:12.5px;
        "
      >
        <span style="font-size:18px;flex-shrink:0">📄</span>
        <span style="font-family:monospace;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${_escHtml(f)}</span>
      </button>`,
    )
    .join("");

  // Hover style
  list.querySelectorAll(".zip-config-item").forEach((btn) => {
    btn.addEventListener("mouseenter", () => {
      btn.style.background = "rgba(124,58,237,0.12)";
      btn.style.borderColor = "rgba(124,58,237,0.35)";
    });
    btn.addEventListener("mouseleave", () => {
      btn.style.background = "rgba(255,255,255,0.03)";
      btn.style.borderColor = "rgba(255,255,255,0.08)";
    });
    btn.addEventListener("click", () => {
      const cfg = btn.dataset.config;
      _closeZipConfigModal();
      _executeImport(_pendingZipPath, cfg);
    });
  });

  modal.style.display = "flex";
  requestAnimationFrame(() => {
    modal.style.opacity = "1";
  });
}

function _closeZipConfigModal() {
  const modal = document.getElementById("zipConfigModal");
  if (modal) {
    modal.style.opacity = "0";
    setTimeout(() => {
      modal.style.display = "none";
    }, 200);
  }
  _pendingZipPath = null;
}

// ── Progress / Result helpers ─────────────────────────────────────────────────

function _setImportProgress(visible, label = "Đang xử lý…", pct = null) {
  const bar = document.getElementById("importProgress");
  const fill = document.getElementById("importProgressFill");
  const lbl = document.getElementById("importProgressLabel");
  if (!bar) return;
  bar.style.display = visible ? "block" : "none";
  if (lbl) lbl.textContent = label;
  if (fill && pct !== null) fill.style.width = pct + "%";
}

// Dùng showImportResult đã có trong settings.js nếu tồn tại,
// nếu không thì define local
if (typeof showImportResult === "undefined") {
  window.showImportResult = function (type, msg) {
    const el = document.getElementById("importResult");
    if (!el) {
      console.log(`[import] [${type}]`, msg);
      return;
    }
    el.className = `import-result import-result-${type}`;
    el.textContent = (type === "success" ? "✓ " : "✕ ") + msg;
    el.style.display = "block";
    clearTimeout(el._timer);
    el._timer = setTimeout(() => {
      el.style.display = "none";
    }, 5000);
  };
}

// ── CSS inject (model cards) ──────────────────────────────────────────────────

(function injectModelSelectorStyles() {
  if (document.getElementById("__model-selector-css")) return;
  const style = document.createElement("style");
  style.id = "__model-selector-css";
  style.textContent = `
    @keyframes spin { to { transform: rotate(360deg) } }

    .model-selector-grid {
      display: grid;
      grid-template-columns: repeat(${GRID_COLS}, 1fr);
      gap: 12px;
      padding: 4px 2px;
    }

    .model-card {
      border-radius: 12px;
      border: 1.5px solid rgba(255,255,255,0.07);
      background: rgba(255,255,255,0.03);
      cursor: pointer;
      transition: all .18s ease;
      padding: 0;
      overflow: hidden;
      outline: none;
      position: relative;
    }
    .model-card:hover {
      border-color: rgba(124,58,237,0.45);
      background: rgba(124,58,237,0.06);
      transform: translateY(-2px);
      box-shadow: 0 6px 24px rgba(124,58,237,0.15);
    }
    .model-card:focus-visible {
      border-color: rgba(124,58,237,0.7);
      box-shadow: 0 0 0 3px rgba(124,58,237,0.2);
    }
    .model-card--active {
      border-color: rgba(124,58,237,0.7) !important;
      background: rgba(124,58,237,0.08) !important;
      box-shadow: 0 0 0 1px rgba(124,58,237,0.35), 0 6px 24px rgba(124,58,237,0.2);
    }
    .model-card__info {
      padding: 8px 10px 8px;
    }

    /* ZIP config modal backdrop */
    #zipConfigModal {
      display: none;
      position: fixed; inset: 0; z-index: 1000;
      align-items: center; justify-content: center;
      background: rgba(0,0,0,0.6);
      backdrop-filter: blur(6px);
      opacity: 0;
      transition: opacity .2s;
    }
  `;
  document.head.appendChild(style);
})();

// ── Wire up buttons ───────────────────────────────────────────────────────────

document.addEventListener("DOMContentLoaded", () => {
  // Import button trong modal header
  const btnImport = document.getElementById("modalBtnImport");
  if (btnImport) {
    btnImport.addEventListener("click", triggerZipImport);
  }

  // Close ZIP config modal
  const zipModal = document.getElementById("zipConfigModal");
  if (zipModal) {
    zipModal.addEventListener("click", (e) => {
      if (e.target === zipModal) _closeZipConfigModal();
    });
    const closeBtn = zipModal.querySelector(
      ".modal-close, [data-close='zipConfigModal']",
    );
    if (closeBtn) closeBtn.addEventListener("click", _closeZipConfigModal);
  }

  // Reload khi nhận broadcast từ main process (Electron)
  if (window.companion) {
    window.companion.on?.("avatar:registry-updated", () => {
      loadModelSelectorGrid();
    });
  }
});

// ── Util ──────────────────────────────────────────────────────────────────────
function _escHtml(s) {
  return String(s ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

// ── Exports (nếu dùng trong module context) ───────────────────────────────────
if (typeof module !== "undefined" && module.exports) {
  module.exports = { loadModelSelectorGrid, importZipFile, triggerZipImport };
}
