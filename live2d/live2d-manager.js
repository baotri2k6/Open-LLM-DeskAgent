/**
 * live2d-manager.js
 *
 * Quản lý Live2D Cubism 4 Web SDK.
 *
 * Chiến lược 3 tầng:
 *  1. Live2D Cubism 4 SDK (PIXI + CubismSdkForWeb) → đầy đủ tính năng
 *  2. pixi-live2d-display (wrapper đơn giản hơn)
 *  3. Fallback ảnh PNG + CSS animation (không cần SDK)
 */

import {
  normalizeExpression,
  EXPRESSION_MAPPINGS,
} from "./expressions/expression.js";
import {
  normalizeMotion,
  MOTION_MAPPINGS,
  getMotionForEmotion,
} from "./motions/motion.js";
import { SpineBackend } from "./runtime/spine-manager.js";
import { AssetRegistry } from "./asset-registry.js";

// ─── Config ──────────────────────────────────────────────────────────────────

const CUBISM_SDK_URL =
  "https://cubism.live2d.com/sdk-web/cubismcore/live2dcubismcore.min.js";
const LOCAL_CUBISM_SDK_URL = "../shared/vendor/live2dcubismcore.min.js";
const LOCAL_PIXI_URL = "../shared/vendor/pixi.min.js";
const LOCAL_PIXI_LIVE2D_URL = "../shared/vendor/cubism4.min.js";
const PIXI_URL =
  "https://cdnjs.cloudflare.com/ajax/libs/pixi.js/6.5.10/browser/pixi.min.js";
const PIXI_LIVE2D_URL =
  "https://cdn.jsdelivr.net/npm/pixi-live2d-display/dist/cubism4.min.js";

// ─── Helpers ─────────────────────────────────────────────────────────────────

function loadScript(src) {
  return new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = src;
    s.onload = resolve;
    s.onerror = () => reject(new Error(`Failed to load ${src}`));
    document.head.appendChild(s);
  });
}

async function loadPixiLive2D() {
  // pixi-live2d-display bundles PIXI + Live2D glue
  if (!window.Live2DCubismCore) {
    try {
      await loadScript(LOCAL_CUBISM_SDK_URL);
    } catch {
      await loadScript(CUBISM_SDK_URL);
    }
  }
  if (!window.PIXI) {
    try {
      await loadScript(LOCAL_PIXI_URL);
    } catch {
      await loadScript(PIXI_URL);
    }
  }
  if (!window.PIXI?.live2d) {
    // pixi-live2d-display không có CDN public ổn định —
    // thử load từ node_modules nếu packaged, hoặc skip.
    try {
      await loadScript(LOCAL_PIXI_LIVE2D_URL);
    } catch {
      await loadScript(PIXI_LIVE2D_URL);
    }
  }
  return !!window.PIXI?.live2d;
}

// ─── Tầng 1: Live2D Cubism 4 via pixi-live2d-display ────────────────────────

class PixiLive2DBackend {
  constructor(container, modelPath) {
    this._container = container;
    this._modelPath = modelPath;
    this._app = null;
    this._model = null;
  }

