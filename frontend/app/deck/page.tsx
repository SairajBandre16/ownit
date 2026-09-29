import { DeckReview } from "@/components/deck/DeckReview";
import { SiteHeader } from "@/components/layout/SiteHeader";

export const metadata = { title: "Revision Deck · OwnIt" };

export default function DeckPage() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto w-full max-w-5xl flex-1 px-4 py-10 sm:px-6">
        <h1 className="font-display text-5xl">Revision Deck</h1>
        <p className="mt-2 max-w-prose text-muted-foreground">
          Flashcards from your own documents, scheduled with spaced repetition (SM-2): cards you know come back less often.
        </p>
        <div className="mt-8">
          <DeckReview />
        </div>
      </main>
    </>
  );
}
