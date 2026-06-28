import { contextBridge, ipcRenderer } from "electron";

contextBridge.exposeInMainWorld("companion", {
  chat: (text: string, imageOrCtx: any = null, ctx: any = {}) => {
    if (imageOrCtx && typeof imageOrCtx === "object" && (!imageOrCtx.startsWith || !imageOrCtx.startsWith("data:"))) {
      return ipcRenderer.invoke("ai:chat", { text, image: null, context: imageOrCtx });
    }
    return ipcRenderer.invoke("ai:chat", { text, image: imageOrCtx, context: ctx });
  },
  health: () => ipcRenderer.invoke("ai:health"),
  avatarClick: () => ipcRenderer.send("avatar:click"),
  hideAvatar: () => ipcRenderer.send("avatar:hide"),
  setEmotion: (emo: string) => ipcRenderer.send("avatar:emotion", emo),
  setLipsync: (active: boolean) => ipcRenderer.send("tts:speaking", active),
  avatarState: (state: any) => ipcRenderer.invoke("avatar:set-state", state),
  startVoice: () => ipcRenderer.invoke("voice:start"),
  stopVoice: () => ipcRenderer.invoke("voice:stop"),
  sysInfo: () => ipcRenderer.invoke("system:info"),
  pythonStatus: () => ipcRenderer.invoke("python:status"),
  petBounds: () => ipcRenderer.invoke("pet:get-bounds"),
  petMoveTo: (point: { x: number; y: number }) => ipcRenderer.invoke("pet:move-to", point),
  petSetSize: (scale: number) => ipcRenderer.invoke("pet:set-size", scale),
  broadcast: (event: string, data: any) => ipcRenderer.send("ai:broadcast", { event, data }),
  invoke: (ch: string, data: any) => ipcRenderer.invoke(ch, data),
  setIgnoreMouseEvents: (ignore: boolean, options: any) =>
    ipcRenderer.send("window:set-ignore-mouse-events", ignore, options),
  openCoding: (folderPath: string) => ipcRenderer.send("window:open-coding", folderPath),

  on: (channel: string, cb: (...args: any[]) => void) => {
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
      "workspace:set-folder",
    ];
    if (ALLOWED.includes(channel)) {
      ipcRenderer.on(channel, (_e, ...args) => cb(...args));
    }
  },
  off: (channel: string, cb: (...args: any[]) => void) => ipcRenderer.removeListener(channel, cb),
});
