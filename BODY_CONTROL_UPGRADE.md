# Nâng cấp Body Control VRM — Spec cho antigravity

> File: `live2d/runtime/vrm-manager.js`
> Làm theo thứ tự P0 → P1 → P2. Sau mỗi task chạy app và kiểm tra bằng mắt.

---

## P0 — Lip-sync theo biên độ âm thanh thực (5 dòng, hiệu quả ngay)

### Vấn đề

`overlay/app.js` dòng 129 đã truyền `amp` (0–1, tính từ RMS) vào callback:

```js
await audioPlayer.play(url, (amp) => avatar.startLipSync(amp));
```

Nhưng `VRMBackend.startLipSync()` hiện tại **bỏ qua tham số**:

```js
// HIỆN TẠI — sai
startLipSync() {
  this._lipSyncActive = true;
  if (!this._vrm?.expressionManager) return;
  try { this._vrm.expressionManager.setValue("aa", 0.55); } catch {}
}
```

Kết quả: miệng luôn mở cố định 55%, không theo tiếng nói.

### Sửa

```js
// SAU KHI SỬA
startLipSync(amp = 0.55) {
  this._lipSyncActive = true;
  if (!this._vrm?.expressionManager) return;
  const value = Math.max(0, Math.min(1, amp * 0.9));
  try { this._vrm.expressionManager.setValue("aa", value); } catch {}
}
```

Không cần sửa `stopLipSync()` hay bất cứ file nào khác.

### DoD

Phát TTS → miệng nhân vật động lên xuống theo cường độ giọng nói, không còn mở cố định một mức.

---

## P0 — Expression transition mượt (lerp, không giật)

### Vấn đề

`setExpression()` hiện reset tất cả về 0 rồi set target lên 1.0 **trong cùng một frame** — nhân vật giật cảm xúc ngay lập tức.

### Sửa

**Bước 1 — Thêm state vào constructor** (trong block `this._blinkInterval = ...`):

```js
// Thêm sau dòng this._blinkInterval = 2.5 + Math.random() * 3.5;
this._exprTarget = "neutral";
this._exprValues = {}; // { "happy": 0, "sad": 0, ... }
```

**Bước 2 — Sửa `setExpression()`** — chỉ set target, không setValue ngay:

```js
setExpression(expr) {
  if (!this._vrm?.expressionManager) return;
  const MAP = {
    smile: "happy", excited: "happy", friendly: "happy", happy: "happy",
    sad: "sad", angry: "angry", surprised: "surprised",
    thinking: "relaxed", focused: "relaxed", normal: "neutral", wink: "happy",
  };
  this._exprTarget = MAP[expr] || "neutral";
}
```

**Bước 3 — Lerp trong `_tick()`**, thêm vào ngay trước dòng `if (this._vrm) this._vrm.update(delta)`:

```js
// Expression lerp — chạy mỗi frame
if (this._vrm?.expressionManager) {
  const EXPRS = ["happy", "sad", "angry", "surprised", "relaxed", "neutral"];
  const factor = 1 - Math.pow(0.01, delta); // ~200ms settle
  for (const e of EXPRS) {
    const current = this._exprValues[e] ?? 0;
    const target = e === this._exprTarget ? 1.0 : 0.0;
    const next = current + (target - current) * factor;
    this._exprValues[e] = next;
    try { this._vrm.expressionManager.setValue(e, next); } catch {}
  }
}
```

### DoD

Gõ chat → nhân vật chuyển từ `neutral` sang `happy` trong ~200ms, không giật. Dùng `setTimeout(() => avatar.setState({expression:"sad"}), 2000)` trong console để test.

---

## P0 — Blink tăng tần suất khi AI đang "thinking"

### Vấn đề

`_blinkInterval` hiện cố định 2.5–6s mọi lúc. AIRI tăng tần suất khi LLM latency cao.

### Sửa

**Bước 1 — Thêm setter** vào `VRMBackend`:

```js
setThinking(active) {
  this._isThinking = active;
  // Khi bắt đầu thinking: reset interval ngắn lại
  if (active) this._blinkInterval = 0.8 + Math.random() * 0.7;
}
```

**Bước 2 — Sửa dòng reset interval** trong `_tick()` (dòng `this._blinkInterval = 2.5 + ...`):

```js
// Thay dòng cũ:
this._blinkInterval = 2.5 + Math.random() * 3.5;

// Bằng:
this._blinkInterval = this._isThinking
  ? 0.8 + Math.random() * 0.7   // thinking: nháy 0.8–1.5s
  : 2.5 + Math.random() * 3.5;  // normal: 2.5–6s
```

**Bước 3 — Gọi từ `live2d-manager.js`**, trong `setState()` khi nhận `motion`:

```js
// Trong LiveManager.setState(), sau dòng this._backend?.playMotion(mot):
if (this._backend?.setThinking) {
  this._backend.setThinking(mot === "thinking");
}
```

### DoD

`avatar.setState({ motion: "thinking" })` → nháy mắt tăng lên, `avatar.setState({ motion: "idle" })` → về bình thường.

---

