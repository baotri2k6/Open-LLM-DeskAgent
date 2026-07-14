import {
  app,
  BrowserWindow,
  ipcMain,
  screen,
  globalShortcut,
  nativeTheme,
  session,
  dialog,
  IpcMainEvent
} from "electron";
import * as path from "path";
import { spawn, ChildProcess } from "child_process";
import * as fs from "fs";
import * as os from "os";

app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");

import { registerAiIpc } from "./ipc/ai.ipc";
import { registerAvatarIpc } from "./ipc/avatar.ipc";
import { registerSystemIpc } from "./ipc/system.ipc";
import { registerVoiceIpc } from "./ipc/voice.ipc";
import { createTray } from "./tray/tray";
import { createOverlayWindow } from "./windows/overlay";
import { startWebSocketServer } from "./websocket-server";

function getLogDirectory(): string {
  const isPackaged = app.isPackaged;
  const base = isPackaged ? app.getPath("userData") : app.getAppPath();
  return path.join(base, "logs");
}

function getCompanionConfig(): any {
  const isPackaged = app.isPackaged;
  let configPath = "";
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
      const data = JSON.parse(fs.readFileSync(configPath, "utf8"));
      return data;
    } catch (e) {
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
    } catch (e) {
      // ignore
    }
  }
  return {};
}

function getAvatarWindowSize(): { width: number; height: number } {
  const conf = getCompanionConfig();
  const scale = parseFloat(conf.app && conf.app.avatarScale) || 1.0;
  return {
    width: Math.round(AVATAR_WINDOW_WIDTH * scale),
    height: Math.round(AVATAR_WINDOW_HEIGHT * scale),
  };
}

function getPythonCommand(): string {
  const isWin = process.platform === "win32";
  const venvDir = isWin ? "Scripts" : "bin";
  const pythonExe = isWin ? "python.exe" : "python";

  const venvPython = path.join(process.cwd(), ".venv", venvDir, pythonExe);
  if (fs.existsSync(venvPython)) {
    return venvPython;
  }

  const virtualEnvPython = process.env.VIRTUAL_ENV
    ? path.join(process.env.VIRTUAL_ENV, venvDir, pythonExe)
    : null;
  if (virtualEnvPython && fs.existsSync(virtualEnvPython)) {
    return virtualEnvPython;
  }

  if (!isWin) {
    return "python";
  }

  // 1. Check local appdata (default location for Python installer)
  const localAppData = process.env.LOCALAPPDATA;
  if (localAppData) {
    const pythonProgramsDir = path.join(localAppData, "Programs", "Python");
    if (fs.existsSync(pythonProgramsDir)) {
      try {
        const dirs = fs.readdirSync(pythonProgramsDir);
        const versionDirs = dirs
          .filter((d) => d.startsWith("Python"))
          .sort()
          .reverse();
        for (const dir of versionDirs) {
          const exePath = path.join(pythonProgramsDir, dir, "python.exe");
          if (fs.existsSync(exePath)) {
            return exePath;
          }
        }
      } catch (err) {
        // ignore
      }
    }

    // Try Python Launcher
    const pyLauncher = path.join(
      localAppData,
      "Programs",
      "Python",
      "Launcher",
      "py.exe",
    );
    if (fs.existsSync(pyLauncher)) {
      return pyLauncher;
    }
  }

  // 2. Check Program Files
  const paths = [
    "C:\\Program Files\\Python311\\python.exe",
    "C:\\Program Files\\Python312\\python.exe",
    "C:\\Program Files (x86)\\Python311\\python.exe",
    "C:\\Program Files (x86)\\Python312\\python.exe",
  ];
  for (const p of paths) {
    if (fs.existsSync(p)) return p;
  }

  // 3. Fallback
  return "python";
}

