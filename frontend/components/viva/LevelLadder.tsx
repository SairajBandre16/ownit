import { LEVELS } from "@/lib/assess";
import { cn } from "@/lib/utils";

/** The difficulty ladder: define → how → why → compare/evaluate, with the current rung lit. */
export function LevelLadder({ level }: { level: number }) {
  return (
    <ol className="flex items-center gap-1.5" aria-label={`Difficulty: level ${level} of 4`}>
      {LEVELS.map((l) => (
        <li key={l.level} className="flex items-center gap-1.5">
          <span
            className={cn(
              "tabular rounded-full border px-2.5 py-0.5 text-[11px] uppercase tracking-wider transition-colors duration-300",
              l.level === level
                ? "border-signal bg-signal/15 text-foreground"
                : l.level < level
                  ? "border-foreground/30 text-foreground/70"
                  : "border-foreground/15 text-foreground/40",
            )}
            aria-current={l.level === level ? "step" : undefined}
          >
            {l.name}
          </span>
          {l.level < 4 && <span className="h-px w-3 bg-foreground/20" aria-hidden />}
        </li>
      ))}
    </ol>
  );
}