  async init() {
    const ok = await loadPixiLive2D();
    if (!ok) return false;

    const { Application } = window.PIXI;
    const { Live2DModel } = window.PIXI.live2d;

    const w = this._container.clientWidth || 280;
    const h = this._container.clientHeight || 390;

    this._app = new PIXI.Application({
      width: w,
      height: h,
      backgroundAlpha: 0,
      transparent: true,
      antialias: true,
      autoDensity: true,
      resolution: window.devicePixelRatio || 1,
      preserveDrawingBuffer: true,
    });
    this._container.appendChild(this._app.view);
    this._app.view.style.cssText =
      "position:absolute;inset:0;width:100%;height:100%;opacity:0;transition:opacity 0.3s ease;";

    try {
      this._model = await Live2DModel.from(this._modelPath, {
        autoInteract: false,
      });
      this._origWidth = this._model.width;
      this._origHeight = this._model.height;
    } catch (err) {
      console.warn("[Live2D] Model load failed:", err);
      this._app.destroy(true);
      return false;
    }

    // Override motionManager.update to reset waving arm and heart trail parameters and apply accessories
    try {
      const motionManager = this._model.internalModel.motionManager;
      const originalUpdate = motionManager.update;
      const self = this;
      motionManager.update = function (model, now) {
        const res = originalUpdate.call(this, model, now);

        // Param58: waving motion (-1 to 1)
        // Param59: waving opacity (0 to 1)
        // Param60: heart trail (0 to 1)
        model.setParameterValueById("Param58", 0);
        model.setParameterValueById("Param59", 0);
        model.setParameterValueById("Param60", 0);

        // Apply active accessories/hairstyles
        if (self._activeAccessories) {
          for (const [pid, val] of Object.entries(self._activeAccessories)) {
            model.setParameterValueById(pid, val);
          }
        }
        return res;
      };
    } catch (err) {
      console.warn("[Live2D] Failed to override motionManager.update:", err);
    }

    this._app.stage.addChild(this._model);
    this._fitModel(w, h);

    // Listen to container resizing (e.g. from Electron window resizing)
    this._onResize = () => {
      if (this._app && this._app.renderer && this._model) {
        const cw = this._container.clientWidth || 280;
        const ch = this._container.clientHeight || 390;
        this._app.renderer.resize(cw, ch);
        this._fitModel(cw, ch);
      }
    };
    window.addEventListener("resize", this._onResize);

    // Use ResizeObserver to reliably detect layout size stabilization on startup and toggling
    this._resizeObserver = new ResizeObserver(() => {
      if (this._onResize) {
        this._onResize();
      }
    });
    this._resizeObserver.observe(this._container);

    // Eye tracking: update model focus coordinates on cursor move
    this._pointerMoveHandler = (e) => {
      if (this._model) {
        this._model.focus(e.clientX, e.clientY);
      }
    };
    window.addEventListener("pointermove", this._pointerMoveHandler);

    // Fade in sau khi model đã render xong 1 frame
    requestAnimationFrame(() => {
      if (this._app?.view) this._app.view.style.opacity = "1";
    });
    console.info("[Live2D] pixi-live2d-display backend ready");
    return true;
  }

  _fitModel(w, h) {
    if (!this._model) return;

    // Scale from registry — avoids hardcoded per-model overrides
    const modelId = AssetRegistry.resolvePathToId(this._modelPath);
    const scaleMultiplier = AssetRegistry.getScale(modelId);

    // Get true original size from Live2D core model canvas size to prevent scaling accumulation bugs
    const coreModel = this._model.internalModel?.coreModel;
    const origW =
      coreModel?.canvasWidth || this._model.internalModel?.originalWidth || 400;
    const origH =
      coreModel?.canvasHeight ||
      this._model.internalModel?.originalHeight ||
      500;

    const scale = Math.min(w / origW, h / origH) * scaleMultiplier;
    this._model.scale.set(scale);
    this._model.position.set(w / 2, h * 0.98);
    this._model.anchor.set(0.5, 1.0);
  }

  setAccessory(paramId, value) {
    if (!this._activeAccessories) {
      this._activeAccessories = {};
    }
    if (Array.isArray(paramId)) {
      paramId.forEach((pid) => {
        this._activeAccessories[pid] = value;
      });
    } else {
      this._activeAccessories[paramId] = value;
    }
  }

  setExpression(expressionName) {
    const modelId = AssetRegistry.resolvePathToId(this._modelPath);
    const exprMapping = EXPRESSION_MAPPINGS[modelId];
    if (!exprMapping) return;

    const live2dName = exprMapping[expressionName];
    if (live2dName) {
      try {
        this._model?.expression(live2dName);
      } catch (err) {
        console.warn(
          `[Live2D] Failed to set expression ${expressionName} for ${modelId}:`,
          err,
        );
      }
    } else {
      // Check registry for expression-to-motion fallback mapping (e.g. Hiyori)
      const fallbackMap = AssetRegistry.getExpressionFallback(modelId);
      const motionFallback = fallbackMap[expressionName];
      if (motionFallback) {
        this.playMotion(motionFallback);
      }
    }
  }

  playMotion(motionName) {
    const modelId = AssetRegistry.resolvePathToId(this._modelPath);
    const mapping = MOTION_MAPPINGS[modelId]?.[motionName];
    if (!mapping) return;

    try {
      if (typeof mapping === "string") {
        this._model?.motion(mapping);
      } else if (mapping.group !== undefined) {
        if (mapping.index !== undefined) {
          this._model?.motion(mapping.group, mapping.index);
        } else {
          this._model?.motion(mapping.group);
        }
      }
    } catch (err) {
      console.warn(
        `[Live2D] Failed to play motion ${motionName} for ${modelKey}:`,
        err,
      );
    }
  }

