"use client";

import { AnimatePresence, motion, useReducedMotion } from "framer-motion";
import { Check, HelpCircle, Pencil, Sparkles } from "lucide-react";
import { forwardRef, useState } from "react";
import type { KeyTerm, WalkthroughParagraph } from "@/lib/api";
import type { ParagraphMark } from "@/lib/types";
import { cn } from "@/lib/utils";
import { SOURCE_LABEL, termDefinition, termPieces } from "@/lib/walkthrough";

const SECTION_LABEL: Record<string, string> = { body: "Body" };
const sectionLabel = (s: string) => SECTION_LABEL[s] ?? s.charAt(0).toUpperCase() + s.slice(1);

interface Props {
  para: WalkthroughParagraph;
  n: number;
  total: number;
  text: string;
  mark?: ParagraphMark;
  active: boolean;
  simple: boolean;
  ownDefs?: Record<string, string>;
  onMark: (m: ParagraphMark | null) => void;
  onToggleSimple: () => void;
  onDefine: (term: string, definition: string) => void;
  onFocus: () => void;
}

export const ParagraphCard = forwardRef<HTMLElement, Props>(function ParagraphCard(
  { para, n, total, text, mark, active, simple, ownDefs, onMark, onToggleSimple, onDefine, onFocus },
  ref,
) {
  const reduce = useReducedMotion();
  const [openTerm, setOpenTerm] = useState<string | null>(null);
  const pieces = termPieces(text, para);
  const simplerDiffers = para.simplified.trim() !== text.slice(para.start, para.end).trim();

  return (
    <article
      ref={ref}
      data-paragraph={para.index}
      tabIndex={0}
      onFocus={onFocus}
      onClick={onFocus}
      aria-label={`Paragraph ${n} of ${total}${mark ? `, marked ${mark === "got" ? "got it" : "confusing"}` : ""}`}
      aria-current={active || undefined}
      className={cn(
        "scroll-mt-28 rounded-xl border bg-card p-5 transition-colors outline-none focus-visible:ring-2 focus-visible:ring-ring sm:p-6",
        active ? "border-foreground/40" : "border-rule",
        mark === "got" && "border-l-4 border-l-[var(--own-insert)]",
        mark === "confusing" && "border-l-4 border-l-signal",
      )}
    >
      <header className="mb-3 flex items-center gap-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">
        <span className="tabular">
          ¶ {String(n).padStart(2, "0")} / {String(total).padStart(2, "0")}
        </span>
        <span aria-hidden>·</span>
        <span>{sectionLabel(para.section)}</span>
      </header>

      {/* gist */}
      <p className="font-display text-xl leading-snug sm:text-2xl">
        <span className="sr-only">In one line: </span>
        {para.gist}
      </p>

      {/* original or simplified text */}
      <div className="mt-4 rounded-lg border border-rule bg-background/60 p-4">
        <div className="mb-2 flex items-center justify-between gap-2 text-[11px] uppercase tracking-wider text-muted-foreground">
          <span>{simple ? "Simpler version" : "Your text"}</span>
          {simplerDiffers && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleSimple();
              }}
              aria-pressed={simple}
              className="inline-flex items-center gap-1 rounded-full border border-rule px-2 py-0.5 normal-case tracking-normal hover:bg-secondary"
              title="Toggle the simpler version (S)"
            >
              <Sparkles className="size-3" /> {simple ? "Show original" : "Simplify"}
            </button>
          )}
        </div>
        <AnimatePresence mode="wait" initial={false}>
          <motion.p
            key={simple ? "s" : "o"}
            initial={reduce ? false : { opacity: 0, y: 4 }}
            animate={{ opacity: 1, y: 0 }}
            exit={reduce ? undefined : { opacity: 0, y: -4 }}
            transition={{ duration: 0.18 }}
            className="leading-relaxed text-[15px]"
          >
            {simple
              ? para.simplified
              : pieces.map((p, i) =>
                  p.term ? (
                    <button
                      key={i}
                      type="button"
                      onClick={(e) => {
                        e.stopPropagation();
                        setOpenTerm(p.term!.term);
                      }}
                      title={termDefinition(p.term, ownDefs).text ?? "Define this term yourself"}
                      className="rounded-sm underline decoration-signal/60 decoration-2 underline-offset-4 hover:bg-signal/10"
                    >
                      {p.text}
                    </button>
                  ) : (
                    <span key={i}>{p.text}</span>
                  ),
                )}
          </motion.p>
        </AnimatePresence>
        {simple && (
          <p className="tabular mt-2 text-xs text-muted-foreground">
            Reading grade {para.grade_before.toFixed(1)} → {para.grade_after.toFixed(1)}
          </p>
        )}
      </div>

      {/* key terms */}
      {para.key_terms.length > 0 && (
        <div className="mt-4">
          <h3 className="mb-2 text-[11px] uppercase tracking-[0.16em] text-muted-foreground">Key terms</h3>
          <ul className="space-y-2">
            {para.key_terms.map((t) => (
              <TermRow
                key={t.term}
                term={t}
                ownDefs={ownDefs}
                open={openTerm === t.term}
                onOpen={(o) => setOpenTerm(o ? t.term : null)}
                onDefine={(d) => onDefine(t.term, d)}
              />
            ))}
          </ul>
        </div>
      )}

      {/* self-check */}
      <footer className="mt-5 flex flex-wrap items-center gap-2">
        <span className="mr-1 text-sm text-muted-foreground">Do you understand this paragraph?</span>
        <button
          type="button"
          aria-pressed={mark === "got"}
          onClick={(e) => {
            e.stopPropagation();
            onMark(mark === "got" ? null : "got");
          }}
          title="Got it (G)"
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors",
            mark === "got" ? "border-[var(--own-insert)] bg-[var(--own-insert)]/15" : "border-rule hover:bg-secondary",
          )}
        >
          <Check className="size-4" /> Got it
        </button>
        <button
          type="button"
          aria-pressed={mark === "confusing"}
          onClick={(e) => {
            e.stopPropagation();
            onMark(mark === "confusing" ? null : "confusing");
          }}
          title="Confusing (C)"
          className={cn(
            "inline-flex items-center gap-1.5 rounded-md border px-3 py-1.5 text-sm transition-colors",
            mark === "confusing" ? "border-signal bg-signal/15" : "border-rule hover:bg-secondary",
          )}
        >
          <HelpCircle className="size-4" /> Confusing
        </button>
        {mark === "confusing" && (
          <span className="text-xs text-muted-foreground">You&apos;ll get extra questions on this paragraph in step 4.</span>
        )}
      </footer>
    </article>
  );
});

