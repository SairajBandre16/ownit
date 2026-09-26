import { SiteHeader } from "@/components/layout/SiteHeader";
import { LessonView } from "@/components/learn/LessonView";

export const metadata = { title: "Lesson — OwnIt" };

export default async function LessonPage({ params }: PageProps<"/learn/[topic]">) {
  const { topic } = await params;
  return (
    <>
      <SiteHeader />
      <main id="main" className="w-full flex-1 px-4 py-10 sm:px-6">
        <LessonView slug={topic} />
      </main>
    </>
  );
}