## P1 — Micro-jitter khi idle (không có input chuột)

### Vấn đề

Khi không di chuột, nhân vật đứng hoàn toàn tĩnh (trừ breathing). AIRI có random micro-movements để tránh "đơ".

### Sửa

Trong `_tick()`, trong block `applyBone("head", ...)`, **đã có** `Math.sin(t * 0.5) * 0.01` cho trục Y. Cần thêm noise cho X và Z:

```js
// Tìm đoạn applyBone("head", ...) — hiện tại:
applyBone("head",
  this._smoothHeadY * 0.7 + Math.sin(t * 0.5) * 0.01,
  this._smoothHeadX * 0.7 + Math.sin(t * 1.3) * 0.008,
  Math.sin(t * 0.7) * 0.005
);

// Sửa thành (thêm noise đa tần số):
applyBone("head",
  this._smoothHeadY * 0.7 + Math.sin(t * 0.5) * 0.012 + Math.sin(t * 1.7) * 0.005,
  this._smoothHeadX * 0.7 + Math.sin(t * 1.3) * 0.010 + Math.sin(t * 2.3) * 0.004,
  Math.sin(t * 0.7) * 0.006 + Math.sin(t * 1.1) * 0.003
);
```

Không cần thêm state, không cần detect "idle" — noise luôn chạy nhưng biên độ nhỏ đủ để không thấy khi đang di chuột.

### DoD

Đứng yên không di chuột 10 giây → đầu nhân vật vẫn có chuyển động nhẹ tự nhiên, không tĩnh hoàn toàn.

---

## P1 — AnimationMixer + 3 motion clip procedural

### Vấn đề

`playMotion()` hiện là stub rỗng. `overlay/app.js` gọi `avatar.setState({ motion: "nod" })` nhưng VRM không làm gì. Đây là gap lớn nhất — không có gesture nào cả.

### Sửa

**Bước 1 — Khởi tạo AnimationMixer** trong `init()`, sau khi VRM load xong (sau dòng `this._vrm = vrm`):

```js
this._mixer = new THREE.AnimationMixer(this._vrm.scene);
this._currentAction = null;
```

**Bước 2 — Update mixer trong `_tick()`**, trước dòng `this._vrm.update(delta)`:

```js
if (this._mixer) this._mixer.update(delta);
```

**Bước 3 — Tạo helper sinh clip procedural**:

```js
_buildNodClip() {
  const head = this._vrm.humanoid.getNormalizedBoneNode("head");
  if (!head) return null;
  const times = [0, 0.2, 0.5, 0.7, 1.0];
  const values = [0, -0.25, 0.1, -0.1, 0]; // rx: gật xuống rồi về
  const track = new THREE.NumberKeyframeTrack(
    `${head.name}.rotation[x]`, times, values
  );
  return new THREE.AnimationClip("nod", 1.0, [track]);
}

_buildWaveClip() {
  const arm = this._vrm.humanoid.getNormalizedBoneNode("rightUpperArm");
  if (!arm) return null;
  const times = [0, 0.3, 0.6, 0.9, 1.2];
  const rz = [-1.15, -0.6, -1.0, -0.65, -1.15]; // vẫy tay phải
  const track = new THREE.NumberKeyframeTrack(
    `${arm.name}.rotation[z]`, times, rz
  );
  return new THREE.AnimationClip("wave", 1.2, [track]);
}

_buildShakeClip() {
  const head = this._vrm.humanoid.getNormalizedBoneNode("head");
  if (!head) return null;
  const times = [0, 0.15, 0.35, 0.55, 0.7];
  const ry = [0, 0.2, -0.2, 0.15, 0]; // lắc đầu ngang
  const track = new THREE.NumberKeyframeTrack(
    `${head.name}.rotation[y]`, times, ry
  );
  return new THREE.AnimationClip("shake", 0.7, [track]);
}
```

**Bước 4 — Sửa `playMotion()`**:

```js
playMotion(motionName) {
  if (!this._mixer) return;

  const builders = {
    nod: () => this._buildNodClip(),
    wave: () => this._buildWaveClip(),
    shake: () => this._buildShakeClip(),
    excited: () => this._buildWaveClip(), // reuse
  };

  const builder = builders[motionName];
  if (!builder) return;

  const clip = builder();
  if (!clip) return;

  // Fade out action cũ
  if (this._currentAction) {
    this._currentAction.fadeOut(0.2);
  }

  const action = this._mixer.clipAction(clip);
  action.setLoop(THREE.LoopOnce, 1);
  action.clampWhenFinished = false;
  action.reset().fadeIn(0.2).play();
  this._currentAction = action;

  // Tự cleanup sau khi clip xong
  this._mixer.addEventListener("finished", (e) => {
    if (e.action === action) {
      action.stop();
      this._currentAction = null;
    }
  }, { once: true });
}
```

### DoD

- `avatar.setState({ motion: "nod" })` trong console → đầu gật 1 lần rồi về vị trí cũ.
- `avatar.setState({ motion: "wave" })` → tay phải vẫy 1 lần.
- Khi LLM trả lời → overlay gọi `setState({ motion: "nod" })` → nhân vật gật theo đúng lúc.

