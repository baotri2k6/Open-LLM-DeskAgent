/**
 * vrm-manager.js
 *
 * VRM 3D character renderer using Three.js + @pixiv/three-vrm.
 * Features:
 *  - Mouse head/eye tracking (character looks at cursor)
 *  - Breathing idle with 3D body sway
 *  - Auto-blink
 *  - Expression system
 *  - Pixel-accurate click-through
 */

// Modules resolved via importmap in index.html
const THREE_URL = "three";
const THREE_VRM_URL = "@pixiv/three-vrm";
const GLTF_LOADER_URL = "three/examples/jsm/loaders/GLTFLoader.js";

let _loadedModules = null;

async function ensureModules() {
  if (_loadedModules) return _loadedModules;
  const THREE = await import(THREE_URL);
  const { GLTFLoader } = await import(GLTF_LOADER_URL);
  const { VRMLoaderPlugin, VRMUtils } = await import(THREE_VRM_URL);
  _loadedModules = { THREE, GLTFLoader, VRMLoaderPlugin, VRMUtils };
  console.log("[VRM] Modules loaded OK");
  return _loadedModules;
}

export class VRMBackend {
  constructor(wrap, modelPath) {
    this._wrap = wrap;
    this._modelPath = modelPath;
    this._canvas = null;
    this._renderer = null;
    this._scene = null;
    this._camera = null;
    this._vrm = null;
    this._clock = null;
    this._animFrame = null;
    this._destroyed = false;
    this._lipSyncActive = false;
    this._VRMUtils = null;
    this._THREE = null;
    this._resizeObserver = null;

    // Mouse tracking state (normalized -1 to 1)
    this._mouseX = 0;
    this._mouseY = 0;
    // Smoothed tracking values
    this._headTargetX = 0;
    this._headTargetY = 0;
    this._smoothHeadX = 0;
    this._smoothHeadY = 0;
    this._bodyTargetX = 0;
    this._smoothBodyX = 0;

    // Blink state machine
    this._blinkTimer = 0;
    this._blinkInterval = 3.5 + Math.random() * 2;
    this._blinking = false;
    this._blinkPhase = 0;

    // Bind mouse handler
    this._onMouseMove = this._onMouseMove.bind(this);
    this._onMouseDown = this._onMouseDown.bind(this);
    this._onMouseUp = this._onMouseUp.bind(this);
    this._onConfigUpdated = this._onConfigUpdated.bind(this);

    // Mouse drag rotation state
    this._isDragging = false;
    this._dragStartX = 0;
    this._dragStartY = 0;
    this._baseTheta = 0;
    this._basePhi = Math.PI / 2;
  }

  _onMouseDown(e) {
    if (e.button !== 0) return; // Left click only
    const rect = this._wrap.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;
    if (this.containsPoint(x, y)) {
      this._isDragging = true;
      this._dragStartX = e.clientX;
      this._dragStartY = e.clientY;
      this._baseTheta = this._theta;
      this._basePhi = this._phi;
      e.preventDefault();
    }
  }

  _onMouseUp(e) {
    this._isDragging = false;
  }

  _onMouseMove(e) {
    const winW = window.innerWidth;
    const winH = window.innerHeight;
    this._mouseX = (e.clientX / winW) * 2 - 1;   // -1 left, +1 right
    this._mouseY = -((e.clientY / winH) * 2 - 1); // -1 bottom, +1 top

    if (this._isDragging && this._camera) {
      const dx = e.clientX - this._dragStartX;
      const dy = e.clientY - this._dragStartY;
      
      // Update spherical angles based on drag delta
      this._theta = this._baseTheta - dx * 0.01;
      this._phi = Math.max(0.1, Math.min(Math.PI - 0.1, this._basePhi - dy * 0.008));
      
      this._updateCameraPosition();
    }
  }