function TermRow({
  term,
  ownDefs,
  open,
  onOpen,
  onDefine,
}: {
  term: KeyTerm;
  ownDefs?: Record<string, string>;
  open: boolean;
  onOpen: (open: boolean) => void;
  onDefine: (definition: string) => void;
}) {
  const def = termDefinition(term, ownDefs);
  const [draft, setDraft] = useState(def.own ? def.text ?? "" : "");
  const missing = !def.text;

  return (
    <li className={cn("rounded-lg border px-3 py-2 text-sm", open ? "border-foreground/40" : "border-rule")}>
      <div className="flex flex-wrap items-baseline gap-x-2">
        <span className="font-medium">{term.term}</span>
        {def.text ? (
          <span className="text-muted-foreground">— {def.text}</span>
        ) : (
          <span className="text-signal-ink">No definition found. Define it in your own words.</span>
        )}
        <span className="ml-auto flex items-center gap-2 text-[11px] text-muted-foreground">
          {def.own ? "your definition" : term.source ? SOURCE_LABEL[term.source] ?? term.source : null}
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onOpen(!open);
            }}
            className="inline-flex items-center gap-1 rounded px-1 hover:bg-secondary"
            aria-expanded={open}
            aria-label={`${missing ? "Define" : "Rewrite"} ${term.term} in your own words`}
          >
            <Pencil className="size-3" /> {missing ? "Define" : "In my words"}
          </button>
        </span>
      </div>
      {open && (
        <form
          className="mt-2 flex gap-2"
          onClick={(e) => e.stopPropagation()}
          onSubmit={(e) => {
            e.preventDefault();
            onDefine(draft.trim());
            onOpen(false);
          }}
        >
          <input
            autoFocus
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => e.key === "Escape" && onOpen(false)}
            placeholder={`${term.term} is…`}
            aria-label={`Your definition of ${term.term}`}
            className="min-w-0 flex-1 rounded-md border border-input bg-background px-2 py-1 text-sm focus:outline-none focus-visible:ring-2 focus-visible:ring-ring"
          />
          <button type="submit" className="rounded-md bg-primary px-3 py-1 text-sm font-medium text-primary-foreground">
            Save
          </button>
        </form>
      )}
    </li>
  );
}
