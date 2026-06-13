// Capture the live-upload golden screenshots against the RUNNING demo (real upload + real agent
// round-trip — not a mock). One Sonnet run for U-1 yields BOTH the cross-source answer shot and the
// citation-resolve shot (a click on the same render). U-2 (honest absence) is a second run.
//
// Usage:
//   CAPTURE_BASE_URL=https://aletheia-agentic-demo.vercel.app node scripts/capture-upload-golden.mjs
//   (omit CAPTURE_BASE_URL for a local stack on :3000)
import { chromium } from "playwright";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const __dirname = dirname(fileURLToPath(import.meta.url));
const OUT = resolve(__dirname, "../docs/features/live-upload/images");
const FX = resolve(__dirname, "../docs/features/live-upload/fixtures");
const BASE = process.env.CAPTURE_BASE_URL ?? "http://localhost:3000";

const XLSX = resolve(FX, "customers.xlsx");
const CSV = resolve(FX, "customers.csv");
const PDF = resolve(FX, "service-agreement.pdf");

function assert(c, m) {
  if (!c) throw new Error("ASSERT FAILED: " + m);
  console.log("  ok:", m);
}
const U1 = "Which customers have overdue payments, and what does their contract say about service suspension?";
const U2 = "Which customers have overdue payments, and what's the penalty interest rate if they don't pay?";

async function uploadAndAsk(page, files, question) {
  await page.goto(BASE, { waitUntil: "networkidle" });
  await page.getByTestId("file-input").setInputFiles(files);
  await page.getByTestId("uploaded-files").waitFor({ state: "visible", timeout: 60_000 });
  await page.getByLabel("Ask a question").fill(question);
  // The submit button is the only <button> with the exact text "Ask" (the dropzone is role=button
  // but has no accessible name "Ask"); scope to the form's button to avoid ambiguity.
  await page.locator("form.ask button[type=submit]").click();
  await page.getByTestId("answer").waitFor({ state: "visible", timeout: 220_000 });
}

const browser = await chromium.launch();
try {
  // U-1: upload XLSX + PDF, ask the client's cross-source question.
  const p1 = await browser.newPage({ viewport: { width: 1100, height: 1500 }, deviceScaleFactor: 2 });
  await uploadAndAsk(p1, [XLSX, PDF], U1);
  await p1.evaluate(() => window.scrollTo(0, 0));
  await p1.screenshot({ path: "/tmp/u1-live-capture.png", fullPage: true }); // always, for diagnosis
  const ans = await p1.getByTestId("answer").innerText();
  const val = await p1.getByTestId("validation").innerText().catch(() => "");
  console.log("  validation:", val.replace(/\n/g, " ").trim());
  // Assert the golden facts BEFORE blessing the screenshot — never save a non-golden.
  assert(/18,965\.50/.test(ans), "answer contains the $18,965.50 overdue total");
  assert(/Contoso/.test(ans), "answer names Contoso (the suspension-eligible customer)");
  assert(/Grounded/i.test(val) && !/Rejected/i.test(val), "validation badge = Grounded");
  await p1.screenshot({ path: resolve(OUT, "u1-upload-cross-source-answer.png"), fullPage: true });
  console.log("saved u1-upload-cross-source-answer.png");
  // click a citation chip → source highlights/scrolls
  await p1.locator(".cite").first().click();
  await p1.waitForTimeout(1500);
  await p1.screenshot({ path: resolve(OUT, "u1-citation-resolves.png"), fullPage: true });
  console.log("saved u1-citation-resolves.png");
  console.log("ALL U-1 GOLDEN ASSERTIONS PASSED");
  await p1.close();

  // U-2 (honest absence) is a SECOND live agent run (~$0.11) — only when CAPTURE_U2=1.
  if (process.env.CAPTURE_U2 === "1") {
    const p2 = await browser.newPage({ viewport: { width: 1100, height: 1500 }, deviceScaleFactor: 2 });
    await uploadAndAsk(p2, [XLSX], U2);
    await p2.screenshot({ path: resolve(OUT, "u2-honest-absence.png"), fullPage: true });
    console.log("saved u2-honest-absence.png");
    await p2.close();
  } else {
    console.log("skipped U-2 (set CAPTURE_U2=1 to refresh it — costs a 2nd run)");
  }
} finally {
  await browser.close().catch(() => {});
}
