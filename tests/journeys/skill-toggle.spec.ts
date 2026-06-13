import { test, expect } from "@playwright/test";

// Lean<->full retrieval-skill toggle gate (permanent regression guard).
// Derived from the toggle in app/page.tsx + the cost-lean kb-retriever-lean variant.
//
// KEYLESS: the toggle is client-side, so this asserts RENDER + BEHAVIOR with NO agent round-trip
// (unlike the answer specs — it stubs the submit/poll). Removable-handler-proof: delete the toggle,
// break setSkill, or stop sending `skill` and these go red. Verified live on the agent box via
// scripts/capture-skill-toggle.mjs (which also captured the golden screenshots in
// docs/features/live-upload/images/skill-toggle*.png); this is the same logic for CI's full chromium.
//
// SCOPE: proves the SWITCH works (renders, flips, the choice is what gets SENT). It does NOT prove
// the lean skill's ANSWER quality — that needs a live agent run (the eval goldens), which is blocked
// by the Anthropic usage limit. Built + this gate != answer-validated.

test("toggle renders, defaults to full, flips to lean and back", async ({ page }) => {
  await page.goto("/");
  await expect(page.getByTestId("skill-toggle")).toBeVisible();

  const full = page.getByTestId("skill-full");
  const lean = page.getByTestId("skill-lean");

  await expect(full).toHaveAttribute("aria-checked", "true"); // default = full
  await expect(lean).toHaveAttribute("aria-checked", "false");

  await lean.click();
  await expect(lean).toHaveAttribute("aria-checked", "true");
  await expect(full).toHaveAttribute("aria-checked", "false");

  await full.click();
  await expect(full).toHaveAttribute("aria-checked", "true");
  await expect(lean).toHaveAttribute("aria-checked", "false");
});

test("the selected skill is sent on the ask request (UI -> wire)", async ({ page }) => {
  await page.goto("/");

  // Stub submit + poll so NO real agent run happens (keyless); capture the body the UI sends.
  let sentBody: { skill?: string; question?: string } | null = null;
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

  await page.getByTestId("skill-lean").click();
  await page.getByLabel("Ask a question").fill("any question");
  await page.getByRole("button", { name: "Ask", exact: true }).click();

  await expect.poll(() => sentBody?.skill).toBe("lean");
});
