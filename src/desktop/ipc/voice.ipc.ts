import { BrowserWindow, IpcMain } from "electron";

let voiceActive = false;

function getAvatarWindow(): BrowserWindow | undefined {
  return BrowserWindow.getAllWindows().find(win => {
    try {
      return win.webContents.getURL().includes("avatar.html");
    } catch {
      return false;
    }
  });
}

export function registerVoiceIpc(ipcMain: IpcMain, avatarWin: any): void {
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
