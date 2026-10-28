import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { NewsEventsPanel } from "./NewsEventsPanel";

describe("NewsEventsPanel", () => {
  it("shows provenance and warns when publication time is unknown", () => {
    render(
      <NewsEventsPanel
        loading={false}
        error={null}
        result={{
          events: [{
            event_id: "event-1",
            title: "Company announcement",
            source_name: "Configured feed",
            source_type: "other",
            source_url: "https://example.com/story",
            category: "company_announcement",
            published_at: null,
            retrieved_at: "2026-10-28T08:00:00Z",
            entity_match_confidence: "0.85",
          }],
        }}
      />,
    );

    expect(screen.getByRole("link", { name: "Company announcement" }).getAttribute("href"))
      .toBe("https://example.com/story");
    expect(screen.getByText(/do not use this event as historical point-in-time evidence/i))
      .toBeTruthy();
    expect(screen.getByText(/Configured feed · other/)).toBeTruthy();
  });

  it("explains empty results without claiming there is no news", () => {
    render(
      <NewsEventsPanel loading={false} error={null} result={{ events: [] }} />,
    );
    expect(screen.getByText(/does not prove that no relevant news exists/i)).toBeTruthy();
  });

  it("renders loading and configuration errors accessibly", () => {
    const { rerender } = render(
      <NewsEventsPanel loading={true} error={null} result={null} />,
    );
    expect(screen.getByRole("status").textContent).toContain("Loading");

    rerender(
      <NewsEventsPanel
        loading={false}
        error={Object.assign(new Error("Unavailable"), { status: 503 })}
        result={null}
      />,
    );
    expect(screen.getByRole("alert").textContent).toMatch(/not configured/i);
  });
});
