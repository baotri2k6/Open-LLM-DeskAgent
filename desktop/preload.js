"use strict";
Object.defineProperty(exports, "__esModule", { value: true });
const electron_1 = require("electron");
electron_1.contextBridge.exposeInMainWorld("companion", {
    chat: (text, imageOrCtx = null, ctx = {}) => {
        if (imageOrCtx && typeof imageOrCtx === "object" && (!imageOrCtx.startsWith || !imageOrCtx.startsWith("data:"))) {
            return electron_1.ipcRenderer.invoke("ai:chat", { text, image: null, context: imageOrCtx });
        }
        return electron_1.ipcRenderer.invoke("ai:chat", { text, image: imageOrCtx, context: ctx });
    },
    health: () => electron_1.ipcRenderer.invoke("ai:health"),
    avatarClick: () => electron_1.ipcRenderer.send("avatar:click"),
    hideAvatar: () => electron_1.ipcRenderer.send("avatar:hide"),
    setEmotion: (emo) => electron_1.ipcRenderer.send("avatar:emotion", emo),
    setLipsync: (active) => electron_1.ipcRenderer.send("tts:speaking", active),
    avatarState: (state) => electron_1.ipcRenderer.invoke("avatar:set-state", state),
    startVoice: () => electron_1.ipcRenderer.invoke("voice:start"),
    stopVoice: () => electron_1.ipcRenderer.invoke("voice:stop"),
    sysInfo: () => electron_1.ipcRenderer.invoke("system:info"),
    pythonStatus: () => electron_1.ipcRenderer.invoke("python:status"),
    petBounds: () => electron_1.ipcRenderer.invoke("pet:get-bounds"),
    petMoveTo: (point) => electron_1.ipcRenderer.invoke("pet:move-to", point),
    petSetSize: (scale) => electron_1.ipcRenderer.invoke("pet:set-size", scale),
    broadcast: (event, data) => electron_1.ipcRenderer.send("ai:broadcast", { event, data }),
    invoke: (ch, data) => electron_1.ipcRenderer.invoke(ch, data),
    setIgnoreMouseEvents: (ignore, options) => electron_1.ipcRenderer.send("window:set-ignore-mouse-events", ignore, options),
    openCoding: (folderPath) => electron_1.ipcRenderer.send("window:open-coding", folderPath),
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
            "workspace:set-folder",
        ];
        if (ALLOWED.includes(channel)) {
            electron_1.ipcRenderer.on(channel, (_e, ...args) => cb(...args));
        }
    },
    off: (channel, cb) => electron_1.ipcRenderer.removeListener(channel, cb),
});
