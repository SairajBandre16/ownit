import { cn } from "@/lib/utils";

/**
 * The OwnIt mark: an "O" whose left half is the thin grey line of the AI draft and whose right
 * half is your solid ink, with the signal-orange pen tip where you take over the line. It is
 * the ownership heatmap in one glyph. The ink half uses currentColor to follow the theme.
 */
export function LogoMark({ className }: { className?: string }) {
  return (
    <svg viewBox="0 0 24 24" fill="none" aria-hidden="true" className={cn("size-6", className)}>
      <path
        d="M12 3.5A8.5 8.5 0 0 0 12 20.5"
        stroke="var(--muted-foreground)"
        strokeWidth="1.3"
        strokeLinecap="round"
      />
      <path d="M12 20.5A8.5 8.5 0 0 0 12 3.5" stroke="currentColor" strokeWidth="2.4" strokeLinecap="round" />
      <circle cx="12" cy="3.5" r="2.7" fill="var(--signal)" />
    </svg>
  );
}

/** Mark plus wordmark: "Own" upright, "It" in the orange italic of the "Own it." headline. */
export function Logo({ className }: { className?: string }) {
  return (
    <span className={cn("flex items-center gap-2", className)}>
      <LogoMark className="size-7" />
      <span className="font-display text-[1.6rem] leading-none tracking-tight">
        Own<em className="text-signal-ink">It</em>
      </span>
    </span>
  );
}
