import * as os from "os";
import { IpcMain, dialog, BrowserWindow } from "electron";

export function registerSystemIpc(ipcMain: IpcMain): void {
  ipcMain.handle("system:info", async () => ({
    platform:    os.platform(),
    release:     os.release(),
    arch:        os.arch(),
    hostname:    os.hostname(),
    memoryTotal: os.totalmem(),
    memoryFree:  os.freemem(),
    cpus:        os.cpus().length,
  }));

  ipcMain.handle("system:open-file-dialog", async (event: any, options: any) => {
    const win = BrowserWindow.fromWebContents(event.sender);
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