  startLipSync(amplitude = 0.5) {
    if (!this._model) return;
    // pixi-live2d-display dùng internalModel để set param
    try {
      this._model.internalModel.coreModel.setParameterValueById(
        "ParamMouthOpenY",
        amplitude,
      );
    } catch {
      /* param not available */
    }
  }

  stopLipSync() {
    this.startLipSync(0);
  }

  containsPoint(x, y) {
    if (!this._model) return false;
    const bounds = this._model.getBounds();
    const isInsideBounds =
      x >= bounds.x &&
      x <= bounds.x + bounds.width &&
      y >= bounds.y &&
      y <= bounds.y + bounds.height;
    if (!isInsideBounds) return false;

    // Inside bounds, now check pixel alpha channel
    try {
      const canvas = this._app.view;
      const gl =
        canvas.getContext("webgl2") ||
        canvas.getContext("webgl") ||
        canvas.getContext("experimental-webgl");
      if (!gl) return true; // Fallback if no WebGL context found

      const rect = canvas.getBoundingClientRect();
      const canvasX = x - rect.left;
      const canvasY = y - rect.top;

      const glX = Math.floor(canvasX * (gl.drawingBufferWidth / rect.width));
      const glY = Math.floor(
        gl.drawingBufferHeight -
          canvasY * (gl.drawingBufferHeight / rect.height),
      );

      if (
        glX < 0 ||
        glX >= gl.drawingBufferWidth ||
        glY < 0 ||
        glY >= gl.drawingBufferHeight
      ) {
        return false;
      }

      const pixels = new Uint8Array(4);
      gl.readPixels(glX, glY, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixels);
      const alpha = pixels[3];
      return alpha > 10; // returns true if pixel is mostly visible/opaque
    } catch (e) {
      console.warn("[Live2D] Failed to read pixel alpha", e);
      return true; // Fallback to true if we hit any errors
    }
  }

  handleTap(x, y) {
    if (!this._model) return null;
    let hitAreas = this._model.hitTest(x, y) || [];
    console.log("[Live2D] Tap at", x, y, "hitAreas:", hitAreas);

    const modelId = AssetRegistry.resolvePathToId(this._modelPath);

    // If the model does not have hit areas defined, estimate based on click height
    if (hitAreas.length === 0) {
      hitAreas.push(y < 200 ? "HitAreaHead" : "HitAreaBody");
    }

    const isHead = hitAreas.some((a) =>
      ["HitAreaHead", "Head"].includes(a),
    );
    const isBody = hitAreas.some((a) =>
      ["HitAreaBody", "Body", "HitArea"].includes(a),
    );

    const area = isHead ? "head" : isBody ? "body" : null;
    if (!area) return null;

    const reactions = AssetRegistry.getHitReactions(modelId, area);
    if (reactions.length === 0) return null;
    return reactions[Math.floor(Math.random() * reactions.length)];
  }

  destroy() {
    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }
    if (this._onResize) {
      window.removeEventListener("resize", this._onResize);
      this._onResize = null;
    }
    if (this._pointerMoveHandler) {
      window.removeEventListener("pointermove", this._pointerMoveHandler);
      this._pointerMoveHandler = null;
    }
    if (this._app) {
      this._app.destroy(true);
      this._app = null;
    }
    this._model = null;
    this._origWidth = null;
    this._origHeight = null;
  }
}

// ─── Tầng 2: CSS/Image fallback ─────────────────────────────────────────────

class CSSFallbackBackend {
  constructor(wrap, imgEl, lightEl) {
    this._wrap = wrap;
    this._img = imgEl;
    this._light = lightEl;
    this._lipInterval = null;
  }

  async init() {
    console.info("[Live2D] Using CSS fallback backend");
    // Show lại img vì mặc định đã bị ẩn
    if (this._img) {
      this._img.style.display = "block";
      this._img.style.visibility = "visible";
    }
    return true;
  }

  setAccessory(paramId, value) {
    // No-op for CSS fallback
  }

  setExpression(name) {
    if (this._wrap) this._wrap.dataset.expression = name;
    if (this._light) this._light.dataset.expression = name;
  }

  playMotion(name) {
    if (!this._wrap) return;
    this._wrap.dataset.motion = name;
    // reset về idle sau animation
    setTimeout(() => {
      if (this._wrap) this._wrap.dataset.motion = "idle";
    }, 1200);
  }

