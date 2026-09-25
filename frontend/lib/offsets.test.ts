import { Editor } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import { describe, expect, it } from "vitest";
import { OriginMark } from "@/components/editor/marks";
import { docText, jsonText, offsetMapper, textToContent } from "./offsets";

function makeEditor(text: string) {
  return new Editor({ extensions: [StarterKit, OriginMark], content: textToContent(text, "ai") });
}

describe("offsetMapper", () => {
  const text = "First line.\n\nThird line here.\nLast";

  it("round-trips every character offset", () => {
    const m = offsetMapper(text);
    for (let o = 0; o <= text.length; o++) {
      expect(m.toOffset(m.toPos(o))).toBe(o);
    }
  });

  it("matches ProseMirror positions in a real editor", () => {
    const editor = makeEditor(text);
    const m = offsetMapper(text);
    const start = text.indexOf("Third");
    const end = start + "Third line".length;
    expect(editor.state.doc.textBetween(m.toPos(start), m.toPos(end))).toBe("Third line");
    const last = text.indexOf("Last");
    expect(editor.state.doc.textBetween(m.toPos(last), m.toPos(last + 4))).toBe("Last");
    editor.destroy();
  });

  it("docText and jsonText reproduce the input", () => {
    const editor = makeEditor(text);
    expect(docText(editor.state.doc)).toBe(text);
    expect(jsonText(textToContent(text))).toBe(text);
    editor.destroy();
  });

  it("handles text without newlines", () => {
    const m = offsetMapper("abc");
    expect(m.toPos(0)).toBe(1);
    expect(m.toPos(3)).toBe(4);
  });

  it("tags all pasted text as ai origin", () => {
    const c = textToContent("a\nb", "ai");
    expect(c.content[0].content?.[0].marks?.[0].attrs.origin).toBe("ai");
    expect(c.content[1].content?.[0].marks?.[0].attrs.origin).toBe("ai");
  });
});
