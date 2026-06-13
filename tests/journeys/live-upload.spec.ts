import { test, expect } from "@playwright/test";
import path from "node:path";

// Live-upload feature gate (permanent regression guard).
// Derived from docs/features/live-upload/02-examples.md (U-1 the cross-source golden + U-2 the
// honest-absence guard). Runs against the RUNNING app (real upload + real agent round-trip),
// asserting what the USER SEES: the uploaded-file list, the rendered [F:<uploaded-file>#<loc>]
// citation chips resolved against the SESSION uploads, the agent TRACE opening BOTH uploaded files,
// and the validateAnswer Grounded badge.
//
// Removable-handler-proof: if the upload were dropped, the session_id not threaded, or the agent
// stubbed, every assertion goes red — a non-uploaded answer has no $18,965.50, no #row-/#p3 chip
// resolved against the uploads, and the trace wouldn't show customers.csv + the contract.
//
// Each test is a real upload + agent round-trip; the generous 180s timeout absorbs LLM latency.

const FIXTURES = path.resolve(__dirname, "../../docs/features/live-upload/fixtures");
const CSV = path.join(FIXTURES, "customers.csv");
const PDF = path.join(FIXTURES, "service-agreement.pdf");

async function upload(page: import("@playwright/test").Page, files: string[]) {
  await page.goto("/");
  await page.getByTestId("file-input").setInputFiles(files);
  // The uploaded-files list appears once the backend stored + parsed them.
  await expect(page.getByTestId("uploaded-files")).toBeVisible({ timeout: 60_000 });
}

async function ask(page: import("@playwright/test").Page, q: string) {
  await page.getByLabel("Ask a question").fill(q);
  await page.getByRole("button", { name: "Ask" }).click();
  await expect(page.getByTestId("answer")).toBeVisible({ timeout: 160_000 });
}

test("U-1: upload CSV+PDF → cross-source answer, $18,965.50, rows + §4.3#p3 cited, both files in trace", async ({
  page,
}) => {
  await upload(page, [CSV, PDF]);
  // both uploaded files are shown as ready
  await expect(page.getByTestId("uploaded-customers.csv")).toBeVisible();
  await expect(page.getByTestId("uploaded-service-agreement.pdf")).toBeVisible();

  await ask(
    page,
    "Which customers have overdue payments, and what does their contract say about service suspension?"
  );

  const answer = page.getByTestId("answer");
  await expect(answer).toContainText(/18,965\.50/); // the exact overdue total
  await expect(answer).toContainText(/Contoso/); // the suspension-eligible customer
  await expect(answer).toContainText(/customers\.csv#row-\d+/); // an uploaded CSV row chip
  await expect(answer).toContainText(/service-agreement\.pdf#p3/); // the §4.3 page chip

  // The agent TRACE proves it opened BOTH uploaded files (an answer using one is incomplete).
  const trace = page.getByTestId("trace-panel");
  await expect(trace).toContainText(/customers\.csv/);
  await expect(trace).toContainText(/service-agreement/);

  // Content-fidelity: every cited token resolved against the SESSION uploads root.
  await expect(page.getByTestId("validation")).toContainText(/Grounded/);
  await expect(page.getByTestId("validation")).not.toContainText(/Rejected/i);
});

test("U-2: upload only the CSV → lists overdue, HONESTLY refuses the penalty rate (no fabricated rate)", async ({
  page,
}) => {
  await upload(page, [CSV]);
  await expect(page.getByTestId("uploaded-customers.csv")).toBeVisible();

  await ask(
    page,
    "Which customers have overdue payments, and what's the penalty interest rate if they don't pay?"
  );

  const answer = page.getByTestId("answer");
  await expect(answer).toContainText(/customers\.csv#row-\d+/); // overdue still cited
  await expect(answer).toContainText(/not available|no .*(rate|penalty)|wasn't uploaded|no contract/i); // honest refusal
  await expect(answer).not.toContainText(/1\.5%/); // the rate lives only in the (un-uploaded) contract — must NOT appear
  await expect(page.getByTestId("validation")).toContainText(/Grounded/);
});
