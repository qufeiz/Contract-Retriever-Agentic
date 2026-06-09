# 02 — Golden Examples: Case File Q&A

Derived from: 01-design.md §workflow (the single golden scenario: Final Judgment + corroborated grounds + filing-date conflict) + the page-level facts verified in 00-research.md.

> **The acceptance bar.** Every example is built from **real page-level facts** in the two Carter PDFs, each cited to its **file + page/section**. `validateCaseAnswer()` in `03` must pass these and fail any answer that drops a citation, hallucinates a holding, conflates the documents, or silently resolves the conflict.

> **Exact filenames (cite these in full):** the court case file is **`📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf`** (the "Court Case File" below) — the ONLY document containing the Final Judgment (Page 24). The narrative is **`story if the Carters .pdf`** (the "case story"/"narrative" below). The Final Judgment must **never** be cited to the story PDF — it isn't in it.

> **Citation format.** The examples below write citations in readable prose (*[source: …, Page 24]*); the **engine renders them as inline `[P:<doc>#<page>]` tokens** (document pages) — e.g. the Final Judgment is `[P:family-court#24]` (the engine's short doc-id for the case file). Same citation, two forms: prose for readability here, the `[P:…]` token in the engine's golden answer + screenshots, with `03`'s gates asserting the token resolves to the real document page. This is a **document-only** feature — answers use `[P:…]` tokens, never `[S:…]` table tokens.

---

## Golden Example A — the Final Judgment (the headline, EN)

**Question:** *"What was the final child support amount, and who got primary residence in the Carter case?"*

**The grounded answer the system must produce:**

> Per the **Final Judgment**, the court ordered **child support of $1,285/month**, with **primary residence to Joni Carter** and **joint legal custody**. The marriage was dissolved, assets divided as an **equal split**, and a **home sale ordered within 12 months**. *[source: `📄 FAMILY COURT CASE FILE (MOCK) – FINAL VERSION.pdf`, **Page 24 – Final Judgment**]*

**Why this is golden:** every fact is a real Page-24 finding, cited to the specific page. The dollar figure (**$1,285/month**) and the residence (**Joni Carter**) are verifiable by opening the PDF to Page 24 — citation-to-page is the trust mechanism.

---

## Golden Example B — corroborated grounds (multi-document, EN)

**Question:** *"What were the grounds for the Carters' divorce?"*

**The grounded answer:**

> The grounds were a progression of addiction-driven instability: **online gambling** discovered in 2018, escalating through 2019–2023 (debt, secrecy, emotional withdrawal), then **regular alcohol use and a 2023 domestic incident in which Michel raised his hand toward Joni**, followed by repeated failed recovery attempts, leading Joni to file in 2026. *[source: Court Case File, **Pages 11–14 – Grounds for Divorce**]* This account is **corroborated by the case narrative**, which lists the same five reasons — chronic gambling, escalating alcohol use, the domestic-violence incident, emotional/psychological harm to the children, and the breakdown of the partnership. *[source: `story if the Carters .pdf`, "Decision to File for Divorce"]*

**Why this is golden:** the finding is **cited to both documents** — the structured court file *and* the narrative — demonstrating multi-document corroboration. A single-source answer would be weaker; conflating the two into one uncited blob would fail.

---

## Golden Example C — surfacing a source conflict (the discriminating example, EN)

**Question:** *"When did Joni Carter file for divorce?"*

**The grounded answer:**

> The sources **disagree on the exact filing date**:
> - The Court Case File **cover sheet** lists **"Filed: 10 February 2026."** *[source: Court Case File, Page 1 – Cover Sheet]*
> - However, both the Court Case File's grounds narrative and the case story state Joni filed on **February 3, 2026.** *[source: Court Case File, Pages 11–14; and `story if the Carters .pdf`, "Decision to File for Divorce"]*
> I'm surfacing both rather than picking one, since the provided documents conflict.

**Why this is golden:** a trustworthy document-QA system **surfaces the discrepancy and cites both sources** instead of silently averaging or guessing. This is the single clearest demonstration of "source attribution you can trust" in this feature — and it's a real conflict in the actual documents, not a contrived one.

---

## Golden Example D — the same Final-Judgment question in Hebrew (HE)

**Question:** *"מה היה סכום המזונות הסופי ולמי ניתנה המשמורת העיקרית בתיק קרטר?"*

**The grounded answer (Hebrew), same facts, same citation:**

> על פי **פסק הדין הסופי**, בית המשפט קבע **מזונות ילדים בסך $1,285 לחודש**, עם **מגורים עיקריים אצל ג'וני קרטר** ומשמורת משפטית משותפת; חלוקת הרכוש שווה ונקבעה מכירת הבית תוך 12 חודשים. *[מקור: תיק בית המשפט, **עמוד 24 – פסק דין סופי**]*

**Why this is golden:** the **$1,285/month figure and the Page-24 citation are identical** to Example A — the Hebrew path preserves the fact and the citation.

---

## Toy-vs-real contrast (the line `validateCaseAnswer()` enforces)

| Aspect | ❌ Toy / sub-par answer | ✅ Real / golden answer |
|---|---|---|
| **The finding** | "The court awarded some child support and gave custody to the mother." | "**$1,285/month**, **primary residence Joni Carter**, joint legal custody." — exact, named. |
| **Citation** | "According to the case file…" *(which page? unverifiable)* | "**Page 24 – Final Judgment**" — a page-level citation a human can open and check. |
| **Corroboration** | one source, or a merged uncited blob. | the grounds **cited to both documents**, kept distinct. |
| **Conflict** | "Joni filed on February 3, 2026." *(silently picks one; hides that the cover says Feb 10)* | **surfaces both dates with both citations** and notes the conflict. |
| **Hallucination** | "The judgment also awarded spousal support of $2,000/month." *(not in the documents)* | only facts present in the documents; "**not stated in the case file**" for the rest. |
| **Exhibits** | invents the contents of Exhibit C (credit-card records). | "the exhibit is referenced but its contents aren't in the provided documents." |
| **Hebrew** | drops the citation or changes the figure. | identical figure + Page-24 citation in Hebrew. |

**The one-line acceptance bar:** *a golden case answer states the exact finding, cites it to a specific document + page/section, corroborates across both documents where they agree, surfaces conflicts with both citations rather than resolving them silently, and says "not stated" rather than hallucinating — in both English and Hebrew.*

---

## Golden screenshots this feature needs (for the Engineer's `user-guide` + README ledger)

| # | Screenshot | What it must show (golden, not toy) |
|---|---|---|
| 1 | `case-final-judgment-answer.png` | Example A — the **$1,285/month** + **primary residence Joni Carter** answer with the **Page 24 – Final Judgment** citation visible. *(headline working shot.)* |
| 2 | `case-grounds-corroborated.png` | Example B — the grounds answer with **two citations** (court file Pages 11–14 + the story PDF) visible, showing multi-document corroboration. |
| 3 | `case-filing-date-conflict.png` | Example C — the **conflict-surfacing** answer showing both Feb 10 and Feb 3 with both citations. *(the trust demonstration.)* |
| 4 | `case-hebrew-judgment.png` | Example D — the **same $1,285 / Page-24 answer in Hebrew** with the citation intact. |

Each must show the assistant **answering real questions over the real case documents** with citations visible — never a placeholder, an empty state, or a toy document.
