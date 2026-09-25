"use client";

import { Upload } from "lucide-react";
import { useRef, useState } from "react";
import { toast } from "sonner";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "@/components/ui/dialog";
import { uploadFile } from "@/lib/api";
import { countWords, createDoc, MAX_WORDS } from "@/lib/docs";

const SAMPLE = `Design and Testing of a Smart Irrigation Controller

Introduction
In today's fast-paced world, water scarcity plays a crucial role in agriculture. It is important to note that farmers utilize a large amount of water in order to irrigate crops. Moreover, the Internet of Things (IoT) has the ability to reduce this waste. Moreover, a microcontroller can make a decision based on soil moisture readings.

Methodology
The controller was built around an ESP32 board. A capacitive soil moisture sensor was used to measure the volumetric water content. The data was sent to a cloud dashboard by the ESP32 every 10 minutes. The pump was switched by a relay module rated at 10 A.

Results
The system reduced water use significantly compared with manual watering. The moisture level stayed within the target band for most of the test period. The results clearly show that the controller is the best solution for small farms.

Conclusion
In conclusion, it is evident that the smart irrigation controller has the potential to revolutionize farming. Further research is needed to delve into the long-term reliability of the sensors.`;

export function NewDocDialog({
  open,
  onOpenChange,
  onCreated,
}: {
  open: boolean;
  onOpenChange: (o: boolean) => void;
  onCreated: (id: string) => void;
}) {
  const [text, setText] = useState("");
  const [title, setTitle] = useState("");
  const [busy, setBusy] = useState(false);
  const fileRef = useRef<HTMLInputElement>(null);
  const words = countWords(text);
  const tooLong = words > MAX_WORDS;

  const create = async () => {
    if (!text.trim() || tooLong) return;
    setBusy(true);
    const doc = await createDoc(text, title);
    setBusy(false);
    setText("");
    setTitle("");
    onOpenChange(false);
    onCreated(doc.id);
  };

  const onFile = async (file: File) => {
    setBusy(true);
    try {
      const res = await uploadFile("/files/extract", file);
      setText(res.text);
      if (!title) setTitle(file.name.replace(/\.(docx|pdf)$/i, ""));
      toast.success(`Extracted ${countWords(res.text)} words from ${file.name}`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Couldn't read that file");
    } finally {
      setBusy(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl">
        <DialogHeader>
          <DialogTitle className="font-display text-3xl font-normal">New document</DialogTitle>
          <DialogDescription>
            Paste your draft (up to {MAX_WORDS.toLocaleString()} words) or upload a .docx / .pdf. Headings like
            “Introduction” or “Results” on their own line help the section-aware checks.
          </DialogDescription>
        </DialogHeader>
        <label className="text-sm font-medium" htmlFor="doc-title">
          Title
        </label>
        <input
          id="doc-title"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder="e.g. Lab 4 — Heat exchanger report"
          className="h-9 rounded-md border border-input bg-background px-3 text-sm"
        />
        <label className="text-sm font-medium" htmlFor="doc-text">
          Draft
        </label>
        <textarea
          id="doc-text"
          value={text}
          onChange={(e) => setText(e.target.value)}
          rows={12}
          placeholder="Paste your draft here…"
          className="grid-paper min-h-48 rounded-md border border-input bg-background p-3 font-[inherit] text-sm leading-relaxed"
        />
        <div className="flex flex-wrap items-center gap-2">
          <span className={`tabular text-xs ${tooLong ? "text-destructive" : "text-muted-foreground"}`}>
            {words.toLocaleString()} / {MAX_WORDS.toLocaleString()} words
          </span>
          <button type="button" onClick={() => setText(SAMPLE)} className="text-xs text-signal-ink underline underline-offset-2">
            Use a sample draft
          </button>
          <input
            ref={fileRef}
            type="file"
            accept=".docx,.pdf,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            className="hidden"
            onChange={(e) => e.target.files?.[0] && onFile(e.target.files[0])}
          />
          <button
            type="button"
            onClick={() => fileRef.current?.click()}
            className="ml-auto inline-flex items-center gap-1.5 rounded-md border border-rule px-3 py-1.5 text-sm hover:bg-secondary"
            disabled={busy}
          >
            <Upload className="size-4" /> Upload .docx / .pdf
          </button>
          <button
            type="button"
            onClick={create}
            disabled={!text.trim() || tooLong || busy}
            className="rounded-md bg-primary px-4 py-1.5 text-sm font-medium text-primary-foreground disabled:opacity-50"
          >
            Start
          </button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
