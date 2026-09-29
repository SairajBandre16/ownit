"use client";

import { useQueryClient } from "@tanstack/react-query";
import { Loader2, RotateCw, ServerOff } from "lucide-react";
import { useEffect, useRef } from "react";
import { ServerAddressForm, useServerHealth } from "./ServerStatus";

const LOCAL = /^https?:\/\/(localhost|127\.0\.0\.1|\[::1\])(:\d+)?$/;

/**
 * Shown in place of silent failures when the OwnIt server can't be reached: says what still
 * works (documents are in this browser), what doesn't, and how to get connected again.
 */
export function ServerOfflineBanner({ className }: { className?: string }) {
  const { url, health, offline } = useServerHealth();
  const client = useQueryClient();
  const wasOffline = useRef(false);
  // back online: re-run the requests that failed while the server was away. Only settled
  // results count: a retry passes through "pending" on its way from error to success.
  useEffect(() => {
    if (health.isError) wasOffline.current = true;
    else if (health.isSuccess && wasOffline.current) {
      wasOffline.current = false;
      void client.invalidateQueries({ predicate: (q) => q.queryKey[0] !== "health" });
    }
  }, [health.isError, health.isSuccess, client]);
  if (!offline) return null;
  const local = LOCAL.test(url);
  return (
    <section
      role="alert"
      aria-labelledby="server-offline-title"
      className={`rounded-xl border border-destructive/40 bg-destructive/5 p-4 ${className ?? ""}`}
    >
      <div className="flex flex-wrap items-start gap-3">
        <ServerOff className="mt-0.5 size-5 shrink-0 text-destructive" aria-hidden />
        <div className="min-w-0 flex-1 space-y-1.5">
          <h2 id="server-offline-title" className="font-sans text-sm font-semibold tracking-normal">
            Can&apos;t reach the OwnIt server
          </h2>
          <p className="text-sm text-muted-foreground">
            Your documents are safe in this browser. Scores, rewrites and quizzes need the server at{" "}
            <span className="tabular break-all text-foreground">{url}</span>.
          </p>
          <p className="text-sm text-muted-foreground">
            {local ? (
              <>
                Start it on this computer with <code className="tabular text-foreground">scripts\dev.ps1</code> (or{" "}
                <code className="tabular text-foreground">docker compose up</code>), then retry.
              </>
            ) : (
              "The computer that shares it may be off, or the link has changed. Ask for a new link and paste it below."
            )}
          </p>
          <ServerAddressForm url={url} className="max-w-md pt-1" />
        </div>
        <button
          type="button"
          onClick={() => void health.refetch()}
          disabled={health.isFetching}
          className="inline-flex shrink-0 items-center gap-1.5 rounded-md border border-rule bg-background px-3 py-1.5 text-sm hover:bg-secondary disabled:opacity-60"
        >
          {health.isFetching ? <Loader2 className="size-4 animate-spin" /> : <RotateCw className="size-4" />}
          Retry
        </button>
      </div>
    </section>
  );
}
