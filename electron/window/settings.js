const { BrowserWindow } = require('electron');
const path = require('path');
let settingsWin = null;

function createSettingsWindow(parent) {
  if (settingsWin) { settingsWin.focus(); return settingsWin; }
  settingsWin = new BrowserWindow({
    width: 640, height: 520,
    parent, modal: false,
    title: 'AI Companion Settings',
    resizable: false,
    webPreferences: {
      preload: path.join(__dirname, '..', 'preload.js'),
      contextIsolation: true,
    }
  });
  settingsWin.loadFile(path.join(__dirname, '..', '..', 'renderer', 'settings.html'));
  settingsWin.on('closed', () => { settingsWin = null; });
  return settingsWin;
}

module.exports = { createSettingsWindow };