/**
 * vrm-manager.js
 *
 * VRM 3D character renderer using Three.js + @pixiv/three-vrm.
 * Features:
 *  - Mouse head/eye tracking (character looks at cursor)
 *  - Breathing idle with 3D body sway & micro-jitter
 *  - Auto-blink (speeds up during thinking state)
 *  - Smooth expression transition (lerping & blending)
 *  - AnimationMixer with procedural clips (nod, wave, shake) and external .vrma loader
 *  - Pixel-accurate click-through
 */

// Modules resolved via importmap in index.html
const THREE_URL = "three";
const THREE_VRM_URL = "@pixiv/three-vrm";
const GLTF_LOADER_URL = "three/examples/jsm/loaders/GLTFLoader.js";
const THREE_VRM_ANIM_URL = "@pixiv/three-vrm-animation";

let _loadedModules = null;

async function ensureModules() {
  if (_loadedModules) return _loadedModules;
  const THREE = await import(THREE_URL);
  const { GLTFLoader } = await import(GLTF_LOADER_URL);
  const { VRMLoaderPlugin, VRMUtils } = await import(THREE_VRM_URL);
  const { VRMAnimationLoaderPlugin, createVRMAnimationClip } = await import(THREE_VRM_ANIM_URL);
  _loadedModules = { THREE, GLTFLoader, VRMLoaderPlugin, VRMUtils, VRMAnimationLoaderPlugin, createVRMAnimationClip };
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
    this._isThinking = false;

    // Expression target and transition states
    this._exprTarget = "neutral";
    this._exprSecondary = null;
    this._exprSecondaryWeight = 0.4;
    this._exprValues = {};

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

    // Camera orbit parameters
    this._cameraTarget = null;
    this._cameraRadius = 3.5;
    this._theta = 0; // horizontal angle
    this._phi = Math.PI / 2; // vertical angle

    // Light and model offset references
    this._modelOffset = null;
    this._dirLight = null;
    this._ambientLight = null;
    this._hemiLight = null;

    // Animation references
    this._mixer = null;
    this._currentAction = null;
    this._gltfLoader = null;
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
      const { THREE, GLTFLoader, VRMLoaderPlugin, VRMUtils, VRMAnimationLoaderPlugin } = await ensureModules();
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
      loader.register((parser) => new VRMAnimationLoaderPlugin(parser));
      this._gltfLoader = loader;

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
      const isVRM0 = typeof vrm.meta?.specVersion === "string";
      console.log("[VRM] version:", isVRM0 ? "VRM0" : "VRM1", vrm.meta);
      if (!isVRM0) vrm.scene.rotation.y = Math.PI;

      // ── Optimize ────────────────────────────────────────────────
      VRMUtils.removeUnnecessaryVertices(gltf.scene);
      try { VRMUtils.combineSkeletons(gltf.scene); } catch {}

      this._scene.add(vrm.scene);

      // ── Initialize AnimationMixer ────────────────────────────────
      this._mixer = new THREE.AnimationMixer(vrm.scene);
      this._currentAction = null;

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

      // Update AnimationMixer
      if (this._mixer) {
        this._mixer.update(delta);
      }

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
        
        // P1 — Idle Micro-Jitter (Head Noise)
        // Multi-frequency sine noises for head to make it look alive when idle
        const jitterX = Math.sin(t * 0.5) * 0.012 + Math.sin(t * 1.7) * 0.005;
        const jitterY = Math.sin(t * 1.3) * 0.010 + Math.sin(t * 2.3) * 0.004;
        const jitterZ = Math.sin(t * 0.7) * 0.006 + Math.sin(t * 1.1) * 0.003;

        // Head: main tracking + jitter noise
        applyBone("head",
          this._smoothHeadY * 0.7 + jitterX,
          this._smoothHeadX * 0.6 + jitterY,
          jitterZ
        );

        // Arms default standing pose (A-pose)
        // Only override arms rotation if not playing an arm animation
        const isArmPlaying = this._currentAction && (this._currentAction.getClip().name === "wave" || this._currentAction.getClip().name.includes("arm") || this._currentAction.getClip().name.includes("dance"));
        if (!isArmPlaying) {
          applyBone("leftUpperArm", 0, 0, 1.15);
          applyBone("rightUpperArm", 0, 0, -1.15);
          applyBone("leftLowerArm", 0.25, 0.1, 0);
          applyBone("rightLowerArm", 0.25, -0.1, 0);
        }

        // Apply positions
        if (this._vrm.scene && this._modelOffset) {
          this._vrm.scene.position.copy(this._modelOffset);
          this._vrm.scene.position.y += bobY;
        }

        // ── Eye gaze tracking ──────────────────────────────────
        if (this._vrm.lookAt) {
          this._vrm.lookAt.target = this._camera;
        }

        // ── Auto blink (Thinking-aware frequency) ───────────────
        this._blinkTimer += delta;
        if (!this._blinking && this._blinkTimer >= this._blinkInterval) {
          this._blinking = true;
          this._blinkPhase = 0;
          this._blinkTimer = 0;
          
          // Reset interval: blink faster if thinking
          this._blinkInterval = this._isThinking
            ? 0.8 + Math.random() * 0.7   // thinking: 0.8s - 1.5s
            : 2.5 + Math.random() * 3.5;  // normal: 2.5s - 6s
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

        // ── P0/P2 — Smooth Expression Transition (Lerping & Blending) ──
        if (this._vrm.expressionManager) {
          const EXPRS = ["happy", "sad", "angry", "surprised", "relaxed", "neutral"];
          const factor = 1 - Math.pow(0.01, delta); // ~200ms transition settle
          for (const e of EXPRS) {
            const current = this._exprValues[e] ?? 0;
            // Support secondary blending
            const target = e === this._exprTarget
              ? 1.0
              : e === this._exprSecondary
                ? this._exprSecondaryWeight
                : 0.0;
            const next = current + (target - current) * factor;
            this._exprValues[e] = next;
            try {
              this._vrm.expressionManager.setValue(e, next);
            } catch {}
          }
        }
      }

      if (this._vrm) this._vrm.update(delta);
      this._renderer.render(this._scene, this._camera);
    };
    tick();
  }

  setExpression(expr, secondary = null, secondaryWeight = 0.4) {
    if (!this._vrm?.expressionManager) return;
    const MAP = {
      smile: "happy", excited: "happy", friendly: "happy", happy: "happy",
      sad: "sad", angry: "angry", surprised: "surprised",
      thinking: "relaxed", focused: "relaxed", normal: "neutral", wink: "happy",
      blush: "relaxed",
    };
    this._exprTarget = MAP[expr] || "neutral";
    this._exprSecondary = secondary ? (MAP[secondary] || null) : null;
    this._exprSecondaryWeight = secondaryWeight;
  }

  setThinking(active) {
    this._isThinking = active;
    if (active) {
      this._blinkInterval = 0.8 + Math.random() * 0.7; // instantly shorten blink interval when AI starts thinking
    }
  }

  // ── P1 — Procedural Motion Clips ──
  _buildNodClip() {
    const humanoid = this._vrm?.humanoid;
    const head = humanoid?.getNormalizedBoneNode("head");
    if (!head) return null;
    const times = [0, 0.2, 0.5, 0.7, 1.0];
    const values = [0, -0.25, 0.1, -0.1, 0]; // nod down and return
    const track = new this._THREE.NumberKeyframeTrack(
      `${head.name}.rotation[x]`, times, values
    );
    return new this._THREE.AnimationClip("nod", 1.0, [track]);
  }

  _buildWaveClip() {
    const humanoid = this._vrm?.humanoid;
    const arm = humanoid?.getNormalizedBoneNode("rightUpperArm");
    if (!arm) return null;
    const times = [0, 0.3, 0.6, 0.9, 1.2];
    const rz = [-1.15, -0.6, -1.0, -0.65, -1.15]; // wave hand
    const track = new this._THREE.NumberKeyframeTrack(
      `${arm.name}.rotation[z]`, times, rz
    );
    return new this._THREE.AnimationClip("wave", 1.2, [track]);
  }

  _buildShakeClip() {
    const humanoid = this._vrm?.humanoid;
    const head = humanoid?.getNormalizedBoneNode("head");
    if (!head) return null;
    const times = [0, 0.15, 0.35, 0.55, 0.7];
    const ry = [0, 0.2, -0.2, 0.15, 0]; // shake head
    const track = new this._THREE.NumberKeyframeTrack(
      `${head.name}.rotation[y]`, times, ry
    );
    return new this._THREE.AnimationClip("shake", 0.7, [track]);
  }

  playMotion(motionName) {
    if (!this._mixer) return;

    const builders = {
      nod: () => this._buildNodClip(),
      wave: () => this._buildWaveClip(),
      shake: () => this._buildShakeClip(),
      excited: () => this._buildWaveClip(),
    };

    const builder = builders[motionName];
    if (!builder) return;

    const clip = builder();
    if (!clip) return;

    if (this._currentAction) {
      this._currentAction.fadeOut(0.2);
    }

    const action = this._mixer.clipAction(clip);
    action.setLoop(this._THREE.LoopOnce, 1);
    action.clampWhenFinished = false;
    action.reset().fadeIn(0.2).play();
    this._currentAction = action;

    // Cleanup when done
    const onFinished = (e) => {
      if (e.action === action) {
        action.stop();
        if (this._currentAction === action) this._currentAction = null;
        this._mixer.removeEventListener("finished", onFinished);
      }
    };
    this._mixer.addEventListener("finished", onFinished);
  }

  // ── P2 — External VRMA Animation Loader ──
  async loadMotionFile(url) {
    if (!this._mixer || !this._vrm || !this._gltfLoader) return;
    try {
      const gltf = await this._gltfLoader.loadAsync(url);
      const vrmAnim = gltf.userData.vrmAnimations?.[0];
      if (!vrmAnim) {
        console.warn("[VRM] No animations found in file:", url);
        return;
      }
      const { createVRMAnimationClip } = _loadedModules;
      const clip = createVRMAnimationClip(vrmAnim, this._vrm);
      
      if (this._currentAction) {
        this._currentAction.fadeOut(0.2);
      }

      const action = this._mixer.clipAction(clip);
      action.setLoop(this._THREE.LoopOnce, 1);
      action.clampWhenFinished = false;
      action.reset().fadeIn(0.2).play();
      this._currentAction = action;

      const onFinished = (e) => {
        if (e.action === action) {
          action.stop();
          if (this._currentAction === action) this._currentAction = null;
          this._mixer.removeEventListener("finished", onFinished);
        }
      };
      this._mixer.addEventListener("finished", onFinished);
      console.log("[VRM] Played external motion file:", url);
    } catch (err) {
      console.warn("[VRM] Failed to load motion file:", err);
    }
  }

  // P0 — Real Audio Amplitude Lip-Sync
  startLipSync(amp = 0.55) {
    this._lipSyncActive = true;
    if (!this._vrm?.expressionManager) return;
    // Map RMS amplitude dynamically to aa value (capped 0.0 to 1.0)
    const val = Math.max(0, Math.min(1.0, amp * 0.9));
    try {
      this._vrm.expressionManager.setValue("aa", val);
    } catch {}
  }

  stopLipSync() {
    this._lipSyncActive = false;
    if (!this._vrm?.expressionManager) return;
    try {
      this._vrm.expressionManager.setValue("aa", 0);
    } catch {}
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
      window.companion.off("avatar:play-motion-file", this.loadMotionFile);
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
    this._mixer = null;
  }
}
