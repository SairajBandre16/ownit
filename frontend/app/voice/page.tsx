import { SiteHeader } from "@/components/layout/SiteHeader";
import { VoiceSetup } from "@/components/voice/VoiceSetup";

export const metadata = { title: "Voice Fingerprint · OwnIt" };

export default function VoicePage() {
  return (
    <>
      <SiteHeader />
      <main id="main" className="mx-auto w-full max-w-6xl flex-1 px-4 py-10 sm:px-6">
        <VoiceSetup />
      </main>
    </>
  );
}
