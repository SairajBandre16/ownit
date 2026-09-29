import Link from "next/link";
import { SiteHeader } from "@/components/layout/SiteHeader";
import { LiveDemo } from "@/components/landing/LiveDemo";
import { StepStory } from "@/components/landing/StepStory";
import { Faq } from "@/components/landing/Faq";

export default function Home() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="flex-1">
        <section className="relative overflow-hidden border-b border-rule">
          <div className="grid-paper absolute inset-0 opacity-70" aria-hidden />
          <div className="relative mx-auto grid max-w-7xl gap-12 px-4 py-20 sm:px-6 lg:grid-cols-[1.1fr_1fr] lg:py-28">
            <div className="flex flex-col justify-center">
              <p className="tabular mb-6 text-xs uppercase tracking-[0.2em] text-signal-ink">
                For engineering reports, lab write-ups and vivas
              </p>
              <h1 className="font-display text-5xl leading-[1.02] sm:text-6xl lg:text-7xl">
                Humanize it.
                <br />
                Understand it.
                <br />
                <em className="text-signal-ink">Own it.</em>
              </h1>
              <p className="mt-6 max-w-xl text-lg text-muted-foreground">
                Paste an AI draft. OwnIt rewrites it clearly and explains every change, walks you
                through each paragraph, asks you to add your own data and examples, and checks you
                can defend it in a viva, before you export.
              </p>
              <div className="mt-8 flex flex-wrap items-center gap-3">
                <Link
                  href="/workspace"
                  className="inline-flex h-11 items-center rounded-lg bg-primary px-5 font-medium text-primary-foreground transition-transform hover:-translate-y-0.5 focus-visible:outline-2 focus-visible:outline-offset-2"
                >
                  Open the workspace
                </Link>
                <a
                  href="#how"
                  className="inline-flex h-11 items-center rounded-lg border border-rule px-5 font-medium hover:bg-secondary"
                >
                  How it works
                </a>
              </div>
              <div className="mt-8 flex flex-wrap gap-2 text-xs">
                <span className="tabular rounded-full border border-ink/80 px-3 py-1">0 AI models · 0 external APIs</span>
                <span className="tabular rounded-full border border-rule px-3 py-1 text-muted-foreground">every change explained</span>
                <span className="tabular rounded-full border border-rule px-3 py-1 text-muted-foreground">text stays on your device</span>
              </div>
            </div>
            <LiveDemo />
          </div>
        </section>

        <StepStory />
        <Faq />
      </main>
      <footer className="border-t border-rule py-8">
        <div className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-4 px-4 text-sm text-muted-foreground sm:px-6">
          <span>OwnIt is a learning tool. It never claims to make text “undetectable”.</span>
          <nav aria-label="Footer" className="flex gap-4">
            <Link href="/learn" prefetch={false} className="hover:text-foreground">Learn</Link>
            <Link href="/deck" prefetch={false} className="hover:text-foreground">Revision Deck</Link>
            <Link href="/progress" prefetch={false} className="hover:text-foreground">Progress</Link>
            <Link href="/voice" prefetch={false} className="hover:text-foreground">Voice</Link>
          </nav>
          <span className="tabular">spaCy · WordNet · n‑gram LM · LanguageTool</span>
        </div>
      </footer>
    </>
  );
}
