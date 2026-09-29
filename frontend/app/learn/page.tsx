import { SiteHeader } from "@/components/layout/SiteHeader";
import { LessonIndex } from "@/components/learn/LessonIndex";

export const metadata = { title: "Learn · OwnIt" };

export default function LearnPage() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <h1 className="font-display text-5xl">Learn</h1>
        <p className="mt-2 max-w-prose text-muted-foreground">
          Short lessons on clear writing and engineering reports. Every suggestion OwnIt makes links to one of these.
        </p>
        <div className="mt-10">
          <LessonIndex />
        </div>
      </main>
    </>
  );
}