  startLipSync() {
    if (this._lipInterval) return;
    let phase = 0;
    this._lipInterval = setInterval(() => {
      phase += 0.4;
      const amp = 0.4 + 0.6 * Math.abs(Math.sin(phase));
      if (this._wrap) this._wrap.dataset.lipsync = amp.toFixed(2);
    }, 60);
    if (this._wrap) this._wrap.classList.add("lipsync-active");
  }

  stopLipSync() {
    if (this._lipInterval) {
      clearInterval(this._lipInterval);
      this._lipInterval = null;
    }
    if (this._wrap) {
      this._wrap.classList.remove("lipsync-active");
      this._wrap.removeAttribute("data-lipsync");
    }
  }

  containsPoint(x, y) {
    const w = this._wrap.clientWidth || 280;
    const h = this._wrap.clientHeight || 390;
    return x >= w * 0.15 && x <= w * 0.85 && y >= h * 0.05 && y <= h * 0.95;
  }

  destroy() {
    this.stopLipSync();
  }
}

// ─── AvatarController (public API) ──────────────────────────────────────────

export class AvatarController {
  /**
   * @param {{wrap: HTMLElement, light: HTMLElement, img?: HTMLElement}} opts
   */
  constructor({ wrap, light, img }) {
    this._wrap = wrap;
    this._light = light;
    this._img = img ?? wrap?.querySelector("#avatarImage");
    if (this._img) {
      this._img.style.display = "none"; // Hide fallback image immediately on constructor
    }
    this._spineCanvas = wrap?.querySelector("#spineCanvas");
    this._backend = null;
    this._state = { expression: "normal", motion: "idle" };
    // Temporary fallback path — will be overwritten in _init once registry is loaded
    this._modelPath = "../../assets/live2d/IceGirl/IceGirl.model3.json";
    this.readyPromise = this._init();
  }

  async _init() {
    console.log("[AvatarController] Initializing...");
    // Load the asset registry first — all subsequent logic reads from it
    await AssetRegistry.load();

    // Set default path from registry so constructor fallback is no longer needed
    this._modelPath = AssetRegistry.getModelPath(AssetRegistry.getDefault()?.id ?? "icegirl");
    console.log("[AvatarController] Default model path from registry:", this._modelPath);

    // Try to override with saved config
    try {
      if (window.companion) {
        console.log("[AvatarController] window.companion is available, calling ai:get-config...");
        const res = await window.companion.invoke("ai:get-config");
        console.log("[AvatarController] Config response:", res);
        if (res && res.avatar_model && !res.error) {
          let path = res.avatar_model;
          console.log("[AvatarController] Config saved avatar_model:", path);
          if (path.endsWith(".vrm")) {
            // VRM not supported — reset to default
            path = AssetRegistry.getDefault()?.path ?? "assets/live2d/IceGirl/IceGirl.model3.json";
            window.companion
              .invoke("ai:update-config", { key: "app.avatarModel", value: path })
              .catch(() => null);
          }
          this._modelPath = "../../" + path;
          console.log("[AvatarController] Updated _modelPath to:", this._modelPath);
        } else {
          console.log("[AvatarController] Config does not contain valid avatar_model or error occurred.");
        }
      } else {
        console.log("[AvatarController] window.companion is NOT available!");
      }
    } catch (err) {
      console.warn("[AvatarController] Failed to load initial config:", err);
    }

    console.log("[AvatarController] Loading backend with path:", this._modelPath);
    await this._loadBackend();

    // idle blinking loop
    this._startIdleLoop();
  }

  async _loadBackend() {
    const pathLower = this._modelPath.toLowerCase();
    const isSpine =
      pathLower.endsWith(".json") && !pathLower.endsWith(".model3.json");

    if (isSpine) {
      if (this._spineCanvas) {
        this._spineCanvas.style.display = "block";
      }
      const spineBackend = new SpineBackend(
        this._wrap,
        this._spineCanvas,
        this._modelPath,
      );
      const spineOk = await spineBackend.init().catch(() => false);
      if (spineOk) {
        this._backend = spineBackend;
        if (this._img) this._img.style.display = "none";
        return;
      }
    }

    // Hide Spine canvas if Live2D or Fallback is used
    if (this._spineCanvas) {
      this._spineCanvas.style.display = "none";
    }

    const pixiBackend = new PixiLive2DBackend(this._wrap, this._modelPath);
    const pixiOk = await pixiBackend.init().catch(() => false);

    if (pixiOk) {
      this._backend = pixiBackend;
      if (this._img) this._img.style.display = "none";
    } else {
      this._backend = new CSSFallbackBackend(
        this._wrap,
        this._img,
        this._light,
      );
      await this._backend.init();
    }
  }

