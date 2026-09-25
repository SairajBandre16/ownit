"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Loader2, RefreshCw } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { DocEditor } from "@/components/editor/DocEditor";
import type { OffsetLayers } from "@/components/editor/Editor";
import { findHighlight } from "@/components/editor/marks";
import { OwnershipPanel } from "@/components/ownership/OwnershipPanel";
import { SpotCard } from "@/components/personalize/SpotCard";
import { LayerToggles } from "@/components/steps/LayerToggles";
import { api } from "@/lib/api";
import { insertAt, scrollToHighlight } from "@/lib/editing";
import { docText, offsetMapper } from "@/lib/offsets";
import { computeOwnership, filledSpots } from "@/lib/ownership";
import { anchorId, formatAnswer, insertionText, locateSpots, mergeSpots } from "@/lib/personalize";
import { useWorkspace } from "@/lib/store";
import type { Spot } from "@/lib/types";
import { Panel, StepLayout } from "./StepLayout";

export function MakeItYoursStep({ onNext }: { onNext: () => void }) {
  const doc = useWorkspace((s) => s.doc)!;
  const text = useWorkspace((s) => s.text);
  const editor = useWorkspace((s) => s.editor);
  const layersOn = useWorkspace((s) => s.layers);
  const toggleLayer = useWorkspace((s) => s.toggleLayer);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const p = doc.personalize;
  const [activeId, setActiveId] = useState<string | null>(null);
  // bumps when the spot layers must be recomputed from offsets (new result, reload, un-skip)
  const [nonce, setNonce] = useState(0);
  const autoRan = useRef(false);
  const cards = useRef(new Map<string, HTMLDivElement>());

  useEffect(() => {
    toggleLayer("spots", true);
  }, [toggleLayer]);

  const run = useMutation({
    mutationFn: (t: string) => api.spots(t).then((r) => ({ spots: r.spots, text: t })),
    onSuccess: ({ spots, text: t }) => {
      patchDoc((d) => ({ personalize: mergeSpots(d.personalize, spots, t, useWorkspace.getState().text) }));
      setNonce((n) => n + 1);
      setActiveId(spots[0]?.id ?? null);
      toast(spots.length ? `${spots.length} generic spots to make your own.` : "No generic spots found. Your text is already specific.");
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // check the document the first time the step is opened
  useEffect(() => {
    if (autoRan.current || p || !text.trim()) return;
    autoRan.current = true;
    run.mutate(text);
  }, [p, text, run]);

  const { located, stale } = useMemo(() => (p ? locateSpots(text, p) : { located: [], stale: [] }), [p, text]);
  const staleSet = useMemo(() => new Set(stale), [stale]);

  // until the student picks one (e.g. after a reload), the first unanswered spot is open
  const openSpotId = activeId ?? located[0]?.spot.id ?? null;

  // ------------------------------------------------------------------ layers
  // computed from offsets only when (re)loaded; afterwards the decorations map through edits
  const layers = useMemo(() => {
    if (!editor || nonce < 0) return undefined;
    const cur = useWorkspace.getState();
    const ps = cur.doc?.personalize;
    if (!ps) return undefined;
    const loc = locateSpots(cur.text, ps).located;
    const spots: OffsetLayers | undefined = layersOn.spots
      ? { text: cur.text, spans: loc.map((l) => ({ start: l.start, end: l.end, id: l.spot.id, kind: "spot" as const, category: l.spot.pattern })) }
      : undefined;
    // invisible anchors on the last character of each spot's sentence: where answers go
    const anchors: OffsetLayers = {
      text: cur.text,
      spans: loc.map((l) => ({ start: Math.max(l.start, l.insertAt - 1), end: l.insertAt, id: anchorId(l.spot.id), kind: "anchor" as const })),
    };
    return { spots, anchors };
  }, [editor, nonce, layersOn.spots]);

  // ------------------------------------------------------------------ actions
  const activate = useCallback(
    (id: string | null) => {
      setActiveId(id);
      if (!id) return;
      if (editor) scrollToHighlight(editor, id);
      cards.current.get(id)?.scrollIntoView({ block: "nearest" });
    },
    [editor],
  );

  const nextOpen = useCallback(
    (after: string) => {
      const ps = useWorkspace.getState().doc?.personalize;
      if (!ps) return null;
      const open = ps.spots.filter((s) => ps.filled[s.id] == null && !ps.skipped[s.id] && s.id !== after);
      const i = ps.spots.findIndex((s) => s.id === after);
      return (open.find((s) => ps.spots.indexOf(s) > i) ?? open[0])?.id ?? null;
    },
    [],
  );

  const insert = useCallback(
    (spot: Spot, answer: string) => {
      const ps = useWorkspace.getState().doc?.personalize;
      if (!editor || !ps) return;
      const formatted = formatAnswer(answer);
      if (!formatted) return;
      let at = findHighlight(editor.state, anchorId(spot.id))?.to;
      if (at == null) {
        const cur = docText(editor.state.doc);
        const l = locateSpots(cur, ps).located.find((x) => x.spot.id === spot.id);
        if (!l) {
          toast("That sentence changed, so the answer can't be placed. Check again to refresh the spots.");
          return;
        }
        at = offsetMapper(cur).toPos(l.insertAt);
      }
      const before = editor.state.doc.textBetween(Math.max(0, at - 1), at);
      const inserted = insertionText(formatted, before);
      insertAt(editor, at, inserted, "student_insert");
      editor.commands.removeHighlight(spot.id);
      editor.commands.removeHighlight(anchorId(spot.id));
      patchDoc((d) => (d.personalize ? { personalize: { ...d.personalize, filled: { ...d.personalize.filled, [spot.id]: formatted } } } : {}));
      toast.success("Added in your words.");
      activate(nextOpen(spot.id));
    },
    [editor, patchDoc, activate, nextOpen],
  );

  const skip = useCallback(
    (spot: Spot, on: boolean) => {
      patchDoc((d) => {
        if (!d.personalize) return {};
        const skipped = { ...d.personalize.skipped };
        if (on) skipped[spot.id] = true;
        else delete skipped[spot.id];
        return { personalize: { ...d.personalize, skipped } };
      });
      if (on) {
        editor?.commands.removeHighlight(spot.id);
        editor?.commands.removeHighlight(anchorId(spot.id));
        activate(nextOpen(spot.id));
      } else {
        setNonce((n) => n + 1);
        setActiveId(spot.id);
      }
    },
    [editor, patchDoc, activate, nextOpen],
  );

  const renderHover = useCallback(
    (id: string, kind: string) => {
      if (kind !== "spot") return null;
      const s = p?.spots.find((x) => x.id === id);
      if (!s) return null;
      return (
        <div className="space-y-2">
          <p className="text-[11px] uppercase tracking-wider text-muted-foreground">{s.label}</p>
          <p>{s.prompt}</p>
          <button type="button" className="rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground" onClick={() => activate(id)}>
            Answer it
          </button>
        </div>
      );
    },
    [p, activate],
  );

  // ------------------------------------------------------------------ render
  const ownership = useMemo(() => computeOwnership(doc, text), [doc, text]);
  const found = p?.spots.length ?? 0;
  const filled = p ? filledSpots(doc, text) : 0;
  const openCount = located.length;

  return (
    <StepLayout
      toolbar={
        <>
          <h1 className="font-display text-3xl">3 · Make it yours</h1>
          <span className="ml-2 text-xs text-muted-foreground">
            {run.isPending ? (
              <span className="inline-flex items-center gap-1">
                <Loader2 className="size-3 animate-spin" /> looking for generic spots…
              </span>
            ) : p ? (
              `${found} spots · ${filled} filled`
            ) : null}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <LayerToggles available={["spots"]} />
            {p && (
              <button
                type="button"
                onClick={() => run.mutate(text)}
                disabled={run.isPending}
                className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary disabled:opacity-50"
              >
                <RefreshCw className="size-4" /> Check again
              </button>
            )}
            <button type="button" onClick={onNext} className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary">
              Prove it <ArrowRight className="size-4" />
            </button>
          </div>
        </>
      }
      main={
        <div className="space-y-3">
          <p className="text-sm text-muted-foreground">
            Dashed highlights are generic spots: vague claims, amounts with no numbers, results with no values. Answer each prompt with your own example, data or
            opinion; it&apos;s added after the sentence and counts as your writing. You can also type anywhere in the text.
          </p>
          <DocEditor layers={layers} activeId={openSpotId} renderHover={renderHover} onHighlightClick={(id, kind) => kind === "spot" && activate(id)} />
        </div>
      }
      aside={
        <>
          <Panel title="Ownership">
            <OwnershipPanel b={ownership} />
          </Panel>

          <Panel
            title="Generic spots"
            action={
              p && found > 0 ? (
                <span className="tabular text-xs text-muted-foreground">
                  {filled}/{found} filled
                </span>
              ) : null
            }
          >
            {!p ? (
              <p className="text-sm text-muted-foreground">{run.isPending ? "Checking your text…" : "Not checked yet."}</p>
            ) : found === 0 ? (
              <p className="text-sm text-muted-foreground">No generic spots found. Your text already names things, gives numbers and has your view.</p>
            ) : (
              <div className="space-y-2">
                {openCount === 0 && <p className="text-sm text-muted-foreground">All spots are answered or skipped. Nice work.</p>}
                {p.spots.map((s, i) => (
                  <SpotCard
                    key={s.id}
                    ref={(el) => {
                      if (el) cards.current.set(s.id, el);
                      else cards.current.delete(s.id);
                    }}
                    spot={s}
                    index={i}
                    active={openSpotId === s.id}
                    filled={p.filled[s.id]}
                    skipped={!!p.skipped[s.id]}
                    stale={staleSet.has(s.id)}
                    onInsert={(a) => insert(s, a)}
                    onSkip={(on) => skip(s, on)}
                    onFocus={() => openSpotId !== s.id && activate(s.id)}
                  />
                ))}
              </div>
            )}
          </Panel>
        </>
      }
    />
  );
}
