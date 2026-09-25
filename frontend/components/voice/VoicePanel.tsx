"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import Link from "next/link";
import { useDebounced } from "@/hooks/useDebounced";
import { useStyleProfile } from "@/hooks/useStyleProfile";
import { api } from "@/lib/api";
import { countWords } from "@/lib/docs";
import { VoiceMatchMeter } from "./VoiceMatchMeter";

/** Live Voice Match of the current text against the student's fingerprint (U1). */
export function VoicePanel({ text, before }: { text: string; before?: number | null }) {
  const { stored, loading } = useStyleProfile();
  const debounced = useDebounced(text, 1200);
  const q = useQuery({
    queryKey: ["voice", debounced, stored?.createdAt],
    queryFn: ({ signal }) => api.compareStyle(debounced, stored!.profile, signal),
    enabled: !!stored && debounced.trim().length > 0,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });
  if (loading) return null;
  if (!stored)
    return (
      <p className="text-sm text-muted-foreground">
        Build your <Link href="/voice" className="text-signal-ink underline">Voice Fingerprint</Link> to see how close this draft is to the way you write.
      </p>
    );
  if (!q.data) return <p className="text-sm text-muted-foreground">Measuring…</p>;
  return (
    <div>
      <VoiceMatchMeter value={q.data.voice_match} before={before} words={countWords(debounced)} />
      {q.data.differences.length > 0 && (
        <ul className="mt-3 space-y-1 text-sm text-muted-foreground">
          {q.data.differences.map((d) => (
            <li key={d.feature}>→ {d.message}</li>
          ))}
        </ul>
      )}
    </div>
  );
}
