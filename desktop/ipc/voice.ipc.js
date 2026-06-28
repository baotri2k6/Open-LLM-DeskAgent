"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerVoiceIpc = registerVoiceIpc;
const electron_1 = require("electron");
let voiceActive = false;
function getAvatarWindow() {
    return electron_1.BrowserWindow.getAllWindows().find(win => {
        try {
            return win.webContents.getURL().includes("avatar.html");
        }
        catch {
            return false;
        }
    });
}
function registerVoiceIpc(ipcMain, avatarWin) {
    ipcMain.handle("voice:start", async () => {
        voiceActive = true;
        const win = getAvatarWindow();
        win?.webContents.send("voice:start-recording");
        return { active: true };
    });
    ipcMain.handle("voice:stop", async () => {
        voiceActive = false;
        const win = getAvatarWindow();
        win?.webContents.send("voice:stop-recording");
        return { active: false };
    });
    ipcMain.handle("voice:status", async () => ({ active: voiceActive }));
}
