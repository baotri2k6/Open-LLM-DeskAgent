const {
  app,
  BrowserWindow,
  ipcMain,
  screen,
  globalShortcut,
  nativeTheme,
} = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

app.commandLine.appendSwitch('autoplay-policy', 'no-user-gesture-required');

const { registerAiIpc } = require("./ipc/ai.ipc");
const { registerAvatarIpc } = require("./ipc/avatar.ipc");
const { registerSystemIpc } = require("./ipc/system.ipc");
const { registerVoiceIpc } = require("./ipc/voice.ipc");
const { createTray } = require("./window/tray");
const { createOverlayWindow } = require("./window/overlay");

function getPythonCommand() {
  if (process.platform !== "win32") {
    return "python";
  }

  // 1. Check local appdata (default location for Python installer)
  const localAppData = process.env.LOCALAPPDATA;
  if (localAppData) {
    const pythonProgramsDir = path.join(localAppData, "Programs", "Python");
    if (fs.existsSync(pythonProgramsDir)) {
      try {
        const dirs = fs.readdirSync(pythonProgramsDir);
        const versionDirs = dirs.filter(d => d.startsWith("Python")).sort().reverse();
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
    const pyLauncher = path.join(localAppData, "Programs", "Python", "Launcher", "py.exe");
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

let avatarWin = null;
let chatWin = null;
let settingsWin = null;
let pythonProc = null;
let pythonReady = false;
const AVATAR_WINDOW_WIDTH = 420;
const AVATAR_WINDOW_HEIGHT = 640;

function startPython() {
  if (pythonProc) return;
  const script = path.join(
    app.getAppPath(),
    "python-services",
    "main_server.py",
  );
  const pythonCmd = getPythonCommand();
  console.log("[electron] Spawning python using:", pythonCmd);

  // Ensure logs directory exists
  const logDir = path.join(app.getAppPath(), "logs");
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }

  pythonProc = spawn(pythonCmd, [script], {
    cwd: app.getAppPath(),
    windowsHide: true,
    stdio: ["ignore", "pipe", "pipe"],
    env: { ...process.env, PYTHONUNBUFFERED: "1" },
  });

  pythonProc.stdout.on("data", (d) => {
    const msg = d.toString().trim();
    console.log("[python]", msg);
    if (msg.includes("READY") || msg.includes("listening")) {
      pythonReady = true;
      avatarWin?.webContents.send("python:ready");
      chatWin?.webContents.send("python:ready");
    }
  });

  pythonProc.stderr.on("data", (d) => {
    const msg = d.toString().trim();
    console.error("[python stderr]", msg);
    fs.appendFileSync(
      path.join(logDir, "python_launch_error.log"),
      `${new Date().toISOString()} | STDERR | ${msg}\n`
    );
  });

  pythonProc.on("error", (err) => {
    console.error("[python spawn error]", err);
    fs.appendFileSync(
      path.join(logDir, "python_launch_error.log"),
      `${new Date().toISOString()} | SPAWN_ERROR | ${err.message}\n`
    );
  });

  pythonProc.on("exit", (code) => {
    console.log("[python] exited", code);
    fs.appendFileSync(
      path.join(logDir, "python_launch_error.log"),
      `${new Date().toISOString()} | EXIT | Python process exited with code ${code}\n`
    );
    pythonProc = null;
    pythonReady = false;
  });
}

function createAvatarWindow() {
  const { width, height } = screen.getPrimaryDisplay().workAreaSize;

  avatarWin = new BrowserWindow({
    width: AVATAR_WINDOW_WIDTH,
    height: AVATAR_WINDOW_HEIGHT,
    x: width - AVATAR_WINDOW_WIDTH,
    y: height - AVATAR_WINDOW_HEIGHT,
    transparent: true, // ← BẮT BUỘC
    frame: false, // ← BẮT BUỘC
    resizable: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    hasShadow: false, // ← tắt shadow
    backgroundColor: "#00000000", // ← RGBA hoàn toàn trong suốt
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  avatarWin.setBackgroundColor("#00000000");
  avatarWin.webContents.on("console-message", (event, level, message, line, sourceId) => {
    const logDir = path.join(app.getAppPath(), "logs");
    if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
    fs.appendFileSync(
      path.join(logDir, "renderer_error.log"),
      `${new Date().toISOString()} | AVATAR | [Level ${level}] ${message} (at ${sourceId}:${line})\n`
    );
  });
  avatarWin.loadFile(path.join(__dirname, "..", "renderer", "avatar.html"));
  avatarWin.on("closed", () => {
    avatarWin = null;
    chatWin = null;
  });

  return avatarWin;
}

function toggleChat() {
  if (!avatarWin) return;
  if (avatarWin.isVisible()) {
    avatarWin.hide();
  } else {
    avatarWin.show();
    avatarWin.focus();
  }
}

function setupCrossWindowIpc() {
  ipcMain.on("avatar:click", () => avatarWin?.show());
  ipcMain.on("avatar:hide", () => avatarWin?.hide());
  ipcMain.on("window:set-ignore-mouse-events", (event, ignore, options) => {
    const win = BrowserWindow.fromWebContents(event.sender);
    if (win) {
      win.setIgnoreMouseEvents(ignore, options);
    }
  });
  ipcMain.on("avatar:emotion", (_e, emotion) => {
    avatarWin?.webContents.send("set:emotion", emotion);
  });
  ipcMain.on("tts:speaking", (_e, active) => {
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
  ipcMain.handle("pet:move-to", (_e, point) => {
    if (!avatarWin || !point) return null;
    const [width, height] = avatarWin.getSize();
    const current = avatarWin.getBounds();
    const display = screen.getDisplayMatching(current);
    
    // Use display.bounds to allow dragging over taskbar
    const { x, y, width: sw, height: sh } = display.bounds;
    
    // Allow dragging partially off-screen (keep at least 80px on-screen so it's retrievable)
    const minVisible = 80;
    const nextX = Math.max(x - width + minVisible, Math.min(x + sw - minVisible, Math.round(point.x)));
    const nextY = Math.max(y - height + minVisible, Math.min(y + sh - minVisible, Math.round(point.y)));
    
    avatarWin.setPosition(nextX, nextY, false);
    return { x: nextX, y: nextY, width, height, workArea: display.workArea };
  });
}

function createSettingsWindow() {
  if (settingsWin) {
    settingsWin.focus();
    return;
  }
  settingsWin = new BrowserWindow({
    width: 600,
    height: 520,
    title: "AI Companion Settings",
    resizable: true,
    icon: path.join(app.getAppPath(), "assets", "icons", "icon.png"),
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });
  settingsWin.webContents.on("console-message", (event, level, message, line, sourceId) => {
    const logDir = path.join(app.getAppPath(), "logs");
    if (!fs.existsSync(logDir)) fs.mkdirSync(logDir, { recursive: true });
    fs.appendFileSync(
      path.join(logDir, "renderer_error.log"),
      `${new Date().toISOString()} | SETTINGS | [Level ${level}] ${message} (at ${sourceId}:${line})\n`
    );
  });
  settingsWin.loadFile(path.join(__dirname, "..", "renderer", "settings.html"));
  settingsWin.on("closed", () => {
    settingsWin = null;
  });
}

app.whenReady().then(() => {
  nativeTheme.themeSource = "dark";

  // Cho phép microphone — không có dòng này getUserMedia bị block im lặng
  const { session } = require("electron");
  session.defaultSession.setPermissionRequestHandler(
    (webContents, permission, callback) => {
      if (permission === "media") return callback(true);
      callback(false);
    },
  );

  startPython();
  createAvatarWindow();
  setupCrossWindowIpc();
  registerAiIpc(ipcMain, avatarWin);
  registerAvatarIpc(ipcMain, avatarWin);
  registerSystemIpc(ipcMain);
  registerVoiceIpc(ipcMain, avatarWin);
  createTray({
    toggleChat,
    showAvatar: () => avatarWin?.show(),
    openSettings: createSettingsWindow,
    quit: () => app.quit(),
  });
  globalShortcut.register("CommandOrControl+Shift+Space", toggleChat);
  globalShortcut.register("CommandOrControl+Shift+S", () => {
    chatWin?.webContents.send("trigger:screenshot");
  });
  globalShortcut.register("CommandOrControl+Shift+H", () => {
    avatarWin?.webContents.send("toggle:console");
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
