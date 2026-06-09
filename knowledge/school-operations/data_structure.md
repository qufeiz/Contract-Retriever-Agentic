# School Operations — structured CSV data

| File | Domain | Notes (read before you answer) |
|---|---|---|
| `contracts.csv` | Vendor contracts (1000 rows) | Columns: `Contract ID, Vendor, Start Date, End Date, Annual Cost`. **`Contract ID` is MISLABELED — it holds job titles** (Registered Nurse, Staff Scientist…), NOT identifiers; treat it as a role label, key rows by (Vendor + End Date). Many `End Date` values **precede** their `Start Date` — preserve and may flag these; do NOT drop or "fix" them. **NO penalty / termination / notice column, and NO vendor-contract documents exist anywhere in this knowledge base** → penalty/termination terms have NO source; answer "not available", never fabricate, never reach into carter-case/. |
| `maintenance.csv` | Maintenance tickets / invoices (750 rows) | Columns: `Ticket ID, Vendor, Invoice, Labor Cost, Parts Cost, Total Cost, Completion Date` (Labor + Parts = Total). Supports real spend analysis (total $40,597.00 / 750; 2026 $13,485.66 / 248; top vendor Oyoba $949.94). **HONESTY BOUNDARY: there is NO payment-status, due-date, or paid/unpaid field**; the vendors are providers we PAY, not customers who owe us; there is **no service-agreement document**. So "overdue payments" / "service suspension" are NOT answerable — say so and cite the column set as evidence of absence; never fabricate an overdue list. `Ticket ID` also holds product/category names, not ids. |

`_dropped/` — five sources vetted and DROPPED for specific defects (see its data_structure.md). Do NOT build answers on them.