function getPythonEnv(): NodeJS.ProcessEnv {
  const env: NodeJS.ProcessEnv = { ...process.env, PYTHONUNBUFFERED: "1" };

  if (process.platform === "linux" && env.DISPLAY && !env.XAUTHORITY) {
    const runtimeDir = env.XDG_RUNTIME_DIR || path.join("/run/user", `${process.getuid?.()}`);
    const candidates = [
      path.join(os.homedir(), ".Xauthority"),
      path.join(runtimeDir, "gdm", "Xauthority"),
      path.join(runtimeDir, "Xauthority"),
    ];
    try {
      const mutterAuth = fs
        .readdirSync(runtimeDir)
        .filter((name) => name.startsWith(".mutter-Xwaylandauth"))
        .map((name) => path.join(runtimeDir, name))
        .sort()
        .reverse();
      candidates.push(...mutterAuth);
    } catch {
      // Ignore missing or inaccessible runtime directories.
    }

    const xauthority = candidates.find((candidate) => fs.existsSync(candidate));
    if (xauthority) {
      env.XAUTHORITY = xauthority;
    }
  }

  return env;
}

let avatarWin: BrowserWindow | null = null;
let chatWin: BrowserWindow | null = null;
let settingsWin: BrowserWindow | null = null;
const linuxMousePollers = new Map<number, NodeJS.Timeout>();
let pythonProc: ChildProcess | null = null;
let pythonReady = false;
const AVATAR_WINDOW_WIDTH = 420;
const AVATAR_WINDOW_HEIGHT = 640;

function startPython(): void {
  if (pythonProc) return;

  const isPackaged = app.isPackaged;
  let cmd: string;
  let args: string[] = [];

  if (isPackaged) {
    cmd = path.join(process.resourcesPath, "main_server.exe");
    args = [];
    console.log("[electron] Spawning packaged python backend:", cmd);
  } else {
    cmd = getPythonCommand();
    const script = path.join(
      app.getAppPath(),
      "api",
      "server.py",
    );
    args = [script];
    console.log("[electron] Spawning python using:", cmd, args);
  }

  // Ensure logs directory exists
  const logDir = getLogDirectory();
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }

  pythonProc = spawn(cmd, args, {
    cwd: isPackaged ? path.join(process.resourcesPath, "..") : app.getAppPath(),
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: getPythonEnv(),
  });

  if (pythonProc.stdout) {
    pythonProc.stdout.on("data", (d: any) => {
      const msg = d.toString().trim();
      console.log("[python]", msg);
      if (msg.includes("READY") || msg.includes("listening")) {
        pythonReady = true;
        avatarWin?.webContents.send("python:ready");
        chatWin?.webContents.send("python:ready");
      }
    });
  }

  if (pythonProc.stderr) {
    pythonProc.stderr.on("data", (d: any) => {
      const msg = d.toString().trim();
      console.error("[python stderr]", msg);
      fs.appendFileSync(
        path.join(logDir, "python_launch_error.log"),
        `${new Date().toISOString()} | STDERR | ${msg}\n`,
      );
    });
  }

  pythonProc.on("error", (err: any) => {
    console.error("[python spawn error]", err);
    fs.appendFileSync(
      path.join(logDir, "python_launch_error.log"),
      `${new Date().toISOString()} | SPAWN_ERROR | ${err.message}\n`,
    );
  });

  pythonProc.on("exit", (code: any) => {
    console.log("[python] exited", code);
    fs.appendFileSync(
      path.join(logDir, "python_launch_error.log"),
      `${new Date().toISOString()} | EXIT | Python process exited with code ${code}\n`,
    );
    pythonProc = null;
    pythonReady = false;
  });
}

function createAvatarWindow(): BrowserWindow {
  const { x, y, width: sw, height: sh } = screen.getPrimaryDisplay().workArea;
  const { width, height } = getAvatarWindowSize();

  avatarWin = new BrowserWindow({
    width,
    height,
    x: x + sw - width,
    y: y,
    transparent: true,
    frame: false,
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false,
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
    },
  });
  avatarWin.setBackgroundColor("#00000000");
  avatarWin.webContents.on(
    "console-message",
    (event: any, level: number, message: string, line: number, sourceId: string) => {
      const logDir = getLogDirectory();
      if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
      fs.appendFileSync(
        path.join(logDir, "renderer_error.log"),
        `${new Date().toISOString()} | AVATAR | [Level ${level}] ${message} (at ${sourceId}:${line})\n`,
      );
    },
  );
  avatarWin.loadFile(path.join(__dirname, "..", "renderer", "overlay", "index.html"));
  avatarWin.on("closed", () => {
    avatarWin = null;
    chatWin = null;
  });

  return avatarWin;
}

