from django.db import migrations

# The seven trades at launch (spec v2). Editable afterwards in the admin.
TRADES = [
    ("makeup", "Maquillage", "Makeup", "Líčenie"),
    ("hair", "Coiffure", "Hair", "Kaderníctvo"),
    ("braids", "Tresses", "Braids", "Vrkôčiky"),
    ("nails", "Ongles", "Nails", "Nechty"),
    ("sewing", "Couture", "Sewing", "Krajčírstvo"),
    ("headwrap", "Attache de foulard", "Headwrap", "Viazanie šatky"),
    ("skincare", "Esthétique", "Skincare", "Kozmetika"),
]


def create_trades(apps, schema_editor):
    Trade = apps.get_model("pros", "Trade")
    for position, (key, fr, en, sk) in enumerate(TRADES):
        Trade.objects.get_or_create(
            key=key,
            defaults={
                "name": fr,
                "name_fr": fr,
                "name_en": en,
                "name_sk": sk,
                "icon": key,
                "position": position,
            },
        )


class Migration(migrations.Migration):
    dependencies = [("pros", "0001_initial")]

    operations = [migrations.RunPython(create_trades, migrations.RunPython.noop)]
