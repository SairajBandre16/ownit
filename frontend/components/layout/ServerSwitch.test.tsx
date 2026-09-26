import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it } from "vitest";
import { DEFAULT_API_URL, getApiUrl, normalizeApiUrl, setApiUrl } from "@/lib/api";
import { ApiLinkHandler } from "./ApiLinkHandler";

function withClient(ui: React.ReactElement) {
  return <QueryClientProvider client={new QueryClient()}>{ui}</QueryClientProvider>;
}

describe("server address", () => {
  beforeEach(() => {
    window.localStorage.clear();
    window.history.replaceState(null, "", "/");
  });

  it("accepts https anywhere and http only on this computer", () => {
    expect(normalizeApiUrl("https://abc-def.trycloudflare.com/")).toBe("https://abc-def.trycloudflare.com");
    expect(normalizeApiUrl("https://x.example.com/some/path?q=1")).toBe("https://x.example.com");
    expect(normalizeApiUrl("http://localhost:8000")).toBe("http://localhost:8000");
    expect(normalizeApiUrl("http://192.168.1.5:8000")).toBeNull();
    expect(normalizeApiUrl("javascript:alert(1)")).toBeNull();
    expect(normalizeApiUrl("https://user:pw@evil.com")).toBeNull();
    expect(normalizeApiUrl("not a url")).toBeNull();
  });

  it("remembers a chosen server and falls back to the default", () => {
    expect(getApiUrl()).toBe(DEFAULT_API_URL);
    setApiUrl("https://abc.trycloudflare.com/");
    expect(getApiUrl()).toBe("https://abc.trycloudflare.com");
    setApiUrl(null);
    expect(getApiUrl()).toBe(DEFAULT_API_URL);
  });

  it("asks before using a server from a share link, and cleans the address bar", () => {
    window.history.replaceState(null, "", "/workspace?api=https%3A%2F%2Fabc.trycloudflare.com&x=1");
    render(withClient(<ApiLinkHandler />));
    expect(screen.getByText("Use this OwnIt server?")).toBeInTheDocument();
    expect(window.location.search).toBe("?x=1");
    expect(getApiUrl()).toBe(DEFAULT_API_URL); // nothing changes before the visitor agrees
    fireEvent.click(screen.getByRole("button", { name: "Connect" }));
    expect(getApiUrl()).toBe("https://abc.trycloudflare.com");
  });

  it("keeps the current server when the visitor declines, and ignores bad links", () => {
    window.history.replaceState(null, "", "/?api=https%3A%2F%2Fabc.trycloudflare.com");
    const { unmount } = render(withClient(<ApiLinkHandler />));
    fireEvent.click(screen.getByRole("button", { name: "Keep the current server" }));
    expect(getApiUrl()).toBe(DEFAULT_API_URL);
    unmount();
    window.history.replaceState(null, "", "/?api=http%3A%2F%2Fevil.example.com");
    render(withClient(<ApiLinkHandler />));
    expect(screen.queryByText("Use this OwnIt server?")).toBeNull();
  });
});
