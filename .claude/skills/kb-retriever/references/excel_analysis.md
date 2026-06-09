# CSV Analysis (pandas)

> Read this in full BEFORE you analyze a CSV. Read `excel_reading.md` first (how to load).
> This covers filtering, aggregation, and the common analyses our knowledge base needs.

## Quick reference

| Task | Method | Example |
|---|---|---|
| Filter rows | boolean index | `df[df["Annual Cost"] > 100000]` |
| Date-window filter | `to_datetime` + comparison | `df[(df["End Date"] >= start) & (df["End Date"] <= end)]` |
| Sum | `.sum()` | `df["Total Cost"].sum()` |
| Group + aggregate | `groupby` | `df.groupby("Vendor")["Total Cost"].sum()` |
| Sort | `sort_values` | `df.sort_values("End Date")` |
| Count | `len` / `.shape[0]` | `len(window)` |

## Worked example — contracts expiring in a window

```python
import pandas as pd, datetime

df = pd.read_csv("knowledge/school-operations/contracts.csv")
df["End Date"] = pd.to_datetime(df["End Date"], format="%m/%d/%Y", errors="coerce")

asof = pd.Timestamp("2026-06-09")          # use the injected anchor date, not the wall clock
window_end = asof + pd.Timedelta(days=90)
expiring = df[(df["End Date"] >= asof) & (df["End Date"] <= window_end)].sort_values("End Date")

print(len(expiring))                        # count
print(expiring["Annual Cost"].sum())        # combined annual value
print(expiring[["Vendor", "End Date", "Annual Cost"]].head())
```

Cite each row by its natural key. `Contract ID` is mislabeled (it holds job titles), so key a
contract row by **(Vendor, End Date)**, not by `Contract ID`.

## Worked example — maintenance spend

```python
df = pd.read_csv("knowledge/school-operations/maintenance.csv")
print(df["Total Cost"].sum(), len(df))                  # total spend, ticket count
print(df.groupby("Vendor")["Total Cost"].sum().sort_values(ascending=False).head())  # top vendors
```

## The absence check

Before answering an "overdue" / "status" / "penalty" style question, list the columns and confirm
the field exists:

```python
print(df.columns.tolist())
```

If the field is absent, that is your evidence — say "not available" and cite the column set. Do not
invent a value. Vendors in `maintenance.csv` are providers we pay, not customers who owe us, so
there is no "customer overdue" relationship in the data.
