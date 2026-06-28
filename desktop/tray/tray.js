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
function createTray({ toggleChat, showAvatar, openSettings, openCoding, quit }) {
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
    tray.setContextMenu(electron_1.Menu.buildFromTemplate([
        { label: "Show / Hide Chat", click: toggleChat },
        { label: "Show Avatar", click: showAvatar },
        { label: "Coding Console", click: openCoding },
        { label: "Option", click: openSettings },
        { type: "separator" },
        { label: "Quit", click: quit },
    ]));
    tray.on("click", toggleChat);
    return tray;
}
