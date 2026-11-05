"""« Talent » becomes « professionnel » in the texts already in the database: see apps/core/wording.py."""

from django.db import migrations

from apps.core.wording import plain_en, plain_fr

FIELDS = {
    ("notifications", "NotificationTemplate"): ["title", "body"],
    ("content", "FaqItem"): ["question", "answer"],
    ("content", "Page"): ["title", "body"],
    ("glowpro", "Plan"): ["name", "description"],
}


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
    dependencies = [("core", "0006_plain_words")]

    operations = [migrations.RunPython(rewrite, migrations.RunPython.noop)]
