"use client";

import { Loader2 } from "lucide-react";
import type { DoctorResponse, Issue } from "@/lib/api";
import { IssueList } from "./IssueList";

export const CHECK_LABEL: Record<string, string> = {
  units: "Units",
  abbreviations: "Abbreviations",
  figures: "Figures & tables",
  tense: "Tense",
  claims: "Claims",
  structure: "Structure",
};

/** Which Report Doctor check an issue comes from ("abbr.undefined" → "abbreviations"). */
export function checkOf(issue: Issue): string {
  const prefix = issue.rule.split(".")[0];
  return CHECK_LABEL[prefix] ? CHECK_LABEL[prefix] : prefix === "abbr" ? CHECK_LABEL.abbreviations : prefix;
}

/** Engineering Report Doctor results (U4): per-check counts and the issue list. */
export function DoctorPanel({
  result,
  loading,
  text,
  activeId,
  onSelect,
  onApply,
}: {
  result?: DoctorResponse;
  loading: boolean;
  text: string;
  activeId: string | null;
  onSelect: (id: string) => void;
  onApply: (i: Issue) => void;
}) {
  if (!result) {
    return (
      <p className="inline-flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-3.5 animate-spin" /> Checking units, abbreviations, figures, tense, claims and structure…
      </p>
    );
  }
  return (
    <div className="space-y-3">
      <ul className="grid grid-cols-3 gap-1.5 text-center" aria-label="Checks">
        {Object.entries(CHECK_LABEL).map(([key, label]) => {
          const n = result.counts[key] ?? 0;
          return (
            <li key={key} className="rounded-md border border-rule px-1 py-1.5">
              <span className={`tabular block text-lg leading-none ${n ? "text-[var(--hl-engineering)]" : "text-[var(--own-insert)]"}`}>{n || "✓"}</span>
              <span className="text-[10px] uppercase tracking-wider text-muted-foreground">{label}</span>
            </li>
          );
        })}
      </ul>
      {loading && <p className="text-xs text-muted-foreground">Updating…</p>}
      {result.issues.length ? (
        <IssueList issues={result.issues} activeId={activeId} onSelect={onSelect} text={text} onApply={onApply} groupOf={checkOf} />
      ) : (
        <p className="text-sm text-muted-foreground">No engineering-report problems found.</p>
      )}
    </div>
  );
}
