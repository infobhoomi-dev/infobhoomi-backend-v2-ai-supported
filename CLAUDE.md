# CLAUDE.md — InfoBhoomi Backend V2

## Project Overview

InfoBhoomi Backend V2 is a Django 5.1 REST API for land and property management, built on the **LADM ISO 19152** standard. It serves the Angular frontend with geospatial data (PostGIS), parcel/building management, role-based access control, and organization administration.

## Tech Stack

- **Framework**: Django 5.1 + Django REST Framework 3.15.2
- **Language**: Python 3.11
- **Database**: PostgreSQL + PostGIS (via `django.contrib.gis`)
- **Auth**: DRF Token Authentication
- **Geospatial**: GDAL 3.4.3, django-restframework-gis 1.1, pyshp 2.3.1
- **Caching**: Redis (production) / LocMemCache (dev fallback) — configured in settings.py
- **Config**: python-decouple + .env.local

## Quick Reference Commands

```bash
python manage.py runserver          # Dev server
python manage.py migrate            # Apply migrations
python manage.py makemigrations     # Create new migrations
python manage.py shell              # Django shell
python audit_tables.py              # Re-run QA audit (generates audit_report.json + audit_summary.csv)
python manage.py test user          # Run tests
```

## Project Structure

```
/
├── infobhoomi/
│   ├── settings.py         # Main settings (DB, cache, DRF config)
│   ├── urls.py             # Root URL config
│   ├── wsgi.py / asgi.py
├── user/                   # Main Django app (all models, serializers, views)
│   ├── models/             # Django models split by domain
│   │   ├── core.py         # Core user/org models
│   │   ├── geo.py          # Geospatial / spatial unit models
│   │   ├── spatial_units.py
│   │   ├── party.py        # Party (owner/person) models
│   │   ├── rrr.py          # Rights, Restrictions, Responsibilities
│   │   ├── assessments.py  # Tax/assessment models
│   │   ├── organization.py
│   │   ├── lookups.py      # Lookup/reference tables
│   │   ├── history.py
│   │   ├── media.py
│   │   ├── misc.py
│   │   └── auth.py
│   ├── serializers/        # DRF serializers split by domain
│   │   ├── auth.py, geo.py, layers.py, lookups.py
│   │   ├── organization.py, party.py, roles.py
│   │   ├── rrr.py, spatial_units.py, survey.py, dynamic.py
│   ├── views/              # DRF ViewSets/APIViews split by domain
│   │   ├── land.py, building.py, spatial_units.py, party.py
│   │   ├── rrr.py, layers.py, organization.py, roles.py
│   │   ├── users.py, auth.py, survey.py, geo_utils.py
│   │   ├── search.py, lookups.py, dynamic.py, building.py
│   ├── urls.py             # App-level URL routing
│   ├── admin.py
│   └── utils.py
├── audit_tables.py         # QA audit script
├── audit_report.json       # Latest audit output (do not edit manually)
├── audit_summary.csv       # CSV summary of audit findings
├── requirements.txt
├── manage.py
└── .env.local              # Local secrets (never commit)
```

## Architecture & Patterns

### App Structure
- All models, serializers, and views live under the single `user` app, split into domain-specific files.
- Models are imported and re-exported via `user/models/__init__.py`.
- Same pattern for serializers and views.

### DRF Configuration
- **Authentication**: Token-based (`Authorization: Token <token>`)
- **Pagination**: `PageNumberPagination`, page size 50
- **Throttling**: 60/min (anon), 300/min (authenticated)
- **Token storage**: `authtoken_token` table

### LADM Domain Model
The database follows ISO 19152 LADM naming conventions:
- `la_*` prefix → Land Administration tables
- `la_spatial_unit` → Core parcel/spatial unit table (3,604 rows)
- `la_ls_*` → Legal Space sub-types (apt, ils, ols, etc.)
- `la_rrr_*` → Rights, Restrictions, Responsibilities
- `la_spatial_source` → Survey/source records
- `survey_rep` → Survey representation points
- `party_*` / `la_party` → Landowners/parties
- `assessment` / `tax_info` → Valuation and tax records

