// One-off golden re-capture: the maintenance overdue-refusal answer, now ✓ Grounded.
// Drives the LIVE deploy (the real engine), waits for the validation banner to read
// "Grounded" (not a stale ✗ Rejected), and writes a full-page screenshot matching the
// existing golden's high-DPI dimensions. Run: node scripts/capture-maintenance-golden.mjs
import { chromium } from "@playwright/test";

const URL = process.env.GOLDEN_BASE_URL ?? "https://contract-retriever-rag.vercel.app";
const OUT =
  "docs/features/maintenance-spend-intelligence/images/maintenance-overdue-honest-refusal.png";
const QUESTION =
  "Which customers have overdue payments and what does the agreement say about service suspension?";

const browser = await chromium.launch();
// Width 1120 @ deviceScaleFactor 2 → 2240px wide, matching the existing golden.
const page = await browser.newPage({ viewport: { width: 1120, height: 1000 }, deviceScaleFactor: 2 });
await page.goto(URL, { waitUntil: "networkidle" });
await page.getByLabel("Ask a question").fill(QUESTION);
await page.getByRole("button", { name: "Ask" }).click();
await page.getByTestId("answer").waitFor({ state: "visible", timeout: 60_000 });

// Hard-require the GREEN banner before capturing — never re-save a ✗ Rejected frame.
const validation = page.getByTestId("validation");
await validation.waitFor({ state: "visible" });
const text = (await validation.textContent()) ?? "";
if (!/Grounded/.test(text) || /Rejected/i.test(text)) {
  console.error(`Refusing to capture — validation banner is not Grounded:\n${text}`);
  await browser.close();
  process.exit(1);
}

await page.screenshot({ path: OUT, fullPage: true });
console.log(`Captured ✓ Grounded golden → ${OUT}`);
await browser.close();
