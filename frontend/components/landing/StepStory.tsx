"use client";

import { motion, useReducedMotion } from "framer-motion";

const STEPS = [
  {
    n: "01",
    title: "Humanize",
    body: "A rule-based rewrite: wordy phrases, repeated transitions, over-long sentences. Every change comes with a plain-English reason, and you accept or reject each one.",
    detail: "“in order to” → “to” — shorter, same meaning.",
  },
  {
    n: "02",
    title: "Walkthrough",
    body: "Paragraph by paragraph: a one-line gist, the key terms with definitions, a simpler version, and a concept map that follows your reading.",
    detail: "Mark each paragraph “Got it” or “Confusing”.",
  },
  {
    n: "03",
    title: "Make it yours",
    body: "OwnIt finds the generic spots — vague quantities, claims without examples, results without numbers — and asks you to add your own data and experience.",
    detail: "“Add the value you measured, with its unit.”",
  },
  {
    n: "04",
    title: "Prove it",
    body: "A quiz built from your report, a teach-back where you explain it in your own words, and an adaptive Viva Simulator that gets harder as you get it right.",
    detail: "definition → how → why → compare",
  },
  {
    n: "05",
    title: "Export",
    body: "Download a clean .docx and an Understanding Report — your viva Q&A, glossary and weak concepts — once you've shown you understand it.",
    detail: "Ownership Score: an honest “you wrote 38% of this”.",
  },
];

export function StepStory() {
  const reduce = useReducedMotion();
  return (
    <section id="how" className="border-b border-rule">
      <div className="mx-auto max-w-7xl px-4 py-20 sm:px-6">
        <h2 className="font-display text-4xl sm:text-5xl">Five steps from draft to defensible.</h2>
        <ol className="mt-12 grid gap-px overflow-hidden rounded-xl border border-rule bg-rule">
          {STEPS.map((s, i) => (
            <motion.li
              key={s.n}
              initial={reduce ? false : { opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: "-80px" }}
              transition={{ duration: 0.45, delay: i * 0.04 }}
              className="grid gap-4 bg-background p-6 sm:grid-cols-[5rem_1fr_1fr] sm:p-8"
            >
              <span className="tabular text-sm text-signal-ink">{s.n}</span>
              <div>
                <h3 className="font-display text-3xl">{s.title}</h3>
                <p className="mt-2 text-muted-foreground">{s.body}</p>
              </div>
              <p className="tabular self-end rounded-md border border-dashed border-rule p-3 text-sm">
                {s.detail}
              </p>
            </motion.li>
          ))}
        </ol>
      </div>
    </section>
  );
}