  _onConfigUpdated({ key, value }) {
    if (!this._vrm || !this._camera) return;
    try {
      if (key.startsWith("3d.")) {
        const subKey = key.split(".")[1];
        const num = parseFloat(value);
        
        switch (subKey) {
          case "pos_x":
            if (this._modelOffset) this._modelOffset.x = num;
            break;
          case "pos_y":
            if (this._modelOffset) this._modelOffset.y = num;
            break;
          case "pos_z":
            if (this._modelOffset) this._modelOffset.z = num;
            break;
          case "fov":
            this._camera.fov = num;
            this._camera.updateProjectionMatrix();
            break;
          case "distance":
            this._cameraRadius = num;
            this._updateCameraPosition();
            break;
          case "rotation_y":
            this._theta = (num * Math.PI) / 180;
            this._updateCameraPosition();
            break;
          case "light_color":
            if (this._dirLight) this._dirLight.color.set(value.slice(0, 7));
            break;
          case "light_intensity":
            if (this._dirLight) this._dirLight.intensity = num;
            break;
          case "ambient_color":
            if (this._ambientLight) this._ambientLight.color.set(value.slice(0, 7));
            break;
          case "ambient_intensity":
            if (this._ambientLight) this._ambientLight.intensity = num;
            break;
          case "hemi_intensity":
            if (this._hemiLight) this._hemiLight.intensity = num;
            break;
          case "hemi_sky_color":
            if (this._hemiLight) this._hemiLight.color.set(value.slice(0, 7));
            break;
          case "hemi_ground_color":
            if (this._hemiLight) this._hemiLight.groundColor.set(value.slice(0, 7));
            break;
        }
      }
    } catch (e) {
      console.warn("[VRM] Failed to apply config update:", e);
    }
  }

  _updateCameraPosition() {
    if (!this._camera || !this._cameraTarget) return;
    
    // Calculate new position using spherical coordinates
    this._camera.position.x = this._cameraTarget.x + this._cameraRadius * Math.sin(this._phi) * Math.sin(this._theta);
    this._camera.position.y = this._cameraTarget.y + this._cameraRadius * Math.cos(this._phi);
    this._camera.position.z = this._cameraTarget.z + this._cameraRadius * Math.sin(this._phi) * Math.cos(this._theta);
    
    this._camera.lookAt(this._cameraTarget);
  }

