const { BrowserWindow } = require('electron');
let voiceActive = false;

function getAvatarWindow() {
  return BrowserWindow.getAllWindows().find(win => {
    try {
      return win.webContents.getURL().includes('avatar.html');
    } catch {
      return false;
    }
  });
}

function registerVoiceIpc(ipcMain) {
  ipcMain.handle('voice:start', async () => {
    voiceActive = true;
    const win = getAvatarWindow();
    win?.webContents.send('voice:start-recording');
    return { active: true };
  });

  ipcMain.handle('voice:stop', async () => {
    voiceActive = false;
    const win = getAvatarWindow();
    win?.webContents.send('voice:stop-recording');
    return { active: false };
  });

  ipcMain.handle('voice:status', async () => ({ active: voiceActive }));
}

module.exports = { registerVoiceIpc };