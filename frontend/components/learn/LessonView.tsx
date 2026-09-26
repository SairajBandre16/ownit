"use client";

import { useQuery } from "@tanstack/react-query";
import { ArrowLeft } from "lucide-react";
import Link from "next/link";
import { api } from "@/lib/api";
import { Markdown } from "@/lib/markdown";

export function LessonView({ slug }: { slug: string }) {
  const q = useQuery({ queryKey: ["lesson", slug], queryFn: ({ signal }) => api.lesson(slug, signal), staleTime: Infinity, retry: false });
  return (
    <article className="mx-auto max-w-2xl">
      <Link href="/learn" className="inline-flex items-center gap-1 text-sm text-muted-foreground hover:text-foreground">
        <ArrowLeft className="size-4" /> All lessons
      </Link>
      {q.isPending ? (
        <p className="mt-8 text-muted-foreground">Loading…</p>
      ) : q.error ? (
        <p className="mt-8 text-destructive">{(q.error as Error).message}</p>
      ) : (
        <>
          <p className="mt-6 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{q.data.group}</p>
          <h1 className="mt-1 font-display text-5xl leading-tight">{q.data.title}</h1>
          <p className="mt-3 text-lg text-muted-foreground">{q.data.summary}</p>
          <div className="mt-8">
            <Markdown source={q.data.markdown} />
          </div>
        </>
      )}
    </article>
  );
}
