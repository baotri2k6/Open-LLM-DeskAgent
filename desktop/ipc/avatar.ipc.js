"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
exports.registerAvatarIpc = registerAvatarIpc;
const electron_1 = require("electron");
let state = { expression: "normal", motion: "idle", lipsync: false };
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
function registerAvatarIpc(ipcMain, avatarWin) {
    ipcMain.handle("avatar:set-state", async (_e, next) => {
        state = { ...state, ...next };
        const win = getAvatarWindow();
        win?.webContents.send("set:emotion", state.expression || "normal");
        return state;
    });
    ipcMain.handle("avatar:get-state", async () => state);
}
