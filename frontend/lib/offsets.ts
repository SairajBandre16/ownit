/**
 * Character offsets <-> ProseMirror positions.
 *
 * The editor document is a flat list of paragraphs, one per line of the plain text
 * (lines joined with "\n"). For a character offset `o` with `k` newlines before it, the
 * ProseMirror position is `o + 1 + k` (each paragraph boundary costs 2 positions but only
 * 1 character).
 */
import type { Node as PMNode } from "@tiptap/pm/model";

export function newlineCountBefore(text: string, offset: number): number {
  let k = 0;
  for (let i = 0; i < offset && i < text.length; i++) if (text.charCodeAt(i) === 10) k++;
  return k;
}

/** Build a converter for a given plain text (O(n) setup, O(log n) per lookup). */
export function offsetMapper(text: string) {
  const newlines: number[] = [];
  for (let i = 0; i < text.length; i++) if (text.charCodeAt(i) === 10) newlines.push(i);
  const countBefore = (offset: number) => {
    let lo = 0;
    let hi = newlines.length;
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (newlines[mid] < offset) lo = mid + 1;
      else hi = mid;
    }
    return lo;
  };
  return {
    toPos: (offset: number) => offset + 1 + countBefore(offset),
    /** ProseMirror position -> character offset. */
    toOffset: (pos: number) => {
      // find k such that pos = o + 1 + k, with k = newlines before o
      let lo = 0;
      let hi = text.length;
      while (lo < hi) {
        const mid = (lo + hi + 1) >> 1;
        if (mid + 1 + countBefore(mid) <= pos) lo = mid;
        else hi = mid - 1;
      }
      return lo;
    },
  };
}

/** Plain text of a ProseMirror doc, paragraphs joined by "\n" (inverse of textToDoc). */
export function docText(doc: PMNode): string {
  const lines: string[] = [];
  doc.forEach((node) => lines.push(node.textContent));
  return lines.join("\n");
}

/** TipTap JSON for plain text: one paragraph per line; optional origin mark on all text. */
export function textToContent(text: string, origin?: string) {
  return {
    type: "doc",
    content: text.split("\n").map((line) =>
      line.length
        ? {
            type: "paragraph",
            content: [
              {
                type: "text",
                text: line,
                ...(origin ? { marks: [{ type: "origin", attrs: { origin } }] } : {}),
              },
            ],
          }
        : { type: "paragraph" },
    ),
  };
}

/** Plain text of TipTap JSON content (same layout as docText). */
export function jsonText(content: { content?: { content?: { text?: string }[] }[] } | null | undefined): string {
  if (!content?.content) return "";
  return content.content.map((p) => (p.content ?? []).map((t) => t.text ?? "").join("")).join("\n");
}
