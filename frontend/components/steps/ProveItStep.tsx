"use client";

export function ProveItStep({ onNext }: { onNext: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-rule p-10 text-center text-muted-foreground">
      <p>This step is being built.</p>
      <button type="button" onClick={onNext} className="mt-4 underline">Skip</button>
    </div>
  );
}