  async init() {
    try {
      const { THREE, GLTFLoader, VRMLoaderPlugin, VRMUtils } = await ensureModules();
      this._THREE = THREE;
      this._VRMUtils = VRMUtils;

      // ── Canvas ──────────────────────────────────────────────────
      this._canvas = document.createElement("canvas");
      this._canvas.style.cssText = `
        position: absolute;
        top: 0; left: 0;
        width: 100%; height: 100%;
        pointer-events: none;
        z-index: 5;
      `;
      this._wrap.appendChild(this._canvas);

      const w = this._wrap.clientWidth || 300;
      const h = this._wrap.clientHeight || 500;
      this._canvas.width = Math.round(w * (window.devicePixelRatio || 1));
      this._canvas.height = Math.round(h * (window.devicePixelRatio || 1));

      // ── Renderer ────────────────────────────────────────────────
      this._renderer = new THREE.WebGLRenderer({
        canvas: this._canvas,
        alpha: true,
        antialias: true,
        preserveDrawingBuffer: true,   // Required for containsPoint pixel read
      });
      this._renderer.setSize(w, h, false);
      this._renderer.setPixelRatio(window.devicePixelRatio || 1);
      this._renderer.setClearColor(0x000000, 0);
      this._renderer.outputColorSpace = THREE.SRGBColorSpace;
      this._renderer.shadowMap.enabled = false;

      // ── Scene ───────────────────────────────────────────────────
      this._scene = new THREE.Scene();

      // ── Load 3D Config ──────────────────────────────────────────
      let config3d = {};
      try {
        if (window.companion) {
          const cfg = await window.companion.invoke("ai:get-config", {});
          config3d = cfg?.["3d"] || {};
        }
      } catch (e) {
        console.warn("[VRM] Could not load config:", e);
      }

      this._modelOffset = new THREE.Vector3(
        parseFloat(config3d.pos_x ?? "0.0"),
        parseFloat(config3d.pos_y ?? "0.0"),
        parseFloat(config3d.pos_z ?? "0.0")
      );

      // ── Camera — wider FOV shows 3D depth ──────────────────────
      const fov = parseFloat(config3d.fov ?? "45");
      this._camera = new THREE.PerspectiveCamera(fov, w / h, 0.1, 20);
      this._cameraTarget = new THREE.Vector3(0, 1.15, 0);
      
      // Calculate initial angles
      this._cameraRadius = parseFloat(config3d.distance ?? "1.45");
      const initialRotY = parseFloat(config3d.rotation_y ?? "0");
      this._theta = (initialRotY * Math.PI) / 180;
      this._phi = Math.PI / 2; // face straight
      
      this._updateCameraPosition();

      // ── Lights ──────────────────────────────────────────────────
      const ambColor = config3d.ambient_color ?? "#ffffffff";
      const ambIntensity = parseFloat(config3d.ambient_intensity ?? "0.60");
      this._ambientLight = new THREE.AmbientLight(ambColor.slice(0, 7), ambIntensity);
      this._scene.add(this._ambientLight);

      // Key Directional Light
      const keyColor = config3d.light_color ?? "#fffbf5ff";
      const keyIntensity = parseFloat(config3d.light_intensity ?? "2.02");
      this._dirLight = new THREE.DirectionalLight(keyColor.slice(0, 7), keyIntensity);
      this._dirLight.position.set(-1.5, 3, 3);
      this._scene.add(this._dirLight);

      // Hemisphere environment light
      const hemiSky = config3d.hemi_sky_color ?? "#ffffffff";
      const hemiGround = config3d.hemi_ground_color ?? "#222222ff";
      const hemiIntensity = parseFloat(config3d.hemi_intensity ?? "0.40");
      this._hemiLight = new THREE.HemisphereLight(hemiSky.slice(0, 7), hemiGround.slice(0, 7), hemiIntensity);
      this._scene.add(this._hemiLight);

      // Rim light (back, gives 3D separation from background)
      const rimLight = new THREE.DirectionalLight(0xffffff, 0.4);
      rimLight.position.set(0, 2, -3);
      this._scene.add(rimLight);

      // ── Load VRM ────────────────────────────────────────────────
      const loader = new GLTFLoader();
      loader.register((parser) => new VRMLoaderPlugin(parser));

      let resolvedPath = this._modelPath;
      if (resolvedPath.startsWith("assets/")) {
        resolvedPath = "../../" + resolvedPath;
      }

      console.log("[VRM] Loading:", resolvedPath);
      const gltf = await new Promise((resolve, reject) => {
        loader.load(resolvedPath, resolve,
          (xhr) => { if (xhr.total > 0) console.log(`[VRM] ${Math.round(xhr.loaded/xhr.total*100)}%`); },
          reject
        );
      });

      const vrm = gltf.userData.vrm;
      if (!vrm) throw new Error("No VRM data found");
      this._vrm = vrm;

      // ── Fix facing direction ────────────────────────────────────
      // VRM0: specVersion exists → faces +Z (toward camera) → no rotation
      // VRM1: no specVersion → faces -Z (away) → rotate π
      const isVRM0 = typeof vrm.meta?.specVersion === "string";
      console.log("[VRM] version:", isVRM0 ? "VRM0" : "VRM1", vrm.meta);
      if (!isVRM0) vrm.scene.rotation.y = Math.PI;

      // ── Optimize ────────────────────────────────────────────────
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      try { VRMUtils.combineSkeletons(gltf.scene); } catch {}

      this._scene.add(vrm.scene);

      // ── Resize observer ─────────────────────────────────────────
      this._resizeObserver = new ResizeObserver(() => this._onResize());
      this._resizeObserver.observe(this._wrap);

      // ── Mouse tracking & Drag rotation ──────────────────────────
      window.addEventListener("mousemove", this._onMouseMove);
      window.addEventListener("mousedown", this._onMouseDown);
      window.addEventListener("mouseup", this._onMouseUp);
      if (window.companion) {
        window.companion.on("config:updated", this._onConfigUpdated);
      }

      // ── Clock & render loop ─────────────────────────────────────
      this._clock = new THREE.Clock();
      this._renderLoop();

      console.log("[VRM] Ready!");
      return true;
    } catch (err) {
      console.error("[VRM] init failed:", err);
      this._destroyCanvas();
      return false;
    }
  }

