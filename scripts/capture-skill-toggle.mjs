// Keyless visual + behavior gate for the lean<->full retrieval-skill toggle.
// Loads the RUNNING app, asserts the toggle renders + actually flips
// (default "full" -> "lean" -> "full"), and captures golden screenshots of both states.
// No agent run / no Anthropic call — the toggle is client-side. Uses the bundled headless
// chromium (chromium.launch(), no channel) so it runs on the agent box.
//
//   node scripts/capture-skill-toggle.mjs   (with `next dev` running on :3000)
import { chromium } from "playwright";

const BASE = process.env.BASE_URL || "http://localhost:3000";
const OUT = process.env.OUT || "docs/features/live-upload/images/skill-toggle.png";

function assert(cond, msg) {
  if (!cond) throw new Error("ASSERT FAILED: " + msg);
  console.log("  ok:", msg);
}

const browser = await chromium.launch();
const page = await browser.newPage({
  viewport: { width: 1120, height: 920 },
  deviceScaleFactor: 2,
});
try {
  await page.goto(BASE, { waitUntil: "networkidle", timeout: 60_000 });

  const toggle = page.locator('[data-testid="skill-toggle"]');
  await toggle.waitFor({ state: "visible", timeout: 30_000 });
  assert(await toggle.isVisible(), "skill-toggle renders");

  const full = page.locator('[data-testid="skill-full"]');
  const lean = page.locator('[data-testid="skill-lean"]');

  // default state = full
  assert((await full.getAttribute("aria-checked")) === "true", "default selected = full");
  assert((await lean.getAttribute("aria-checked")) === "false", "lean not selected by default");
  await page.screenshot({ path: OUT });
  console.log("golden (full) ->", OUT);

  // flip to lean — must actually move the selection
  await lean.click();
  assert((await lean.getAttribute("aria-checked")) === "true", "click lean -> lean selected");
  assert((await full.getAttribute("aria-checked")) === "false", "full deselected after lean");
  const OUT_LEAN = OUT.replace(/\.png$/, "-lean.png");
  await page.screenshot({ path: OUT_LEAN });
  console.log("golden (lean) ->", OUT_LEAN);

  // flip back to full
  await full.click();
  assert((await full.getAttribute("aria-checked")) === "true", "click full -> full re-selected");

  // Behavioral: the selected skill must be SENT on the ask request (UI -> wire). Stub the
  // submit + poll so NO real agent run happens (keyless), capturing the body the UI sends.
  let sentBody = null;
  await page.route("**/api/ask/jobs", async (route) => {
    sentBody = route.request().postDataJSON();
    await route.fulfill({
      status: 202,
      contentType: "application/json",
      body: JSON.stringify({ job_id: "test", status: "running" }),
    });
  });
  await page.route("**/api/ask/jobs/*", async (route) => {
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({
        status: "done",
        result: { question: "q", answer: "ok", evidence: [], trace: [], validation: { ok: true, reasons: [] } },
      }),
    });
  });
  await lean.click(); // choose lean, then ask
  await page.getByLabel("Ask a question").fill("any question");
  await page.getByRole("button", { name: "Ask", exact: true }).click();
  await page.waitForTimeout(800);
  assert(sentBody !== null, "ask request was sent");
  assert(sentBody.skill === "lean", "ask request body carries skill='lean' (UI choice reaches the wire)");

  console.log("ALL TOGGLE ASSERTIONS PASSED");
} finally {
  await browser.close();
}
