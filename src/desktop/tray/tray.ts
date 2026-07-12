import { Tray, Menu, app, nativeImage, dialog } from "electron";
import * as path from "path";

let tray: Tray | null = null;

interface TrayCallbacks {
  toggleChat: () => void;
  showAvatar: () => void;
  openSettings: () => void;
  quit: () => void;
  setSize: (scale: number) => void;
  alignTo: (position: "bottom-right" | "bottom-left" | "top-right" | "top-left" | "center") => void;
  openDevTools: () => void;
  openWidgets?: () => void;
  openInlay?: () => void;
  openCaption?: () => void;
  toggleCaptionOverlay?: (enabled: boolean) => void;
  troubleshootBeatSync?: () => void;
}

export function createTray({
  toggleChat,
  showAvatar,
  openSettings,
  quit,
  setSize,
  alignTo,
  openDevTools,
  openWidgets = () => {},
  openInlay = () => {},
  openCaption = () => {},
  toggleCaptionOverlay = () => {},
  troubleshootBeatSync = () => {}
}: TrayCallbacks): Tray {
  const iconPath = path.join(app.getAppPath(), "assets", "icons", "icon.png");
  let icon: any;
  try {
    icon = nativeImage
      .createFromPath(iconPath)
      .resize({ width: 16, height: 16 });
  } catch {
    icon = nativeImage.createEmpty();
  }
  tray = new Tray(icon);
  tray.setToolTip("AI Companion Desktop 2D");

  const contextMenu = Menu.buildFromTemplate([
    { label: "Show", click: showAvatar },
    { type: "separator" },
    {
      label: "Adjust sizes",
      submenu: [
        { label: "0.5x", click: () => setSize(0.5) },
        { label: "0.75x", click: () => setSize(0.75) },
        { label: "1.0x (Default)", click: () => setSize(1.0) },
        { label: "1.25x", click: () => setSize(1.25) },
        { label: "1.5x", click: () => setSize(1.5) },
        { label: "2.0x", click: () => setSize(2.0) }
      ]
    },
    {
      label: "Align to",
      submenu: [
        { label: "Bottom Right", click: () => alignTo("bottom-right") },
        { label: "Bottom Left", click: () => alignTo("bottom-left") },
        { label: "Top Right", click: () => alignTo("top-right") },
        { label: "Top Left", click: () => alignTo("top-left") },
        { label: "Center", click: () => alignTo("center") }
      ]
    },
    { type: "separator" },
    { label: "Settings...", click: openSettings },
    {
      label: "About...",
      click: () => {
        dialog.showMessageBox({
          type: "info",
          title: "About DeskAgent",
          message: "DeskAgent AI Companion",
          detail: "An advanced desktop AI assistant driven by Live2D and LLM cognition systems.\n\nVersion: 0.2.0\nCreated by Google Deepmind team.",
          buttons: ["OK"]
        });
      }
    },
    { type: "separator" },
    { label: "Open Inlay...", click: openInlay },
    { label: "Open Widgets...", click: openWidgets },
    { label: "Open Caption...", click: openCaption },
    {
      label: "Caption Overlay",
      submenu: [
        { label: "Enabled", type: "radio", checked: true, click: () => toggleCaptionOverlay(true) },
        { label: "Disabled", type: "radio", checked: false, click: () => toggleCaptionOverlay(false) }
      ]
    },
    { type: "separator" },
    { label: "DevTools", click: openDevTools },
    { label: "Troubleshoot BeatSync...", click: troubleshootBeatSync },
    { type: "separator" },
    { label: "Quit", click: quit }
  ]);

  tray.setContextMenu(contextMenu);
  tray.on("double-click", toggleChat);
  return tray;
}
