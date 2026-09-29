"use client";

import Link from "next/link";
import { useMemo, useState } from "react";
import type { Issue } from "@/lib/api";
import { cn } from "@/lib/utils";

export const CATEGORY_COLORS: Record<string, string> = {
  clarity: "var(--hl-clarity)",
  rhythm: "var(--hl-rhythm)",
  vocabulary: "var(--hl-vocabulary)",
  voice: "var(--hl-voice)",
  correctness: "var(--hl-grammar)",
  grammar: "var(--hl-grammar)",
  engineering: "var(--hl-engineering)",
};

const ORDER = ["correctness", "engineering", "clarity", "vocabulary", "voice", "rhythm"];
const byCategory = (i: Issue) => i.category;

export function IssueCard({ issue, text, onApply }: { issue: Issue; text?: string; onApply?: (i: Issue) => void }) {
  const quote = text ? text.slice(issue.start, issue.end) : "";
  return (
    <div className="space-y-2">
      <div className="flex items-center gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
        <span className="size-2 rounded-full" style={{ background: CATEGORY_COLORS[issue.category] }} aria-hidden />
        {issue.category} · {issue.rule.replace(/^lt:/, "").replaceAll("_", " ").toLowerCase()}
        <span className={cn("ml-auto rounded px-1.5 py-0.5 normal-case", issue.severity === "error" ? "bg-destructive/15 text-destructive" : issue.severity === "warn" ? "bg-[var(--hl-clarity)]/15" : "bg-secondary")}>
          {issue.severity}
        </span>
      </div>
      <p className="leading-snug">{issue.message}</p>
      {quote && quote.length < 140 && <p className="tabular line-clamp-2 text-xs text-muted-foreground">“{quote}”</p>}
      <div className="flex flex-wrap items-center gap-2">
        {issue.suggestion != null && onApply && (
          <button
            type="button"
            onClick={() => onApply(issue)}
            className="rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground"
          >
            {issue.suggestion === "" ? "Delete it" : `Use “${issue.suggestion}”`}
          </button>
        )}
        {issue.lesson_slug && (
          <Link href={`/learn/${issue.lesson_slug}`} className="text-xs text-signal-ink underline underline-offset-2" target="_blank">
            Lesson: {issue.lesson_slug.replaceAll("-", " ")}
          </Link>
        )}
      </div>
    </div>
  );
}

export function IssueList({
  issues,
  activeId,
  onSelect,
  text,
  onApply,
  groupOf = byCategory,
  filter: controlled,
  onFilter,
  note,
}: {
  issues: Issue[];
  activeId?: string | null;
  onSelect?: (id: string) => void;
  text?: string;
  onApply?: (i: Issue) => void;
  /** what the filter chips group by (default: category) */
  groupOf?: (i: Issue) => string;
  /** controlled filter (e.g. shared with the editor highlights); uncontrolled when omitted */
  filter?: string | null;
  onFilter?: (group: string | null) => void;
  /** line under the chips explaining what the editor shows */
  note?: React.ReactNode;
}) {
  const [ownFilter, setOwnFilter] = useState<string | null>(null);
  const filter = onFilter ? (controlled ?? null) : ownFilter;
  const setFilter = onFilter ?? setOwnFilter;
  const counts = useMemo(() => {
    const c: Record<string, number> = {};
    for (const i of issues) c[groupOf(i)] = (c[groupOf(i)] ?? 0) + 1;
    return c;
  }, [issues, groupOf]);
  const shown = useMemo(
    () =>
      issues
        .filter((i) => !filter || groupOf(i) === filter)
        .sort((a, b) => ORDER.indexOf(a.category) - ORDER.indexOf(b.category) || a.start - b.start),
    [issues, filter, groupOf],
  );
  if (!issues.length) return <p className="text-sm text-muted-foreground">No issues found.</p>;
  return (
    <div>
      <div className="mb-2 flex flex-wrap gap-1" role="toolbar" aria-label="Filter issues">
        <button type="button" onClick={() => setFilter(null)} aria-pressed={!filter} className={cn("rounded-full border px-2 py-0.5 text-xs", !filter ? "border-foreground" : "border-rule text-muted-foreground")}>
          All {issues.length}
        </button>
        {Object.entries(counts).map(([cat, n]) => (
          <button
            key={cat}
            type="button"
            onClick={() => setFilter(filter === cat ? null : cat)}
            aria-pressed={filter === cat}
            className={cn("flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs", filter === cat ? "border-foreground" : "border-rule text-muted-foreground")}
          >
            <span className="size-1.5 rounded-full" style={{ background: CATEGORY_COLORS[cat] ?? CATEGORY_COLORS.engineering }} />
            {cat} {n}
          </button>
        ))}
      </div>
      {note && <p className="mb-2 text-xs text-muted-foreground">{note}</p>}
      <ul className="max-h-[28rem] space-y-1 overflow-y-auto pr-1">
        {shown.map((iss) => (
          <li
            key={iss.id}
            className={cn("rounded-md border-l-2 transition-colors", activeId === iss.id && "bg-secondary")}
            style={{ borderLeftColor: CATEGORY_COLORS[iss.category] }}
          >
            <button
              type="button"
              onClick={() => onSelect?.(iss.id)}
              aria-expanded={activeId === iss.id}
              className="w-full rounded-md px-2 py-1.5 text-left text-sm hover:bg-secondary"
            >
              <span className="line-clamp-2">{iss.message}</span>
            </button>
            {activeId === iss.id && (
              <div className="px-2 pb-2">
                <IssueCard issue={iss} text={text} onApply={onApply} />
              </div>
            )}
          </li>
        ))}
      </ul>
    </div>
  );
}
