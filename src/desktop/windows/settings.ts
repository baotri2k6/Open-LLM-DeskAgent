import { BrowserWindow } from "electron";
import * as path from "path";

let settingsWin: BrowserWindow | null = null;

export function createSettingsWindow(parent?: BrowserWindow): BrowserWindow {
  if (settingsWin) {
    settingsWin.focus();
    return settingsWin;
  }
  settingsWin = new BrowserWindow({
    width: 640,
    height: 520,
    parent,
    modal: false,
    title: "AI Companion Settings",
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, "..", "preload.js"),
      contextIsolation: true,
    }
  });
  settingsWin.loadFile(path.join(__dirname, "..", "..", "renderer", "settings", "settings.html"));
  settingsWin.on("closed", () => {
    settingsWin = null;
  });
  return settingsWin;
}
