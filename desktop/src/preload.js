"use strict";
const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("ownit", {
  onStatus: (cb) => ipcRenderer.on("status", (_e, msg) => cb(msg)),
  onError: (cb) => ipcRenderer.on("boot-error", (_e, html) => cb(html)),
});