  _onResize() {
    if (!this._renderer || !this._camera) return;
    const w = this._wrap.clientWidth || 300;
    const h = this._wrap.clientHeight || 500;
    this._camera.aspect = w / h;
    this._camera.updateProjectionMatrix();
    this._renderer.setSize(w, h, false);
    this._canvas.width = Math.round(w * (window.devicePixelRatio || 1));
    this._canvas.height = Math.round(h * (window.devicePixelRatio || 1));
  }

  _renderLoop() {
    const tick = () => {
      if (this._destroyed) return;
      this._animFrame = requestAnimationFrame(tick);
      const delta = Math.min(this._clock.getDelta(), 0.05); // cap at 50ms
      const t = performance.now() / 1000;

      if (this._vrm && this._vrm.humanoid) {
        const humanoid = this._vrm.humanoid;

        // ── Smooth mouse tracking ──────────────────────────────
        const lerpFactor = 1 - Math.pow(0.05, delta);
        this._headTargetX = this._mouseX * 0.4;   // max ±0.4 rad
        this._headTargetY = this._mouseY * 0.25;  // max ±0.25 rad
        this._bodyTargetX = this._mouseX * 0.15;  // body follows less

        this._smoothHeadX += (this._headTargetX - this._smoothHeadX) * lerpFactor;
        this._smoothHeadY += (this._headTargetY - this._smoothHeadY) * lerpFactor;
        this._smoothBodyX += (this._bodyTargetX - this._smoothBodyX) * lerpFactor;

        // ── Breathing (spine/chest oscillation) ───────────────
        const breathe = Math.sin(t * 1.1) * 0.018;
        const breatheSlow = Math.sin(t * 0.55) * 0.01;

        // ── 3D body sway ───────────────────────────────────────
        const sway = Math.sin(t * 0.7) * 0.012;  // side sway
        const bobY = Math.sin(t * 1.1) * 0.008;  // up-down bob

        // Apply to bones
        const applyBone = (boneName, rx, ry, rz) => {
          const bone = humanoid.getNormalizedBoneNode(boneName);
          if (bone) {
            bone.rotation.x = rx || 0;
            bone.rotation.y = ry || 0;
            bone.rotation.z = rz || 0;
          }
        };

        // Spine: breathing depth + sway
        applyBone("spine", breathe * 0.5, this._smoothBodyX * 0.3, sway * 0.5);
        // Chest: main breathing
        applyBone("chest", breathe, this._smoothBodyX * 0.4, sway * 0.3);
        // Upper chest
        applyBone("upperChest", breathe * 0.5, this._smoothBodyX * 0.3, 0);
        // Hips: counter-sway for natural movement
        applyBone("hips", breatheSlow, 0, -sway * 0.4);
        // Neck: intermediate between body and head
        applyBone("neck", this._smoothHeadY * 0.3, this._smoothHeadX * 0.4, 0);
        // Head: main tracking
        applyBone("head",
          this._smoothHeadY * 0.7 + Math.sin(t * 0.5) * 0.01,
          this._smoothHeadX * 0.6,
          Math.sin(t * 0.4) * 0.008
        );

        // Arms default standing pose (A-pose)
        // Inverting Z rotations: positive Z for left upper arm, negative Z for right upper arm
        applyBone("leftUpperArm", 0, 0, 1.15);
        applyBone("rightUpperArm", 0, 0, -1.15);
        
        // Lower arms bent slightly forward/inward
        applyBone("leftLowerArm", 0.25, 0.1, 0);
        applyBone("rightLowerArm", 0.25, -0.1, 0);

        // Apply positions
        if (this._vrm.scene && this._modelOffset) {
          this._vrm.scene.position.copy(this._modelOffset);
          this._vrm.scene.position.y += bobY;
        }

        // ── Eye gaze tracking ──────────────────────────────────
        if (this._vrm.lookAt) {
          // Make character look at the camera (user) so they maintain eye contact during rotation
          this._vrm.lookAt.target = this._camera;
        }

        // ── Auto blink ─────────────────────────────────────────
        this._blinkTimer += delta;
        if (!this._blinking && this._blinkTimer >= this._blinkInterval) {
          this._blinking = true;
          this._blinkPhase = 0;
          this._blinkTimer = 0;
          this._blinkInterval = 2.5 + Math.random() * 3.5;
        }
        if (this._blinking && this._vrm.expressionManager) {
          this._blinkPhase += delta * 8; // blink speed
          const blinkCurve = Math.sin(this._blinkPhase * Math.PI);
          try {
            this._vrm.expressionManager.setValue("blink", Math.max(0, blinkCurve));
          } catch {}
          if (this._blinkPhase >= 1) {
            this._blinking = false;
            try { this._vrm.expressionManager.setValue("blink", 0); } catch {}
          }
        }
      }

      if (this._vrm) this._vrm.update(delta);
      this._renderer.render(this._scene, this._camera);
    };
    tick();
  }

