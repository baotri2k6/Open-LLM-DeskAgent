let voiceActive = false;
let chatWinRef = null;

function registerVoiceIpc(ipcMain, chatWin) {
  chatWinRef = chatWin;

  ipcMain.handle('voice:start', async () => {
    voiceActive = true;
    chatWinRef?.webContents.send('voice:start-recording');
    return { active: true };
  });

  ipcMain.handle('voice:stop', async () => {
    voiceActive = false;
    chatWinRef?.webContents.send('voice:stop-recording');
    return { active: false };
  });

  ipcMain.handle('voice:status', async () => ({ active: voiceActive }));
}

module.exports = { registerVoiceIpc };