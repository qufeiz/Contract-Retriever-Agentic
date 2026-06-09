# Dropped sources — vetted, then dropped (do NOT answer from these)

These were inspected at the row level and dropped for a specific, named defect. Building on them
would produce confident, fabricated answers. If asked about their domain, state it's unavailable
because the source is defective (name the defect) — do not retrieve from these files.

| File | Intended domain | Verdict & exact defect |
|---|---|---|
| `enrollment.csv` (school data 2) | course enrollment | UNUSABLE — `term_name` is 100% a Ruby error string; `status` holds gender values. Header/data misaligned. |
| `payroll_v1.csv` (school data 4) | payroll | DROPPED — `pay_method` & `payroll_notes` are 100% error strings. |
| `payroll_v2.csv` (school data 6) | payroll (alt) | DROPPED — `pay_month` ranges 1–100; `payment_method` is a random integer; 80+ currency codes; irreconcilable with payroll_v1. |
| `invoice_volume.csv` (school data 5) | invoice totals | UNUSABLE — all 788 rows identical (students=180, invoices_per_student=6, total=1080). Zero variance. |
| `people.csv` (school data) | person directory | OUT OF SCOPE — generic id/name/email/gender/ip list; no business question; PII-shaped. |
