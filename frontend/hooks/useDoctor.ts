"use client";

import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { api } from "@/lib/api";
import { useDebounced } from "./useDebounced";

/** Debounced Engineering Report Doctor run. `data.text` is the text the offsets refer to. */
export function useDoctor(text: string, enabled = true) {
  const debounced = useDebounced(text, 1200);
  return useQuery({
    queryKey: ["doctor", debounced],
    queryFn: async ({ signal }) => ({ text: debounced, result: await api.doctor(debounced, signal) }),
    enabled: enabled && debounced.trim().length > 0,
    placeholderData: keepPreviousData,
    staleTime: Infinity,
  });
}
