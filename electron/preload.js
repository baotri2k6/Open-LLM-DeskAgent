const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("companion", {
  chat: (text, imageOrCtx = null, ctx = {}) => {
    if (imageOrCtx && typeof imageOrCtx === "object" && (!imageOrCtx.startsWith || !imageOrCtx.startsWith("data:"))) {
      return ipcRenderer.invoke("ai:chat", { text, image: null, context: imageOrCtx });
    }
    return ipcRenderer.invoke("ai:chat", { text, image: imageOrCtx, context: ctx });
  },
  health: () => ipcRenderer.invoke("ai:health"),
  avatarClick: () => ipcRenderer.send("avatar:click"),
  hideAvatar: () => ipcRenderer.send("avatar:hide"),
  setEmotion: (emo) => ipcRenderer.send("avatar:emotion", emo),
  setLipsync: (active) => ipcRenderer.send("tts:speaking", active),
  avatarState: (state) => ipcRenderer.invoke("avatar:set-state", state),
  startVoice: () => ipcRenderer.invoke("voice:start"),
  stopVoice: () => ipcRenderer.invoke("voice:stop"),
  sysInfo: () => ipcRenderer.invoke("system:info"),
  pythonStatus: () => ipcRenderer.invoke("python:status"),
  petBounds: () => ipcRenderer.invoke("pet:get-bounds"),
  petMoveTo: (point) => ipcRenderer.invoke("pet:move-to", point),
  petSetSize: (scale) => ipcRenderer.invoke("pet:set-size", scale),
  broadcast: (event, data) => ipcRenderer.send("ai:broadcast", { event, data }),
  invoke: (ch, data) => ipcRenderer.invoke(ch, data),
  setIgnoreMouseEvents: (ignore, options) =>
    ipcRenderer.send("window:set-ignore-mouse-events", ignore, options),

  on: (channel, cb) => {
    const ALLOWED = [
      "set:emotion",
      "set:lipsync",
      "python:ready",
      "chat:chunk",
      "chat:thought-chunk",
      "chat:done",
      "trigger:screenshot",
      "stt:result",
      "tts:audio",
      "tts:done",
      "voice:start-recording",
      "voice:stop-recording",
      "doc:loaded",
      "toggle:console",
      "chat:command",
      "config:updated",
      "chat:request-approval",
    ];
    if (ALLOWED.includes(channel)) {
      ipcRenderer.on(channel, (_e, ...args) => cb(...args));
    }
  },
  off: (channel, cb) => ipcRenderer.removeListener(channel, cb),
});
