import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider, useQuery } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { setApiUrl } from "@/lib/api";

const health = vi.fn();
vi.mock("@/lib/api", async (orig) => {
  const real = await orig<typeof import("@/lib/api")>();
  return { ...real, api: { ...real.api, health: () => health() } };
});

// imported after the mock
const { ServerOfflineBanner } = await import("./ServerOfflineBanner");

function show() {
  return render(
    <QueryClientProvider client={new QueryClient({ defaultOptions: { queries: { retry: false } } })}>
      <ServerOfflineBanner />
    </QueryClientProvider>,
  );
}

describe("ServerOfflineBanner", () => {
  beforeEach(() => {
    window.localStorage.clear();
    health.mockReset();
  });

  it("stays hidden while the server answers", async () => {
    health.mockResolvedValue({ status: "ok", languagetool: true });
    show();
    await waitFor(() => expect(health).toHaveBeenCalled());
    expect(screen.queryByRole("alert")).toBeNull();
  });

  it("explains how to start a local server when it is down", async () => {
    health.mockRejectedValue(new Error("Failed to fetch"));
    show();
    expect(await screen.findByRole("alert")).toHaveTextContent("Can't reach the OwnIt server");
    expect(screen.getByText(/scripts\\dev\.ps1/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Retry/ })).toBeInTheDocument();
    expect(screen.getByLabelText("Server address")).toBeInTheDocument();
  });

  it("asks for a new link when a shared server is down", async () => {
    setApiUrl("https://abc.trycloudflare.com");
    health.mockRejectedValue(new Error("Failed to fetch"));
    show();
    expect(await screen.findByText(/Ask for a new link/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back to the default server" })).toBeInTheDocument();
  });
});

describe("ServerOfflineBanner recovery", () => {
  it("re-runs failed requests once the server answers again", async () => {
    window.localStorage.clear();
    health.mockReset();
    health.mockRejectedValueOnce(new Error("Failed to fetch")).mockResolvedValue({ status: "ok", languagetool: true });
    const analyze = vi.fn().mockRejectedValueOnce(new Error("Failed to fetch")).mockResolvedValue("ok");
    const client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
    function Analysis() {
      const q = useQuery({ queryKey: ["analyze"], queryFn: analyze });
      return <p>{q.isSuccess ? "analysed" : "waiting"}</p>;
    }
    render(
      <QueryClientProvider client={client}>
        <ServerOfflineBanner />
        <Analysis />
      </QueryClientProvider>,
    );
    fireEvent.click(await screen.findByRole("button", { name: /Retry/ }));
    expect(await screen.findByText("analysed")).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole("alert")).toBeNull());
  });
});