  setExpression(expr) {
    if (!this._vrm?.expressionManager) return;
    const em = this._vrm.expressionManager;
    ["happy", "sad", "angry", "surprised", "relaxed", "neutral"].forEach(
      (e) => { try { em.setValue(e, 0); } catch {} }
    );
    const MAP = {
      smile: "happy", excited: "happy", friendly: "happy", happy: "happy",
      sad: "sad", angry: "angry", surprised: "surprised",
      thinking: "relaxed", focused: "relaxed", normal: "neutral", wink: "happy",
    };
    try { em.setValue(MAP[expr] || "neutral", 1.0); } catch {}
  }

  playMotion(_motion) { /* Motion via AnimationMixer — future enhancement */ }

  startLipSync() {
    this._lipSyncActive = true;
    if (!this._vrm?.expressionManager) return;
    try { this._vrm.expressionManager.setValue("aa", 0.55); } catch {}
  }

  stopLipSync() {
    this._lipSyncActive = false;
    if (!this._vrm?.expressionManager) return;
    try { this._vrm.expressionManager.setValue("aa", 0); } catch {}
  }

  containsPoint(x, y) {
    // Pixel-accurate alpha check (preserveDrawingBuffer: true required)
    if (this._renderer && this._canvas) {
      try {
        const gl = this._renderer.getContext();
        const ratio = window.devicePixelRatio || 1;
        const cx = Math.round(x * ratio);
        const ch = this._canvas.height;
        const cy = Math.round(ch - y * ratio); // WebGL Y is flipped
        const cw = this._canvas.width;
        if (cx >= 0 && cx < cw && cy >= 0 && cy < ch) {
          const pixel = new Uint8Array(4);
          gl.readPixels(cx, cy, 1, 1, gl.RGBA, gl.UNSIGNED_BYTE, pixel);
          return pixel[3] > 10; // alpha > 10/255 = has content
        }
      } catch { /* fall through */ }
    }
    // Bounding box fallback
    const w = this._wrap.clientWidth || 300;
    const h = this._wrap.clientHeight || 500;
    return x >= w * 0.1 && x <= w * 0.9 && y >= h * 0.02 && y <= h * 0.95;
  }

  _destroyCanvas() {
    if (this._animFrame) cancelAnimationFrame(this._animFrame);
    this._animFrame = null;
    if (this._resizeObserver) this._resizeObserver.disconnect();
    window.removeEventListener("mousemove", this._onMouseMove);
    window.removeEventListener("mousedown", this._onMouseDown);
    window.removeEventListener("mouseup", this._onMouseUp);
    if (window.companion) {
      window.companion.off("config:updated", this._onConfigUpdated);
    }
    if (this._canvas?.parentNode) this._canvas.parentNode.removeChild(this._canvas);
    this._canvas = null;
  }

  destroy() {
    this._destroyed = true;
    this._destroyCanvas();
    if (this._renderer) { this._renderer.dispose(); this._renderer = null; }
    if (this._vrm && this._VRMUtils) {
      try { this._VRMUtils.deepDispose(this._vrm.scene); } catch {}
    }
    this._vrm = null;
    this._scene = null;
    this._camera = null;
    this._clock = null;
  }
}
