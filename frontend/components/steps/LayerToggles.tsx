"use client";

import { Check, Layers } from "lucide-react";
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover";
import { type Layer, useWorkspace } from "@/lib/store";
import { cn } from "@/lib/utils";

const LABELS: Record<Layer, { label: string; hint: string }> = {
  issues: { label: "Suggestions", hint: "Writing issues from the analysis" },
  protected: { label: "Protected", hint: "Quotes, citations, units, terms the rewriter never touches" },
  changes: { label: "Changes", hint: "Rewrites waiting for your decision" },
  engineering: { label: "Report Doctor", hint: "Units, abbreviations, figures, tense, claims" },
  spots: { label: "Generic spots", hint: "Places that need your own data or example" },
};

function Row({ on, label, hint, onClick, swatch }: { on: boolean; label: string; hint: string; onClick: () => void; swatch?: string }) {
  return (
    <button
      type="button"
      role="menuitemcheckbox"
      aria-checked={on}
      onClick={onClick}
      className="flex w-full items-start gap-2.5 rounded-md px-2 py-1.5 text-left hover:bg-secondary"
    >
      <span
        className={cn(
          "mt-0.5 flex size-4 shrink-0 items-center justify-center rounded border",
          on ? "border-foreground bg-foreground text-background" : "border-rule",
        )}
        style={on && swatch ? { background: swatch, borderColor: swatch } : undefined}
        aria-hidden
      >
        {on && <Check className="size-3" />}
      </span>
      <span className="min-w-0">
        <span className="block text-sm">{label}</span>
        <span className="block text-xs text-muted-foreground">{hint}</span>
      </span>
    </button>
  );
}

/** One "Layers" menu for the editor highlight layers and the ownership heatmap. */
export function LayerToggles({ available }: { available: Layer[] }) {
  const layers = useWorkspace((s) => s.layers);
  const toggle = useWorkspace((s) => s.toggleLayer);
  const heatmap = useWorkspace((s) => s.heatmap);
  const setHeatmap = useWorkspace((s) => s.setHeatmap);
  const on = available.filter((l) => layers[l]).length + (heatmap ? 1 : 0);
  return (
    <Popover>
      <PopoverTrigger
        className="inline-flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary"
        aria-label={`Highlight layers, ${on} on`}
      >
        <Layers className="size-4" aria-hidden />
        Layers
        <span className="tabular rounded bg-secondary px-1 text-[11px] text-muted-foreground">{on}</span>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-80 gap-1 p-1.5">
        <div role="menu" aria-label="Highlight layers">
          {available.map((l) => (
            <Row key={l} on={layers[l]} label={LABELS[l].label} hint={LABELS[l].hint} onClick={() => toggle(l)} />
          ))}
          <div className="my-1 border-t border-rule" />
          <Row
            on={heatmap}
            label="Ownership heatmap"
            hint="Colour the text by who wrote it: AI, engine, or you"
            onClick={() => setHeatmap(!heatmap)}
            swatch="var(--own-insert)"
          />
        </div>
      </PopoverContent>
    </Popover>
  );
}
