"""
Per-category upload limits and a shared validator.

The categories correspond to the FileField `upload_to=` paths used throughout
the app. Edit `UPLOAD_LIMITS` to adjust a size cap or allowed extensions in one
place — every serializer that calls validate_upload() picks up the change.

Frontend code mirrors these limits in
``infoBhoomi-frontedend-div2/src/app/core/upload-limits.ts`` for pre-upload UX
checks. Keep the two in sync if you change a value.

The Tier-1 hard cap is in settings.py (DATA_UPLOAD_MAX_MEMORY_SIZE).
"""

from __future__ import annotations

import os
from typing import Iterable

from rest_framework import serializers


MB = 1024 * 1024


# ---------------------------------------------------------------------------
# Category rules
# ---------------------------------------------------------------------------
#
# Each entry defines:
#   max_size_mb        — reject files larger than this many megabytes.
#   allowed_extensions — case-insensitive set; "" allows any extension.
#   description        — short label used in error messages.
#
# Sizes are tuned for InfoBhoomi's data shapes:
#   - "image":          phone photos (modern phones produce 4–8 MB images).
#   - "sketch_ref":     sketches, often PDFs or photos of paper plans.
#   - "admin_source":   scanned title deeds, often multi-page PDFs (5–20 pages).
#   - "spatial_source": survey reference / source documents.
#   - "message":        ad-hoc chat attachments.
#   - "raster":         GeoTIFFs (kept for the commented-out raster upload).
#
UPLOAD_LIMITS: dict[str, dict] = {
    "image": {
        "max_size_mb": 10,
        "allowed_extensions": {".jpg", ".jpeg", ".png", ".webp"},
        "description": "image",
    },
    "sketch_ref": {
        "max_size_mb": 15,
        "allowed_extensions": {".pdf", ".jpg", ".jpeg", ".png", ".dwg", ".dxf"},
        "description": "sketch reference",
    },
    "admin_source": {
        "max_size_mb": 25,
        "allowed_extensions": {".pdf"},
        "description": "administrative source document",
    },
    "spatial_source": {
        "max_size_mb": 50,
        "allowed_extensions": {".pdf", ".jpg", ".jpeg", ".png", ".geojson", ".kml"},
        "description": "spatial source document",
    },
    "message": {
        "max_size_mb": 10,
        "allowed_extensions": {".pdf", ".jpg", ".jpeg", ".png", ".docx", ".xlsx"},
        "description": "message attachment",
    },
    "raster": {
        "max_size_mb": 100,
        "allowed_extensions": {".tif", ".tiff", ".geotiff"},
        "description": "raster dataset",
    },
}


def _ext(name: str) -> str:
    """Return the lowercased extension (including the dot), e.g. '.pdf'."""
    return os.path.splitext(name or "")[1].lower()


def validate_upload(uploaded_file, category: str):
    """
    Validate an uploaded file against the rules for `category`.

    Raises ``serializers.ValidationError`` on size or extension violations.
    Returns the file unchanged on success so it can be used inline:

        def validate_file_path(self, value):
            return validate_upload(value, "admin_source")

    Notes:
      * NULL/blank uploads are passed through unchanged — model-level
        ``null=True/blank=True`` decides whether they are acceptable.
      * Category names must exist in UPLOAD_LIMITS; an unknown category
        is treated as a programming error and raises ValueError.
    """
    if uploaded_file in (None, "", b""):
        return uploaded_file

    if category not in UPLOAD_LIMITS:
        raise ValueError(
            f"validate_upload(): unknown category '{category}'. "
            f"Known: {sorted(UPLOAD_LIMITS)}"
        )

    rules = UPLOAD_LIMITS[category]
    label = rules["description"]

    # ── Size check ────────────────────────────────────────────────────────
    max_bytes = rules["max_size_mb"] * MB
    size = getattr(uploaded_file, "size", None)
    if size is not None and size > max_bytes:
        size_mb = size / MB
        raise serializers.ValidationError(
            f"{label.capitalize()} is too large ({size_mb:.1f} MB). "
            f"Maximum allowed: {rules['max_size_mb']} MB."
        )

    # ── Extension check ──────────────────────────────────────────────────
    allowed: Iterable[str] = rules["allowed_extensions"]
    ext = _ext(getattr(uploaded_file, "name", ""))
    if allowed and ext not in allowed:
        nice = ", ".join(sorted(allowed))
        raise serializers.ValidationError(
            f"{label.capitalize()} has unsupported file type '{ext or '(none)'}'. "
            f"Allowed: {nice}."
        )

    return uploaded_file


def get_limits_for_frontend() -> list[dict]:
    """
    Return a JSON-serialisable list of the upload rules.

    Exposed via an API endpoint if you want the frontend to fetch limits
    dynamically rather than hard-coding them in upload-limits.ts.
    """
    return [
        {
            "category": cat,
            "max_size_mb": rules["max_size_mb"],
            "allowed_extensions": sorted(rules["allowed_extensions"]),
            "description": rules["description"],
        }
        for cat, rules in UPLOAD_LIMITS.items()
    ]
