import { BrowserWindow } from "electron";
import * as path from "path";

export function createOverlayWindow(options: { show?: boolean } = {}): BrowserWindow {
  const win = new BrowserWindow({
    width: 360,
    height: 520,
    show: options.show ?? true,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      preload: path.join(__dirname, "..", "preload.js"),
      contextIsolation: true
    }
  });
  win.loadFile(path.join(__dirname, "..", "..", "renderer", "overlay", "index.html"));
  return win;
}
