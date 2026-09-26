"use client";

import { useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { api } from "@/lib/api";

/** All lessons, grouped (the same lessons that issues link to). */
export function LessonIndex() {
  const q = useQuery({ queryKey: ["lessons"], queryFn: ({ signal }) => api.lessons(signal), staleTime: Infinity });
  if (q.isPending) return <p className="text-muted-foreground">Loading lessons…</p>;
  if (q.error) return <p className="text-destructive">{(q.error as Error).message}</p>;
  const groups = new Map<string, typeof q.data>();
  for (const l of q.data) groups.set(l.group, [...(groups.get(l.group) ?? []), l]);
  return (
    <div className="space-y-10">
      {[...groups.entries()].map(([group, lessons]) => (
        <section key={group} aria-labelledby={`g-${group}`}>
          <h2 id={`g-${group}`} className="mb-3 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            {group}
          </h2>
          <ul className="grid gap-3 sm:grid-cols-2 lg:grid-cols-3">
            {lessons.map((l) => (
              <li key={l.slug}>
                <Link href={`/learn/${l.slug}`} className="block h-full rounded-xl border border-rule bg-card p-4 transition-colors hover:border-foreground/40">
                  <span className="font-display text-xl">{l.title}</span>
                  <span className="mt-1 block text-sm text-muted-foreground">{l.summary}</span>
                </Link>
              </li>
            ))}
          </ul>
        </section>
      ))}
    </div>
  );
}
