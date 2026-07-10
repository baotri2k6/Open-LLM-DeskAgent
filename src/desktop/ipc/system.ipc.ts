import * as os from "os";
import { IpcMain } from "electron";

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
}