---

## P2 — Expression blending (Joy + Blush cùng lúc)

### Vấn đề

Không thể set 2 expression cùng lúc.

### Sửa

Sửa `setExpression()` để nhận optional `secondary`:

```js
setExpression(expr, secondary = null, secondaryWeight = 0.4) {
  if (!this._vrm?.expressionManager) return;
  const MAP = {
    smile: "happy", excited: "happy", happy: "happy",
    sad: "sad", angry: "angry", surprised: "surprised",
    thinking: "relaxed", focused: "relaxed", normal: "neutral", wink: "happy",
    blush: "relaxed", // map blush → relaxed nếu model không có blush riêng
  };
  this._exprTarget = MAP[expr] || "neutral";
  this._exprSecondary = secondary ? (MAP[secondary] || null) : null;
  this._exprSecondaryWeight = secondaryWeight;
}
```

Cập nhật lerp trong `_tick()` để xét `_exprSecondary`:

```js
const target = e === this._exprTarget
  ? 1.0
  : e === this._exprSecondary
    ? this._exprSecondaryWeight
    : 0.0;
```

Gọi từ `ai.ipc.js` khi parse emotion chunk có blush flag:

```js
// Ví dụ trong ai.ipc.js khi nhận chunk:
if (chunk.emotion === "happy" && chunk.blush) {
  setEmotion("happy|blush"); // cần parse thêm ở live2d-manager
}
```

### DoD

`avatar.setState({ expression: "happy" })` sau đó thêm blush → nhân vật vừa cười vừa đỏ mặt nhẹ.

---

## P2 — .vrma animation loader (file animation ngoài)

### Vấn đề

Không load được file `.vrma` (VRM Animation format) từ bên ngoài.

### Sửa

**Bước 1 — Thêm vào importmap** trong `renderer/overlay/index.html`:

```json
"@pixiv/three-vrm-animation": "https://cdn.jsdelivr.net/npm/@pixiv/three-vrm-animation@3/lib/three-vrm-animation.module.js"
```

**Bước 2 — Trong `init()` của VRMBackend**, thêm plugin:

```js
import { VRMAnimationLoaderPlugin, createVRMAnimationClip } from "@pixiv/three-vrm-animation";

// Trong init(), sau khi setup GLTFLoader:
this._gltfLoader.register((parser) => new VRMAnimationLoaderPlugin(parser));
```

**Bước 3 — Thêm method `loadMotionFile(url)`**:

```js
async loadMotionFile(url) {
  if (!this._mixer || !this._vrm) return;
  try {
    const gltf = await this._gltfLoader.loadAsync(url);
    const clip = createVRMAnimationClip(gltf.userData.vrmAnimations[0], this._vrm);
    const action = this._mixer.clipAction(clip);
    action.setLoop(THREE.LoopOnce, 1);
    action.clampWhenFinished = false;
    action.reset().play();
    this._currentAction = action;
  } catch (err) {
    console.warn("[VRM] Failed to load motion file:", err);
  }
}
```

**Bước 4 — Expose qua IPC** trong `desktop/ipc/avatar.ipc.js`:

```js
ipcMain.handle("avatar:play-motion-file", async (_, filePath) => {
  sendToTargets("avatar:play-motion-file", filePath);
});
```

### DoD

Đặt file `.vrma` vào `assets/motions/`, gọi `window.companion.invoke("avatar:play-motion-file", "assets/motions/dance.vrma")` → nhân vật thực hiện animation từ file.

---

## Thứ tự thực thi

```
P0-1  startLipSync(amp)           ~15 phút   live2d/runtime/vrm-manager.js
P0-2  Expression lerp             ~30 phút   live2d/runtime/vrm-manager.js
P0-3  Blink thinking mode         ~20 phút   vrm-manager.js + live2d-manager.js
P1-1  Micro-jitter                ~10 phút   vrm-manager.js
P1-2  AnimationMixer + 3 clips    ~2 giờ     vrm-manager.js
P2-1  Expression blending         ~30 phút   vrm-manager.js
P2-2  .vrma loader                ~1 giờ     vrm-manager.js + avatar.ipc.js
```

## Kiểm tra nhanh sau mỗi task

```js
// Trong DevTools console của overlay window:

// Test P0-1 (lip sync):
// Phát TTS bất kỳ → quan sát miệng động theo tiếng

// Test P0-2 (expression lerp):
avatar.setState({ expression: "happy" });
setTimeout(() => avatar.setState({ expression: "sad" }), 1500);
// Kỳ vọng: chuyển mượt, không giật

// Test P0-3 (blink thinking):
avatar.setState({ motion: "thinking" });
// Kỳ vọng: nháy mắt nhanh hơn trong ~5 giây
avatar.setState({ motion: "idle" });

// Test P1-2 (motion clips):
avatar.setState({ motion: "nod" });   // gật đầu
avatar.setState({ motion: "wave" });  // vẫy tay
avatar.setState({ motion: "shake" }); // lắc đầu
```
