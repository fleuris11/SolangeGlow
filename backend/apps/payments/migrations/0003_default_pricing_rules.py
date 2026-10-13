from django.db import migrations

# Launch values (owner's choice, October 2026): no commission; buyer protection 3 %
# with a minimum of 100 FCFA or 0.30 €. Edited afterwards in the admin, never here.
RULES = [
    {"kind": "commission", "name": "Commission at launch (0 %)", "percent_bps": 0},
    {
        "kind": "buyer_protection",
        "name": "Buyer protection XOF (3 %, min. 100 FCFA)",
        "currency": "XOF",
        "percent_bps": 300,
        "min_minor": 100,
    },
    {
        "kind": "buyer_protection",
        "name": "Buyer protection EUR (3 %, min. 0.30 €)",
        "currency": "EUR",
        "percent_bps": 300,
        "min_minor": 30,
    },
]


def create_rules(apps, schema_editor):
    PricingRule = apps.get_model("payments", "PricingRule")
    for values in RULES:
        PricingRule.objects.get_or_create(name=values["name"], defaults=values)


class Migration(migrations.Migration):
    dependencies = [("payments", "0002_append_only_ledger")]

    operations = [migrations.RunPython(create_rules, migrations.RunPython.noop)]
