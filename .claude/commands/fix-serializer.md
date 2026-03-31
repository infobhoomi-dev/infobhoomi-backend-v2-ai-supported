# Fix Serializer Coverage

You are helping fix missing serializer field coverage in the InfoBhoomi Django backend.

## Context

The QA audit (`audit_report.json`) found **131 model fields** that exist in Django models but are NOT included in any DRF serializer. This means the API is silently hiding data the frontend needs.

## Your Task

1. **Read the audit report** to find which fields are missing from serializers:
   ```bash
   python3 -c "
   import json
   with open('audit_report.json') as f:
       data = json.load(f)
   for table, info in data.items():
       missing = [c['column'] for c in info['columns'] if c['in_model'] and not c['in_serializer'] and c['priority'] == 'HIGH']
       if missing:
           print(f'{table}: {missing}')
   "
   ```

2. **For each table with missing fields**, find the corresponding model in `user/models/` and the serializer in `user/serializers/`.

3. **Fix the serializer** by adding the missing fields. Follow this pattern:

   ```python
   # BAD — silently excludes fields
   class MySerializer(serializers.ModelSerializer):
       class Meta:
           model = MyModel
           fields = ['id', 'name']  # missing fields!

   # GOOD — explicitly include all needed fields
   class MySerializer(serializers.ModelSerializer):
       class Meta:
           model = MyModel
           fields = ['id', 'name', 'reference_id', 'level_id']  # all fields
   ```

4. **Priority order** for which serializers to fix first:
   - `user/serializers/spatial_units.py` → fixes `la_spatial_unit` (3,604 rows affected)
   - `user/serializers/survey.py` → fixes `survey_rep` (3,599 rows affected)
   - `user/serializers/rrr.py` → fixes RRR tables
   - `user/serializers/party.py` → fixes party/owner tables

5. **After fixing each serializer file**, re-run the audit to verify improvement:
   ```bash
   python audit_tables.py
   ```

## Rules
- Never use `exclude = [...]` in serializers — always be explicit with `fields = [...]`
- For geometry fields, use `GeoJSON` representation (already handled by `rest_framework_gis`)
- Read-only fields (audit trails, computed) should be marked `read_only=True`
- If a field is a ForeignKey, add both the ID field (`field_id`) and optionally a nested serializer
- Do NOT add fields from `models_backup.py` — that file is a legacy snapshot

## Verify Your Work
After fixing serializers, run:
```bash
python manage.py check          # No Django errors
python audit_tables.py          # Re-audit — HIGH count should decrease
python manage.py test user      # Tests still pass
```
