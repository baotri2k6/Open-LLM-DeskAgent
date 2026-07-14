import * as http from "http";
import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { BrowserWindow, IpcMain, app } from "electron";
import { broadcast } from "../websocket-server";

const API_HOST = "127.0.0.1";
const API_PORT = 8765;

function liveTargets(): BrowserWindow[] {
  return BrowserWindow.getAllWindows().filter(win => win && !win.isDestroyed());
}

function sendToTargets(channel: string, payload: any): void {
  for (const win of liveTargets()) {
    win.webContents.send(channel, payload);
  }
}

function getLocalConfig(): any {
  let configPath = "";
  const isPackaged = app.isPackaged;
  if (isPackaged) {
    configPath = path.join(
      os.homedir(),
      ".deskagent",
      "config",
      "companion.config.json",
    );
  } else {
    configPath = path.join(app.getAppPath(), "config", "companion.config.json");
  }

  if (fs.existsSync(configPath)) {
    try {
      return JSON.parse(fs.readFileSync(configPath, "utf8"));
    } catch {
      // ignore
    }
  }

  const fallbackPath = path.join(
    app.getAppPath(),
    "config",
    "companion.config.json",
  );
  if (fs.existsSync(fallbackPath)) {
    try {
      return JSON.parse(fs.readFileSync(fallbackPath, "utf8"));
    } catch {
      // ignore
    }
  }
  return {};
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

function requestStream(
  method: string,
  path: string,
  payload: any,
  onChunk: (data: any) => void,
  onDone: () => void,
  onError: (err: any) => void
): void {
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
      let buffer = "";
      res.on("data", chunk => {
        buffer += chunk.toString("utf8");
        const lines = buffer.split("\n");
        const last = lines.pop(); // Keep last partial line
        buffer = last !== undefined ? last : "";
        for (const line of lines) {
          const trimmed = line.trim();
          if (!trimmed) continue;
          try {
            const data = JSON.parse(trimmed);
            onChunk(data);
          } catch (err) {
            console.error("[electron] error parsing stream chunk:", err, trimmed);
          }
        }
      });
      res.on("end", () => {
        if (buffer.trim()) {
          try {
            const data = JSON.parse(buffer.trim());
            onChunk(data);
          } catch (err) {
            // ignore
          }
        }
        onDone();
      });
    }
  );

  req.on("timeout", () => req.destroy(new Error("request timeout")));
  req.on("error", onError);
  if (body) req.write(body);
  req.end();
}

function setLipsync(active: boolean): void {
  sendToTargets("set:lipsync", active);
  broadcast("lipsync", active);
}

function setEmotion(emotion: string): void {
  sendToTargets("set:emotion", emotion);
  broadcast("emotion", emotion);
}

function sendAvatarState(response: any): void {
  const avatar = response?.avatar || {};
  const expression = avatar.expression || response?.emotion;
  if (expression) setEmotion(expression);
  if (typeof avatar.lipsync === "boolean") {
    setLipsync(avatar.lipsync);
  }
}

function emitAssistantResponse(response: any): void {
  sendAvatarState(response);
  const text = response?.text || response?.message || "";
  if (text) {
    sendToTargets("chat:chunk", text);
    broadcast("chat_chunk", text);
  }
  if (response?.audio_url) {
    sendToTargets("tts:audio", {
      url: response.audio_url,
      duration_ms: response.duration_ms || 0,
    });
    broadcast("tts_audio", {
      url: response.audio_url,
      duration_ms: response.duration_ms || 0,
    });
  }
  sendToTargets("chat:done", text);
  broadcast("chat_done", text);
  if (!response?.audio_url) setLipsync(false);
}

function audioBase64ToByteArray(audioB64: string): number[] {
  return Array.from(Buffer.from(audioB64, "base64"));
}

