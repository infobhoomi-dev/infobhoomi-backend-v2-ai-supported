"""
Management command: load_gnd_geom
===================================
Loads GND boundary geometry into sl_gnd_10m.geom from a GeoJSON or Shapefile.

Usage:
    python manage.py load_gnd_geom --file /path/to/gnd_boundaries.geojson
    python manage.py load_gnd_geom --file /path/to/gnd_boundaries.shp
    python manage.py load_gnd_geom --file /path/to/gnd_boundaries.geojson --match-field GND_NAME

The GeoJSON/SHP must contain a field whose value matches the 'gnd' column in
sl_gnd_10m.  By default the command tries 'GND_NAME', 'gnd', 'GND', 'NAME'.

Run this after every DB restore to repopulate geometry data.
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import connection, transaction


CANDIDATE_MATCH_FIELDS = ['GND_NAME', 'gnd', 'GND', 'NAME', 'name']


class Command(BaseCommand):
    help = 'Load GND boundary geometry from a GeoJSON or Shapefile into sl_gnd_10m.geom'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file', required=True,
            help='Path to the GeoJSON or Shapefile containing GND boundaries',
        )
        parser.add_argument(
            '--match-field', default=None,
            help='Property name in the file that matches the gnd column (auto-detected if omitted)',
        )
        parser.add_argument(
            '--match-by', choices=['gnd', 'gid'], default='gnd',
            help='Match features to rows using the gnd name (default) or gid integer',
        )

    def handle(self, *args, **options):
        file_path = Path(options['file'])
        if not file_path.exists():
            raise CommandError(f'File not found: {file_path}')

        suffix = file_path.suffix.lower()
        if suffix in ('.geojson', '.json'):
            features = self._load_geojson(file_path)
        elif suffix == '.shp':
            features = self._load_shapefile(file_path)
        else:
            raise CommandError(f'Unsupported file format: {suffix}  (use .geojson or .shp)')

        self.stdout.write(f'Loaded {len(features)} features from {file_path.name}')

        # Auto-detect match field if not provided
        match_field = options['match_field']
        match_by = options['match_by']
        if match_field is None and match_by == 'gnd':
            sample_props = features[0]['properties'] if features else {}
            for candidate in CANDIDATE_MATCH_FIELDS:
                if candidate in sample_props:
                    match_field = candidate
                    break
            if not match_field:
                raise CommandError(
                    f'Could not auto-detect match field. Available properties: '
                    f'{list(sample_props.keys())}. '
                    f'Specify one with --match-field.'
                )
            self.stdout.write(f'Auto-detected match field: {match_field!r}')

        # Ensure column exists before loading
        with connection.cursor() as cursor:
            cursor.execute("""
                ALTER TABLE sl_gnd_10m
                ADD COLUMN IF NOT EXISTS geom geometry(Geometry, 4326);
            """)

        updated = 0
        skipped = 0
        with transaction.atomic():
            with connection.cursor() as cursor:
                for feat in features:
                    geom_json = json.dumps(feat['geometry'])
                    props = feat.get('properties') or {}

                    if match_by == 'gid':
                        row_key = props.get('gid') or props.get('GID')
                        if not row_key:
                            skipped += 1
                            continue
                        cursor.execute(
                            "UPDATE sl_gnd_10m SET geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) WHERE gid = %s",
                            [geom_json, int(row_key)],
                        )
                    else:
                        gnd_name = props.get(match_field)
                        if not gnd_name:
                            skipped += 1
                            continue
                        cursor.execute(
                            "UPDATE sl_gnd_10m SET geom = ST_SetSRID(ST_GeomFromGeoJSON(%s), 4326) WHERE gnd = %s",
                            [geom_json, gnd_name],
                        )

                    if cursor.rowcount > 0:
                        updated += 1
                    else:
                        skipped += 1

        self.stdout.write(self.style.SUCCESS(
            f'Done: {updated} rows updated, {skipped} features skipped (no matching row).'
        ))
        if skipped > 0:
            self.stdout.write(self.style.WARNING(
                'Skipped features had no matching gnd name in sl_gnd_10m. '
                'Check --match-field or --match-by if count is unexpectedly high.'
            ))

    def _load_geojson(self, file_path: Path) -> list:
        with open(file_path, encoding='utf-8') as f:
            data = json.load(f)
        if data.get('type') == 'FeatureCollection':
            return data['features']
        if data.get('type') == 'Feature':
            return [data]
        raise CommandError('GeoJSON must be a Feature or FeatureCollection.')

    def _load_shapefile(self, file_path: Path) -> list:
        try:
            import shapefile  # pyshp
        except ImportError:
            raise CommandError(
                'pyshp is required for shapefile loading: pip install pyshp'
            )
        features = []
        with shapefile.Reader(str(file_path)) as sf:
            field_names = [f[0] for f in sf.fields[1:]]
            for rec in sf.shapeRecords():
                features.append({
                    'type': 'Feature',
                    'geometry': rec.shape.__geo_interface__,
                    'properties': dict(zip(field_names, rec.record)),
                })
        return features
