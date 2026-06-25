const os = require('os');

function registerSystemIpc(ipcMain) {
  ipcMain.handle('system:info', async () => ({
    platform:    os.platform(),
    release:     os.release(),
    arch:        os.arch(),
    hostname:    os.hostname(),
    memoryTotal: os.totalmem(),
    memoryFree:  os.freemem(),
    cpus:        os.cpus().length,
  }));
}

module.exports = { registerSystemIpc };