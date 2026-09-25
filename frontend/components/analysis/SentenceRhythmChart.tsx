"use client";

import { Bar, BarChart, Cell, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export function SentenceRhythmChart({ lengths, compare }: { lengths: number[]; compare?: number[] | null }) {
  if (!lengths.length) return null;
  const data = lengths.map((n, i) => ({ i: i + 1, n, before: compare?.[i] }));
  const mean = lengths.reduce((a, b) => a + b, 0) / lengths.length;
  const sd = Math.sqrt(lengths.reduce((a, b) => a + (b - mean) ** 2, 0) / lengths.length);
  return (
    <figure>
      <div className="h-32 w-full" aria-hidden>
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <XAxis dataKey="i" tick={false} axisLine={{ stroke: "var(--rule)" }} />
            <YAxis tick={{ fontSize: 10, fill: "var(--muted-foreground)" }} width={24} axisLine={false} tickLine={false} />
            <Tooltip
              cursor={{ fill: "var(--secondary)" }}
              contentStyle={{ background: "var(--popover)", border: "1px solid var(--rule)", borderRadius: 8, fontSize: 12 }}
              formatter={(v) => [`${v} words`, "Sentence"]}
              labelFormatter={(l) => `Sentence ${l}`}
            />
            <ReferenceLine y={30} stroke="var(--hl-clarity)" strokeDasharray="3 3" />
            <Bar dataKey="n" radius={[2, 2, 0, 0]}>
              {data.map((d) => (
                <Cell key={d.i} fill={d.n > 30 ? "var(--hl-clarity)" : "var(--hl-rhythm)"} />
              ))}
            </Bar>
          </BarChart>
        </ResponsiveContainer>
      </div>
      <figcaption className="tabular mt-1 flex justify-between text-[11px] text-muted-foreground">
        <span>{lengths.length} sentences</span>
        <span>
          mean {mean.toFixed(1)} · SD {sd.toFixed(1)}
        </span>
      </figcaption>
      <p className="sr-only">
        Sentence lengths in words: {lengths.join(", ")}. Mean {mean.toFixed(1)}, standard deviation {sd.toFixed(1)}.
      </p>
    </figure>
  );
}
