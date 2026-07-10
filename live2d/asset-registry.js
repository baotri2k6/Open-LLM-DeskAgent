/**
 * asset-registry.js
 *
 * Singleton loader cho assets/live2d/models.json.
 * Cung cap API truy van model, accessories va metadata
 * thay the cho tat ca chuoi hardcode trong codebase.
 */

const MANIFEST_PATH = "../assets/live2d/models.json";

class _AssetRegistry {
  constructor() {
    this._models = null;
    this._loadPromise = null;
  }

  async load(force = false) {
    if (force) {
      this._models = null;
      this._loadPromise = null;
    }
    if (this._models !== null) return;
    if (this._loadPromise) return this._loadPromise;

    this._loadPromise = (async () => {
      try {
        const url = new URL(MANIFEST_PATH, import.meta.url).href;
        const res = await fetch(url);
        if (!res.ok) throw new Error("HTTP " + res.status);
        const data = await res.json();
        this._models = Array.isArray(data.models) ? data.models : [];
        console.info("[AssetRegistry] Loaded " + this._models.length + " models from manifest.");
      } catch (err) {
        console.warn("[AssetRegistry] Failed to load models.json, using empty registry.", err);
        this._models = [];
      }
    })();
    return this._loadPromise;
  }

  _assertLoaded() {
    if (this._models === null) {
      throw new Error("[AssetRegistry] Registry not loaded. Call load() first.");
    }
  }

  getAll() {
    this._assertLoaded();
    return this._models;
  }

  getById(id) {
    this._assertLoaded();
    return this._models.find((m) => m.id === id) ?? null;
  }

  getDefault() {
    this._assertLoaded();
    return this._models.find((m) => m.default) ?? this._models[0] ?? null;
  }

  resolvePathToId(filePath) {
    this._assertLoaded();
    if (!filePath) return this.getDefault()?.id ?? "icegirl";
    const lower = filePath.toLowerCase();
    const exact = this._models.find((m) => m.path && lower.endsWith(m.path.toLowerCase()));
    if (exact) return exact.id;
    const byId = this._models.find((m) => lower.includes(m.id.toLowerCase()));
    if (byId) return byId.id;
    return this.getDefault()?.id ?? "icegirl";
  }

  getModelPath(id) {
    const entry = this.getById(id);
    if (!entry) {
      console.warn("[AssetRegistry] Unknown model: " + id + ". Falling back to default.");
      return "../../" + (this.getDefault()?.path ?? "assets/live2d/IceGirl/IceGirl.model3.json");
    }
    return "../../" + entry.path;
  }

  getScale(id) {
    return this.getById(id)?.scale ?? 0.85;
  }

  getAccessories(id) {
    return this.getById(id)?.accessories ?? [];
  }

  getHitReactions(id, area) {
    return this.getById(id)?.hitReactions?.[area] ?? [];
  }

  getExpressionFallback(id) {
    return this.getById(id)?.expressionFallback ?? {};
  }
}

export const AssetRegistry = new _AssetRegistry();
