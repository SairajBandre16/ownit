"use strict";

const { app, BrowserWindow, shell, Menu } = require("electron");
const path = require("node:path");
const docker = require("./docker");
const webServer = require("./web-server");

const isDev = !app.isPackaged;
const composeFile = isDev
  ? path.join(__dirname, "..", "docker-compose.desktop.yml")
  : path.join(process.resourcesPath, "docker-compose.desktop.yml");
const webDir = isDev
  ? path.join(__dirname, "..", "resources", "web")
  : path.join(process.resourcesPath, "web");

const BACKEND_HEALTH_URL = "http://127.0.0.1:8000/health";
const BACKEND_BOOT_TIMEOUT_MS = 120000;
const DOCKER_INSTALL_URL = "https://www.docker.com/products/docker-desktop/";

let loadingWindow = null;
let mainWindow = null;

function createLoadingWindow() {
  const win = new BrowserWindow({
    width: 420,
    height: 260,
    resizable: false,
    frame: true,
    title: "OwnIt",
    webPreferences: { preload: path.join(__dirname, "preload.js") },
  });
  win.setMenuBarVisibility(false);
  win.loadFile(path.join(__dirname, "loading.html"));
  return win;
}

function status(msg) {
  console.log("[boot]", msg);
  loadingWindow?.webContents.send("status", msg);
}

function bootError(html) {
  loadingWindow?.webContents.send("boot-error", html);
}

async function createMainWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 900,
    show: false,
    title: "OwnIt",
  });
  mainWindow.setMenuBarVisibility(false);
  mainWindow.once("ready-to-show", () => {
    loadingWindow?.close();
    loadingWindow = null;
    mainWindow.show();
  });
  // Links to the outside web (e.g. a "learn more") open in the real browser.
  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url);
    return { action: "deny" };
  });
  await mainWindow.loadURL(webServer.url);
}

async function boot() {
  loadingWindow = createLoadingWindow();

  status("Checking Docker...");
  const hasDocker = await docker.isDockerAvailable();
  if (!hasDocker) {
    bootError(
      `OwnIt needs <b>Docker Desktop</b> to run its backend locally.<br/>` +
        `A download page has been opened for you. Install it, start it, then reopen OwnIt.`
    );
    shell.openExternal(DOCKER_INSTALL_URL);
    return;
  }

  try {
    await docker.startStack(composeFile, status);
    status("Waiting for the backend to be ready...");
    await docker.waitForHealth(BACKEND_HEALTH_URL, BACKEND_BOOT_TIMEOUT_MS, status);

    status("Starting the app...");
    await webServer.start(webDir);

    await createMainWindow();

    const updater = require("./updater");
    updater.init();
  } catch (err) {
    console.error(err);
    bootError(`Something went wrong starting OwnIt:<br/><code>${escapeHtml(String(err.message || err))}</code>`);
  }
}

function escapeHtml(s) {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}

app.whenReady().then(() => {
  Menu.setApplicationMenu(null);
  boot();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) boot();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") app.quit();
});

app.on("before-quit", () => {
  webServer.stop();
});

let stopping = false;
app.on("will-quit", async (e) => {
  if (stopping) return;
  stopping = true;
  e.preventDefault();
  await docker.stopStack(composeFile).catch(() => {});
  app.exit(0);
});
