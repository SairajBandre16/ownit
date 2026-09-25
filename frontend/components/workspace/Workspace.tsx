"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { ExportStep } from "@/components/steps/ExportStep";
import { HumanizeStep } from "@/components/steps/HumanizeStep";
import { MakeItYoursStep } from "@/components/steps/MakeItYoursStep";
import { ProveItStep } from "@/components/steps/ProveItStep";
import { Stepper } from "@/components/steps/Stepper";
import { WalkthroughStep } from "@/components/steps/WalkthroughStep";
import { getDoc } from "@/lib/db";
import { useGate } from "@/lib/gate";
import { jsonText } from "@/lib/offsets";
import { flushSave, useWorkspace } from "@/lib/store";
import type { StepId } from "@/lib/types";

export function Workspace({ docId }: { docId: string }) {
  const doc = useWorkspace((s) => s.doc);
  const setDoc = useWorkspace((s) => s.setDoc);
  const setText = useWorkspace((s) => s.setText);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const [missing, setMissing] = useState(false);
  const gate = useGate(doc);

  useEffect(() => {
    let alive = true;
    getDoc(docId).then((d) => {
      if (!alive) return;
      if (!d) {
        setMissing(true);
        return;
      }
      setDoc(d);
      setText(jsonText(d.content));
    });
    return () => {
      alive = false;
      void flushSave();
      setDoc(null);
    };
  }, [docId, setDoc, setText]);

  if (missing) {
    return (
      <>
        <SiteHeader />
        <main className="mx-auto max-w-xl flex-1 px-4 py-20 text-center">
          <h1 className="font-display text-4xl">Document not found</h1>
          <p className="mt-2 text-muted-foreground">It may have been deleted, or it was created in another browser.</p>
          <Link href="/workspace" className="mt-6 inline-block text-signal-ink underline">
            Back to workspace
          </Link>
        </main>
      </>
    );
  }
  if (!doc) {
    return (
      <>
        <SiteHeader />
        <main className="flex-1 p-10 text-muted-foreground">Loading…</main>
      </>
    );
  }

  const go = (step: StepId) => {
    void flushSave();
    patchDoc({ step });
    window.scrollTo({ top: 0 });
  };

  const done: Partial<Record<StepId, boolean>> = {
    humanize: !!doc.humanize && Object.keys(doc.humanize.decisions).length > 0,
    walkthrough: gate.walkthroughPct >= 0.8,
    personalize: !!doc.personalize && Object.keys(doc.personalize.filled).length > 0,
    prove: gate.quizOk && gate.teachbackOk,
    export: false,
  };

  return (
    <>
      <SiteHeader />
      <div className="mx-auto grid w-full max-w-[96rem] flex-1 gap-6 px-4 py-6 sm:px-6 lg:grid-cols-[14rem_minmax(0,1fr)]">
        <div className="lg:sticky lg:top-20 lg:self-start">
          <input
            aria-label="Document title"
            value={doc.title}
            onChange={(e) => patchDoc({ title: e.target.value })}
            className="mb-4 w-full truncate rounded-md bg-transparent px-2 py-1 font-display text-2xl leading-tight hover:bg-secondary focus:bg-secondary focus:outline-none"
          />
          <Stepper
            current={doc.step}
            done={done}
            locked={gate.enabled && !gate.passed ? { export: "Pass the understanding checks to unlock export" } : undefined}
            onSelect={go}
          />
        </div>
        <main id="main" className="min-w-0">
          {doc.step === "humanize" && <HumanizeStep onNext={() => go("walkthrough")} />}
          {doc.step === "walkthrough" && <WalkthroughStep onNext={() => go("personalize")} />}
          {doc.step === "personalize" && <MakeItYoursStep onNext={() => go("prove")} />}
          {doc.step === "prove" && <ProveItStep onNext={() => go("export")} />}
          {doc.step === "export" && <ExportStep onBack={() => go("prove")} />}
        </main>
      </div>
    </>
  );
}
