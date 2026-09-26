"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowLeft, Check, FileDown, FileText, Lock } from "lucide-react";
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { OwnershipPanel } from "@/components/ownership/OwnershipPanel";
import { GatePanel } from "@/components/prove/GatePanel";
import { api } from "@/lib/api";
import { wordCount } from "@/lib/assess";
import { saveBlob } from "@/lib/download";
import { useGate } from "@/lib/gate";
import { computeOwnership } from "@/lib/ownership";
import { buildReportData } from "@/lib/report";
import { useWorkspace } from "@/lib/store";
import type { StepId } from "@/lib/types";
import { Panel, StepLayout } from "./StepLayout";

/** Step 5: download the document and the Understanding Report, once the checks are passed. */
export function ExportStep({ onGo }: { onGo: (step: StepId) => void }) {
  const doc = useWorkspace((s) => s.doc)!;
  const text = useWorkspace((s) => s.text);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const gate = useGate(doc);
  const ownership = useMemo(() => computeOwnership(doc, text), [doc, text]);
  const [addNote, setAddNote] = useState(false);

  const docx = useMutation({
    mutationFn: () =>
      api.exportDocx({
        text,
        title: doc.title,
        author: doc.author || null,
        understanding: addNote
          ? { score: ownership.score, student_share: ownership.studentShare, passed_at: gate.passed ? new Date().toISOString().slice(0, 10) : null }
          : null,
      }),
    onSuccess: ({ blob, filename }) => {
      saveBlob(blob, filename);
      patchDoc((d) => ({ exports: [...(d.exports ?? []), { at: Date.now(), kind: "docx" as const }] }));
      toast.success(`Saved ${filename}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const report = useMutation({
    mutationFn: () => api.exportReport(buildReportData(doc, gate, ownership)),
    onSuccess: ({ blob, filename }) => {
      saveBlob(blob, filename);
      patchDoc((d) => ({ exports: [...(d.exports ?? []), { at: Date.now(), kind: "report" as const }] }));
      toast.success(`Saved ${filename}`);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const unmet: { label: string; step: StepId; detail: string }[] = [];
  if (!gate.walkthroughOk)
    unmet.push({ label: "Walkthrough", step: "walkthrough", detail: `Mark at least ${gate.thresholds.walkthrough}% of paragraphs Got it or Confusing.` });
  if (!gate.quizOk) unmet.push({ label: "Quiz", step: "prove", detail: `Score at least ${gate.thresholds.quiz}% on the quiz.` });
  if (!gate.teachbackOk)
    unmet.push({ label: "Teach-back", step: "prove", detail: `Cover at least ${gate.thresholds.teachback}% of the key ideas in your explanation.` });

  return (
    <StepLayout
      toolbar={
        <>
          <h1 className="font-display text-3xl">5 · Export</h1>
          <div className="ml-auto">
            <button type="button" onClick={() => onGo("prove")} className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary">
              <ArrowLeft className="size-4" /> Prove it
            </button>
          </div>
        </>
      }
      main={
        !gate.passed ? (
          <section className="rounded-xl border border-rule bg-card p-6 sm:p-8" aria-labelledby="locked-title">
            <Lock className="size-6 text-signal-ink" aria-hidden />
            <h2 id="locked-title" className="mt-3 font-display text-3xl">
              Export unlocks when you understand what you&apos;re handing in
            </h2>
            <p className="mt-2 max-w-prose text-muted-foreground">Still to do:</p>
            <ul className="mt-3 space-y-2">
              {unmet.map((u) => (
                <li key={u.label} className="flex flex-wrap items-center gap-3 rounded-lg border border-rule px-4 py-3">
                  <span className="font-medium">{u.label}</span>
                  <span className="text-sm text-muted-foreground">{u.detail}</span>
                  <button type="button" onClick={() => onGo(u.step)} className="ml-auto text-sm text-signal-ink underline underline-offset-4">
                    Go there
                  </button>
                </li>
              ))}
            </ul>
            <p className="mt-4 text-xs text-muted-foreground">You can switch this gate off in the panel on the right, but it&apos;s there to protect you in your viva.</p>
          </section>
        ) : (
          <div className="space-y-5">
            <section className="rounded-xl border border-rule bg-card p-6 sm:p-8">
              <p className="inline-flex items-center gap-2 text-sm text-[var(--own-insert)]">
                <Check className="size-4" /> {gate.enabled ? "All understanding checks passed" : "Understanding gate is switched off"}
              </p>
              <div className="mt-4 grid gap-3 sm:grid-cols-2">
                <label className="text-sm">
                  <span className="mb-1 block text-muted-foreground">Title</span>
                  <input
                    value={doc.title}
                    onChange={(e) => patchDoc({ title: e.target.value })}
                    className="w-full rounded-md border border-input bg-background px-3 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>
                <label className="text-sm">
                  <span className="mb-1 block text-muted-foreground">Author (optional)</span>
                  <input
                    value={doc.author ?? ""}
                    onChange={(e) => patchDoc({ author: e.target.value })}
                    placeholder="Your name"
                    className="w-full rounded-md border border-input bg-background px-3 py-2 focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
                  />
                </label>
              </div>
              <label className="mt-4 flex items-center gap-2 text-sm">
                <input type="checkbox" checked={addNote} onChange={(e) => setAddNote(e.target.checked)} className="size-4 accent-[var(--signal)]" />
                Add an ownership note at the end (score and share of text you wrote)
              </label>
              <div className="mt-6 flex flex-wrap gap-3">
                <button
                  type="button"
                  onClick={() => docx.mutate()}
                  disabled={docx.isPending || !text.trim()}
                  className="inline-flex items-center gap-2 rounded-md bg-primary px-5 py-2.5 font-medium text-primary-foreground disabled:opacity-50"
                >
                  <FileDown className="size-4" /> {docx.isPending ? "Preparing…" : "Download .docx"}
                </button>
                <button
                  type="button"
                  onClick={() => report.mutate()}
                  disabled={report.isPending}
                  className="inline-flex items-center gap-2 rounded-md border border-rule px-5 py-2.5 hover:bg-secondary disabled:opacity-50"
                >
                  <FileText className="size-4" /> {report.isPending ? "Preparing…" : "Download Understanding Report"}
                </button>
              </div>
              <p className="tabular mt-3 text-xs text-muted-foreground">{wordCount(text).toLocaleString()} words</p>
            </section>
            <section className="rounded-xl border border-rule bg-card p-6 text-sm">
              <h2 className="font-display text-2xl">What&apos;s in the Understanding Report</h2>
              <p className="mt-2 text-muted-foreground">
                Your Ownership Score breakdown, the three understanding checks, concepts you&apos;ve mastered and ones to revise, your glossary (with
                your own definitions), every viva question with your answer and feedback, quiz questions you missed, your teach-back, and a revision
                list. Use it as a revision sheet before the viva.
              </p>
            </section>
          </div>
        )
      }
      aside={
        <>
          <Panel title="Understanding gate">
            <GatePanel gate={gate} />
          </Panel>
          <Panel title="Ownership">
            <OwnershipPanel b={ownership} />
          </Panel>
        </>
      }
    />
  );
}
