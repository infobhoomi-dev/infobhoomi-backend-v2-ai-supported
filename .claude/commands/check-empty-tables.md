# Check Empty Tables — InfoBhoomi Backend

Investigate the 27 empty tables found in the QA audit to determine if they need seed data, have broken FK references, or are intentionally empty.

## Empty Tables to Investigate

### Priority 1 — Core LADM tables (should NOT be empty)
- `la_level` — LADM hierarchy levels. Required for spatial unit classification.
- `la_ba_unit_spatial_unit` — Links BA Units to Spatial Units. Should have entries for all 3,604 spatial units.
- `la_rrr_document` — Document attachments for RRR entries. Frontend has upload UI.
- `la_ls_apt_unit` — Apartment legal space units.
- `la_ls_ils_unit` — ILS legal space units.
- `la_spatial_unit_sketch_ref` — Sketch references for parcels.
- `residence_info` — Residence information.

### Priority 2 — Feature tables (may need data or may be unused)
- `Inquiries` — User inquiry system. Check if frontend sends inquiries.
- `attrib_panel_images` — Attribute panel images.
- `dynamic_attribute` — Dynamic attribute definitions.
- `messages` — Internal messaging.
- `reminders` — Reminder system.
- `sl_org_area_child_bndry` / `sl_org_area_parent_bndry` — Org boundary data.
- `survey_rep_func_history` — Survey function history.

### Priority 3 — Likely intentionally empty (skip)
- `test_list` — Test data placeholder.
- `tags` — Tagging system not yet used.
- `user_user_groups` — Django auth (no groups defined yet).
- `user_user_user_permissions` — Django auth (no custom perms).
- `history_party_attrib` — History log, empty until data changes occur.

## Investigation Steps

For each Priority 1 table:

1. **Check the model definition:**
   ```bash
   grep -rn "class LaLevel\|class LaBaUnitSpatialUnit" user/models/
   ```

2. **Check for FK constraints that might prevent inserts:**
   ```bash
   python manage.py shell -c "
   from user.models import LaLevel
   print(LaLevel._meta.get_fields())
   "
   ```

3. **Check if data should be seeded from migrations:**
   ```bash
   ls user/migrations/ | grep -i seed
   ls user/management/commands/
   ```

4. **Check if the frontend is sending data to the right endpoint:**
   - Look at `user/urls.py` for the endpoint
   - Check if the view exists in `user/views/`

## Fix Options

- **Missing seed data**: Create a management command in `user/management/commands/seed_<table>.py`
- **Broken FK**: Check if parent records exist first
- **No endpoint**: Add the view and URL (use `/fix-serializer` first)
- **Frontend not sending**: Note it in `TASKS.md` for frontend team
