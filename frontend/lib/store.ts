"use client";

import type { Editor } from "@tiptap/core";
import { create } from "zustand";
import { persist } from "zustand/middleware";
import { saveDoc } from "./db";
import type { OwnDoc } from "./types";

export type Layer = "issues" | "protected" | "changes" | "engineering" | "spots";

interface WorkspaceState {
  doc: OwnDoc | null;
  editor: Editor | null;
  /** plain text currently in the editor */
  text: string;
  layers: Record<Layer, boolean>;
  heatmap: boolean;
  /** suggestion category shown in the editor and the list; null = the main (warn/error) issues */
  issueFocus: string | null;
  activeIssueId: string | null;
  activeChangeId: string | null;
  activeParagraph: number | null;
  setDoc: (doc: OwnDoc | null) => void;
  patchDoc: (patch: Partial<OwnDoc> | ((d: OwnDoc) => Partial<OwnDoc>)) => void;
  setEditor: (e: Editor | null) => void;
  setText: (t: string) => void;
  toggleLayer: (l: Layer, on?: boolean) => void;
  setHeatmap: (on: boolean) => void;
  setIssueFocus: (category: string | null) => void;
  setActiveIssue: (id: string | null) => void;
  setActiveChange: (id: string | null) => void;
  setActiveParagraph: (i: number | null) => void;
}

let saveTimer: ReturnType<typeof setTimeout> | null = null;
function scheduleSave(doc: OwnDoc) {
  if (saveTimer) clearTimeout(saveTimer);
  saveTimer = setTimeout(() => void saveDoc(doc), 400);
}

export const useWorkspace = create<WorkspaceState>((set, get) => ({
  doc: null,
  editor: null,
  text: "",
  layers: { issues: true, protected: true, changes: true, engineering: false, spots: false },
  heatmap: false,
  issueFocus: null,
  activeIssueId: null,
  activeChangeId: null,
  activeParagraph: null,
  setDoc: (doc) => set({ doc }),
  patchDoc: (patch) => {
    const cur = get().doc;
    if (!cur) return;
    const p = typeof patch === "function" ? patch(cur) : patch;
    const next = { ...cur, ...p, updatedAt: Date.now() };
    set({ doc: next });
    scheduleSave(next);
  },
  setEditor: (editor) => set({ editor }),
  setText: (text) => set({ text }),
  toggleLayer: (l, on) => set((s) => ({ layers: { ...s.layers, [l]: on ?? !s.layers[l] } })),
  setHeatmap: (heatmap) => set({ heatmap }),
  setIssueFocus: (issueFocus) => set({ issueFocus }),
  setActiveIssue: (activeIssueId) => set({ activeIssueId }),
  setActiveChange: (activeChangeId) => set({ activeChangeId }),
  setActiveParagraph: (activeParagraph) => set({ activeParagraph }),
}));

/** Flush any pending save immediately (e.g. before navigating away). */
export async function flushSave() {
  const doc = useWorkspace.getState().doc;
  if (saveTimer) clearTimeout(saveTimer);
  if (doc) await saveDoc(doc);
}

export interface AppSettings {
  gateEnabled: boolean;
  quizThreshold: number;
  teachbackThreshold: number;
  walkthroughThreshold: number;
  vivaTimer: boolean;
  setSettings: (p: Partial<Omit<AppSettings, "setSettings">>) => void;
}

export const useSettings = create<AppSettings>()(
  persist(
    (set) => ({
      gateEnabled: true,
      quizThreshold: 70,
      teachbackThreshold: 60,
      walkthroughThreshold: 80,
      vivaTimer: false,
      setSettings: (p) => set(p),
    }),
    { name: "ownit-settings" },
  ),
);
