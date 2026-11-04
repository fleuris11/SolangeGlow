"""A pro gets an e-mail when a client books, asks or cancels (off until now).

Can be switched off again in the admin, like every template.
"""

from django.db import migrations

EVENTS = ["booking.new", "booking.request", "booking.cancelled_by_client"]


def switch_on(apps, schema_editor):
    Template = apps.get_model("notifications", "NotificationTemplate")
    Template.objects.filter(event_key__in=EVENTS, channel="email").update(is_active=True)


class Migration(migrations.Migration):
    dependencies = [("booking", "0005_slots_places_home")]

    operations = [migrations.RunPython(switch_on, migrations.RunPython.noop)]
