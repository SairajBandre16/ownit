"use client";

import { useMutation } from "@tanstack/react-query";
import { ArrowRight, Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { IssueCard, IssueList } from "@/components/analysis/IssueList";
import { ScoreGauge } from "@/components/analysis/ScoreGauge";
import { SentenceRhythmChart } from "@/components/analysis/SentenceRhythmChart";
import { SubScoreBars } from "@/components/analysis/SubScoreBars";
import { DiffView } from "@/components/diff/DiffView";
import { DocEditor } from "@/components/editor/DocEditor";
import type { OffsetLayers, OffsetSpan } from "@/components/editor/Editor";
import { LayerToggles } from "@/components/steps/LayerToggles";
import { useAnalysis } from "@/hooks/useAnalysis";
import { useDoctor } from "@/hooks/useDoctor";
import { useStyleProfile } from "@/hooks/useStyleProfile";
import { api, type Issue } from "@/lib/api";
import { decisionStats, displayPair, locatePending } from "@/lib/changes";
import { replaceHighlight, scrollToHighlight } from "@/lib/editing";
import { useWorkspace } from "@/lib/store";
import type { Decision, DocSettings, HumanizeState } from "@/lib/types";
import { VoicePanel } from "@/components/voice/VoicePanel";
import { DoctorPanel } from "@/components/analysis/DoctorPanel";
import { HumanizeControls } from "./HumanizeControls";

type ReviewTab = "changes" | "suggestions" | "doctor";
import { Panel, StepLayout } from "./StepLayout";

export function HumanizeStep({ onNext }: { onNext: () => void }) {
  const doc = useWorkspace((s) => s.doc)!;
  const text = useWorkspace((s) => s.text);
  const editor = useWorkspace((s) => s.editor);
  const layersOn = useWorkspace((s) => s.layers);
  const activeIssueId = useWorkspace((s) => s.activeIssueId);
  const setActiveIssue = useWorkspace((s) => s.setActiveIssue);
  const activeChangeId = useWorkspace((s) => s.activeChangeId);
  const setActiveChange = useWorkspace((s) => s.setActiveChange);
  const patchDoc = useWorkspace((s) => s.patchDoc);
  const { stored: voice } = useStyleProfile();
  const [tab, setTab] = useState<ReviewTab>(doc.humanize ? "changes" : "suggestions");
  // bumps when the pending-change layer must be recomputed from offsets (new result, reload)
  const [changesNonce, setChangesNonce] = useState(0);

  const analysis = useAnalysis(text, doc.settings.targetGrade);
  const doctor = useDoctor(text);
  const doctorResult = doctor.data?.result;
  const doctorText = doctor.data?.text ?? "";
  const result = analysis.data?.result;
  const analyzedText = analysis.data?.text ?? "";

  useEffect(() => {
    if (!result) return;
    patchDoc((d) => ({ analysis: result, firstScore: d.firstScore ?? result.score }));
  }, [result, patchDoc]);

  useEffect(() => {
    if (analysis.error) toast.error((analysis.error as Error).message, { id: "analyze-error" });
  }, [analysis.error]);

  const h = doc.humanize;
  const setSettings = (p: Partial<DocSettings>) => patchDoc((d) => ({ settings: { ...d.settings, ...p } }));

  // ------------------------------------------------------------------ humanize request
  const run = useMutation({
    mutationFn: () =>
      api.humanize({
        text,
        tone: doc.settings.tone,
        intensity: doc.settings.intensity,
        keep_terms: doc.settings.keepTerms,
        style_profile: doc.settings.useVoice && voice ? voice.profile : null,
      }),
    onSuccess: (res) => {
      const state: HumanizeState = {
        baseText: text,
        resultText: res.text,
        changes: res.changes,
        protected: res.protected,
        scoreBefore: res.score_before,
        scoreAfter: res.score_after,
        voiceMatch: res.voice_match ?? null,
        voiceMatchBefore: res.voice_match_before ?? null,
        decisions: {},
      };
      patchDoc((d) => ({
        humanize: state,
        // decisions from earlier runs still count as decisions made (ownership score)
        decisionHistory: {
          offered: (d.decisionHistory?.offered ?? 0) + (d.humanize?.changes.length ?? 0),
          decided: (d.decisionHistory?.decided ?? 0) + Object.keys(d.humanize?.decisions ?? {}).length,
        },
      }));
      setTab("changes");
      setChangesNonce((n) => n + 1);
      setActiveChange(res.changes[0]?.id ?? null);
      toast.success(
        res.changes.length
          ? `${res.changes.length} suggested changes. Review each one.`
          : "No change passed the checks, so your text is kept as it is.",
      );
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // ------------------------------------------------------------------ layers
  const analysisLayer: OffsetLayers | undefined = useMemo(() => {
    if (!result) return undefined;
    const spans: OffsetSpan[] = [];
    for (const sec of result.sections)
      if (sec.heading) spans.push({ start: sec.start, end: sec.start + sec.heading.length, id: `h-${sec.start}`, kind: "heading" });
    if (layersOn.protected)
      for (const p of result.protected) spans.push({ start: p.start, end: p.end, id: `p-${p.start}`, kind: "protected", label: p.kind });
    if (layersOn.issues && tab === "suggestions")
      for (const i of result.issues)
        spans.push({ start: i.start, end: i.end, id: i.id, kind: "issue", category: i.category, rule: i.rule });
    return { text: analyzedText, spans };
  }, [result, analyzedText, layersOn, tab]);

  const stale = useMemo(() => new Set(h ? locatePending(text, h).stale : []), [h, text]);

  // pending changes as decorations: computed from offsets only on (re)load, then mapped
  const changesLayer: OffsetLayers | undefined = useMemo(() => {
    if (!editor || changesNonce < 0) return undefined; // (re)computed when the editor mounts
    const cur = useWorkspace.getState();
    const hs = cur.doc?.humanize;
    if (!hs || !layersOn.changes) return undefined;
    const loc = locatePending(cur.text, hs);
    return {
      text: cur.text,
      spans: loc.located.map((l) => ({
        start: l.start,
        end: l.end,
        id: l.change.id,
        kind: "change" as const,
        category: l.change.category,
      })),
    };
  }, [editor, changesNonce, layersOn.changes]);

  // Report Doctor issues: shown on the Doctor tab, or everywhere when its layer is switched on
  const doctorLayer: OffsetLayers | undefined = useMemo(() => {
    if (!doctorResult || !(layersOn.engineering || tab === "doctor")) return undefined;
    return {
      text: doctorText,
      spans: doctorResult.issues.map((i) => ({ start: i.start, end: i.end, id: i.id, kind: "engineering" as const, category: "engineering", rule: i.rule })),
    };
  }, [doctorResult, doctorText, layersOn.engineering, tab]);

  const layers = useMemo(
    () => ({ analysis: analysisLayer, changes: changesLayer, doctor: doctorLayer }),
    [analysisLayer, changesLayer, doctorLayer],
  );

  // ------------------------------------------------------------------ decisions
  const decide = useCallback(
    (id: string, d: Decision | null) => {
      const cur = useWorkspace.getState().doc?.humanize;
      if (!cur || !editor) return;
      const change = cur.changes.find((c) => c.id === id);
      if (!change) return;
      if (d === "accepted") {
        if (!replaceHighlight(editor, id, change.replacement, "engine")) {
          toast("That text changed after the suggestion was made, so it can't be applied.");
          return;
        }
        editor.commands.removeHighlight(id, "changes");
      } else if (d === "rejected") {
        editor.commands.removeHighlight(id, "changes");
      }
      const decisions = { ...cur.decisions };
      if (d) decisions[id] = d;
      else delete decisions[id];
      patchDoc({ humanize: { ...cur, decisions } });
      if (d === null) setChangesNonce((n) => n + 1);
    },
    [editor, patchDoc],
  );

  const bulk = useCallback(
    (ids: string[], d: Decision) => {
      const cur = useWorkspace.getState().doc?.humanize;
      if (!cur || !editor) return;
      const decisions = { ...cur.decisions };
      let failed = 0;
      for (const id of ids) {
        const change = cur.changes.find((c) => c.id === id);
        if (!change) continue;
        if (d === "accepted") {
          if (!replaceHighlight(editor, id, change.replacement, "engine")) {
            failed++;
            continue;
          }
        }
        editor.commands.removeHighlight(id, "changes");
        decisions[id] = d;
      }
      patchDoc({ humanize: { ...cur, decisions } });
      if (failed) toast(`${failed} change(s) couldn't be applied because the text was edited.`);
    },
    [editor, patchDoc],
  );

  const applyIssue = useCallback(
    (issue: Issue) => {
      if (!editor || issue.suggestion == null) return;
      if (!replaceHighlight(editor, issue.id, issue.suggestion, "engine")) toast("That text has changed since the analysis.");
      setActiveIssue(null);
    },
    [editor, setActiveIssue],
  );

  const activate = useCallback(
    (id: string | null) => {
      setActiveChange(id);
      if (id && editor) scrollToHighlight(editor, id);
    },
    [editor, setActiveChange],
  );

  // ------------------------------------------------------------------ hover cards
  const issuesById = useMemo(() => new Map((result?.issues ?? []).map((i) => [i.id, i])), [result]);
  const doctorById = useMemo(() => new Map((doctorResult?.issues ?? []).map((i) => [i.id, i])), [doctorResult]);
  const renderHover = useCallback(
    (id: string, kind: string) => {
      if (kind === "protected") {
        const p = result?.protected.find((x) => `p-${x.start}` === id);
        return p ? (
          <p>
            <span className="tabular text-xs uppercase tracking-wider text-muted-foreground">Protected · {p.kind}</span>
            <br />
            The rewriter never changes this text.
          </p>
        ) : null;
      }
      if (kind === "change") {
        const c = h?.changes.find((x) => x.id === id);
        if (!c) return null;
        const { from, to } = displayPair(c);
        return (
          <div className="space-y-2">
            <p className="tabular text-xs">
              <del className="text-destructive">{from}</del> → <ins className="no-underline">{to || "(removed)"}</ins>
            </p>
            <p className="text-muted-foreground">{c.reason}</p>
            <div className="flex gap-2">
              <button type="button" className="rounded-md bg-primary px-2 py-1 text-xs font-medium text-primary-foreground" onClick={() => decide(id, "accepted")}>
                Accept
              </button>
              <button type="button" className="rounded-md border border-rule px-2 py-1 text-xs" onClick={() => decide(id, "rejected")}>
                Reject
              </button>
            </div>
          </div>
        );
      }
      const issue = issuesById.get(id);
      if (kind === "engineering") {
        const d = doctorById.get(id);
        return d ? <IssueCard issue={d} text={doctorText} onApply={applyIssue} /> : null;
      }
      return issue ? <IssueCard issue={issue} text={analyzedText} onApply={applyIssue} /> : null;
    },
    [issuesById, analyzedText, applyIssue, result, h, decide, doctorById, doctorText],
  );

  const stats = decisionStats(h);

  return (
    <StepLayout
      toolbar={
        <>
          <h1 className="font-display text-3xl">1 · Humanize</h1>
          <span className="ml-2 text-xs text-muted-foreground">
            {analysis.isFetching ? (
              <span className="inline-flex items-center gap-1">
                <Loader2 className="size-3 animate-spin" /> analysing…
              </span>
            ) : result ? (
              `${result.stats.words} words · ${result.issues.length} suggestions`
            ) : null}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <LayerToggles available={["issues", "protected", "changes", "engineering"]} />
            <button type="button" onClick={onNext} className="inline-flex items-center gap-1 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary">
              Walkthrough <ArrowRight className="size-4" />
            </button>
          </div>
        </>
      }
      main={
        <DocEditor
          layers={layers}
          activeId={tab === "changes" ? activeChangeId : activeIssueId}
          renderHover={renderHover}
          onHighlightClick={(id, kind) => (kind === "change" ? setActiveChange(id) : (kind === "issue" || kind === "engineering") && setActiveIssue(id))}
        />
      }
      aside={
        <>
          <Panel title="Writing score">
            <ScoreGauge
              value={result?.score ?? null}
              from={h ? h.scoreBefore : doc.firstScore}
              caption={
                h && stats.decided < stats.offered
                  ? `${Math.round(h.scoreAfter)} if you accept every change`
                  : result && !result.languagetool
                    ? "Grammar check offline"
                    : undefined
              }
            />
            {result && (
              <div className="mt-4">
                <SubScoreBars analysis={result} />
              </div>
            )}
          </Panel>

          <Panel title="Your voice">
            <VoicePanel text={text} before={h?.voiceMatchBefore} />
          </Panel>

          <Panel title="Rewrite">
            <HumanizeControls settings={doc.settings} onChange={setSettings} onRun={() => run.mutate()} running={run.isPending} hasProfile={!!voice} />
          </Panel>

          <section className="rounded-xl border border-rule bg-card p-4">
            <div className="mb-3 flex gap-1 rounded-lg bg-secondary p-1 text-xs" role="tablist" aria-label="Review">
              {(["changes", "suggestions", "doctor"] as const).map((t) => (
                <button
                  key={t}
                  role="tab"
                  aria-selected={tab === t}
                  type="button"
                  onClick={() => setTab(t)}
                  className={`flex-1 rounded-md px-2 py-1 ${tab === t ? "bg-background shadow-sm" : "text-muted-foreground"}`}
                >
                  {t === "changes"
                    ? `Changes${h ? ` (${stats.offered - stats.decided})` : ""}`
                    : t === "suggestions"
                      ? `Suggestions${result ? ` (${result.issues.length})` : ""}`
                      : `Doctor${doctorResult ? ` (${doctorResult.issues.length})` : ""}`}
                </button>
              ))}
            </div>
            {tab === "changes" ? (
              h ? (
                <DiffView changes={h.changes} decisions={h.decisions} stale={stale} activeId={activeChangeId} onActivate={activate} onDecide={decide} onBulk={bulk} />
              ) : (
                <p className="text-sm text-muted-foreground">Press “Suggest rewrites” to get changes you can accept or reject one by one.</p>
              )
            ) : tab === "doctor" ? (
              <DoctorPanel
                result={doctorResult}
                loading={doctor.isFetching}
                text={doctorText}
                activeId={activeIssueId}
                onSelect={(id) => {
                  setActiveIssue(activeIssueId === id ? null : id);
                  if (editor) scrollToHighlight(editor, id);
                }}
                onApply={applyIssue}
              />
            ) : result ? (
              <IssueList
                issues={result.issues}
                activeId={activeIssueId}
                onSelect={(id) => {
                  setActiveIssue(activeIssueId === id ? null : id);
                  if (editor) scrollToHighlight(editor, id);
                }}
                text={analyzedText}
                onApply={applyIssue}
              />
            ) : null}
          </section>

          {result && (
            <Panel title="Sentence rhythm">
              <SentenceRhythmChart lengths={result.stats.sentence_lengths} />
            </Panel>
          )}
        </>
      }
    />
  );
}
