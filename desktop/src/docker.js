"use strict";
// Drives the local backend stack through Docker Compose. The app never talks
// to the containers except over HTTP (127.0.0.1:8000), so this module only
// needs to start them, watch for readiness, and stop them on quit.

const { spawn } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");
const http = require("node:http");

const PROJECT = "ownit";

// Windows only applies a new PATH entry to processes started after it
// propagates (a fresh logon, usually), so an app launched right after
// installing Docker Desktop can fail to find "docker" even though it is
// installed and running. Fall back to the well-known install locations
// instead of trusting PATH alone.
function findDockerOnWindows() {
  const candidates = [
    path.join(process.env.ProgramFiles || "C:\\Program Files", "Docker", "Docker", "resources", "bin", "docker.exe"),
    path.join(process.env.LOCALAPPDATA || "", "Programs", "DockerDesktop", "resources", "bin", "docker.exe"),
  ];
  return candidates.find((p) => p && fs.existsSync(p)) || null;
}

let dockerCmd = null;

/** Resolves the docker executable once: PATH first, then known install locations. */
async function resolveDocker() {
  if (dockerCmd) return dockerCmd;
  try {
    await run("docker", ["info"]);
    dockerCmd = "docker";
    return dockerCmd;
  } catch {
    if (process.platform === "win32") {
      const found = findDockerOnWindows();
      if (found) {
        dockerCmd = found;
        return dockerCmd;
      }
    }
    return null;
  }
}

function run(cmd, args) {
  return new Promise((resolve, reject) => {
    const child = spawn(cmd, args, { windowsHide: true });
    let out = "";
    let err = "";
    child.stdout.on("data", (d) => (out += d.toString()));
    child.stderr.on("data", (d) => (err += d.toString()));
    child.on("error", reject);
    child.on("close", (code) => {
      if (code === 0) resolve(out);
      else reject(new Error(err || out || `${cmd} exited with code ${code}`));
    });
  });
}

/** True if the Docker daemon is installed and reachable. */
async function isDockerAvailable() {
  return (await resolveDocker()) !== null;
}

/**
 * Pulls the latest images and starts the stack. Pulling every launch is how
 * a backend update reaches every installed copy of the app without a new
 * app release: push a new image, users get it next time they open OwnIt.
 */
async function startStack(composeFile, onLog) {
  const cmd = await resolveDocker();
  if (!cmd) throw new Error("Docker was available at check time but is now unreachable.");

  onLog?.("Checking for backend updates...");
  try {
    await run(cmd, ["compose", "-p", PROJECT, "-f", composeFile, "pull"]);
  } catch (e) {
    // Offline or rate-limited: fall back to whatever image is already local.
    onLog?.("Could not check for updates, using the last downloaded backend.");
  }
  onLog?.("Starting the backend...");
  await run(cmd, ["compose", "-p", PROJECT, "-f", composeFile, "up", "-d"]);
}

/** Stops (but does not remove) the stack so containers restart fast next time. */
async function stopStack(composeFile) {
  try {
    const cmd = await resolveDocker();
    if (!cmd) return;
    await run(cmd, ["compose", "-p", PROJECT, "-f", composeFile, "stop"]);
  } catch {
    // Best effort: the app is quitting regardless.
  }
}

function pingHealth(url) {
  return new Promise((resolve) => {
    const req = http.get(url, { timeout: 2000 }, (res) => {
      res.resume();
      resolve(res.statusCode === 200);
    });
    req.on("error", () => resolve(false));
    req.on("timeout", () => {
      req.destroy();
      resolve(false);
    });
  });
}

/** Polls /health until the backend answers, or throws after timeoutMs. */
async function waitForHealth(url, timeoutMs, onLog) {
  const start = Date.now();
  let attempt = 0;
  while (Date.now() - start < timeoutMs) {
    attempt += 1;
    if (await pingHealth(url)) return;
    if (attempt % 5 === 0) onLog?.("Still warming up the backend...");
    await new Promise((r) => setTimeout(r, 1000));
  }
  throw new Error("Backend did not become healthy in time.");
}

module.exports = { isDockerAvailable, startStack, stopStack, waitForHealth };
