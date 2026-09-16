import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import App from "../src/App";

describe("Dashboard", () => {
  it("renders the analysis symbol input and action", () => {
    render(<App />);

    expect(screen.getByLabelText(/stock symbol/i)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /analyze/i })).toBeInTheDocument();
  });
});
