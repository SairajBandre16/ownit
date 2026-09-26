import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Markdown, parseBlocks } from "./markdown";

describe("parseBlocks", () => {
  it("parses headings, paragraphs, lists and quotes", () => {
    const md = "## Why\nLine one\nline two.\n\n- a\n- b\n\n1. first\n2. second\n\n> note";
    expect(parseBlocks(md)).toEqual([
      { kind: "h2", text: "Why" },
      { kind: "p", text: "Line one line two." },
      { kind: "ul", items: ["a", "b"] },
      { kind: "ol", items: ["first", "second"] },
      { kind: "quote", text: "note" },
    ]);
  });
});

describe("Markdown", () => {
  it("renders inline bold, italic, code and safe links", () => {
    render(<Markdown source={"**Before:** use `12 V`, see [units](/learn/units) or _this_. [bad](javascript:alert(1))"} />);
    expect(screen.getByText("Before:").tagName).toBe("STRONG");
    expect(screen.getByText("12 V").tagName).toBe("CODE");
    expect(screen.getByRole("link", { name: "units" })).toHaveAttribute("href", "/learn/units");
    expect(screen.getByText("this").tagName).toBe("EM");
    expect(screen.queryByRole("link", { name: "bad" })).toBeNull();
  });

  it("never renders raw HTML", () => {
    const { container } = render(<Markdown source={'<img src=x onerror="alert(1)"> text'} />);
    expect(container.querySelector("img")).toBeNull();
    expect(container.textContent).toContain("<img");
  });
});