export function registerAiIpc(ipcMain: IpcMain, windows: any): void {
  ipcMain.handle("ai:health", async () => {
    try {
      await requestJSON("GET", "/health");
      sendToTargets("python:ready", null);
      return { status: "ok" };
    } catch (err: any) {
      return { status: "offline", error: err.message };
    }
  });

  ipcMain.handle("ai:chat", async (_e: any, { text, image, context }: any) => {
    return new Promise((resolve) => {
      let fullText = "";
      let audioUrl: string | null = null;
      let durationMs = 0;

      requestStream(
        "POST",
        "/chat",
        { text, image, context },
        chunk => {
          if (chunk.type === "start") {
            setEmotion(chunk.emotion || "normal");
            if (chunk.motion) setLipsync(chunk.motion === "thinking");
            broadcast("start", { emotion: chunk.emotion || "normal", motion: chunk.motion });
          } else if (chunk.type === "request_approval") {
            sendToTargets("chat:request-approval", {
              req_id: chunk.req_id,
              action: chunk.action,
              details: chunk.details
            });
          } else if (chunk.type === "text") {
            if (chunk.thought) {
              sendToTargets("chat:thought-chunk", chunk.text);
              broadcast("thought_chunk", chunk.text);
            } else {
              sendToTargets("chat:chunk", chunk.text);
              fullText += chunk.text;
              broadcast("chat_chunk", chunk.text);
            }
          } else if (chunk.type === "emotion") {
            if (chunk.emotion) setEmotion(chunk.emotion);
          } else if (chunk.type === "command") {
            sendToTargets("chat:command", chunk.command);
          } else if (chunk.type === "audio") {
            sendToTargets("tts:audio", {
              url: chunk.audio_url,
              duration_ms: chunk.duration_ms || 0,
            });
            broadcast("tts_audio", {
              url: chunk.audio_url,
              duration_ms: chunk.duration_ms || 0,
            });
          } else if (chunk.type === "done") {
            audioUrl = chunk.audio_url;
            durationMs = chunk.duration_ms;
            if (chunk.emotion) setEmotion(chunk.emotion);
          }
        },
        () => {
          if (audioUrl) {
            sendToTargets("tts:audio", {
              url: audioUrl,
              duration_ms: durationMs || 0,
            });
            broadcast("tts_audio", {
              url: audioUrl,
              duration_ms: durationMs || 0,
            });
          } else {
            setLipsync(false);
          }
          sendToTargets("chat:done", fullText);
          broadcast("chat_done", fullText);
          resolve({ ok: true, response: { text: fullText, audio_url: audioUrl } });
        },
        (err: any) => {
          console.error("[electron] stream error:", err);
          sendToTargets("chat:done", `Có lỗi xảy ra: ${err.message}`);
          broadcast("chat_done", `Có lỗi xảy ra: ${err.message}`);
          resolve({ ok: false, error: err.message });
        }
      );
    });
  });

  ipcMain.handle("ai:voice-input", async (_e: any, { audio_b64, is_draft, sequence, timestamp }: any) => {
    try {
      const response = await requestJSON("POST", "/voice/transcribe", {
        audio_bytes: audioBase64ToByteArray(audio_b64),
        mime_type: "audio/wav",
        is_draft,
        sequence,
        timestamp,
      });
      if (response.success && !is_draft) {
        sendToTargets("stt:result", response.text);
      }
      return { ok: response.success, response };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle("ai:cancel-chat", async () => {
    try {
      const response = await requestJSON("POST", "/chat/cancel", {});
      return { ok: true, response };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle("ai:load-doc", async (_e: any, { path: p }: any) => {
    try {
      const response = await requestJSON("POST", "/documents/import", { path: p });
      sendToTargets("doc:loaded", response);
      return { ok: response.success !== false, response };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle("ai:screenshot", async (_e: any, { question }: any) => {
    try {
      const response = await requestJSON("POST", "/chat", {
        text: question || "Nhin man hinh va mo ta noi dung dang hien thi.",
        context: {},
      });
      emitAssistantResponse(response);
      return { ok: true, response };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle("ai:get-memories", async () => {
    try {
      const response = await requestJSON("GET", "/memories");
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:update-memory", async (_e: any, { id, text }: any) => {
    try {
      const response = await requestJSON("POST", "/memories/update", { id, text });
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:delete-memory", async (_e: any, { id }: any) => {
    try {
      const response = await requestJSON("POST", "/memories/delete", { id });
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:add-memory", async (_e: any, { text }: any) => {
    try {
      const response = await requestJSON("POST", "/memories/add", { text });
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:tts", async (_e: any, { text }: any) => {
    try {
      const response = await requestJSON("POST", "/voice/tts", { text });
      return { ok: response.success !== false, response };
    } catch (err: any) {
      return { ok: false, error: err.message };
    }
  });

  ipcMain.handle("ai:get-config", async () => {
    try {
      const response = await requestJSON("GET", "/config");
      return response;
    } catch (err: any) {
      console.log("[ai.ipc] Python config server not ready, using local config fallback...");
      try {
        const localConfig = getLocalConfig();
        if (localConfig && Object.keys(localConfig).length > 0) {
          return {
            avatar_model: localConfig.app?.avatarModel || "assets/live2d/IceGirl/IceGirl.model3.json",
            avatar_scale: localConfig.app?.avatarScale || "1.0",
            avatar_x: localConfig.app?.avatarX || "0",
            avatar_y: localConfig.app?.avatarY || "0",
            background_image: localConfig.app?.backgroundImage || "",
            interaction_mode: localConfig.app?.interactionMode || "streamer",
            llm_provider: localConfig.llm?.provider || "ollama",
            stt_model: localConfig.stt?.model || "base",
            tts_backend: localConfig.tts?.backend || "edge",
            screen_awareness: localConfig.features?.screenAwareness || false,
            twitch_mode: localConfig.features?.twitchMode || false,
            twitch_channel: localConfig.twitch?.channel || "",
            memory: localConfig.features?.memory !== false
          };
        }
      } catch (fallbackErr) {
        console.error("[ai.ipc] Fallback local config error:", fallbackErr);
      }
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:get-notifications", async (_e: any, client = "avatar") => {
    try {
      const response = await requestJSON("GET", `/notifications?client=${client}`);
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:update-config", async (_e: any, { key, value }: any) => {
    try {
      const response = await requestJSON("POST", "/config/update", { key, value });
      sendToTargets("config:updated", { key, value });

      if (key === "app.avatarScale") {
        const scale = parseFloat(value) || 1.0;
        const AVATAR_WINDOW_WIDTH = 420;
        const AVATAR_WINDOW_HEIGHT = 640;
        const avatarWin = BrowserWindow.getAllWindows().find(win => {
          try {
            return win.webContents.getURL().includes("avatar.html") || win.webContents.getURL().includes("overlay");
          } catch {
            return false;
          }
        });
        if (avatarWin && !avatarWin.isDestroyed()) {
          const newW = Math.round(AVATAR_WINDOW_WIDTH * scale);
          const newH = Math.round(AVATAR_WINDOW_HEIGHT * scale);
          const [curX, curY] = avatarWin.getPosition();
          const [curW, curH] = avatarWin.getSize();
          const newX = curX + curW - newW;
          const newY = curY + curH - newH;
          
          const wasResizable = avatarWin.isResizable();
          avatarWin.setResizable(true);
          avatarWin.setSize(newW, newH);
          avatarWin.setPosition(newX, newY);
          avatarWin.setResizable(wasResizable);
        }
      }

      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:interact", async () => {
    try {
      const response = await requestJSON("POST", "/interact");
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:submit-approval", async (_e: any, { req_id, approved }: any) => {
    try {
      const response = await requestJSON("POST", "/chat/approve", { req_id, approved });
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });

  ipcMain.handle("ai:trigger-voice", async () => {
    sendToTargets("voice:listen", "start");
    return { success: true };
  });

  ipcMain.on("ai:broadcast", (_e: any, { event, data }: any) => {
    broadcast(event, data);
  });

  ipcMain.handle("avatar:upload-background", async (_e: any, { filePath }: { filePath: string }) => {
    try {
      const destDir = path.join(app.getAppPath(), "assets", "backgrounds");
      if (!fs.existsSync(destDir)) {
        fs.mkdirSync(destDir, { recursive: true });
      }
      const ext = path.extname(filePath);
      const fileName = `bg_${Date.now()}${ext}`;
      const destPath = path.join(destDir, fileName);
      fs.copyFileSync(filePath, destPath);
      return { success: true, path: `assets/backgrounds/${fileName}` };
    } catch (err: any) {
      return { success: false, error: err.message };
    }
  });

  ipcMain.handle("avatar:get-backgrounds", async () => {
    try {
      const dir = path.join(app.getAppPath(), "assets", "backgrounds");
      if (!fs.existsSync(dir)) return [];
      const files = fs.readdirSync(dir);
      const images = files.filter(f => {
        const ext = path.extname(f).toLowerCase();
        return [".png", ".jpg", ".jpeg", ".webp", ".gif"].includes(ext);
      });
      return images.map(f => `assets/backgrounds/${f}`);
    } catch {
      return [];
    }
  });

  ipcMain.handle("system:import-document", async (_e: any, { path }: { path: string }) => {
    try {
      const response = await requestJSON("POST", "/documents/import", { file_path: path });
      return response;
    } catch (err: any) {
      return { error: err.message };
    }
  });
}
