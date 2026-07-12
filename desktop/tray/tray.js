"use strict";
var __createBinding = (this && this.__createBinding) || (Object.create ? (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    var desc = Object.getOwnPropertyDescriptor(m, k);
    if (!desc || ("get" in desc ? !m.__esModule : desc.writable || desc.configurable)) {
      desc = { enumerable: true, get: function() { return m[k]; } };
    }
    Object.defineProperty(o, k2, desc);
}) : (function(o, m, k, k2) {
    if (k2 === undefined) k2 = k;
    o[k2] = m[k];
}));
var __setModuleDefault = (this && this.__setModuleDefault) || (Object.create ? (function(o, v) {
    Object.defineProperty(o, "default", { enumerable: true, value: v });
}) : function(o, v) {
    o["default"] = v;
});
var __importStar = (this && this.__importStar) || (function () {
    var ownKeys = function(o) {
        ownKeys = Object.getOwnPropertyNames || function (o) {
            var ar = [];
            for (var k in o) if (Object.prototype.hasOwnProperty.call(o, k)) ar[ar.length] = k;
            return ar;
        };
        return ownKeys(o);
    };
    return function (mod) {
        if (mod && mod.__esModule) return mod;
        var result = {};
        if (mod != null) for (var k = ownKeys(mod), i = 0; i < k.length; i++) if (k[i] !== "default") __createBinding(result, mod, k[i]);
        __setModuleDefault(result, mod);
        return result;
    };
})();
Object.defineProperty(exports, "__esModule", { value: true });
exports.createTray = createTray;
const electron_1 = require("electron");
const path = __importStar(require("path"));
let tray = null;
function createTray({ toggleChat, showAvatar, openSettings, quit, setSize, alignTo, openDevTools, openWidgets = () => { }, openInlay = () => { }, openCaption = () => { }, toggleCaptionOverlay = () => { }, troubleshootBeatSync = () => { } }) {
    const iconPath = path.join(electron_1.app.getAppPath(), "assets", "icons", "icon.png");
    let icon;
    try {
        icon = electron_1.nativeImage
            .createFromPath(iconPath)
            .resize({ width: 16, height: 16 });
    }
    catch {
        icon = electron_1.nativeImage.createEmpty();
    }
    tray = new electron_1.Tray(icon);
    tray.setToolTip("AI Companion Desktop 2D");
    const contextMenu = electron_1.Menu.buildFromTemplate([
        { label: "Show", click: showAvatar },
        { type: "separator" },
        {
            label: "Adjust sizes",
            submenu: [
                { label: "0.5x", click: () => setSize(0.5) },
                { label: "0.75x", click: () => setSize(0.75) },
                { label: "1.0x (Default)", click: () => setSize(1.0) },
                { label: "1.25x", click: () => setSize(1.25) },
                { label: "1.5x", click: () => setSize(1.5) },
                { label: "2.0x", click: () => setSize(2.0) }
            ]
        },
        {
            label: "Align to",
            submenu: [
                { label: "Bottom Right", click: () => alignTo("bottom-right") },
                { label: "Bottom Left", click: () => alignTo("bottom-left") },
                { label: "Top Right", click: () => alignTo("top-right") },
                { label: "Top Left", click: () => alignTo("top-left") },
                { label: "Center", click: () => alignTo("center") }
            ]
        },
        { type: "separator" },
        { label: "Settings...", click: openSettings },
        {
            label: "About...",
            click: () => {
                electron_1.dialog.showMessageBox({
                    type: "info",
                    title: "About DeskAgent",
                    message: "DeskAgent AI Companion",
                    detail: "An advanced desktop AI assistant driven by Live2D and LLM cognition systems.\n\nVersion: 0.2.0\nCreated by Google Deepmind team.",
                    buttons: ["OK"]
                });
            }
        },
        { type: "separator" },
        { label: "Open Inlay...", click: openInlay },
        { label: "Open Widgets...", click: openWidgets },
        { label: "Open Caption...", click: openCaption },
        {
            label: "Caption Overlay",
            submenu: [
                { label: "Enabled", type: "radio", checked: true, click: () => toggleCaptionOverlay(true) },
                { label: "Disabled", type: "radio", checked: false, click: () => toggleCaptionOverlay(false) }
            ]
        },
        { type: "separator" },
        { label: "DevTools", click: openDevTools },
        { label: "Troubleshoot BeatSync...", click: troubleshootBeatSync },
        { type: "separator" },
        { label: "Quit", click: quit }
    ]);
    tray.setContextMenu(contextMenu);
    tray.on("double-click", toggleChat);
    return tray;
}
