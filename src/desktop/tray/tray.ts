import { Tray, Menu, app, nativeImage } from "electron";
import * as path from "path";

let tray: Tray | null = null;

interface TrayCallbacks {
  toggleChat: () => void;
  showAvatar: () => void;
  openSettings: () => void;
  openCoding: () => void;
  quit: () => void;
}

export function createTray({ toggleChat, showAvatar, openSettings, openCoding, quit }: TrayCallbacks): Tray {
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
  tray.setContextMenu(
    Menu.buildFromTemplate([
      { label: "Show / Hide Chat", click: toggleChat },
      { label: "Show Avatar", click: showAvatar },
      { label: "Coding Console", click: openCoding },
      { label: "Option", click: openSettings },
      { type: "separator" },
      { label: "Quit", click: quit },
    ]),
  );
  tray.on("click", toggleChat);
  return tray;
}
