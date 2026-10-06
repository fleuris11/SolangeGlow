import { screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import messages from "@/messages/fr.json";
import { called, mockApi } from "@/test/fetch-mock";
import { renderWithProviders } from "@/test/render";

import { HealthStatus } from "./health-status";

describe("HealthStatus", () => {
  it("shows that the server responds", async () => {
    const fetchMock = mockApi([{ path: "/health", body: { status: "ok" } }]);

    renderWithProviders(<HealthStatus />);

    expect(await screen.findByText(messages.health.ok)).toBeInTheDocument();
    expect(called(fetchMock, "/health", "GET")).toBe(true);
  });

  it("explains what to do when the server is down", async () => {
    mockApi([{ path: "/health", status: 502, body: {} }]);

    renderWithProviders(<HealthStatus />);

    expect(await screen.findByText(messages.health.error)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: messages.health.retry })).toBeInTheDocument();
  });
});
