"use strict";
// Runs the bundled Next.js standalone server with Electron's own Node, so
// the desktop app needs no separately installed Node or npm.

const { fork } = require("node:child_process");
const path = require("node:path");
const http = require("node:http");

const PORT = 4173;
const HOST = "127.0.0.1";

let child = null;

function start(webDir) {
  return new Promise((resolve, reject) => {
    const serverJs = path.join(webDir, "server.js");
    child = fork(serverJs, [], {
      cwd: webDir,
      env: { ...process.env, PORT: String(PORT), HOSTNAME: HOST, NODE_ENV: "production" },
      stdio: ["ignore", "pipe", "pipe", "ipc"],
    });
    child.stdout?.on("data", (d) => process.stdout.write(`[web] ${d}`));
    child.stderr?.on("data", (d) => process.stderr.write(`[web] ${d}`));
    child.on("error", reject);
    child.once("exit", (code) => {
      if (code && code !== 0) reject(new Error(`web server exited with code ${code}`));
    });

    waitForPort(`http://${HOST}:${PORT}`, 30000).then(resolve, reject);
  });
}

function waitForPort(url, timeoutMs) {
  const start = Date.now();
  return new Promise((resolve, reject) => {
    const attempt = () => {
      const req = http.get(url, (res) => {
        res.resume();
        resolve(url);
      });
      req.on("error", () => {
        if (Date.now() - start > timeoutMs) reject(new Error("web server did not start in time"));
        else setTimeout(attempt, 300);
      });
    };
    attempt();
  });
}

function stop() {
  if (child && !child.killed) child.kill();
  child = null;
}

module.exports = { start, stop, url: `http://${HOST}:${PORT}` };
