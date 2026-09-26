"use client";

import { useQuery, useQueryClient } from "@tanstack/react-query";
import { useState, useSyncExternalStore } from "react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { DEFAULT_API_URL, api, getApiUrl, normalizeApiUrl, setApiUrl } from "@/lib/api";
import { cn } from "@/lib/utils";

// re-render when the saved server changes (this tab or another)
const listeners = new Set<() => void>();
export function notifyServerChange() {
  listeners.forEach((l) => l());
}
function subscribe(l: () => void) {
  listeners.add(l);
  window.addEventListener("storage", l);
  return () => {
    listeners.delete(l);
    window.removeEventListener("storage", l);
  };
}
export function useApiUrl(): string {
  return useSyncExternalStore(subscribe, getApiUrl, () => DEFAULT_API_URL);
}

/** Header indicator: which OwnIt server this browser uses, whether it answers, and a way to change it. */
export function ServerStatus() {
  const url = useApiUrl();
  const client = useQueryClient();
  const [draft, setDraft] = useState("");
  const [error, setError] = useState<string | null>(null);
  const health = useQuery({
    queryKey: ["health", url],
    queryFn: () => api.health(),
    retry: false,
    refetchInterval: 60_000,
    staleTime: 30_000,
  });
  const ok = health.isSuccess;
  const state = health.isPending ? "checking" : ok ? "connected" : "offline";

  const apply = (next: string | null) => {
    setApiUrl(next);
    notifyServerChange();
    setDraft("");
    setError(null);
    void client.invalidateQueries();
  };

  return (
    <Popover>
      <PopoverTrigger
        className="inline-flex items-center gap-1.5 rounded-full border border-rule px-2.5 py-0.5 text-xs text-muted-foreground hover:text-foreground"
        aria-label={`OwnIt server: ${state}`}
      >
        <span
          className={cn("size-2 rounded-full", ok ? "bg-[var(--own-insert)]" : health.isPending ? "bg-muted-foreground/50" : "bg-destructive")}
          aria-hidden
        />
        <span className="hidden sm:inline">Server</span>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80">
        <p className="font-medium">OwnIt server</p>
        <p className="tabular break-all text-xs text-muted-foreground">{url}</p>
        <p className="text-sm">
          {health.isPending
            ? "Checking…"
            : ok
              ? `Connected${health.data.languagetool ? "" : " · grammar check off"}.`
              : "Not reachable. Start it on the computer that hosts it, or use another address."}
        </p>
        <form
          className="flex gap-2"
          onSubmit={(e) => {
            e.preventDefault();
            const n = normalizeApiUrl(draft);
            if (!n) setError("Use an https:// address (or http://localhost).");
            else apply(n);
          }}
        >
          <input
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            placeholder="https://….trycloudflare.com"
            aria-label="Server address"
            className="min-w-0 flex-1 rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <button type="submit" className="rounded-md bg-primary px-3 py-1 text-sm font-medium text-primary-foreground">
            Use
          </button>
        </form>
        {error && <p className="text-xs text-destructive">{error}</p>}
        {url !== DEFAULT_API_URL && (
          <button type="button" onClick={() => apply(null)} className="self-start text-xs underline underline-offset-2">
            Back to the default server
          </button>
        )}
        <p className="text-xs text-muted-foreground">Your text is sent to this server for processing and isn&apos;t stored there.</p>
      </PopoverContent>
    </Popover>
  );
}
