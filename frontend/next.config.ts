import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  // Standalone server bundle: the desktop app runs this with Electron's own
  // Node, so end users never need Node or npm installed.
  output: "standalone",
};

export default nextConfig;
