#!/usr/bin/env node
// Builds the Next.js frontend as a standalone server and copies it into
// desktop/resources/web, where Electron runs it with its own bundled Node.
// No end user ever needs Node, npm, or a build step.

const { execSync } = require("node:child_process");
const fs = require("node:fs");
const path = require("node:path");

const root = path.resolve(__dirname, "..", "..");
const frontendDir = path.join(root, "frontend");
const desktopDir = path.join(root, "desktop");
const webOut = path.join(desktopDir, "resources", "web");

console.log("[build-web] npm ci in frontend/");
execSync("npm ci", { cwd: frontendDir, stdio: "inherit" });

console.log("[build-web] next build (standalone)");
execSync("npm run build", { cwd: frontendDir, stdio: "inherit" });

console.log("[build-web] copying standalone bundle");
fs.rmSync(webOut, { recursive: true, force: true });
fs.mkdirSync(webOut, { recursive: true });

const standaloneDir = path.join(frontendDir, ".next", "standalone");
copyDir(standaloneDir, webOut);

// Static assets and public files are not part of the standalone output by
// default and must sit next to server.js at .next/static and public/.
copyDir(path.join(frontendDir, ".next", "static"), path.join(webOut, ".next", "static"));
if (fs.existsSync(path.join(frontendDir, "public"))) {
  copyDir(path.join(frontendDir, "public"), path.join(webOut, "public"));
}

console.log("[build-web] done ->", webOut);

function copyDir(src, dest) {
  fs.mkdirSync(dest, { recursive: true });
  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const s = path.join(src, entry.name);
    const d = path.join(dest, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}
