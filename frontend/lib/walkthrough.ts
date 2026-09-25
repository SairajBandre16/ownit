import type { KeyTerm, WalkthroughParagraph, WalkthroughResponse } from "./api";
import type { ParagraphMark } from "./types";

export type TextPiece = { text: string; term?: KeyTerm };

/**
 * Split a paragraph into plain text and key-term pieces. Term offsets are absolute
 * (into the walkthrough text); overlapping terms keep the earlier/longer one.
 */
export function termPieces(text: string, para: Pick<WalkthroughParagraph, "start" | "end" | "key_terms">): TextPiece[] {
  const terms = [...para.key_terms]
    .filter((t) => t.start >= para.start && t.end <= para.end && t.end > t.start)
    .sort((a, b) => a.start - b.start || b.end - a.end);
  const pieces: TextPiece[] = [];
  let pos = para.start;
  for (const t of terms) {
    if (t.start < pos) continue; // overlaps a previous term
    if (t.start > pos) pieces.push({ text: text.slice(pos, t.start) });
    pieces.push({ text: text.slice(t.start, t.end), term: t });
    pos = t.end;
  }
  if (pos < para.end) pieces.push({ text: text.slice(pos, para.end) });
  return pieces;
}

const norm = (s: string) => s.replace(/\s+/g, " ").trim();

/**
 * Carry "Got it / Confusing" marks over to a refreshed walkthrough: a paragraph keeps its
 * mark if its text is unchanged (paragraph indices may shift when text is edited).
 */
export function remapMarks(
  old: { data: WalkthroughResponse; text: string; marks: Record<number, ParagraphMark> } | undefined,
  next: WalkthroughResponse,
  nextText: string,
): Record<number, ParagraphMark> {
  if (!old) return {};
  const byText = new Map<string, ParagraphMark>();
  for (const p of old.data.paragraphs) {
    const m = old.marks[p.index];
    if (m) byText.set(norm(old.text.slice(p.start, p.end)), m);
  }
  const out: Record<number, ParagraphMark> = {};
  for (const p of next.paragraphs) {
    const m = byText.get(norm(nextText.slice(p.start, p.end)));
    if (m) out[p.index] = m;
  }
  return out;
}

/** Definition to show for a term: the student's own wins over the tool's. */
export function termDefinition(term: KeyTerm, ownDefs: Record<string, string> | undefined): { text: string | null; own: boolean } {
  const own = ownDefs?.[term.term.toLowerCase()];
  if (own) return { text: own, own: true };
  return { text: term.definition ?? null, own: false };
}

export const SOURCE_LABEL: Record<string, string> = {
  document: "from your text",
  abbreviation: "abbreviation list",
  wordnet: "dictionary (WordNet)",
};

/** Concept-map node ids that appear in a paragraph. */
export function nodesForParagraph(data: WalkthroughResponse, paragraph: number | null): string[] {
  if (paragraph == null) return [];
  return data.concept_map.nodes.filter((n) => n.paragraphs.includes(paragraph)).map((n) => n.id);
}
