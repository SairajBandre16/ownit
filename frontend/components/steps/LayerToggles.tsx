"use client";

import { type Layer, useWorkspace } from "@/lib/store";
import { cn } from "@/lib/utils";

const LABELS: Record<Layer, string> = {
  issues: "Suggestions",
  protected: "Protected",
  changes: "Changes",
  engineering: "Report Doctor",
  spots: "Generic spots",
};

export function LayerToggles({ available }: { available: Layer[] }) {
  const layers = useWorkspace((s) => s.layers);
  const toggle = useWorkspace((s) => s.toggleLayer);
  const heatmap = useWorkspace((s) => s.heatmap);
  const setHeatmap = useWorkspace((s) => s.setHeatmap);
  return (
    <div className="flex flex-wrap items-center gap-1" role="group" aria-label="Highlight layers">
      {available.map((l) => (
        <button
          key={l}
          type="button"
          aria-pressed={layers[l]}
          onClick={() => toggle(l)}
          className={cn(
            "rounded-full border px-2.5 py-1 text-xs transition-colors",
            layers[l] ? "border-foreground/70 bg-secondary" : "border-rule text-muted-foreground",
          )}
        >
          {LABELS[l]}
        </button>
      ))}
      <button
        type="button"
        aria-pressed={heatmap}
        onClick={() => setHeatmap(!heatmap)}
        className={cn(
          "rounded-full border px-2.5 py-1 text-xs transition-colors",
          heatmap ? "border-[var(--own-insert)] bg-[var(--own-insert)]/15" : "border-rule text-muted-foreground",
        )}
      >
        Ownership heatmap
      </button>
    </div>
  );
}
