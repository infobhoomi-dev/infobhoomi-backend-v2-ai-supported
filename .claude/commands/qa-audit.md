# QA Audit — InfoBhoomi Backend

Run and interpret the full QA audit for the InfoBhoomi backend database coverage.

## Step 1: Run the Audit

```bash
python audit_tables.py
```

This generates:
- `audit_report.json` — detailed per-table, per-column analysis
- `audit_summary.csv` — sortable CSV of all issues

## Step 2: Parse the Results

```python
import json

with open('audit_report.json') as f:
    data = json.load(f)

all_cols = [c for t in data.values() for c in t['columns']]
high = [c for c in all_cols if c['priority'] == 'HIGH']
medium = [c for c in all_cols if c['priority'] == 'MEDIUM']

not_in_serializer = [c for c in high if c['in_model'] and not c['in_serializer']]
not_in_views = [c for c in high if c['in_model'] and not c['in_views']]
empty_tables = [(t, v['row_count']) for t, v in data.items() if v['row_count'] == 0]

print(f"HIGH: {len(high)}, MEDIUM: {len(medium)}")
print(f"Missing from serializer: {len(not_in_serializer)}")
print(f"Missing from views: {len(not_in_views)}")
print(f"Empty tables: {len(empty_tables)}")
```

## Step 3: Interpret Results

### Priority Scoring
- **Score 85** = Field exists in DB but NOT in model, serializer, or view — orphaned column
- **Score 65** = Field in model, NOT in serializer or view — API gap
- **Score 55** = Field in model + serializer, NOT in view — endpoint gap
- **Score 35** = Field has 100% null data — data quality issue

### What to Fix First
1. Score ≥ 65 + `in_model=True` + `in_serializer=False` → Fix serializer (use `/fix-serializer`)
2. Score ≥ 55 + `in_serializer=True` + `in_views=False` → Fix view/endpoint
3. Empty LADM tables (`la_*` prefix) → Investigate FK issues or missing seed data
4. 100% null columns in populated tables → Check if data pipeline is broken

### Known Baseline (March 2026)
| Metric | Count |
|--------|-------|
| Tables audited | 108 |
| HIGH priority issues | 142 |
| MEDIUM priority issues | 188 |
| Missing from serializer | 131 |
| Missing from views | 133 |
| Empty tables | 27 |

**Goal**: Reduce HIGH count below 50 by fixing serializer coverage.

## Step 4: After Fixing

Always re-run the audit after changes:
```bash
python audit_tables.py && python manage.py check && python manage.py test user
```
