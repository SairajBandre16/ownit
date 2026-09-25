const FAQ = [
  {
    q: "Is this an AI detector bypass?",
    a: "No. OwnIt is a learning tool. It makes writing clearer and helps you understand and add to your own report. It has no “detection score” and never claims text is undetectable.",
  },
  {
    q: "Does it use ChatGPT or any AI model?",
    a: "No. Every rewrite comes from explicit rules, a dictionary (WordNet), word statistics and a small n‑gram language model trained on Wikipedia text. There are no neural models and no external APIs.",
  },
  {
    q: "Where is my text stored?",
    a: "In your browser (IndexedDB). The server processes each request in memory and doesn't save it.",
  },
  {
    q: "Why do some sentences not change?",
    a: "Rule-based rewriting is conservative. If no candidate keeps the meaning and reads at least as well, OwnIt keeps your sentence. That's intended.",
  },
  {
    q: "What is the Ownership Score?",
    a: "An honest measure of how much of the final text is yours, how many suggestions you reviewed, how well you understood it, and how many generic spots you filled with your own work.",
  },
];

export function Faq() {
  return (
    <section id="faq" className="mx-auto w-full max-w-4xl px-4 py-20 sm:px-6">
      <h2 className="font-display text-4xl">Questions, answered plainly</h2>
      <div className="mt-8 divide-y divide-rule border-y border-rule">
        {FAQ.map((f) => (
          <details key={f.q} className="group py-5">
            <summary className="flex cursor-pointer list-none items-center justify-between gap-4 text-lg font-medium">
              {f.q}
              <span className="tabular text-signal-ink transition-transform group-open:rotate-45" aria-hidden>
                +
              </span>
            </summary>
            <p className="mt-3 text-muted-foreground">{f.a}</p>
          </details>
        ))}
      </div>
    </section>
  );
}
