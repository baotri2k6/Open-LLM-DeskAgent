const { BrowserWindow } = require('electron');
const path = require('path');

function createOverlayWindow(options = {}) {
  const win = new BrowserWindow({
    width: 360,
    height: 520,
    show: options.show ?? true,
    transparent: true,
    frame: false,
    alwaysOnTop: true,
    skipTaskbar: true,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true
    }
  });
  win.loadFile(path.join(__dirname, '..', '..', 'renderer', 'index.html'));
  return win;
}

module.exports = { createOverlayWindow };
