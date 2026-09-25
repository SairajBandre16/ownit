import { SiteHeader } from "@/components/layout/SiteHeader";
import { DocList } from "@/components/workspace/DocList";

export const metadata = { title: "Workspace — OwnIt" };

export default function WorkspacePage() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <DocList />
      </main>
    </>
  );
}
