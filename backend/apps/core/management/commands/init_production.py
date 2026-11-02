"""First start of a production server: everything needed to open, no demo data.

Safe to run again: what exists is kept, what is missing is added. Countries, currencies and
settings come from seed_core; trades, legal pages, categories, plans and notification
templates from the data migrations; team roles from the post-migrate signal.
"""

from __future__ import annotations

import os
import secrets

from django.contrib.auth import get_user_model
from django.core.management import BaseCommand, CommandError, call_command
from django.core.validators import validate_email
from django.db import transaction

from apps.core import readiness
from apps.core.models import Country, Currency, PlatformSetting

GENERATED_PASSWORD_BYTES = 18


class Command(BaseCommand):
    help = "Prepare a production database and the first admin account (no demo data)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--admin-email",
            default=os.environ.get("ADMIN_EMAIL", ""),
            help="E-mail of the first admin account (or ADMIN_EMAIL).",
        )

    def handle(self, *args, **options):
        email = (options["admin_email"] or "").strip().lower()
        if email:
            validate_email(email)

        call_command("migrate", interactive=False, verbosity=0)
        call_command("seed_core", verbosity=0)
        self._check_reference_data()
        password = self._admin(email)
        self._report(password)

    def _check_reference_data(self):
        from apps.content.models import Page
        from apps.glowpro.models import Plan
        from apps.pros.models import Trade

        expected = {
            "countries": Country.objects.count(),
            "currencies": Currency.objects.count(),
            "settings": PlatformSetting.objects.count(),
            "trades": Trade.objects.count(),
            "legal and help pages": Page.objects.count(),
            "Glow Pro plans": Plan.objects.count(),
        }
        empty = [name for name, count in expected.items() if not count]
        if empty:
            raise CommandError("Missing reference data: " + ", ".join(empty))
        for name, count in expected.items():
            self.stdout.write(f"  {name}: {count}")

    def _admin(self, email: str) -> str | None:
        """Creates the first admin; the password is shown once and never stored in clear."""
        User = get_user_model()
        if User.objects.filter(is_superuser=True).exists():
            self.stdout.write("  admin account: already there, not changed")
            return None
        if not email:
            raise CommandError("No admin account yet: give --admin-email (or ADMIN_EMAIL).")
        if User.objects.filter(email=email).exists():
            raise CommandError("This e-mail already has an account that is not an admin.")
        password = os.environ.get("ADMIN_PASSWORD") or secrets.token_urlsafe(
            GENERATED_PASSWORD_BYTES
        )
        with transaction.atomic():
            User.objects.create_superuser(email=email, password=password, first_name="Admin")
        return None if os.environ.get("ADMIN_PASSWORD") else password

    def _report(self, password: str | None):
        if password:
            self.stdout.write(self.style.WARNING("\nFirst admin password (shown only this once):"))
            self.stdout.write(self.style.WARNING(f"  {password}"))
            self.stdout.write("The first sign-in in /admin asks to set up two-factor sign-in.")
        found = readiness.missing()
        if found["no_sign_in"]:
            self.stdout.write(
                self.style.WARNING("\nNobody can sign in yet: connect WhatsApp, SMS or e-mail.")
            )
        if found["entries"]:
            self.stdout.write("\nStill to connect (docs/checklist-mise-en-ligne.md):")
            for entry in found["entries"]:
                self.stdout.write(f"  [{entry['level']}] {entry['label']}: {entry['variables']}")
        self.stdout.write(self.style.SUCCESS("\ninit_production: done."))
