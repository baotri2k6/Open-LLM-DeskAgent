"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerAvatarIpc = registerAvatarIpc;
const electron_1 = require("electron");
const http = __importStar(require("http"));
const fs = __importStar(require("fs"));
const path = __importStar(require("path"));
// eslint-disable-next-line @typescript-eslint/no-var-requires
const _admZipMod = require("adm-zip");
// adm-zip may export as CJS or as ESM default — handle both
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const AdmZip = _admZipMod.default || _admZipMod;
let state = { expression: "normal", motion: "idle", lipsync: false };
const API_HOST = "127.0.0.1";
const API_PORT = 8765;
function getAvatarWindow() {
    return electron_1.BrowserWindow.getAllWindows().find(win => {
        try {
            return win.webContents.getURL().includes("avatar.html") || win.webContents.getURL().includes("overlay");
        }
        catch {
            return false;
        }
    });
}
function sendToTargets(channel, payload) {
    const wins = electron_1.BrowserWindow.getAllWindows().filter(win => win && !win.isDestroyed());
    for (const win of wins) {
        win.webContents.send(channel, payload);
    }
}
function requestJSON(method, path, payload = null) {
    return new Promise((resolve, reject) => {
        const body = payload ? JSON.stringify(payload) : null;
        const req = http.request({
            hostname: API_HOST,
            port: API_PORT,
            path,
            method,
            headers: {
                Accept: "application/json",
                ...(body
                    ? {
                        "Content-Type": "application/json; charset=utf-8",
                        "Content-Length": Buffer.byteLength(body),
                    }
                    : {}),
            },
            timeout: 30000,
        }, res => {
            const chunks = [];
            res.on("data", chunk => chunks.push(chunk));
            res.on("end", () => {
                const raw = Buffer.concat(chunks).toString("utf8");
                let data = {};
                try {
                    data = raw ? JSON.parse(raw) : {};
                }
                catch {
                    data = { raw };
                }
                if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
                    resolve(data);
                }
                else {
                    reject(new Error(data.message || data.error || `HTTP ${res.statusCode}`));
                }
            });
        });
        req.on("timeout", () => req.destroy(new Error("request timeout")));
        req.on("error", reject);
        if (body)
            req.write(body);
        req.end();
    });
}
function registerAvatarIpc(ipcMain, avatarWin) {
    ipcMain.handle("avatar:set-state", async (_e, next) => {
        state = { ...state, ...next };
        const win = getAvatarWindow();
        win?.webContents.send("set:emotion", state.expression || "normal");
        return state;
    });
    ipcMain.handle("avatar:get-state", async () => state);
    // 1. avatar:list-models
    ipcMain.handle("avatar:list-models", async () => {
        try {
            const res = await requestJSON("GET", "/model/list");
            return res;
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    });
    // 2. avatar:scan-zip
    ipcMain.handle("avatar:scan-zip", async (_e, { path }) => {
        try {
            const res = await requestJSON("POST", "/model/scan-zip", { zip_path: path });
            return res;
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    });
    // 3. avatar:import-zip
    ipcMain.handle("avatar:import-zip", async (_e, { path, selectedConfig }) => {
        try {
            const res = await requestJSON("POST", "/model/import", {
                zip_path: path,
                model_path: selectedConfig || "",
            });
            // Broadcast update to reload grids in other windows
            sendToTargets("avatar:registry-updated", {});
            return res;
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    });
    // 4. avatar:delete-model
    ipcMain.handle("avatar:delete-model", async (_e, { modelId }) => {
        try {
            const res = await requestJSON("POST", "/model/remove", { model_id: modelId });
            sendToTargets("avatar:registry-updated", {});
            return res;
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    });
    // Alias for deleteCharacter
    ipcMain.handle("character:delete", async (_e, { id }) => {
        try {
            const res = await requestJSON("POST", "/model/remove", { model_id: id });
            sendToTargets("avatar:registry-updated", {});
            return res;
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    });
    // 5. avatar:set-model
    ipcMain.handle("avatar:set-model", async (_e, { modelId, modelPath }) => {
        try {
            // Update config on backend
            const res = await requestJSON("POST", "/config/update", { key: "app.avatarModel", value: modelPath });
            // Broadcast update to all windows (overlay app.ts relies on config:updated to dynamically swap models)
            sendToTargets("config:updated", { key: "app.avatarModel", value: modelPath });
            return { success: true, ...res };
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    });
    // 6. avatar:import-vrm (supports .vrm directly and .zip containing .vrm)
    ipcMain.handle("avatar:import-vrm", async (_e, { filePath }) => {
        try {
            const ext = path.extname(filePath).toLowerCase();
            if (ext !== ".vrm" && ext !== ".zip") {
                return { success: false, error: "Chỉ hỗ trợ tệp tin định dạng .vrm hoặc .zip chứa model VRM" };
            }
            const vrmDir = path.join(process.cwd(), "assets", "live2d", "vrm");
            if (!fs.existsSync(vrmDir)) {
                fs.mkdirSync(vrmDir, { recursive: true });
            }
            let finalVrmName = "";
            let finalVrmPath = "";
            if (ext === ".vrm") {
                const stem = path.basename(filePath, ext);
                const destPath = path.join(vrmDir, path.basename(filePath));
                // Copy file vrm
                fs.copyFileSync(filePath, destPath);
                finalVrmName = stem;
                finalVrmPath = `assets/live2d/vrm/${path.basename(filePath)}`;
            }
            else {
                // Handle ZIP file
                const zip = new AdmZip(filePath);
                const zipEntries = zip.getEntries();
                // Find .vrm entry
                const vrmEntry = zipEntries.find((entry) => entry.entryName.toLowerCase().endsWith(".vrm"));
                if (!vrmEntry) {
                    return { success: false, error: "Không tìm thấy tệp tin định dạng .vrm bên trong tệp ZIP" };
                }
                const vrmFileName = path.basename(vrmEntry.entryName);
                const destPath = path.join(vrmDir, vrmFileName);
                // Extract vrm file directly
                const vrmData = vrmEntry.getData();
                fs.writeFileSync(destPath, vrmData);
                finalVrmName = path.basename(vrmFileName, ".vrm");
                finalVrmPath = `assets/live2d/vrm/${vrmFileName}`;
            }
            // Register in models.json
            const manifestPath = path.join(process.cwd(), "assets", "live2d", "models.json");
            let manifest = { models: [] };
            if (fs.existsSync(manifestPath)) {
                try {
                    manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
                }
                catch {
                    // ignore
                }
            }
            if (!manifest.models)
                manifest.models = [];
            const modelId = finalVrmName.toLowerCase().replace(/[^a-z0-9]/g, "_");
            // Remove old entry with same path or id
            manifest.models = manifest.models.filter(m => m.id !== modelId && m.path !== finalVrmPath);
            const newEntry = {
                id: modelId,
                name: finalVrmName,
                description: `Imported VRM 3D character`,
                path: finalVrmPath,
                thumbnail: null,
                scale: 1.0,
                default: false,
                tags: ["vrm", "imported"],
                accessories: [],
                hitReactions: {},
                expressionFallback: {}
            };
            manifest.models.push(newEntry);
            fs.writeFileSync(manifestPath, JSON.stringify(manifest, null, 2), "utf8");
            sendToTargets("avatar:registry-updated", {});
            return { success: true, model: newEntry };
        }
        catch (err) {
            return { success: false, error: err.message };
        }
    });
    // 7. avatar:play-motion-file (plays an external .vrma animation)
    ipcMain.handle("avatar:play-motion-file", async (_e, { filePath }) => {
        sendToTargets("avatar:play-motion-file", filePath);
        return { success: true };
    });
}
