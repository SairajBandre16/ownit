import { VivaSimulator } from "@/components/viva/VivaSimulator";

export const metadata = { title: "Viva Simulator — OwnIt" };

export default async function VivaPage({ params }: PageProps<"/viva/[docId]">) {
  const { docId } = await params;
  return <VivaSimulator docId={docId} />;
}