  /**
   * Switch to a different model.
   * Accepts either a model id (e.g. "huohuo") or a relative file path
   * (e.g. "assets/live2d/huohuo2/huohuo2.model3.json").
   * @param {string} modelIdOrPath
   */
  async changeModel(modelIdOrPath) {
    console.log("[AvatarController] Changing model to:", modelIdOrPath);
    this.destroy();

    // Clear any residual canvas elements from wrapper EXCEPT spineCanvas
    const canvases = this._wrap.querySelectorAll("canvas");
    canvases.forEach((c) => {
      if (c !== this._spineCanvas) c.remove();
    });
    if (this._img) this._img.style.display = "none";

    // Resolve via registry: accepts both id and path
    const resolvedId = AssetRegistry.resolvePathToId(modelIdOrPath);
    this._modelPath = AssetRegistry.getModelPath(resolvedId);
    await this._loadBackend();
  }

  setAccessory(paramId, value) {
    this._backend?.setAccessory(paramId, value);
  }

  setState({ expression, emotion, motion, lipsync } = {}) {
    const expr = normalizeExpression(expression ?? emotion ?? "normal");
    const requestedMotion =
      motion ?? (emotion ? getMotionForEmotion(emotion) : undefined) ?? "idle";
    const mot = normalizeMotion(requestedMotion);

    if (expr !== this._state.expression) {
      this._state.expression = expr;
      this._backend?.setExpression(expr);
    }
    if (mot !== this._state.motion) {
      this._state.motion = mot;
      this._backend?.playMotion(mot);
    }

    if (lipsync === true) this.startLipSync();
    else if (lipsync === false) this.stopLipSync();
  }

  startLipSync(durationMs = 0) {
    this._backend?.startLipSync();
    if (durationMs > 0) {
      setTimeout(() => this.stopLipSync(), durationMs);
    }
  }

  stopLipSync() {
    this._backend?.stopLipSync();
  }

  containsPoint(x, y) {
    if (this._backend && typeof this._backend.containsPoint === "function") {
      return this._backend.containsPoint(x, y);
    }
    const w = this._wrap.clientWidth || 280;
    const h = this._wrap.clientHeight || 390;
    return x >= w * 0.15 && x <= w * 0.85 && y >= h * 0.05 && y <= h * 0.95;
  }

  handleTap(x, y) {
    if (this._backend && typeof this._backend.handleTap === "function") {
      const reaction = this._backend.handleTap(x, y);
      if (reaction) {
        this.setState(reaction);
        return;
      }
    }
    // Fallback if no hit area matched or not a live2d backend
    const defaultReactions = [
      { expression: "smile", motion: "nod" },
      { expression: "happy", motion: "excited" },
      { expression: "wink", motion: "nod" },
      { expression: "surprised", motion: "nod" },
      { expression: "smile", motion: "look_side" },
    ];
    const reaction =
      defaultReactions[Math.floor(Math.random() * defaultReactions.length)];
    this.setState(reaction);
  }

  /**
   * Lipsync tự động theo duration của TTS audio.
   */
  syncWithAudio(audioEl) {
    if (!audioEl) return;
    audioEl.addEventListener("play", () => this.startLipSync(), {
      once: false,
    });
    audioEl.addEventListener("pause", () => this.stopLipSync(), {
      once: false,
    });
    audioEl.addEventListener("ended", () => this.stopLipSync(), {
      once: false,
    });
  }

  _startIdleLoop() {
    // Ngẫu nhiên blink và motion nhỏ mỗi 4-8s
    const scheduleNext = () => {
      const delay = 4000 + Math.random() * 4000;
      setTimeout(() => {
        if (this._state.motion === "idle") {
          const motions = ["idle", "idle", "idle", "look_side", "nod"];
          const m = motions[Math.floor(Math.random() * motions.length)];
          if (m !== "idle") this._backend?.playMotion(m);
        }
        scheduleNext();
      }, delay);
    };
    scheduleNext();
  }

  destroy() {
    this.stopLipSync();
    this._backend?.destroy();
    this._backend = null;
  }
}
