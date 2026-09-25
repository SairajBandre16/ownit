import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { afterEach, describe, expect, it } from "vitest";
import { replaceRange, insertAt } from "@/lib/editing";
import { originCounts } from "@/lib/ownership";
import { docText, offsetMapper, textToContent } from "@/lib/offsets";
import { OriginMark, OriginTracker } from "./marks";

let editor: Editor;
afterEach(() => editor?.destroy());

function make(text: string) {
  editor = new Editor({ extensions: [StarterKit, OriginMark, OriginTracker], content: textToContent(text, "ai") });
  return editor;
}

/** Origin of each character of the plain text ("." = AI, "e" = engine, "d" = edit, "i" = insert). */
function originMap(e: Editor): string {
  const code: Record<string, string> = { ai: ".", engine: "e", student_edit: "d", student_insert: "i" };
  const lines: string[] = [];
  e.state.doc.forEach((para) => {
    let line = "";
    para.forEach((node) => {
      const o = node.marks.find((m) => m.type.name === "origin")?.attrs.origin ?? "none";
      line += (code[o] ?? "?").repeat(node.text?.length ?? 0);
    });
    lines.push(line);
  });
  return lines.join("\n");
}

const pos = (e: Editor, offset: number) => offsetMapper(docText(e.state.doc)).toPos(offset);
const type = (e: Editor, offset: number, text: string) => e.chain().insertContentAt(pos(e, offset), text).run();

describe("origin tracking (§9.2)", () => {
  it("loads pasted drafts as AI text", () => {
    const e = make("The pump runs.");
    expect(originMap(e)).toBe("..............");
  });

  it("typing inside an AI sentence is a student edit", () => {
    const e = make("The pump runs.");
    type(e, 4, "big ");
    expect(docText(e.state.doc)).toBe("The big pump runs.");
    expect(originMap(e)).toBe("....dddd..........");
  });

  it("typing after a finished sentence or in a new paragraph is a student insertion", () => {
    const e = make("The pump runs.\n");
    type(e, 14, " It is loud.");
    expect(originMap(e).split("\n")[0]).toBe(".".repeat(14) + "i".repeat(12));
    type(e, docText(e.state.doc).length, "My note");
    expect(originMap(e).split("\n")[1]).toBe("iiiiiii");
  });

  it("continuing the student's own text keeps its origin", () => {
    const e = make("The pump runs.");
    type(e, 4, "big ");
    type(e, 8, "red ");
    expect(originMap(e)).toBe("....dddddddd..........");
  });

  it("accepted engine changes are tagged engine; later typing inside them is a student edit", () => {
    const e = make("We utilize a pump.");
    replaceRange(e, pos(e, 3), pos(e, 10), "use", "engine");
    expect(docText(e.state.doc)).toBe("We use a pump.");
    expect(originMap(e)).toBe("...eee........");
    type(e, 6, "d");
    expect(originMap(e)).toBe("...eeed........");
  });

  it("'Make it yours' insertions are student insertions", () => {
    const e = make("Robots help.");
    insertAt(e, pos(e, 12), " In our lab, a KUKA arm welds frames.", "student_insert");
    expect(originCounts(e.getJSON()).student_insert).toBe("Inourlab,aKUKAarmweldsframes.".length);
  });

  // what ProseMirror dispatches for a paste: the slice replaces the selection, uiEvent = paste
  function paste(e: Editor, offset: number, text: string, origin?: string) {
    const { schema } = e.state;
    const marks = origin ? [schema.marks.origin.create({ origin })] : [];
    const at = pos(e, offset);
    e.view.dispatch(e.state.tr.replaceWith(at, at, schema.text(text, marks)).setMeta("uiEvent", "paste"));
  }

  it("text pasted from outside is AI, even after a finished sentence", () => {
    const e = make("The pump runs.");
    paste(e, 14, " Copied from a website.");
    expect(originCounts(e.getJSON())).toMatchObject({ ai: "Thepumpruns.Copiedfromawebsite.".length, student_insert: 0 });
  });

  it("text copied inside the editor keeps its origin when pasted", () => {
    const e = make("The pump runs.");
    paste(e, 14, " My own words.", "student_insert");
    expect(originMap(e)).toBe(".".repeat(14) + "i".repeat(14));
  });

  it("deleting text never creates student text", () => {
    const e = make("The big pump runs.");
    e.chain().deleteRange({ from: pos(e, 4), to: pos(e, 8) }).run();
    expect(docText(e.state.doc)).toBe("The pump runs.");
    expect(originMap(e)).toBe("..............");
  });
});
