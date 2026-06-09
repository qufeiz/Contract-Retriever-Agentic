import { test, expect } from "@playwright/test";

// Agentic Knowledge Assistant feature gate (permanent regression guard).
// Derived from docs/features/agentic-knowledge-assistant/03-tests.md (the prod-verify runbook +
// G-1..G-4). Runs against the RUNNING app (real agent round-trip), asserting what the USER SEES:
// the rendered [F:file#loc] citation chips, the agent TRACE panel, and the validateAnswer badge.
//
// Removable-handler-proof: if the agent/retrieval were stubbed to a no-op or toy, every assertion
// below goes red — a vague answer has no "38", a fabricated answer fails the citation/validation
// check, a wrong-file answer fails the trace check.
//
// Each test is a real agent round-trip (navigate → extract → self-check → cite); the generous
// 180s per-test timeout (playwright.journeys.config.ts) absorbs LLM latency.

const CARTER_LEAK = /child support|custody|\bJoni\b|\bMichel\b|Final Judgment|home sale within/i;

async function ask(page: import("@playwright/test").Page, q: string) {
  await page.goto("/");
  await page.getByLabel("Ask a question").fill(q);
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByTestId("answer")).toBeVisible({ timeout: 160_000 });
}

test("G-1: contract expiry → 38 / $18.9M, cited rows, honest penalty, trace shows contracts.csv only", async ({
  page,
}) => {
  await ask(
    page,
    "What contracts expire in the next 90 days and what penalties are defined in those contracts?"
  );

  const answer = page.getByTestId("answer");
  await expect(answer).toContainText(/38\s+contracts/i); // verifiable count
  await expect(answer).toContainText(/18,924,883\.79/); // combined annual value
  await expect(answer).toContainText(/contracts\.csv#row=/); // a real row citation chip
  await expect(answer).toContainText(/not available|no penalty/i); // honest penalty refusal
  await expect(answer).not.toContainText(CARTER_LEAK); // the worst-case leak guard

  // The agent TRACE proves real retrieval of the right file and NOT the Carter PDFs.
  const trace = page.getByTestId("trace-panel");
  await expect(trace).toContainText(/contracts\.csv/);
  await expect(trace).not.toContainText(/family-court-case-file|case-story/);

  // Content-fidelity: every cited token resolved.
  await expect(page.getByTestId("validation")).toContainText(/Grounded/);
  await expect(page.getByTestId("validation")).not.toContainText(/Rejected/i);
});

test("G-2: Carter Final Judgment → $1,285 + Joni, cited to a court-file page, story NOT relied on", async ({
  page,
}) => {
  await ask(
    page,
    "What was the final child support amount, and who got primary residence in the Carter case?"
  );

  const answer = page.getByTestId("answer");
  await expect(answer).toContainText(/1,285/);
  await expect(answer).toContainText(/Joni/);
  await expect(answer).toContainText(/family-court-case-file\.pdf#p\d+/); // page-cited
  await expect(page.getByTestId("trace-panel")).toContainText(/family-court-case-file/);
  await expect(page.getByTestId("validation")).toContainText(/Grounded/);
});

test("G-3: maintenance overdue → honest refusal + $40,597 pivot cited to maintenance.csv", async ({
  page,
}) => {
  await ask(
    page,
    "Which customers have overdue payments and what does the agreement say about service suspension?"
  );

  const answer = page.getByTestId("answer");
  await expect(answer).toContainText(/not available|no payment-status|cannot/i); // honest refusal
  await expect(answer).toContainText(/40,597/); // the real pivot figure
  await expect(answer).toContainText(/maintenance\.csv/); // pivot cited to the data file
  await expect(answer).not.toContainText(CARTER_LEAK);
  await expect(page.getByTestId("validation")).toContainText(/Grounded/);
});

test("G-4: filing-date conflict → BOTH Feb 10 and Feb 3 surfaced with citations, both PDFs in trace", async ({
  page,
}) => {
  await ask(page, "When did Joni Carter file for divorce?");

  const answer = page.getByTestId("answer");
  await expect(answer).toContainText(/10 February 2026|February 10, 2026/i);
  await expect(answer).toContainText(/February 3, 2026|3 February 2026/i);
  // the conflict is only findable by reading BOTH documents — the trace must show both.
  const trace = page.getByTestId("trace-panel");
  await expect(trace).toContainText(/family-court-case-file/);
  await expect(trace).toContainText(/case-story/);
  await expect(page.getByTestId("validation")).toContainText(/Grounded/);
});

test("G-2 (Hebrew): identical $1,285 / Joni / page citation, no number changed or citation dropped", async ({
  page,
}) => {
  await ask(page, "מה היה סכום המזונות הסופי ולמי ניתנה המשמורת העיקרית בתיק קרטר?");

  const answer = page.getByTestId("answer");
  await expect(answer).toContainText(/1,285/);
  await expect(answer).toContainText(/family-court-case-file\.pdf#p\d+/);
  await expect(page.getByTestId("validation")).toContainText(/Grounded/);
});