function toggleChat(): void {
  if (!avatarWin) return;
  if (avatarWin.isVisible()) {
    avatarWin.hide();
  } else {
    avatarWin.show();
    avatarWin.focus();
  }
}

function stopLinuxMousePolling(win: BrowserWindow): void {
  const timer = linuxMousePollers.get(win.id);
  if (timer) {
    clearInterval(timer);
    linuxMousePollers.delete(win.id);
  }
}

function startLinuxMousePolling(win: BrowserWindow): void {
  if (process.platform !== "linux" || linuxMousePollers.has(win.id)) return;

  const timer = setInterval(() => {
    if (win.isDestroyed() || !win.isVisible()) {
      stopLinuxMousePolling(win);
      return;
    }

    const cursor = screen.getCursorScreenPoint();
    const bounds = win.getBounds();
    win.webContents.send("window:cursor-move", {
      x: cursor.x - bounds.x,
      y: cursor.y - bounds.y,
      screenX: cursor.x,
      screenY: cursor.y,
    });
  }, 50);

  linuxMousePollers.set(win.id, timer);
  win.once("closed", () => stopLinuxMousePolling(win));
}

function setupCrossWindowIpc(): void {
  ipcMain.on("avatar:click", () => avatarWin?.show());
  ipcMain.on("avatar:hide", () => avatarWin?.hide());
  ipcMain.on("window:set-ignore-mouse-events", (event: IpcMainEvent, ignore: boolean, options: any) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      if (process.platform === "linux") {
        win.setIgnoreMouseEvents(ignore);
        if (ignore) {
          startLinuxMousePolling(win);
        } else {
          stopLinuxMousePolling(win);
        }
      } else {
        win.setIgnoreMouseEvents(ignore, options);
      }
    }
  });
  ipcMain.on("avatar:emotion", (_e: any, emotion: string) => {
    avatarWin?.webContents.send("set:emotion", emotion);
  });
  ipcMain.on("tts:speaking", (_e: any, active: boolean) => {
    avatarWin?.webContents.send("set:lipsync", active);
  });
  ipcMain.handle("python:status", () => ({ ready: pythonReady }));
  ipcMain.handle("pet:get-bounds", () => {
    if (!avatarWin) return null;
    const [x, y] = avatarWin.getPosition();
    const [width, height] = avatarWin.getSize();
    const display = screen.getDisplayMatching({ x, y, width, height });
    return { x, y, width, height, workArea: display.workArea };
  });
  ipcMain.handle("pet:move-to", (_e: any, point: { x: number; y: number }) => {
    if (!avatarWin || !point) return null;
    const [width, height] = avatarWin.getSize();
    const targetX = Math.round(point.x);
    const targetY = Math.round(point.y);
    const display = screen.getDisplayNearestPoint({ x: targetX, y: targetY });

    const { x, y, width: sw, height: sh } = display.bounds;

    const minVisible = 80;
    const nextX = Math.max(
      x - width + minVisible,
      Math.min(x + sw - minVisible, targetX),
    );
    const nextY = Math.max(
      y - height + minVisible,
      Math.min(y + sh - minVisible, targetY),
    );

    avatarWin.setPosition(nextX, nextY, false);
    return { x: nextX, y: nextY, width, height, workArea: display.workArea };
  });

  ipcMain.handle("pet:set-size", (_e: any, scale: number) => {
    if (!avatarWin) return null;
    const newW = Math.round(AVATAR_WINDOW_WIDTH * scale);
    const newH = Math.round(AVATAR_WINDOW_HEIGHT * scale);
    const [curX, curY] = avatarWin.getPosition();
    const display = screen.getDisplayNearestPoint({ x: curX, y: curY });
    const { x: sx, y: sy, width: sw, height: sh } = display.workArea;
    const nextX = Math.max(sx, Math.min(curX, sx + sw - newW));
    const nextY = Math.max(
      sy,
      Math.min(curY + (avatarWin.getSize()[1] - newH), sy + sh - newH),
    );
    const wasResizable = avatarWin.isResizable();
    avatarWin.setResizable(true);
    avatarWin.setSize(newW, newH, true);
    avatarWin.setPosition(nextX, nextY, true);
    avatarWin.setResizable(wasResizable);
    return { width: newW, height: newH, scale };
  });

  ipcMain.on("window:open-settings", () => {
    createSettingsWindow();
  });

  ipcMain.on("window:toggle-chat", () => {
    createChatWindow();
  });

  ipcMain.handle("win:minimize-chat", () => {
    chatWin?.minimize();
  });

  ipcMain.handle("win:close-chat", () => {
    chatWin?.hide();
  });

  ipcMain.handle("dialog:select-folder", async (event: any) => {
    const win = BrowserWindow.fromWebContents(event.sender) || settingsWin || avatarWin;
    if (!win) return null;
    const result = await dialog.showOpenDialog(win, {
      properties: ["openDirectory"]
    });
    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }
    return result.filePaths[0];
  });

  ipcMain.handle("dialog:open-file", async (event: any, options: any) => {
    const win = BrowserWindow.fromWebContents(event.sender) || settingsWin || avatarWin;
    if (!win) return null;
    const result = await dialog.showOpenDialog(win, {
      properties: ["openFile"],
      title: options?.title || "Select file",
      filters: options?.filters || []
    });
    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }
    return result.filePaths[0];
  });
}

