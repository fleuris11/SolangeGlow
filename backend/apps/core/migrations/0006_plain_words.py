"""« Pro » means nothing to someone who does this as an amateur: see apps/core/wording.py."""

from django.conf import settings
from django.db import migrations

from apps.core.wording import plain_en, plain_fr

FIELDS = {
    ("notifications", "NotificationTemplate"): ["title", "body"],
    ("content", "FaqItem"): ["question", "answer"],
    ("content", "Page"): ["title", "body"],
    ("glowpro", "Plan"): ["name", "description"],
}


def payments_switch(apps, schema_editor):
    apps.get_model("core", "FeatureFlag").objects.get_or_create(
        key="payments_closed",
        defaults={
            "name": "Paiements fermés",
            "description": "Activé : aucun paiement, plus d'acomptes, toutes les options offertes.",
            "is_enabled": settings.PAYMENTS_CLOSED_AT_START,
        },
    )


def rewrite(apps, schema_editor):
    for (app, model), fields in FIELDS.items():
        Model = apps.get_model(app, model)
        for row in Model.objects.all():
            changed = []
            for field in fields:
                for suffix, plain in (("", plain_fr), ("_fr", plain_fr), ("_en", plain_en)):
                    name = field + suffix
                    value = getattr(row, name, None)
                    if isinstance(value, str) and plain(value) != value:
                        setattr(row, name, plain(value))
                        changed.append(name)
            if changed:
                row.save(update_fields=changed)


class Migration(migrations.Migration):
    dependencies = [("core", "0005_cities"), ("notifications", "0004_contactmessage"), ("content", "0002_reference_data"), ("glowpro", "0002_reference_data")]

    operations = [
        migrations.RunPython(rewrite, migrations.RunPython.noop),
        migrations.RunPython(payments_switch, migrations.RunPython.noop),
    ]