### Geospatial
- PostGIS geometry columns — always use `GeoJSON` or `WKT` in serializers, not raw geometry objects.
- Spatial queries use `django.contrib.gis.db.models` (e.g., `intersects`, `within`, `distance_lte`).
- Add `GIST` indexes on geometry columns for performance.

---

## Current QA Status (Last audit: March 2026)

### Summary
| Priority | Count |
|----------|-------|
| HIGH issues (columns) | 142 |
| MEDIUM issues (columns) | 188 |
| Empty tables | 27 |
| Tables audited | 108 |

### Biggest Gap: Serializer Coverage
**131 model fields are NOT exposed in any serializer.** This is the #1 priority.

Key tables with missing serializer coverage:
- `la_spatial_unit` — `reference_id`, `level_id` missing from serializer
- `survey_rep` — `original_code`, `original_point_id`, `original_x/y/z_coord` missing
- `tax_info` — `external_tax_id`, `date_valuation`, `tax_out_balance` missing
- `la_sp_fire_rescue` — `officer`, `issued_date`, `expired_date` missing
- `la_spatial_source` — `date_expire`, `surveyor_tp` missing

### Empty Tables (27 total — investigate each)
Core LADM tables that should have data:
- `la_rrr_document` — RRR document attachments (frontend has upload UI)
- `la_level` — LADM levels (required for spatial unit hierarchy)
- `la_ls_apt_unit` — Apartment units
- `la_ls_ils_unit` — ILS units
- `la_ba_unit_spatial_unit` — BA Unit ↔ Spatial Unit link table
- `Inquiries` — User inquiries system
- `residence_info` — Residence data

Tables likely intentionally empty (can skip):
- `test_list`, `tags`, `messages`, `reminders`
- `user_user_groups`, `user_user_user_permissions` (Django auth intermediaries)

---

## Active Task Priority Order

1. **Fix serializer coverage** — Add missing fields to serializers in `user/serializers/`
   - Use `/fix-serializer` command to guide this work
   - Start with: `spatial_units.py`, `survey.py`, `rrr.py`

2. **Fix view/endpoint coverage** — 133 fields not exposed in any view
   - After serializers are fixed, views need `fields` or `read_only_fields` updates

3. **Investigate empty LADM tables** — Determine if missing seed data or broken FK references
   - Use `/check-empty-tables` command

4. **PostGIS spatial indexes** — Add GIST indexes on geometry columns
   - Use `/add-spatial-indexes` command

5. **Redis caching** — Layer/org endpoints need caching decorators
   - Settings already configured for Redis, just needs `@cache_page` or `cache.get/set`

---

## Development Conventions

### Adding/Fixing a Serializer
```python
# In user/serializers/<domain>.py
class MyModelSerializer(serializers.ModelSerializer):
    class Meta:
        model = MyModel
        fields = '__all__'   # OR list fields explicitly for security
        # Never use exclude= — always be explicit about what's exposed
```

### Adding a New Endpoint
1. Add/update serializer in `user/serializers/<domain>.py`
2. Add/update ViewSet or APIView in `user/views/<domain>.py`
3. Register in `user/urls.py`
4. Re-run `python audit_tables.py` to verify coverage improved

### Environment Variables (.env.local)
```
SECRET_KEY=...
DEBUG=True
DB_NAME=...
DB_USER=...
DB_PASSWORD=...
DB_HOST=localhost
DB_PORT=5432
DJANGO_ALLOWED_HOSTS=localhost,127.0.0.1
REDIS_URL=redis://127.0.0.1:6379/1   # optional in dev
```

### Never Commit
- `.env.local`
- `psw.txt`
- `venv/`
- `*.pyc` / `__pycache__/`
- `audit_report.json` (regenerate with audit script)

---

## Common Pitfalls

- `audit_tables.py` requires a live DB connection — run it after `python manage.py migrate`.
- The `user` app has `models_backup.py`, `serializers_backup.py`, `views_backup.py` — these are snapshots, do NOT import from them.
- `GDAL_LIBRARY_PATH` must be set correctly on Windows (configured via venv PATH in settings.py).
- Token auth header format is `Authorization: Token <token>` (not `Bearer`).
- DRF throttle rates are per-user, not per-IP — logged-in users get 300/min.
- `DEFAULT_AUTO_FIELD = BigAutoField` — all new models get `BigInt` PKs automatically.