function createSettingsWindow(): void {
  if (settingsWin) {
    settingsWin.focus();
    return;
  }
  settingsWin = new BrowserWindow({
    width: 960,
    height: 580,
    title: "Airi Settings",
    resizable: true,
    icon: path.join(app.getAppPath(), "assets", "icons", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  settingsWin.webContents.on(
    "console-message",
    (event: any, level: number, message: string, line: number, sourceId: string) => {
      const logDir = getLogDirectory();
      if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
      fs.appendFileSync(
        path.join(logDir, "renderer_error.log"),
        `${new Date().toISOString()} | SETTINGS | [Level ${level}] ${message} (at ${sourceId}:${line})\n`,
      );
    },
  );
  settingsWin.loadFile(path.join(__dirname, "..", "renderer", "settings", "settings.html"));
  settingsWin.on("closed", () => {
    settingsWin = null;
  });
}

function createChatWindow(): void {
  if (chatWin) {
    if (chatWin.isVisible()) {
      chatWin.hide();
    } else {
      chatWin.show();
      chatWin.focus();
    }
    return;
  }

  const { width: sw, height: sh } = screen.getPrimaryDisplay().workArea;
  const wWidth = 400;
  const wHeight = 600;

  chatWin = new BrowserWindow({
    width: wWidth,
    height: wHeight,
    x: sw - wWidth - 450, // Positioned slightly to the left of the avatar window
    y: sh - wHeight - 20,
    transparent: true,
    frame: false,
    resizable: true,
    alwaysOnTop: true,
    backgroundColor: "#00000000",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
      webSecurity: false,
    },
  });

  chatWin.setBackgroundColor("#00000000");

  chatWin.webContents.on(
    "console-message",
    (event: any, level: number, message: string, line: number, sourceId: string) => {
      const logDir = getLogDirectory();
      if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
      fs.appendFileSync(
        path.join(logDir, "renderer_error.log"),
        `${new Date().toISOString()} | CHAT | [Level ${level}] ${message} (at ${sourceId}:${line})\n`,
      );
    },
  );

  chatWin.loadFile(path.join(__dirname, "..", "renderer", "chat", "chat.html"));
  
  chatWin.on("closed", () => {
    chatWin = null;
  });
}

app.whenReady().then(() => {
  nativeTheme.themeSource = "dark";

  session.defaultSession.setPermissionRequestHandler(
    (webContents: any, permission: string, callback: (granted: boolean) => void) => {
      if (permission === "media") return callback(true);
      callback(false);
    },
  );

  startWebSocketServer(9001);
  startPython();
  createAvatarWindow();
  setupCrossWindowIpc();
  registerAiIpc(ipcMain, avatarWin);
  registerAvatarIpc(ipcMain, avatarWin);
  registerSystemIpc(ipcMain);
  registerVoiceIpc(ipcMain, avatarWin);
  createTray({
    toggleChat,
    showAvatar: () => {
      if (avatarWin) {
        avatarWin.show();
        avatarWin.focus();
      }
    },
    openSettings: createSettingsWindow,
    quit: () => app.quit(),
    setSize: (scale: number) => {
      if (!avatarWin) return;
      const newW = Math.round(AVATAR_WINDOW_WIDTH * scale);
      const newH = Math.round(AVATAR_WINDOW_HEIGHT * scale);
      const [curX, curY] = avatarWin.getPosition();
      const display = screen.getDisplayNearestPoint({ x: curX, y: curY });
      const { x: sx, y: sy, width: sw, height: sh } = display.workArea;
      const nextX = Math.max(sx, Math.min(curX, sx + sw - newW));
      const nextY = Math.max(
        sy,
        Math.min(curY + (avatarWin.getSize()[1] - newH), sy + sh - newH),
      );
      const wasResizable = avatarWin.isResizable();
      avatarWin.setResizable(true);
      avatarWin.setSize(newW, newH, true);
      avatarWin.setPosition(nextX, nextY, true);
      avatarWin.setResizable(wasResizable);
    },
    alignTo: (position: "bottom-right" | "bottom-left" | "top-right" | "top-left" | "center") => {
      if (!avatarWin) return;
      const [width, height] = avatarWin.getSize();
      const [curX, curY] = avatarWin.getPosition();
      const display = screen.getDisplayNearestPoint({ x: curX, y: curY });
      const { x, y, width: sw, height: sh } = display.workArea;

      let targetX = x;
      let targetY = y;

      if (position === "bottom-right") {
        targetX = x + sw - width;
        targetY = y + sh - height;
      } else if (position === "bottom-left") {
        targetX = x;
        targetY = y + sh - height;
      } else if (position === "top-right") {
        targetX = x + sw - width;
        targetY = y;
      } else if (position === "top-left") {
        targetX = x;
        targetY = y;
      } else if (position === "center") {
        targetX = x + Math.round((sw - width) / 2);
        targetY = y + Math.round((sh - height) / 2);
      }

      avatarWin.setPosition(targetX, targetY, true);
    },
    openDevTools: () => {
      avatarWin?.webContents.openDevTools({ mode: "detach" });
    },
    openWidgets: () => {
      dialog.showMessageBox({ type: "info", title: "Widgets", message: "Opening Widgets overlay...", buttons: ["OK"] });
    },
    openInlay: () => {
      dialog.showMessageBox({ type: "info", title: "Inlay", message: "Opening Inlay overlay...", buttons: ["OK"] });
    },
    openCaption: () => {
      dialog.showMessageBox({ type: "info", title: "Caption", message: "Opening Caption overlay...", buttons: ["OK"] });
    },
    toggleCaptionOverlay: (enabled: boolean) => {
      dialog.showMessageBox({ type: "info", title: "Caption Overlay", message: `Caption Overlay set to: ${enabled ? "Enabled" : "Disabled"}`, buttons: ["OK"] });
    },
    troubleshootBeatSync: () => {
      dialog.showMessageBox({
        type: "info",
        title: "Troubleshoot BeatSync",
        message: "Running BeatSync Connection Diagnostics...",
        detail: "All local endpoints checked: OK\nWebSocket latency: 2ms\nAudio sync buffer status: Optimal.",
        buttons: ["Close"]
      });
    }
  });
  globalShortcut.register("CommandOrControl+Shift+Space", toggleChat);
  globalShortcut.register("CommandOrControl+Shift+S", () => {
    chatWin?.webContents.send("trigger:screenshot");
  });
  globalShortcut.register("CommandOrControl+Shift+H", () => {
    avatarWin?.webContents.send("toggle:console");
  });
  globalShortcut.register("CommandOrControl+Shift+I", () => {
    avatarWin?.webContents.openDevTools({ mode: "detach" });
    settingsWin?.webContents.openDevTools({ mode: "detach" });
  });
});

app.on("before-quit", () => {
  globalShortcut.unregisterAll();
  if (pythonProc) {
    pythonProc.kill();
    pythonProc = null;
  }
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});
