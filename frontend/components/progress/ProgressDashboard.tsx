"use client";

import Link from "next/link";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { summarizeViva } from "@/lib/assess";
import { listDocs } from "@/lib/db";
import { loadCards, loadReviews } from "@/lib/deck";
import { computeGate } from "@/lib/gate";
import { jsonText } from "@/lib/offsets";
import { type Card, DAY, type Review, dueCards, localDay, streak } from "@/lib/srs";
import { useSettings } from "@/lib/store";
import type { OwnDoc } from "@/lib/types";

// one series per chart; #0284c7 passes the palette checks on both the light and dark surfaces
const SERIES = "var(--chart-2)";
const TOOLTIP_STYLE = { background: "var(--popover)", border: "1px solid var(--rule)", borderRadius: 8, fontSize: 12, color: "var(--popover-foreground)" };
const AXIS_TICK = { fontSize: 11, fill: "var(--muted-foreground)" };

const fmtDate = (t: number) => new Date(t).toLocaleDateString(undefined, { day: "numeric", month: "short" });
const words = (d: OwnDoc) => jsonText(d.content).split(/\s+/).filter(Boolean).length;
const n = (x: number | null | undefined) => (x == null ? "—" : Math.round(x).toString());

export function ProgressDashboard() {
  const settings = useSettings();
  const [docs, setDocs] = useState<OwnDoc[] | null>(null);
  const [cards, setCards] = useState<Card[]>([]);
  const [reviews, setReviews] = useState<Review[]>([]);
  const [now] = useState(() => Date.now());

  useEffect(() => {
    void Promise.all([listDocs(), loadCards(), loadReviews()]).then(([d, c, r]) => {
      setDocs(d);
      setCards(c);
      setReviews(r);
    });
  }, []);

  const vivaSeries = useMemo(
    () =>
      (docs ?? [])
        .flatMap((d) => (d.assess?.vivaHistory ?? []).map((h) => ({ t: h.finishedAt, average: h.average, doc: d.title })))
        .sort((a, b) => a.t - b.t)
        .map((p) => ({ ...p, label: fmtDate(p.t) })),
    [docs],
  );

  const reviewSeries = useMemo(() => {
    const today = localDay(now);
    const counts = new Map<number, number>();
    for (const r of reviews) counts.set(localDay(r.at), (counts.get(localDay(r.at)) ?? 0) + 1);
    return Array.from({ length: 14 }, (_, i) => {
      const day = today - 13 + i;
      return { label: fmtDate(now - (13 - i) * DAY), reviews: counts.get(day) ?? 0 };
    });
  }, [reviews, now]);

  if (docs === null) return <p className="text-muted-foreground">Loading your progress…</p>;
  if (!docs.length)
    return (
      <p className="rounded-xl border border-dashed border-rule p-8 text-center text-muted-foreground">
        No documents yet. <Link href="/workspace" className="text-signal-ink underline">Start one in the workspace</Link>.
      </p>
    );

  const owned = docs.filter((d) => d.ownership);
  const avgOwnership = owned.length ? owned.reduce((s, d) => s + (d.ownership?.score ?? 0), 0) / owned.length : null;
  const sessions = docs.reduce((s, d) => s + (d.assess?.vivaHistory?.length ?? 0), 0);
  const passed = docs.filter((d) => {
    const g = computeGate(d, settings);
    return g.quizOk && g.teachbackOk && g.walkthroughOk;
  }).length;

  const tiles: [string, string][] = [
    ["Documents", String(docs.length)],
    ["Avg ownership", n(avgOwnership)],
    ["Checks passed", `${passed}/${docs.length}`],
    ["Viva sessions", String(sessions)],
    ["Cards due", String(dueCards(cards, now).length)],
    ["Review streak", `${streak(reviews, now)} d`],
  ];

  return (
    <div className="space-y-10">
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {tiles.map(([label, value]) => (
          <div key={label} className="rounded-xl border border-rule bg-card p-4">
            <p className="tabular text-3xl leading-none">{value}</p>
            <p className="mt-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">{label}</p>
          </div>
        ))}
      </div>

      <section aria-labelledby="docs-h">
        <h2 id="docs-h" className="mb-3 font-display text-3xl">
          Documents
        </h2>
        <div className="overflow-x-auto rounded-xl border border-rule bg-card">
          <table className="w-full min-w-[44rem] text-sm">
            <thead className="text-left text-[11px] uppercase tracking-wider text-muted-foreground">
              <tr className="border-b border-rule">
                <th className="px-4 py-2 font-normal">Document</th>
                <th className="px-3 py-2 text-right font-normal">Words</th>
                <th className="px-3 py-2 text-right font-normal">Writing score</th>
                <th className="px-3 py-2 text-right font-normal">Ownership</th>
                <th className="px-3 py-2 text-right font-normal">Quiz</th>
                <th className="px-3 py-2 text-right font-normal">Teach-back</th>
                <th className="px-3 py-2 text-right font-normal">Viva avg</th>
                <th className="px-3 py-2 font-normal">Status</th>
              </tr>
            </thead>
            <tbody className="tabular">
              {docs.map((d) => {
                const viva = d.assess?.viva ? summarizeViva(d.assess.viva.turns) : null;
                const gate = computeGate(d, settings);
                const first = d.firstScore;
                const latest = d.analysis?.score;
                return (
                  <tr key={d.id} className="border-b border-rule last:border-0">
                    <td className="px-4 py-2 font-sans">
                      <Link href={`/workspace/${d.id}`} className="hover:underline">
                        {d.title}
                      </Link>
                      <span className="block text-xs text-muted-foreground">updated {fmtDate(d.updatedAt)}</span>
                    </td>
                    <td className="px-3 py-2 text-right">{words(d).toLocaleString()}</td>
                    <td className="px-3 py-2 text-right">
                      {first != null && latest != null && Math.round(first) !== Math.round(latest) ? `${n(first)} → ${n(latest)}` : n(latest ?? first)}
                    </td>
                    <td className="px-3 py-2 text-right">{n(d.ownership?.score)}</td>
                    <td className="px-3 py-2 text-right">{d.assess?.quiz?.total != null ? `${n(d.assess.quiz.total)}%` : "—"}</td>
                    <td className="px-3 py-2 text-right">{d.assess?.teachback ? `${n(d.assess.teachback.coverage)}%` : "—"}</td>
                    <td className="px-3 py-2 text-right">{viva && viva.answered ? n(viva.average) : "—"}</td>
                    <td className="px-3 py-2 font-sans text-xs">
                      {d.exports?.length ? "exported" : gate.passed ? "ready to export" : `step ${["humanize", "walkthrough", "personalize", "prove", "export"].indexOf(d.step) + 1} of 5`}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <ChartCard
          title="Viva practice"
          subtitle="Average score of each finished session"
          empty={vivaSeries.length === 0 ? "No finished viva sessions yet." : null}
          table={vivaSeries.map((p) => [`${p.label} · ${p.doc}`, String(p.average)])}
        >
          <LineChart data={vivaSeries} margin={{ top: 8, right: 12, bottom: 0, left: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--rule)" strokeOpacity={0.6} />
            <XAxis dataKey="label" tick={AXIS_TICK} axisLine={{ stroke: "var(--rule)" }} tickLine={false} />
            <YAxis domain={[0, 100]} ticks={[0, 40, 70, 100]} tick={AXIS_TICK} width={32} axisLine={false} tickLine={false} />
            <Tooltip
              contentStyle={TOOLTIP_STYLE}
              cursor={{ stroke: "var(--muted-foreground)", strokeDasharray: "3 3" }}
              formatter={(v) => [`${v}`, "Average score"]}
              labelFormatter={(_, p) => (p?.[0] ? `${p[0].payload.label} · ${p[0].payload.doc}` : "")}
            />
            <Line type="monotone" dataKey="average" stroke={SERIES} strokeWidth={2} dot={{ r: 4, strokeWidth: 2, stroke: "var(--card)", fill: SERIES }} activeDot={{ r: 5 }} isAnimationActive={false} />
          </LineChart>
        </ChartCard>

        <ChartCard
          title="Revision Deck"
          subtitle="Cards reviewed per day, last 14 days"
          empty={reviews.length === 0 ? "No reviews yet: open the Deck." : null}
          table={reviewSeries.map((p) => [p.label, String(p.reviews)])}
        >
          <BarChart data={reviewSeries} margin={{ top: 8, right: 12, bottom: 0, left: 0 }} barCategoryGap={2}>
            <CartesianGrid vertical={false} stroke="var(--rule)" strokeOpacity={0.6} />
            <XAxis dataKey="label" tick={AXIS_TICK} interval={3} axisLine={{ stroke: "var(--rule)" }} tickLine={false} />
            <YAxis allowDecimals={false} tick={AXIS_TICK} width={32} axisLine={false} tickLine={false} />
            <Tooltip contentStyle={TOOLTIP_STYLE} cursor={{ fill: "var(--secondary)" }} formatter={(v) => [`${v}`, "Reviews"]} />
            <Bar dataKey="reviews" fill={SERIES} radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ChartCard>
      </div>
    </div>
  );
}

function ChartCard({
  title,
  subtitle,
  empty,
  table,
  children,
}: {
  title: string;
  subtitle: string;
  empty: string | null;
  table: [string, string][];
  children: React.ReactElement;
}) {
  return (
    <figure className="rounded-xl border border-rule bg-card p-4">
      <figcaption>
        <p className="font-display text-2xl">{title}</p>
        <p className="text-xs text-muted-foreground">{subtitle}</p>
      </figcaption>
      {empty ? (
        <p className="py-12 text-center text-sm text-muted-foreground">{empty}</p>
      ) : (
        <>
          <div className="mt-3 h-56" aria-hidden>
            <ResponsiveContainer width="100%" height="100%">
              {children}
            </ResponsiveContainer>
          </div>
          <details className="mt-2 text-xs text-muted-foreground">
            <summary className="cursor-pointer">Show as a table</summary>
            <table className="tabular mt-2 w-full">
              <tbody>
                {table.map(([k, v], i) => (
                  <tr key={i} className="border-t border-rule">
                    <td className="py-1">{k}</td>
                    <td className="py-1 text-right text-foreground">{v}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </details>
        </>
      )}
    </figure>
  );
}
