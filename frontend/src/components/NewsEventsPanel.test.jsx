import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NewsEventsPanel } from "./NewsEventsPanel";

describe("NewsEventsPanel", () => {
  it("renders source links and point-in-time provenance", () => {
    render(
      <NewsEventsPanel
        data={{
          as_of: "2026-10-26T12:00:00Z",
          events: [{
            event_id: "event-1",
            source_name: "Official source",
            source_url: "https://example.com/disclosure",
            title: "Company announces results",
            category: "earnings",
            published_at: "2026-10-26T10:00:00Z",
            first_seen_at: "2026-10-26T10:05:00Z",
            matched_symbols: ["EGAL"],
            entity_match_confidence: "0.99",
          }],
        }}
        loading={false}
        error={null}
      />,
    );

    const link = screen.getByRole("link", { name: "Company announces results" });
    expect(link.getAttribute("href")).toBe("https://example.com/disclosure");
    expect(link.getAttribute("rel")).toBe("noopener noreferrer");
    expect(screen.getByText(/Published:/)).toBeTruthy();
    expect(screen.getByText(/First seen:/)).toBeTruthy();
    expect(screen.getByText(/Entity-match confidence: 0.99/)).toBeTruthy();
  });

  it("does not create a link for an unsafe source URL", () => {
    render(
      <NewsEventsPanel
        data={{
          events: [{
            event_id: "event-2",
            source_name: "Untrusted source",
            source_url: "javascript:alert(1)",
            title: "Untrusted link",
            category: "other",
            published_at: null,
            first_seen_at: "2026-10-26T10:05:00Z",
            matched_symbols: [],
            entity_match_confidence: "0.5",
          }],
        }}
        loading={false}
        error={null}
      />,
    );

    expect(screen.queryByRole("link", { name: "Untrusted link" })).toBeNull();
    expect(screen.getByText("Untrusted link")).toBeTruthy();
  });

  it("announces loading, empty, and error states", () => {
    const { rerender } = render(
      <NewsEventsPanel data={null} loading={true} error={null} />,
    );
    expect(screen.getByRole("status")).toBeTruthy();

    rerender(
      <NewsEventsPanel data={{ events: [] }} loading={false} error={null} />,
    );
    expect(screen.getByText(/No qualifying news events/)).toBeTruthy();

    rerender(
      <NewsEventsPanel data={null} loading={false} error={new Error("Feed unavailable")} />,
    );
    expect(screen.getByRole("alert").textContent).toContain("Feed unavailable");
  });
});
