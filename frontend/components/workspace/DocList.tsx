"use client";

import { FileText, Plus, Trash2 } from "lucide-react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { deleteDoc, listDocs } from "@/lib/db";
import { STEPS, type OwnDoc } from "@/lib/types";
import { NewDocDialog } from "./NewDocDialog";

function timeAgo(ts: number) {
  const s = Math.round((Date.now() - ts) / 1000);
  if (s < 60) return "just now";
  if (s < 3600) return `${Math.round(s / 60)} min ago`;
  if (s < 86400) return `${Math.round(s / 3600)} h ago`;
  return new Date(ts).toLocaleDateString();
}

export function DocList() {
  const [docs, setDocs] = useState<OwnDoc[] | null>(null);
  const [open, setOpen] = useState(false);
  const router = useRouter();

  useEffect(() => {
    listDocs().then(setDocs);
  }, []);

  const remove = async (id: string) => {
    if (!confirm("Delete this document from this device? This can't be undone.")) return;
    await deleteDoc(id);
    setDocs(await listDocs());
  };

  return (
    <div>
      <div className="flex flex-wrap items-end justify-between gap-4 border-b border-rule pb-6">
        <div>
          <p className="tabular text-xs uppercase tracking-[0.2em] text-muted-foreground">Workspace</p>
          <h1 className="font-display text-5xl">Your documents</h1>
          <p className="mt-2 max-w-xl text-muted-foreground">
            Stored only in this browser. Start by pasting a draft or uploading a .docx / .pdf.
          </p>
        </div>
        <button
          type="button"
          onClick={() => setOpen(true)}
          className="inline-flex h-10 items-center gap-2 rounded-lg bg-primary px-4 font-medium text-primary-foreground"
        >
          <Plus className="size-4" /> New document
        </button>
      </div>

      {docs === null ? (
        <p className="mt-10 text-muted-foreground">Loading…</p>
      ) : docs.length === 0 ? (
        <div className="grid-paper mt-10 rounded-xl border border-dashed border-rule p-12 text-center">
          <FileText className="mx-auto size-8 text-muted-foreground" />
          <p className="mt-3 font-display text-2xl">No documents yet</p>
          <p className="mt-1 text-sm text-muted-foreground">Paste an AI draft of your report to begin.</p>
          <button type="button" onClick={() => setOpen(true)} className="mt-5 rounded-lg border border-rule px-4 py-2 text-sm hover:bg-secondary">
            Paste a draft
          </button>
        </div>
      ) : (
        <ul className="mt-6 divide-y divide-rule">
          {docs.map((d) => {
            const step = STEPS.find((s) => s.id === d.step)!;
            return (
              <li key={d.id} className="group flex items-center gap-4 py-4">
                <Link href={`/workspace/${d.id}`} className="min-w-0 flex-1">
                  <p className="truncate font-display text-2xl group-hover:text-signal-ink">{d.title || "Untitled"}</p>
                  <p className="tabular mt-0.5 text-xs text-muted-foreground">
                    Step {step.n} · {step.label} · edited {timeAgo(d.updatedAt)}
                    {d.analysis && ` · score ${Math.round(d.analysis.score)}`}
                    {d.ownership && ` · ownership ${Math.round(d.ownership.score)}`}
                  </p>
                </Link>
                <div className="hidden gap-1 sm:flex" aria-hidden>
                  {STEPS.map((s) => (
                    <span key={s.id} className={`h-1.5 w-6 rounded-full ${s.n <= step.n ? "bg-signal" : "bg-rule"}`} />
                  ))}
                </div>
                <button
                  type="button"
                  onClick={() => remove(d.id)}
                  aria-label={`Delete ${d.title}`}
                  className="rounded-md p-2 text-muted-foreground opacity-60 hover:bg-secondary hover:text-destructive group-hover:opacity-100"
                >
                  <Trash2 className="size-4" />
                </button>
              </li>
            );
          })}
        </ul>
      )}
      <NewDocDialog open={open} onOpenChange={setOpen} onCreated={(id) => router.push(`/workspace/${id}`)} />
    </div>
  );
}
