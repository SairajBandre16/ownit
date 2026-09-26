import { SiteHeader } from "@/components/layout/SiteHeader";
import { ProgressDashboard } from "@/components/progress/ProgressDashboard";

export const metadata = { title: "Progress — OwnIt" };

export default function ProgressPage() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <h1 className="font-display text-5xl">Progress</h1>
        <p className="mt-2 max-w-prose text-muted-foreground">Everything here is stored in this browser only.</p>
        <div className="mt-8">
          <ProgressDashboard />
        </div>
      </main>
    </>
  );
}
