"use client";

import { ArrowRight, Mic } from "lucide-react";
import Link from "next/link";
import { useMemo, useState } from "react";
import { OwnershipPanel } from "@/components/ownership/OwnershipPanel";
import { GatePanel } from "@/components/prove/GatePanel";
import { QuizPanel } from "@/components/prove/QuizPanel";
import { TeachbackPanel } from "@/components/prove/TeachbackPanel";
import { summarizeViva } from "@/lib/assess";
import { useGate } from "@/lib/gate";
import { computeOwnership } from "@/lib/ownership";
import { flushSave, useWorkspace } from "@/lib/store";
import { cn } from "@/lib/utils";
import { Panel, StepLayout } from "./StepLayout";

type Tab = "quiz" | "teachback" | "viva";
const TABS: { id: Tab; label: string }[] = [
  { id: "quiz", label: "Quiz" },
  { id: "teachback", label: "Teach-back" },
  { id: "viva", label: "Viva Simulator" },
];

export function ProveItStep({ onNext }: { onNext: () => void }) {
  const doc = useWorkspace((s) => s.doc)!;
  const text = useWorkspace((s) => s.text);
  const gate = useGate(doc);
  const [tab, setTab] = useState<Tab>("quiz");
  const ownership = useMemo(() => computeOwnership(doc, text), [doc, text]);
  const viva = doc.assess?.viva;
  const vivaSummary = viva ? summarizeViva(viva.turns) : null;

  return (
    <StepLayout
      toolbar={
        <>
          <h1 className="font-display text-3xl">4 · Prove it</h1>
          <div className="ml-2 flex gap-1 rounded-lg bg-secondary p-1 text-sm" role="tablist" aria-label="Checks">
            {TABS.map((t) => (
              <button
                key={t.id}
                type="button"
                role="tab"
                aria-selected={tab === t.id}
                aria-controls={`panel-${t.id}`}
                onClick={() => setTab(t.id)}
                className={cn("rounded-md px-3 py-1", tab === t.id ? "bg-background shadow-sm" : "text-muted-foreground hover:text-foreground")}
              >
                {t.label}
              </button>
            ))}
          </div>
          <div className="ml-auto">
            <button
              type="button"
              onClick={onNext}
              className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary"
              title={gate.passed ? undefined : "Pass the checks to unlock export"}
            >
              Export <ArrowRight className="size-4" />
            </button>
          </div>
        </>
      }
      main={
        <div id={`panel-${tab}`} role="tabpanel" className="min-w-0">
          {tab === "quiz" && <QuizPanel threshold={gate.thresholds.quiz} />}
          {tab === "teachback" && <TeachbackPanel threshold={gate.thresholds.teachback} />}
          {tab === "viva" && (
            <div className="rounded-xl border border-rule bg-card p-6 sm:p-8">
              <Mic className="size-6 text-signal-ink" aria-hidden />
              <h2 className="mt-3 font-display text-3xl">Viva Simulator</h2>
              <p className="mt-2 max-w-prose text-muted-foreground">
                Ten spoken-exam style questions from your report. They start with definitions and get harder as you answer well: how, why, then
                compare and evaluate. A weak answer takes you back to the basics of the concept you missed. Answers are graded by the key ideas
                they cover.
              </p>
              <Link
                href={`/viva/${doc.id}`}
                onClick={() => void flushSave()}
                className="mt-5 inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground"
              >
                {viva ? "Start a new session" : "Enter the exam hall"} <ArrowRight className="size-4" />
              </Link>
              {vivaSummary && vivaSummary.answered > 0 && (
                <div className="mt-6 border-t border-rule pt-4">
                  <p className="text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Last session</p>
                  <p className="mt-1 text-sm">
                    <span className="tabular text-2xl">{Math.round(vivaSummary.average)}</span>
                    <span className="text-muted-foreground"> average over {vivaSummary.answered} questions</span>
                  </p>
                  {vivaSummary.weak.length > 0 && (
                    <p className="mt-2 text-sm">
                      Revise: <span className="text-muted-foreground">{vivaSummary.weak.slice(0, 5).map((w) => w.concept).join(", ")}</span>
                    </p>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
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
