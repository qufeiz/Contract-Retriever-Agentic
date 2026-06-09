# CSV Reading (pandas)

> Read this in full BEFORE you process a CSV in the knowledge base. It tells you how to load and
> inspect a CSV with pandas without reading the whole file into context. Pair it with
> `excel_analysis.md` for filtering/aggregation.

Our knowledge base stores structured data as `.csv` files. Use pandas.

## Quick start

```python
import pandas as pd

# Preview structure WITHOUT loading the whole file
df_preview = pd.read_csv("knowledge/school-operations/contracts.csv", nrows=10)
print(df_preview.columns.tolist())   # the real column set — check before assuming a field exists
print(df_preview.head())

# Load only the columns you need
df = pd.read_csv("knowledge/school-operations/contracts.csv",
                 usecols=["Vendor", "End Date", "Annual Cost"])
```

## Inspect the columns FIRST (the honesty step)

Before answering, confirm which fields actually exist — do not assume a field because the question
implies it:

```python
df = pd.read_csv(path)
print(df.columns.tolist())   # e.g. contracts.csv has NO penalty column; maintenance.csv has NO payment-status field
print(df.shape)              # row count
print(df.head(3))
```

If the asked-for concept has no column, that is the evidence of absence — cite the column set and
say "not available", do not fabricate.

## Dates

Many columns are date strings (`M/D/YYYY`). Parse explicitly before comparing:

```python
df["End Date"] = pd.to_datetime(df["End Date"], format="%m/%d/%Y", errors="coerce")
```

`errors="coerce"` turns unparseable values into `NaT` instead of crashing — important because some
rows are malformed. **Do not drop malformed or out-of-order rows silently** (e.g. contracts where
End Date precedes Start Date are real data — preserve them; you may flag them).

## Performance / large files

- Use `nrows` to preview, `usecols` to load only needed columns.
- Filter to the rows you need (see `excel_analysis.md`); never print the whole frame to context.
