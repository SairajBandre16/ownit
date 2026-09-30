"use strict";
// Auto-update via GitHub Releases: a pushed tag builds installers in CI and
// publishes them as a release; every running app checks this on launch and
// installs silently, so "push an update, everyone gets it" also covers the
// app shell itself, not just the backend image.

const { autoUpdater } = require("electron-updater");
const log = require("electron-log");

autoUpdater.logger = log;
autoUpdater.autoDownload = true;
autoUpdater.autoInstallOnAppQuit = true;

function init() {
  autoUpdater.checkForUpdatesAndNotify().catch((e) => log.warn("update check failed", e));
}

module.exports = { init, autoUpdater };
