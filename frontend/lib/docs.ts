import { newId, saveDoc } from "./db";
import { textToContent } from "./offsets";
import { DEFAULT_SETTINGS, type OwnDoc } from "./types";

export const MAX_WORDS = 3000;

export function countWords(text: string): number {
  return text.split(/\s+/).filter(Boolean).length;
}

/** Normalise pasted text: unix newlines, no trailing spaces, at most one blank line in a row. */
export function normalizeText(text: string): string {
  return text
    .replace(/\r\n?/g, "\n")
    .replace(/ /g, " ")
    .replace(/[ \t]+\n/g, "\n")
    .replace(/\n{3,}/g, "\n\n")
    .trim();
}

export function guessTitle(text: string): string {
  const first = text.split("\n").find((l) => l.trim()) ?? "Untitled";
  const t = first.trim().replace(/[.:]$/, "");
  return t.length > 70 ? `${t.slice(0, 67)}…` : t;
}

export async function createDoc(rawText: string, title?: string): Promise<OwnDoc> {
  const text = normalizeText(rawText);
  const now = Date.now();
  const doc: OwnDoc = {
    id: newId(),
    title: title?.trim() || guessTitle(text),
    createdAt: now,
    updatedAt: now,
    originalText: text,
    content: textToContent(text, "ai"),
    step: "humanize",
    settings: { ...DEFAULT_SETTINGS },
  };
  await saveDoc(doc);
  return doc;
}
