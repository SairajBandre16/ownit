"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useDebounced } from "./useDebounced";

/** Debounced /analyze of the current text. `data.text` is the text the offsets refer to. */
export function useAnalysis(text: string, targetGrade?: number, enabled = true) {
  const debounced = useDebounced(text, 900);
  return useQuery({
    queryKey: ["analyze", debounced, targetGrade],
    queryFn: async ({ signal }) => ({ text: debounced, result: await api.analyze(debounced, targetGrade, signal) }),
    enabled: enabled && debounced.trim().length > 0,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });
}
