// Capture ONLY g1-citation-resolves.png — the "click a citation chip → the
// source row highlights" behavior — using the FAST single-contract query (one
// contracts.csv row, ~1 min) instead of the 8.5-min 38-row G-1 run. The
// click-to-source behavior is identical; this is the credit-efficient capture.
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "../docs/features/agentic-knowledge-assistant/images");
const BASE = process.env.CAPTURE_BASE_URL ?? "http://localhost:3000";
const Q = "When does the Skalith Project Manager contract expire and what is its penalty?";

const browser = await chromium.launch();
try {
  const page = await browser.newPage({ viewport: { width: 1100, height: 1400 } });
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.getByLabel("Ask a question").fill(Q);
  await page.getByRole("button", { name: "Ask" }).click();
  await page.getByTestId("answer").waitFor({ state: "visible", timeout: 200_000 });
  const chip = page.locator(".cite").first();
  await chip.click();
  await page.waitForTimeout(1500); // let the source panel scroll + highlight
  await page.screenshot({ path: resolve(OUT, "g1-citation-resolves.png"), fullPage: true });
  console.log("saved g1-citation-resolves.png");
} finally {
  await browser.close().catch(() => {});
}
