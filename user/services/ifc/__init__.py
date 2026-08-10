"""
IFC / CityJSON services for InfoBhoomi 3D Cadastre.

Public API (see ifc2cityjson_cadastral.py):
    process_ifc(ifc_path, transform)             -> ConversionResult
    convert_ifc_to_cityjson(ifc_path, transform) -> dict (CityJSON)
    extract_footprint(ifc_path, transform)       -> shapely Polygon (EPSG:4326)
    TransformParams                              -> manual georeferencing params
"""

from .ifc2cityjson_cadastral import (  # noqa: F401
    TransformParams,
    ConversionResult,
    UnitResult,
    process_ifc,
    convert_ifc_to_cityjson,
    extract_footprint,
)
