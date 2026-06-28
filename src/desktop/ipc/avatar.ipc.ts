import { BrowserWindow, IpcMain } from "electron";

interface AvatarState {
  expression: string;
  motion: string;
  lipsync: boolean;
}

let state: AvatarState = { expression: "normal", motion: "idle", lipsync: false };

function getAvatarWindow(): BrowserWindow | undefined {
  return BrowserWindow.getAllWindows().find(win => {
    try {
      return win.webContents.getURL().includes("avatar.html");
    } catch {
      return false;
    }
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
}
