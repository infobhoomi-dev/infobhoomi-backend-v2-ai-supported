from django.db import migrations


def normalize_audit_events(apps, schema_editor):
    ParcelEvent = apps.get_model("user", "Parcel_Event_Model")
    ParcelEvent.objects.filter(
        event_type__in=["geometry_restore", "undo_rectification"],
    ).exclude(status="recorded").update(status="recorded", can_rectify=False)


def reverse_noop(apps, schema_editor):
    pass


class Migration(migrations.Migration):

    dependencies = [
        ("user", "0011_create_parcel_event"),
    ]

    operations = [
        migrations.RunPython(normalize_audit_events, reverse_noop),
    ]
