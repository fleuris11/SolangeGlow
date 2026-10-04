import { screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import messages from "@/messages/fr.json";
import { renderWithProviders } from "@/test/render";

import { HealthStatus } from "./health-status";

function mockFetch(response: Partial<Response>) {
  vi.stubGlobal("fetch", vi.fn().mockResolvedValue(response));
}

describe("HealthStatus", () => {
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it("shows that the server responds", async () => {
    mockFetch({ ok: true, status: 200, json: async () => ({ status: "ok" }) });

    renderWithProviders(<HealthStatus />);

    expect(await screen.findByText(messages.health.ok)).toBeInTheDocument();
    expect(fetch).toHaveBeenCalledWith("/api/v1/health", expect.anything());
  });

  it("explains what to do when the server is down", async () => {
    mockFetch({ ok: false, status: 502, json: async () => ({}) });

    renderWithProviders(<HealthStatus />);

    expect(await screen.findByText(messages.health.error)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: messages.health.retry })).toBeInTheDocument();
  });
});
