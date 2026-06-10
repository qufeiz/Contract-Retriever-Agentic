// Capture the golden screenshots for the agentic-knowledge-assistant feature ledger.
// Drives the LIVE app (real agent round-trips) and saves the named PNGs the user-guide + README
// reference. Run with the frontend (:3000) + backend (:8000) up:
//   node scripts/capture-golden-screenshots.mjs
//
// Each shot is captured at the pinned asOfDate=2026-06-09 so the 38 count is stable.
import { chromium } from "playwright";
import { mkdirSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "../docs/features/agentic-knowledge-assistant/images");
mkdirSync(OUT, { recursive: true });

const BASE = process.env.CAPTURE_BASE_URL ?? "http://localhost:3000";
// The slowest golden query (G-1, the 38-row contract table) is an ~8.5-minute
// real agent run, so the per-answer wait is configurable. Default 170s suits the
// faster queries / the public demo; bump it (e.g. 560000) when capturing the
// heavy G-1 shot against a host without a request-timeout cap.
const ANSWER_TIMEOUT = Number(process.env.CAPTURE_ANSWER_TIMEOUT ?? 170_000);

// [filename, question, optional post-action ("clickFirstChip")]
const SHOTS = [
  ["g1-contract-90day-answer.png", "What contracts expire in the next 90 days and what penalties are defined in those contracts?"],
  ["g1-citation-resolves.png", "What contracts expire in the next 90 days and what penalties are defined in those contracts?", "clickFirstChip"],
  ["g2-final-judgment-answer.png", "What was the final child support amount, and who got primary residence in the Carter case?"],
  ["g3-overdue-honest-refusal.png", "Which customers have overdue payments and what does the agreement say about service suspension?"],
  ["g4-filing-date-conflict.png", "When did Joni Carter file for divorce?"],
  ["g2-hebrew-judgment.png", "מה היה סכום המזונות הסופי ולמי ניתנה המשמורת העיקרית בתיק קרטר?"],
];

// Use the bundled headless_shell chromium (default launch target).
const browser = await chromium.launch();
const page = await browser.newPage({ viewport: { width: 1100, height: 1400 } });

for (const [file, question, action] of SHOTS) {
  console.log(`→ ${file}`);
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.getByLabel("Ask a question").fill(question);
  await page.getByRole("button", { name: "Ask" }).click();
  await page.getByTestId("answer").waitFor({ state: "visible", timeout: ANSWER_TIMEOUT });
  if (action === "clickFirstChip") {
    const chip = page.locator(".cite").first();
    if (await chip.count()) {
      await chip.click();
      await page.waitForTimeout(1200); // let the source panel scroll/highlight
    }
  }
  await page.screenshot({ path: resolve(OUT, file), fullPage: true });
}

await browser.close();
console.log("done — screenshots in", OUT);
