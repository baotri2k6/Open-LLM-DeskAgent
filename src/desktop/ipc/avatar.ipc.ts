import { BrowserWindow, IpcMain } from "electron";
import * as http from "http";
import * as fs from "fs";
import * as path from "path";

interface AvatarState {
  expression: string;
  motion: string;
  lipsync: boolean;
}

let state: AvatarState = { expression: "normal", motion: "idle", lipsync: false };

const API_HOST = "127.0.0.1";
const API_PORT = 8765;

function getAvatarWindow(): BrowserWindow | undefined {
  return BrowserWindow.getAllWindows().find(win => {
    try {
      return win.webContents.getURL().includes("avatar.html") || win.webContents.getURL().includes("overlay");
    } catch {
      return false;
    }
  });
}

function sendToTargets(channel: string, payload: any): void {
  const wins = BrowserWindow.getAllWindows().filter(win => win && !win.isDestroyed());
  for (const win of wins) {
    win.webContents.send(channel, payload);
  }
}

function requestJSON(method: string, path: string, payload: any = null): Promise<any> {
  return new Promise((resolve, reject) => {
    const body = payload ? JSON.stringify(payload) : null;
    const req = http.request(
      {
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
      },
      res => {
        const chunks: any[] = [];
        res.on("data", chunk => chunks.push(chunk));
        res.on("end", () => {
          const raw = Buffer.concat(chunks).toString("utf8");
          let data = {};
          try {
            data = raw ? JSON.parse(raw) : {};
          } catch {
            data = { raw };
          }
          if (res.statusCode && res.statusCode >= 200 && res.statusCode < 300) {
            resolve(data);
          } else {
            reject(new Error((data as any).message || (data as any).error || `HTTP ${res.statusCode}`));
          }
        });
      }
    );

    req.on("timeout", () => req.destroy(new Error("request timeout")));
    req.on("error", reject);
    if (body) req.write(body);
    req.end();
  });
}

export function registerAvatarIpc(ipcMain: IpcMain, avatarWin: any): void {
  ipcMain.handle("avatar:set-state", async (_e: any, next: Partial<AvatarState>) => {
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
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });

  // 2. avatar:scan-zip
  ipcMain.handle("avatar:scan-zip", async (_e: any, { path }: { path: string }) => {
    try {
      const res = await requestJSON("POST", "/model/scan-zip", { zip_path: path });
      return res;
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });

  // 3. avatar:import-zip
  ipcMain.handle("avatar:import-zip", async (_e: any, { path, selectedConfig }: { path: string; selectedConfig?: string }) => {
    try {
      const res = await requestJSON("POST", "/model/import", {
        zip_path: path,
        model_path: selectedConfig || "",
      });
      // Broadcast update to reload grids in other windows
      sendToTargets("avatar:registry-updated", {});
      return res;
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });

  // 4. avatar:delete-model
  ipcMain.handle("avatar:delete-model", async (_e: any, { modelId }: { modelId: string }) => {
    try {
      const res = await requestJSON("POST", "/model/remove", { model_id: modelId });
      sendToTargets("avatar:registry-updated", {});
      return res;
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });

  // Alias for deleteCharacter
  ipcMain.handle("character:delete", async (_e: any, { id }: { id: string }) => {
    try {
      const res = await requestJSON("POST", "/model/remove", { model_id: id });
      sendToTargets("avatar:registry-updated", {});
      return res;
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });

  // 5. avatar:set-model
  ipcMain.handle("avatar:set-model", async (_e: any, { modelId, modelPath }: { modelId: string; modelPath: string }) => {
    try {
      // Update config on backend
      const res = await requestJSON("POST", "/config/update", { key: "app.avatarModel", value: modelPath });
      // Broadcast update to all windows (overlay app.ts relies on config:updated to dynamically swap models)
      sendToTargets("config:updated", { key: "app.avatarModel", value: modelPath });
      return { success: true, ...res };
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });

  // 6. avatar:import-vrm
  ipcMain.handle("avatar:import-vrm", async (_e: any, { filePath }: { filePath: string }) => {
    try {
      const ext = path.extname(filePath).toLowerCase();
      if (ext !== ".vrm") {
        return { success: false, error: "Chỉ hỗ trợ tệp tin định dạng .vrm" };
      }

      const vrmDir = path.join(process.cwd(), "assets", "live2d", "vrm");
      if (!fs.existsSync(vrmDir)) {
        fs.mkdirSync(vrmDir, { recursive: true });
      }

      const stem = path.basename(filePath, ext);
      const destPath = path.join(vrmDir, path.basename(filePath));
      
      // Copy file vrm
      fs.copyFileSync(filePath, destPath);

      // Register in models.json
      const manifestPath = path.join(process.cwd(), "assets", "live2d", "models.json");
      let manifest = { models: [] as any[] };
      if (fs.existsSync(manifestPath)) {
        try {
          manifest = JSON.parse(fs.readFileSync(manifestPath, "utf8"));
        } catch {
          // ignore
        }
      }

      if (!manifest.models) manifest.models = [];

      const modelId = stem.toLowerCase().replace(/[^a-z0-9]/g, "_");
      const relPath = `assets/live2d/vrm/${path.basename(filePath)}`;

      // Remove old entry with same path or id
      manifest.models = manifest.models.filter(m => m.id !== modelId && m.path !== relPath);

      const newEntry = {
        id: modelId,
        name: stem,
        description: `Imported VRM 3D character`,
        path: relPath,
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
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });
}
