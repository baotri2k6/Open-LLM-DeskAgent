import { SpineCanvas } from '@esotericsoftware/spine-webgl';

export class SpineBackend {
  constructor(container, canvasEl, modelPath) {
    this._container = container;
    this._canvas = canvasEl;
    this._modelPath = modelPath;
    this._spineCanvas = null;
    this._isDestroyed = false;
    this._skeleton = null;
    this._animationState = null;
    this._lipInterval = null;
    this._onResize = null;

    const lastSlash = modelPath.lastIndexOf('/');
    this._baseDir = modelPath.substring(0, lastSlash + 1);
    this._baseName = modelPath.substring(lastSlash + 1, modelPath.lastIndexOf('.'));
    this._jsonPath = modelPath;
    this._atlasPath = this._baseDir + this._baseName + '.atlas';
  }

  async init() {
    try {
      if (this._canvas) {
        this._canvas.style.display = "block";
      }
      const w = this._container.clientWidth || 280;
      const h = this._container.clientHeight || 390;
      this._canvas.width = w;
      this._canvas.height = h;

      return new Promise((resolve) => {
        this._spineCanvas = new SpineCanvas(this._canvas, {
          config: {
            alpha: true,
            premultipliedAlpha: true
          },
          loadAssets: (canvas) => {
            canvas.assetManager.loadText(this._jsonPath);
            canvas.assetManager.loadText(this._atlasPath);
          },
          initialize: (canvas) => {
            if (this._isDestroyed) {
              resolve(false);
              return;
            }
            try {
              const assetManager = canvas.assetManager;
              const atlasText = assetManager.require(this._atlasPath);
              
              const lines = atlasText.split(/\r\n|\r|\n/);
              const texturesToLoad = [];
              for (let i = 0; i < lines.length; i++) {
                const line = lines[i].trim();
                if (line.endsWith('.png')) {
                  texturesToLoad.push(line);
                }
              }

              texturesToLoad.forEach(texName => {
                canvas.assetManager.loadTexture(this._baseDir + texName);
              });

              const checkLoaded = setInterval(() => {
                if (this._isDestroyed) {
                  clearInterval(checkLoaded);
                  resolve(false);
                  return;
                }
                if (canvas.assetManager.isLoadingComplete()) {
                  clearInterval(checkLoaded);
                  
                  const spineNamespace = window.spine;
                  const atlas = new spineNamespace.TextureAtlas(atlasText, (path) => {
                    return assetManager.require(this._baseDir + path);
                  });
                  const atlasLoader = new spineNamespace.AtlasAttachmentLoader(atlas);
                  const skeletonJson = new spineNamespace.SkeletonJson(atlasLoader);
                  
                  const scale = 0.5;
                  skeletonJson.scale = scale;
                  
                  const skeletonData = skeletonJson.readSkeletonData(assetManager.require(this._jsonPath));
                  this._skeleton = new spineNamespace.Skeleton(skeletonData);
                  
                  this._skeleton.x = w / 2;
                  this._skeleton.y = h * 0.15;
                  
                  const animationStateData = new spineNamespace.AnimationStateData(skeletonData);
                  this._animationState = new spineNamespace.AnimationState(animationStateData);

                  const idleAnim = skeletonData.animations.find(a => 
                    a.name === 'idle' || a.name === 'default' || a.name === 'walk' || a.name === 'run'
                  );
                  if (idleAnim) {
                    this._animationState.setAnimation(0, idleAnim.name, true);
                  }

                  this._onResize = () => {
                    if (this._isDestroyed) return;
                    const cw = this._container.clientWidth || 280;
                    const ch = this._container.clientHeight || 390;
                    this._canvas.width = cw;
                    this._canvas.height = ch;
                    if (this._skeleton) {
                      this._skeleton.x = cw / 2;
                      this._skeleton.y = ch * 0.15;
                    }
                  };
                  window.addEventListener('resize', this._onResize);

                  console.log("[Spine] Model loaded successfully:", this._jsonPath);
                  resolve(true);
                }
              }, 100);

            } catch (err) {
              console.error("[Spine] Initialize error:", err);
              resolve(false);
            }
          },
          update: (canvas, delta) => {
            if (this._isDestroyed || !this._animationState || !this._skeleton) return;
            this._animationState.update(delta);
            this._animationState.apply(this._skeleton);
            this._skeleton.updateWorldTransform();
          },
          render: (canvas) => {
            if (this._isDestroyed || !this._skeleton) return;
            canvas.renderer.begin();
            canvas.renderer.drawSkeleton(this._skeleton, true);
            canvas.renderer.end();
          }
        });

      });
    } catch (err) {
      console.error("[Spine] init error:", err);
      return false;
    }
  }

  setAccessory(paramId, value) {
    if (!this._skeleton) return;
    try {
      this._skeleton.setSkinByName(value);
      this._skeleton.setSlotsToSetupPose();
    } catch (e) {
      // ignore
    }
  }

  setExpression(expressionName) {
    this.playMotion(expressionName);
  }

  playMotion(motionName) {
    if (!this._animationState || !this._skeleton) return;
    try {
      const anims = this._skeleton.data.animations;
      const match = anims.find(a => 
        a.name === motionName || a.name.toLowerCase().includes(motionName.toLowerCase())
      );
      if (match) {
        this._animationState.setAnimation(1, match.name, false);
        this._animationState.addAnimation(1, 'idle', true, 1.5);
      }
    } catch (e) {
      // ignore
    }
  }

  startLipSync(amplitude = 0.5) {
    if (!this._skeleton) return;
    if (this._lipInterval) return;

    let phase = 0;
    this._lipInterval = setInterval(() => {
      if (!this._skeleton) return;
      phase += 0.5;
      const val = Math.abs(Math.sin(phase)) * 25;
      
      const jawBone = this._skeleton.findBone('jaw') || this._skeleton.findBone('mouth');
      if (jawBone) {
        jawBone.y = -val;
      }
    }, 60);
  }

  stopLipSync() {
    if (this._lipInterval) {
      clearInterval(this._lipInterval);
      this._lipInterval = null;
    }
    if (this._skeleton) {
      const jawBone = this._skeleton.findBone('jaw') || this._skeleton.findBone('mouth');
      if (jawBone) {
        jawBone.y = 0;
      }
    }
  }

  containsPoint(x, y) {
    const w = this._container.clientWidth || 280;
    const h = this._container.clientHeight || 390;
    return x >= w * 0.15 && x <= w * 0.85 && y >= h * 0.05 && y <= h * 0.95;
  }

  handleTap(x, y) {
    const defaultReactions = [
      { expression: "smile", motion: "nod" },
      { expression: "happy", motion: "excited" }
    ];
    return defaultReactions[Math.floor(Math.random() * defaultReactions.length)];
  }

  destroy() {
    this._isDestroyed = true;
    this.stopLipSync();
    if (this._onResize) {
      window.removeEventListener('resize', this._onResize);
    }
    if (this._spineCanvas) {
      try {
        this._spineCanvas.dispose();
      } catch (e) {}
      this._spineCanvas = null;
    }
    if (this._canvas) {
      this._canvas.style.display = "none";
    }
    this._skeleton = null;
    this._animationState = null;
  }
}
