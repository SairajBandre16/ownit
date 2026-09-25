/** Main column + insight panel. The step rail is rendered by the workspace shell. */
export function StepLayout({
  toolbar,
  main,
  aside,
}: {
  toolbar?: React.ReactNode;
  main: React.ReactNode;
  aside?: React.ReactNode;
}) {
  return (
    <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_22rem]">
      <section className="min-w-0">
        {toolbar && <div className="sticky top-14 z-20 -mx-1 mb-3 flex flex-wrap items-center gap-2 bg-background/90 px-1 py-2 backdrop-blur">{toolbar}</div>}
        {main}
      </section>
      {aside && (
        <aside className="min-w-0 space-y-6 xl:sticky xl:top-20 xl:max-h-[calc(100vh-6rem)] xl:overflow-y-auto xl:pb-8" aria-label="Insights">
          {aside}
        </aside>
      )}
    </div>
  );
}

export function Panel({ title, children, action }: { title: string; children: React.ReactNode; action?: React.ReactNode }) {
  return (
    <section className="rounded-xl border border-rule bg-card p-4">
      <div className="mb-3 flex items-center justify-between gap-2">
        <h2 className="tabular text-[11px] uppercase tracking-[0.18em] text-muted-foreground">{title}</h2>
        {action}
      </div>
      {children}
    </section>
  );
}
