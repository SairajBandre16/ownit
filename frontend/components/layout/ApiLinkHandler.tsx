"use client";

import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { getApiUrl, normalizeApiUrl, setApiUrl } from "@/lib/api";
import { notifyServerChange } from "./ServerStatus";

/**
 * Handles share links like https://ownit.vercel.app/?api=https://xyz.trycloudflare.com
 * (printed by scripts/share.ps1). The visitor confirms before the address is used, because
 * whoever runs that server receives the text they send.
 */
export function ApiLinkHandler() {
  const [proposed, setProposed] = useState<string | null>(null);
  const client = useQueryClient();

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const raw = params.get("api");
    if (raw == null) return;
    // take the parameter out of the address bar either way
    params.delete("api");
    const qs = params.toString();
    window.history.replaceState(null, "", window.location.pathname + (qs ? `?${qs}` : "") + window.location.hash);
    const url = normalizeApiUrl(raw);
    // eslint-disable-next-line react-hooks/set-state-in-effect -- reading the address bar once on load
    if (url && url !== getApiUrl()) setProposed(url);
  }, []);

  const decide = (accept: boolean) => {
    if (accept && proposed) {
      setApiUrl(proposed);
      notifyServerChange();
      void client.invalidateQueries();
    }
    setProposed(null);
  };

  return (
    <Dialog open={proposed != null} onOpenChange={(o) => !o && decide(false)}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Use this OwnIt server?</DialogTitle>
          <DialogDescription>
            This link asks OwnIt to send your text to <span className="tabular break-all font-medium text-foreground">{proposed}</span> for
            processing. Only connect if you trust the person who shared it. You can change it later from “Server” in the top bar.
          </DialogDescription>
        </DialogHeader>
        <DialogFooter>
          <button type="button" onClick={() => decide(false)} className="rounded-md border border-rule px-4 py-2 text-sm hover:bg-secondary">
            Keep the current server
          </button>
          <button type="button" onClick={() => decide(true)} className="rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground">
            Connect
          </button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
