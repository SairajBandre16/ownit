/**
 * A small Markdown renderer for the lessons: headings (##, ###), paragraphs, bullet and
 * numbered lists, block quotes, **bold**, *italic* / _italic_, `code` and links. It builds React
 * elements (no raw HTML), so lesson text can never inject markup. Only internal links ("/…")
 * and https links are rendered as links.
 */
import Link from "next/link";
import type { ReactNode } from "react";

type Block =
  | { kind: "h2" | "h3" | "p" | "quote"; text: string }
  | { kind: "ul" | "ol"; items: string[] };

export function parseBlocks(md: string): Block[] {
  const blocks: Block[] = [];
  const lines = md.replace(/\r\n/g, "\n").split("\n");
  let para: string[] = [];
  const flush = () => {
    if (para.length) blocks.push({ kind: "p", text: para.join(" ") });
    para = [];
  };
  for (const raw of lines) {
    const line = raw.trimEnd();
    const last = blocks[blocks.length - 1];
    let m: RegExpMatchArray | null;
    if (!line.trim()) {
      flush();
    } else if ((m = line.match(/^(#{2,3})\s+(.*)$/))) {
      flush();
      blocks.push({ kind: m[1].length === 2 ? "h2" : "h3", text: m[2] });
    } else if ((m = line.match(/^\s*[-*]\s+(.*)$/))) {
      flush();
      if (last?.kind === "ul") last.items.push(m[1]);
      else blocks.push({ kind: "ul", items: [m[1]] });
    } else if ((m = line.match(/^\s*\d+[.)]\s+(.*)$/))) {
      flush();
      if (last?.kind === "ol") last.items.push(m[1]);
      else blocks.push({ kind: "ol", items: [m[1]] });
    } else if ((m = line.match(/^>\s?(.*)$/))) {
      flush();
      if (last?.kind === "quote") last.text += ` ${m[1]}`;
      else blocks.push({ kind: "quote", text: m[1] });
    } else if (last && (last.kind === "ul" || last.kind === "ol") && /^\s{2,}\S/.test(raw) && !para.length) {
      last.items[last.items.length - 1] += ` ${line.trim()}`; // continuation of a list item
    } else {
      para.push(line.trim());
    }
  }
  flush();
  return blocks;
}

const INLINE = /(\*\*[^*]+\*\*|`[^`]+`|\[[^\]]+\]\([^)\s]+\)|\*[^*\s][^*]*\*|_[^_\s][^_]*_)/g;

export function renderInline(text: string): ReactNode[] {
  const out: ReactNode[] = [];
  let last = 0;
  let k = 0;
  for (const m of text.matchAll(INLINE)) {
    const tok = m[0];
    const at = m.index ?? 0;
    if (at > last) out.push(text.slice(last, at));
    if (tok.startsWith("**")) out.push(<strong key={k++}>{tok.slice(2, -2)}</strong>);
    else if (tok.startsWith("`")) out.push(<code key={k++} className="tabular rounded bg-secondary px-1 text-[0.9em]">{tok.slice(1, -1)}</code>);
    else if (tok.startsWith("[")) {
      const lm = tok.match(/^\[([^\]]+)\]\(([^)\s]+)\)$/)!;
      const href = lm[2];
      if (href.startsWith("/")) out.push(<Link key={k++} href={href} className="text-signal-ink underline underline-offset-2">{lm[1]}</Link>);
      else if (href.startsWith("https://"))
        out.push(
          <a key={k++} href={href} target="_blank" rel="noreferrer noopener" className="text-signal-ink underline underline-offset-2">
            {lm[1]}
          </a>,
        );
      else out.push(lm[1]);
    } else out.push(<em key={k++}>{tok.slice(1, -1)}</em>);
    last = at + tok.length;
  }
  if (last < text.length) out.push(text.slice(last));
  return out;
}

export function Markdown({ source }: { source: string }) {
  return (
    <div className="space-y-4 leading-relaxed">
      {parseBlocks(source).map((b, i) => {
        switch (b.kind) {
          case "h2":
            return (
              <h2 key={i} className="pt-2 font-display text-2xl">
                {renderInline(b.text)}
              </h2>
            );
          case "h3":
            return (
              <h3 key={i} className="text-lg font-medium">
                {renderInline(b.text)}
              </h3>
            );
          case "quote":
            return (
              <blockquote key={i} className="border-l-2 border-signal/70 pl-4 text-muted-foreground">
                {renderInline(b.text)}
              </blockquote>
            );
          case "ul":
            return (
              <ul key={i} className="list-disc space-y-1 pl-6">
                {b.items.map((it, j) => (
                  <li key={j}>{renderInline(it)}</li>
                ))}
              </ul>
            );
          case "ol":
            return (
              <ol key={i} className="list-decimal space-y-1 pl-6">
                {b.items.map((it, j) => (
                  <li key={j}>{renderInline(it)}</li>
                ))}
              </ol>
            );
          default:
            return <p key={i}>{renderInline(b.text)}</p>;
        }
      })}
    </div>
  );
}
