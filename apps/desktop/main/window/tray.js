const { Tray, Menu, app, nativeImage } = require("electron");
const path = require("path");
let tray = null;

function createTray({ toggleChat, showAvatar, openSettings, quit }) {
  const iconPath = path.join(app.getAppPath(), "assets", "icons", "icon.png");
  let icon;
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

module.exports = { createTray };
