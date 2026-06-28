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
const electron_1 = require("electron");
const path = __importStar(require("path"));
const child_process_1 = require("child_process");
const fs = __importStar(require("fs"));
const os = __importStar(require("os"));
electron_1.app.commandLine.appendSwitch("autoplay-policy", "no-user-gesture-required");
const ai_ipc_1 = require("./ipc/ai.ipc");
const avatar_ipc_1 = require("./ipc/avatar.ipc");
const system_ipc_1 = require("./ipc/system.ipc");
const voice_ipc_1 = require("./ipc/voice.ipc");
const tray_1 = require("./tray/tray");
const websocket_server_1 = require("./websocket-server");
function getLogDirectory() {
    const isPackaged = electron_1.app.isPackaged;
    const base = isPackaged ? electron_1.app.getPath("userData") : electron_1.app.getAppPath();
    return path.join(base, "logs");
}
function getCompanionConfig() {
    const isPackaged = electron_1.app.isPackaged;
    let configPath = "";
    if (isPackaged) {
        configPath = path.join(os.homedir(), ".deskagent", "config", "companion.config.json");
    }
    else {
        configPath = path.join(electron_1.app.getAppPath(), "config", "companion.config.json");
    }
    if (fs.existsSync(configPath)) {
        try {
            const data = JSON.parse(fs.readFileSync(configPath, "utf8"));
            return data;
        }
        catch (e) {
            // ignore
        }
    }
    const fallbackPath = path.join(electron_1.app.getAppPath(), "config", "companion.config.json");
    if (fs.existsSync(fallbackPath)) {
        try {
            return JSON.parse(fs.readFileSync(fallbackPath, "utf8"));
        }
        catch (e) {
            // ignore
        }
    }
    return {};
}
function getAvatarWindowSize() {
    const conf = getCompanionConfig();
    const scale = parseFloat(conf.app && conf.app.avatarScale) || 1.0;
    return {
        width: Math.round(AVATAR_WINDOW_WIDTH * scale),
        height: Math.round(AVATAR_WINDOW_HEIGHT * scale),
    };
}
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
            }
            catch (err) {
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
        if (fs.existsSync(p))
            return p;
    }
    // 3. Fallback
    return "python";
}
let avatarWin = null;
let chatWin = null;
let settingsWin = null;
let codingWin = null;
let pythonProc = null;
let pythonReady = false;
const AVATAR_WINDOW_WIDTH = 420;
const AVATAR_WINDOW_HEIGHT = 640;
function startPython() {
    if (pythonProc)
        return;
    const isPackaged = electron_1.app.isPackaged;
    let cmd;
    let args = [];
    if (isPackaged) {
        cmd = path.join(process.resourcesPath, "main_server.exe");
        args = [];
        console.log("[electron] Spawning packaged python backend:", cmd);
    }
    else {
        cmd = getPythonCommand();
        const script = path.join(electron_1.app.getAppPath(), "api", "server.py");
        args = [script];
        console.log("[electron] Spawning python using:", cmd, args);
    }
    // Ensure logs directory exists
    const logDir = getLogDirectory();
    if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
    }
    pythonProc = (0, child_process_1.spawn)(cmd, args, {
        cwd: isPackaged ? path.join(process.resourcesPath, "..") : electron_1.app.getAppPath(),
        windowsHide: true,
        stdio: ["ignore", "pipe", "pipe"],
        env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });
    if (pythonProc.stdout) {
        pythonProc.stdout.on("data", (d) => {
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
        pythonProc.stderr.on("data", (d) => {
            const msg = d.toString().trim();
            console.error("[python stderr]", msg);
            fs.appendFileSync(path.join(logDir, "python_launch_error.log"), `${new Date().toISOString()} | STDERR | ${msg}\n`);
        });
    }
    pythonProc.on("error", (err) => {
        console.error("[python spawn error]", err);
        fs.appendFileSync(path.join(logDir, "python_launch_error.log"), `${new Date().toISOString()} | SPAWN_ERROR | ${err.message}\n`);
    });
    pythonProc.on("exit", (code) => {
        console.log("[python] exited", code);
        fs.appendFileSync(path.join(logDir, "python_launch_error.log"), `${new Date().toISOString()} | EXIT | Python process exited with code ${code}\n`);
        pythonProc = null;
        pythonReady = false;
    });
}
function createAvatarWindow() {
    const { width: screenWidth, height: screenHeight } = electron_1.screen.getPrimaryDisplay().workAreaSize;
    const { width, height } = getAvatarWindowSize();
    avatarWin = new electron_1.BrowserWindow({
        width,
        height,
        x: screenWidth - width,
        y: screenHeight - height,
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
        },
    });
    avatarWin.setBackgroundColor("#00000000");
    avatarWin.webContents.on("console-message", (event, level, message, line, sourceId) => {
        const logDir = getLogDirectory();
        if (!fs.existsSync(logDir))
            fs.mkdirSync(logDir, { recursive: true });
        fs.appendFileSync(path.join(logDir, "renderer_error.log"), `${new Date().toISOString()} | AVATAR | [Level ${level}] ${message} (at ${sourceId}:${line})\n`);
    });
    avatarWin.loadFile(path.join(__dirname, "..", "renderer", "avatar", "avatar.html"));
    avatarWin.on("closed", () => {
        avatarWin = null;
        chatWin = null;
    });
    return avatarWin;
}
function toggleChat() {
    if (!avatarWin)
        return;
    if (avatarWin.isVisible()) {
        avatarWin.hide();
    }
    else {
        avatarWin.show();
        avatarWin.focus();
    }
}
function setupCrossWindowIpc() {
    electron_1.ipcMain.on("avatar:click", () => avatarWin?.show());
    electron_1.ipcMain.on("avatar:hide", () => avatarWin?.hide());
    electron_1.ipcMain.on("window:set-ignore-mouse-events", (event, ignore, options) => {
        const win = electron_1.BrowserWindow.fromWebContents(event.sender);
        if (win) {
            win.setIgnoreMouseEvents(ignore, options);
        }
    });
    electron_1.ipcMain.on("avatar:emotion", (_e, emotion) => {
        avatarWin?.webContents.send("set:emotion", emotion);
    });
    electron_1.ipcMain.on("tts:speaking", (_e, active) => {
        avatarWin?.webContents.send("set:lipsync", active);
    });
    electron_1.ipcMain.handle("python:status", () => ({ ready: pythonReady }));
    electron_1.ipcMain.handle("pet:get-bounds", () => {
        if (!avatarWin)
            return null;
        const [x, y] = avatarWin.getPosition();
        const [width, height] = avatarWin.getSize();
        const display = electron_1.screen.getDisplayMatching({ x, y, width, height });
        return { x, y, width, height, workArea: display.workArea };
    });
    electron_1.ipcMain.handle("pet:move-to", (_e, point) => {
        if (!avatarWin || !point)
            return null;
        const [width, height] = avatarWin.getSize();
        const targetX = Math.round(point.x);
        const targetY = Math.round(point.y);
        const display = electron_1.screen.getDisplayNearestPoint({ x: targetX, y: targetY });
        const { x, y, width: sw, height: sh } = display.bounds;
        const minVisible = 80;
        const nextX = Math.max(x - width + minVisible, Math.min(x + sw - minVisible, targetX));
        const nextY = Math.max(y - height + minVisible, Math.min(y + sh - minVisible, targetY));
        avatarWin.setPosition(nextX, nextY, false);
        return { x: nextX, y: nextY, width, height, workArea: display.workArea };
    });
    electron_1.ipcMain.handle("pet:set-size", (_e, scale) => {
        if (!avatarWin)
            return null;
        const newW = Math.round(AVATAR_WINDOW_WIDTH * scale);
        const newH = Math.round(AVATAR_WINDOW_HEIGHT * scale);
        const [curX, curY] = avatarWin.getPosition();
        const display = electron_1.screen.getDisplayNearestPoint({ x: curX, y: curY });
        const { x: sx, y: sy, width: sw, height: sh } = display.workArea;
        const nextX = Math.max(sx, Math.min(curX, sx + sw - newW));
        const nextY = Math.max(sy, Math.min(curY + (avatarWin.getSize()[1] - newH), sy + sh - newH));
        const wasResizable = avatarWin.isResizable();
        avatarWin.setResizable(true);
        avatarWin.setSize(newW, newH, true);
        avatarWin.setPosition(nextX, nextY, true);
        avatarWin.setResizable(wasResizable);
        return { width: newW, height: newH, scale };
    });
    electron_1.ipcMain.on("window:open-coding", (_e, folderPath) => {
        createCodingWindow(folderPath);
    });
    electron_1.ipcMain.handle("dialog:select-folder", async (event) => {
        const win = electron_1.BrowserWindow.fromWebContents(event.sender) || codingWin || avatarWin;
        if (!win)
            return null;
        const result = await electron_1.dialog.showOpenDialog(win, {
            properties: ["openDirectory"]
        });
        if (result.canceled || result.filePaths.length === 0) {
            return null;
        }
        return result.filePaths[0];
    });
}
function createSettingsWindow() {
    if (settingsWin) {
        settingsWin.focus();
        return;
    }
    settingsWin = new electron_1.BrowserWindow({
        width: 600,
        height: 520,
        title: "AI Companion Settings",
        resizable: true,
        icon: path.join(electron_1.app.getAppPath(), "assets", "icons", "icon.png"),
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });
    settingsWin.webContents.on("console-message", (event, level, message, line, sourceId) => {
        const logDir = getLogDirectory();
        if (!fs.existsSync(logDir))
            fs.mkdirSync(logDir, { recursive: true });
        fs.appendFileSync(path.join(logDir, "renderer_error.log"), `${new Date().toISOString()} | SETTINGS | [Level ${level}] ${message} (at ${sourceId}:${line})\n`);
    });
    settingsWin.loadFile(path.join(__dirname, "..", "renderer", "settings", "settings.html"));
    settingsWin.on("closed", () => {
        settingsWin = null;
    });
}
function createCodingWindow(folderPath = null) {
    if (codingWin) {
        codingWin.focus();
        if (folderPath) {
            codingWin.webContents.send("workspace:set-folder", folderPath);
        }
        return;
    }
    const win = new electron_1.BrowserWindow({
        width: 1100,
        height: 750,
        title: "DeskAgent Coding Console",
        resizable: true,
        icon: path.join(electron_1.app.getAppPath(), "assets", "icons", "icon.png"),
        webPreferences: {
            preload: path.join(__dirname, "preload.js"),
            contextIsolation: true,
            nodeIntegration: false,
        },
    });
    codingWin = win;
    win.webContents.on("console-message", (event, level, message, line, sourceId) => {
        const logDir = getLogDirectory();
        if (!fs.existsSync(logDir))
            fs.mkdirSync(logDir, { recursive: true });
        fs.appendFileSync(path.join(logDir, "renderer_error.log"), `${new Date().toISOString()} | CODING | [Level ${level}] ${message} (at ${sourceId}:${line})\n`);
    });
    win.loadFile(path.join(__dirname, "..", "renderer", "chat", "coding.html"));
    win.webContents.on("did-finish-load", () => {
        if (folderPath) {
            win.webContents.send("workspace:set-folder", folderPath);
        }
    });
    win.on("closed", () => {
        codingWin = null;
    });
}
electron_1.app.whenReady().then(() => {
    electron_1.nativeTheme.themeSource = "dark";
    electron_1.session.defaultSession.setPermissionRequestHandler((webContents, permission, callback) => {
        if (permission === "media")
            return callback(true);
        callback(false);
    });
    (0, websocket_server_1.startWebSocketServer)(9001);
    startPython();
    createAvatarWindow();
    setupCrossWindowIpc();
    (0, ai_ipc_1.registerAiIpc)(electron_1.ipcMain, avatarWin);
    (0, avatar_ipc_1.registerAvatarIpc)(electron_1.ipcMain, avatarWin);
    (0, system_ipc_1.registerSystemIpc)(electron_1.ipcMain);
    (0, voice_ipc_1.registerVoiceIpc)(electron_1.ipcMain, avatarWin);
    (0, tray_1.createTray)({
        toggleChat,
        showAvatar: () => avatarWin?.show(),
        openSettings: createSettingsWindow,
        openCoding: () => createCodingWindow(),
        quit: () => electron_1.app.quit(),
    });
    electron_1.globalShortcut.register("CommandOrControl+Shift+Space", toggleChat);
    electron_1.globalShortcut.register("CommandOrControl+Shift+S", () => {
        chatWin?.webContents.send("trigger:screenshot");
    });
    electron_1.globalShortcut.register("CommandOrControl+Shift+H", () => {
        avatarWin?.webContents.send("toggle:console");
    });
    electron_1.globalShortcut.register("CommandOrControl+Shift+I", () => {
        avatarWin?.webContents.openDevTools({ mode: "detach" });
        settingsWin?.webContents.openDevTools({ mode: "detach" });
    });
});
electron_1.app.on("before-quit", () => {
    electron_1.globalShortcut.unregisterAll();
    if (pythonProc) {
        pythonProc.kill();
        pythonProc = null;
    }
});
electron_1.app.on("window-all-closed", () => {
    if (process.platform !== "darwin")
        electron_1.app.quit();
});
