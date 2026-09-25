"use client";

import { useMutation } from "@tanstack/react-query";
import { motion, useReducedMotion } from "framer-motion";
import { ArrowRight, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { ConceptMap } from "@/components/concept-map/ConceptMap";
import { ParagraphCard } from "@/components/walkthrough/ParagraphCard";
import { api } from "@/lib/api";
import { useGate } from "@/lib/gate";
import { useWorkspace } from "@/lib/store";
import type { ParagraphMark, WalkthroughState } from "@/lib/types";
import { nodesForParagraph, remapMarks } from "@/lib/walkthrough";
import { Panel, StepLayout } from "./StepLayout";

const isTyping = (t: EventTarget | null) =>
  t instanceof HTMLElement && (t.tagName === "INPUT" || t.tagName === "TEXTAREA" || t.isContentEditable);

export function WalkthroughStep({ onNext }: { onNext: () => void }) {
  const doc = useWorkspace((s) => s.doc)!;
  const text = useWorkspace((s) => s.text);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const active = useWorkspace((s) => s.activeParagraph);
  const setActive = useWorkspace((s) => s.setActiveParagraph);
  const gate = useGate(doc);
  const reduce = useReducedMotion();
  const wt = doc.walkthrough;
  const [simple, setSimple] = useState<Set<number>>(new Set());
  const cards = useRef(new Map<number, HTMLElement>());
  const autoRan = useRef(false);

  const run = useMutation({
    mutationFn: (t: string) => api.walkthrough(t).then((data) => ({ data, text: t })),
    onSuccess: ({ data, text: t }) => {
      patchDoc((d) => {
        const next: WalkthroughState = {
          data,
          text: t,
          marks: remapMarks(d.walkthrough, data, t),
          ownDefs: d.walkthrough?.ownDefs ?? {},
        };
        return { walkthrough: next };
      });
      setSimple(new Set());
      setActive(data.paragraphs[0]?.index ?? null);
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // build the walkthrough the first time the step is opened
  useEffect(() => {
    if (autoRan.current || wt || !text.trim()) return;
    autoRan.current = true;
    run.mutate(text);
  }, [wt, text, run]);

  const paragraphs = useMemo(() => wt?.data.paragraphs ?? [], [wt]);
  const stale = !!wt && wt.text !== text;
  const reviewed = paragraphs.filter((p) => wt?.marks[p.index]).length;
  const confusing = paragraphs.filter((p) => wt?.marks[p.index] === "confusing");

  // ------------------------------------------------------------------ updates
  const mark = useCallback(
    (index: number, m: ParagraphMark | null) =>
      patchDoc((d) => {
        if (!d.walkthrough) return {};
        const marks = { ...d.walkthrough.marks };
        if (m) marks[index] = m;
        else delete marks[index];
        return { walkthrough: { ...d.walkthrough, marks } };
      }),
    [patchDoc],
  );

  const define = useCallback(
    (term: string, definition: string) =>
      patchDoc((d) => {
        if (!d.walkthrough) return {};
        const ownDefs = { ...(d.walkthrough.ownDefs ?? {}) };
        if (definition) ownDefs[term.toLowerCase()] = definition;
        else delete ownDefs[term.toLowerCase()];
        return { walkthrough: { ...d.walkthrough, ownDefs } };
      }),
    [patchDoc],
  );

  const toggleSimple = useCallback((index: number) => {
    setSimple((s) => {
      const n = new Set(s);
      if (n.has(index)) n.delete(index);
      else n.add(index);
      return n;
    });
  }, []);

  const goTo = useCallback(
    (index: number) => {
      setActive(index);
      const el = cards.current.get(index);
      if (el) {
        el.scrollIntoView({ behavior: reduce ? "auto" : "smooth", block: "start" });
        el.focus({ preventScroll: true });
      }
    },
    [reduce, setActive],
  );

  // ------------------------------------------------------------------ scroll sync
  useEffect(() => {
    if (!paragraphs.length) return;
    const visible = new Map<number, number>();
    const io = new IntersectionObserver(
      (entries) => {
        for (const e of entries) {
          const idx = Number((e.target as HTMLElement).dataset.paragraph);
          if (e.isIntersecting) visible.set(idx, e.boundingClientRect.top);
          else visible.delete(idx);
        }
        if (visible.size) {
          const top = [...visible.entries()].sort((a, b) => a[1] - b[1])[0][0];
          if (useWorkspace.getState().activeParagraph !== top) setActive(top);
        }
      },
      // a band a little above the middle of the screen = "the paragraph being read"
      { rootMargin: "-30% 0px -55% 0px" },
    );
    cards.current.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, [paragraphs, setActive]);

  // ------------------------------------------------------------------ keyboard
  useEffect(() => {
    const onKey = (e: KeyboardEvent) => {
      if (e.metaKey || e.ctrlKey || e.altKey || isTyping(e.target) || !paragraphs.length) return;
      const i = Math.max(0, paragraphs.findIndex((p) => p.index === active));
      const cur = paragraphs[i];
      const key = e.key.toLowerCase();
      if (key === "j" && i < paragraphs.length - 1) goTo(paragraphs[i + 1].index);
      else if (key === "k" && i > 0) goTo(paragraphs[i - 1].index);
      else if (key === "g") {
        mark(cur.index, wt?.marks[cur.index] === "got" ? null : "got");
        if (wt?.marks[cur.index] !== "got" && i < paragraphs.length - 1) goTo(paragraphs[i + 1].index);
      } else if (key === "c") mark(cur.index, wt?.marks[cur.index] === "confusing" ? null : "confusing");
      else if (key === "s") toggleSimple(cur.index);
      else return;
      e.preventDefault();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [paragraphs, active, wt, goTo, mark, toggleSimple]);

  const focusNodes = useMemo(() => (wt ? nodesForParagraph(wt.data, active) : []), [wt, active]);
  const onNodeClick = useCallback(
    (id: string) => {
      const node = wt?.data.concept_map.nodes.find((n) => n.id === id);
      const target = node?.paragraphs.find((p) => p !== active) ?? node?.paragraphs[0];
      if (target != null) goTo(target);
    },
    [wt, active, goTo],
  );

  // ------------------------------------------------------------------ render
  const pct = paragraphs.length ? reviewed / paragraphs.length : 0;
  const needed = gate.thresholds.walkthrough;

  return (
    <StepLayout
      toolbar={
        <>
          <h1 className="font-display text-3xl">2 · Walkthrough</h1>
          <span className="ml-2 text-xs text-muted-foreground">
            {run.isPending ? (
              <span className="inline-flex items-center gap-1">
                <Loader2 className="size-3 animate-spin" /> reading your document…
              </span>
            ) : wt ? (
              `${paragraphs.length} paragraphs · ${reviewed} reviewed`
            ) : null}
          </span>
          <div className="ml-auto flex items-center gap-2">
            {wt && (
              <button
                type="button"
                onClick={() => run.mutate(text)}
                disabled={run.isPending}
                className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary disabled:opacity-50"
              >
                <RefreshCw className="size-4" /> Refresh
              </button>
            )}
            <button type="button" onClick={onNext} className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary">
              Make it yours <ArrowRight className="size-4" />
            </button>
          </div>
        </>
      }
      main={
        !text.trim() ? (
          <p className="rounded-xl border border-dashed border-rule p-10 text-center text-muted-foreground">
            This document is empty. Add text in step 1 first.
          </p>
        ) : !wt ? (
          <div className="space-y-4" aria-busy="true" aria-label="Building the walkthrough">
            {[0, 1, 2].map((i) => (
              <div key={i} className="h-48 animate-pulse rounded-xl border border-rule bg-card" />
            ))}
          </div>
        ) : (
          <div className="space-y-5">
            {stale && (
              <div role="status" className="flex flex-wrap items-center gap-3 rounded-lg border border-signal/50 bg-signal/10 px-4 py-2 text-sm">
                Your text changed since this walkthrough was made.
                <button type="button" onClick={() => run.mutate(text)} className="font-medium underline" disabled={run.isPending}>
                  Refresh it
                </button>
                <span className="text-muted-foreground">(your marks stay on paragraphs that didn&apos;t change)</span>
              </div>
            )}
            <p className="text-sm text-muted-foreground">
              Read each paragraph&apos;s one-line gist, check the key terms, then mark it <b>Got it</b> or <b>Confusing</b>. Keys:{" "}
              <kbd className="tabular">J</kbd>/<kbd className="tabular">K</kbd> move, <kbd className="tabular">G</kbd> got it,{" "}
              <kbd className="tabular">C</kbd> confusing, <kbd className="tabular">S</kbd> simpler version.
            </p>
            {paragraphs.map((p, i) => (
              <ParagraphCard
                key={p.index}
                ref={(el) => {
                  if (el) cards.current.set(p.index, el);
                  else cards.current.delete(p.index);
                }}
                para={p}
                n={i + 1}
                total={paragraphs.length}
                text={wt.text}
                mark={wt.marks[p.index]}
                active={active === p.index}
                simple={simple.has(p.index)}
                ownDefs={wt.ownDefs}
                onMark={(m) => mark(p.index, m)}
                onToggleSimple={() => toggleSimple(p.index)}
                onDefine={define}
                onFocus={() => setActive(p.index)}
              />
            ))}
            {paragraphs.length === 0 && <p className="text-muted-foreground">No paragraphs found.</p>}
          </div>
        )
      }
      aside={
        <>
          <Panel title="Understanding">
            <div className="flex items-baseline justify-between">
              <span className="tabular text-3xl">{Math.round(pct * 100)}%</span>
              <span className="text-xs text-muted-foreground">
                {reviewed} / {paragraphs.length} reviewed
              </span>
            </div>
            <div className="relative mt-2 h-2 overflow-hidden rounded-full bg-secondary" role="progressbar" aria-valuenow={Math.round(pct * 100)} aria-valuemin={0} aria-valuemax={100} aria-label="Paragraphs reviewed">
              <motion.div
                className="h-full rounded-full bg-[var(--own-insert)]"
                initial={false}
                animate={{ width: `${pct * 100}%` }}
                transition={{ duration: reduce ? 0 : 0.4 }}
              />
              <span className="absolute inset-y-0 w-px bg-foreground/60" style={{ left: `${needed}%` }} aria-hidden />
            </div>
            <p className="mt-2 text-xs text-muted-foreground">
              {gate.walkthroughOk
                ? "Walkthrough check passed."
                : `Review at least ${needed}% of paragraphs to unlock export.`}
            </p>
            {confusing.length > 0 && (
              <div className="mt-3 border-t border-rule pt-3">
                <p className="mb-1 text-xs text-muted-foreground">Marked confusing ({confusing.length}), and you&apos;ll be quizzed on these:</p>
                <ul className="space-y-1">
                  {confusing.map((p) => (
                    <li key={p.index}>
                      <button type="button" onClick={() => goTo(p.index)} className="line-clamp-1 text-left text-sm hover:underline">
                        ¶ {paragraphs.indexOf(p) + 1} · {p.gist}
                      </button>
                    </li>
                  ))}
                </ul>
              </div>
            )}
          </Panel>

          {wt && (
            <Panel title="Concept map">
              <ConceptMap data={wt.data.concept_map} focus={focusNodes} onNodeClick={onNodeClick} />
              <p className="mt-2 text-xs text-muted-foreground">
                Highlighted: concepts in the paragraph you&apos;re reading. Click a concept to jump to where it appears.
              </p>
            </Panel>
          )}
        </>
      }
    />
  );
}
