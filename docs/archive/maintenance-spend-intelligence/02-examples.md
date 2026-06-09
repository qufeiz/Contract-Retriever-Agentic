# 02 — Golden Examples: Maintenance Spend Intelligence

Derived from: 01-design.md §workflow (the single golden scenario: the honest refusal of literal Q2 + a real spend answer) + the verified figures in 00-research.md.

> **The acceptance bar.** The headline example here is the **honest refusal** — the single clearest demonstration of the trust property the client is paying for — paired with a **real, cited spend answer** so the feature is shown *working*, not just refusing. `validateNoFabrication()` in `03` must pass these and fail any answer that invents an overdue status.

> **Citation format.** The examples below write citations in readable prose (*[source: `maintenance` table …]*); the **engine renders them as inline `[S:maintenance#<id>]` tokens** (structured rows), and a spend total cites the set of row tokens that compose it. Same citation, two forms: prose for readability, the `[S:…]` token in the engine's golden answer + screenshots, with `03` asserting the token resolves to a real row. The honest-refusal answers cite the **schema** (the column set) as evidence of absence — they carry **no** row token for the missing "overdue" concept, because no such row exists.

---

## Golden Example A — the literal spec Q2: HONEST REFUSAL (the trust demo, EN)

**Question:** *"Which customers have overdue payments and what does the agreement say about service suspension?"*

**The grounded answer the system must produce:**

> I can't determine **overdue payments** or **service-suspension terms** from this dataset, and here's exactly why:
> - The maintenance dataset (`school data 3.csv`) has **no payment-status, due-date, or paid/unpaid field** — its columns are only *Vendor, Invoice, Labor Cost, Parts Cost, Total Cost, Completion Date*. A completed ticket is not the same as a paid (or overdue) invoice. *[source: `maintenance` table schema — the listed columns are the complete set]*
> - The vendors here (e.g. Oyoba, Voolith) are **maintenance providers we pay**, not customers who owe us — so there is no "customer overdue" relationship in this data either.
> - There is **no service-agreement document** on file defining suspension terms.
>
> So I won't guess an "overdue" list — that would be fabricated. **What I can tell you from this data:** total maintenance spend is **$40,597.00 across 750 tickets**, and I can break that down by vendor, period, or category. Would you like the top vendors by spend, or spend for a specific year?

**Why this is golden:** it (1) **refuses honestly** with the *specific reason* (no status field, vendors aren't customers, no agreement doc), (2) **cites the schema** as the evidence of absence, (3) **does not fabricate** any overdue name or figure, and (4) **pivots to real, cited value** it can actually deliver. This is the answer a trustworthy analyst gives — and exactly the behavior the client says distinguishes a real system from "PDFs in a vector DB."

---

## Golden Example B — a real spend answer (the feature WORKING, EN)

**Question:** *"How much did we spend on maintenance in 2026, and which vendors cost the most overall?"*

**The grounded answer:**

> **In 2026, maintenance spend was $13,485.66 across 248 completed tickets.** *[source: `maintenance` table, `Completion Date` year = 2026 → 248 rows, SUM(Total Cost)]*
> **Top vendors by total spend (all time):**
> | Vendor | Total spend | Tickets |
> |---|---|---|
> | Oyoba | $949.94 | 3 |
> | Voolith | $783.67 | 7 |
> | Photobug | $549.90 | 5 |
> | Zoovu | $525.54 | 3 |
> *[source: `maintenance` table, GROUP BY Vendor, SUM(Total Cost); each figure drillable to its tickets]*
> Across all 750 tickets, total maintenance spend is **$40,597.00**. *[source: `maintenance` table, SUM(Total Cost) over all rows]*

**Why this is golden:** every figure is a **real SQL aggregation cited to the rows** that compose it (verified: $13,485.66/248 for 2026; Oyoba $949.94; $40,597.00 total). It is drillable — a reviewer can sum the rows and get the same number. No invented data.

---

## Golden Example C — the refusal in Hebrew (HE)

**Question:** *"אילו לקוחות מאחרים בתשלומים ומה אומר ההסכם על השעיית שירות?"*

**The grounded answer (Hebrew), same logic, same honesty:**

> לא ניתן לקבוע **איחורים בתשלום** או **תנאי השעיית שירות** מתוך מערך הנתונים הזה: בקובץ `school data 3.csv` אין שדה סטטוס תשלום או תאריך יעד — העמודות הן רק *Vendor, Invoice, Labor Cost, Parts Cost, Total Cost, Completion Date*. הספקים כאן הם מי שאנו משלמים להם, לא לקוחות שחייבים לנו, ואין מסמך הסכם המגדיר השעיה. *[מקור: סכמת הטבלה]*
> **מה כן ניתן:** סך ההוצאה על תחזוקה הוא **$40,597.00** על פני 750 כרטיסים, וניתן לפלח לפי ספק, תקופה או קטגוריה.

**Why this is golden:** the Hebrew refusal carries the **identical reasoning, the same schema citation, and the same $40,597.00 figure** — the honesty and the citations survive translation.

---

## Toy-vs-real contrast (the line `validateNoFabrication()` enforces)

| Aspect | ❌ Toy / dangerous answer | ✅ Real / golden answer |
|---|---|---|
| **Overdue question** | "Customers Oyoba and Voolith have overdue payments totaling $1,733." *(fabricated — there is no payment status; these are vendors, not customers)* | "There's **no payment-status field** in this data, so I can't determine overdue payments — and I won't guess." |
| **Evidence** | none — confident assertion | **cites the schema** (the columns that exist) to prove the field is absent. |
| **Vendors vs customers** | calls vendors "customers who owe." | states vendors are **providers we pay**, not debtors. |
| **Suspension terms** | "The agreement suspends service after 30 days overdue." *(no such agreement exists)* | "There is **no service-agreement document** on file defining suspension." |
| **Recovery** | leaves the user with fiction. | **pivots to real, cited spend analysis** ($40,597.00 total, top vendors). |
| **Spend figures** | "We spent roughly forty thousand on maintenance." | "**$40,597.00 across 750 tickets**" — exact, cited, drillable. |
| **Hebrew** | refuses in EN but fabricates or errors in HE. | identical honest refusal + figures in HE. |

**The one-line acceptance bar:** *when asked for a field the data doesn't have (overdue/paid/suspension/customer-debt), the answer says so, cites the schema as evidence of the absence, fabricates nothing, and pivots to the real cited spend analysis it can do — in both English and Hebrew.*

---

## Golden screenshots this feature needs (for the Engineer's `user-guide` + README ledger)

| # | Screenshot | What it must show (golden, not toy) |
|---|---|---|
| 1 | `maintenance-spend-breakdown.png` | Example B **doing real work** — the 2026 total **$13,485.66 / 248 tickets**, the top-vendor table (Oyoba $949.94 …), the $40,597.00 grand total, with **citations to rows** visible. *(This is the headline "working" shot — must NOT be a no-results state.)* |
| 2 | `maintenance-overdue-honest-refusal.png` | Example A — the **honest refusal** of the literal Q2, with the schema-citation evidence visible. Clearly labeled as the *honesty/trust* demonstration. |
| 3 | `maintenance-hebrew-refusal.png` | Example C — the **same honest refusal in Hebrew** with the $40,597.00 figure intact. |

The headline shot (1) shows the feature **working on real data**; the refusal shots (2,3) are the trust demonstration and must be **clearly labeled as the refusal case** so the README/user-guide doesn't read as "the product can't do anything." Per the self-check: a refusal is a fine *separate* shot, but the headline must show real work.
