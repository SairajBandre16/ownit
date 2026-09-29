import { Workspace } from "@/components/workspace/Workspace";

export const metadata = { title: "Document · OwnIt" };

export default async function DocPage({ params }: PageProps<"/workspace/[docId]">) {
  const { docId } = await params;
  return <Workspace docId={docId} />;
}
