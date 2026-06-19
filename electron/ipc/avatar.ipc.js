let avatarWinRef = null;
let state = { expression: 'normal', motion: 'idle', lipsync: false };

function registerAvatarIpc(ipcMain, avatarWin) {
  avatarWinRef = avatarWin;
  ipcMain.handle('avatar:set-state', async (_e, next) => {
    state = { ...state, ...next };
    avatarWinRef?.webContents.send('set:emotion', state.expression || 'normal');
    return state;
  });
  ipcMain.handle('avatar:get-state', async () => state);
}

module.exports = { registerAvatarIpc };