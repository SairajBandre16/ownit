"use client";

export function ExportStep({ onBack }: { onBack: () => void }) {
  return (
    <div className="rounded-xl border border-dashed border-rule p-10 text-center text-muted-foreground">
      <p>This step is being built.</p>
      <button type="button" onClick={onBack} className="mt-4 underline">Back</button>
    </div>
  );
}
