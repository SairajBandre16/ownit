import { loadFont as loadMono } from "@remotion/google-fonts/IBMPlexMono";
import { loadFont as loadSerif } from "@remotion/google-fonts/Newsreader";
import { loadFont as loadSans } from "@remotion/google-fonts/SchibstedGrotesk";

// The app's own type system: Newsreader for display and document text, Schibsted Grotesk for UI,
// IBM Plex Mono for numbers, scores and units.
const serif = loadSerif("normal", { weights: ["400", "500"], subsets: ["latin"] });
loadSerif("italic", { weights: ["400", "500"], subsets: ["latin"] });
const sans = loadSans("normal", { weights: ["400", "500", "600"], subsets: ["latin"] });
const mono = loadMono("normal", { weights: ["400", "500"], subsets: ["latin"] });

export const F = {
  serif: serif.fontFamily,
  sans: sans.fontFamily,
  mono: mono.fontFamily,
};

// Design tokens from frontend/app/globals.css ("a modern engineering notebook").
export const C = {
  paper: "#F7F5F0",
  ink: "#1A1A1A",
  muted: "#6B6B6B",
  rule: "#E4E0D8",
  card: "#FBFAF7",
  signal: "#FF5A1F",
  signalInk: "#C2410C",
  dark: "#111214",
  darkCard: "#17181B",
  darkText: "#EDEBE6",
  darkMuted: "#A3A09A",
  darkRule: "#2A2B2F",
  clarity: "#D97706",
  rhythm: "#0284C7",
  vocabulary: "#7C3AED",
  voice: "#0D9488",
  grammar: "#DC2626",
  engineering: "#B45309",
  ownAi: "#9CA3AF",
  ownEngine: "#3B82F6",
  ownEdit: "#22C55E",
  ownInsert: "#15803D",
};

export const cardStyle: React.CSSProperties = {
  background: C.card,
  border: `1px solid ${C.rule}`,
  borderRadius: 16,
  boxShadow: `0 1px 0 ${C.rule}, 0 40px 80px -40px rgba(0,0,0,0.28)`,
};

export const monoLabel: React.CSSProperties = {
  fontFamily: F.mono,
  fontSize: 18,
  letterSpacing: "0.14em",
  textTransform: "uppercase",
};
