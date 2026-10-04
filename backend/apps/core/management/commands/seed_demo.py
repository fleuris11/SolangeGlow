"""Realistic demo data (Benin and France) for local development.

Development only. Idempotent: run it as often as needed. Each new module adds its
data in its own `seed_<module>(stdout)` function, called at the end of `handle`.
"""

import datetime

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from apps.accounts.models import GuestIdentity, SignupChannel, User
from apps.core.choices import Role
from apps.core.models import Country
from apps.notifications.services import notify
from apps.pros.models import ProProfile, Trade

PROS = [
    # first name, last name, phone, country, city, trades, birth date
    ("Aïcha", "Hounkpè", "+2290197000101", "BJ", "Cotonou", ["braids"], "1994-03-12"),
    ("Gloria", "Adjovi", "+2290196000102", "BJ", "Cotonou", ["makeup"], "1998-07-25"),
    ("Sènami", "Dossou", "+2290166000103", "BJ", "Abomey-Calavi", ["hair", "braids"], "1990-11-02"),
    ("Nafissatou", "Bio", "+2290197000104", "BJ", "Cotonou", ["headwrap"], "1987-05-18"),
    ("Rachida", "Soulé", "+2290161000105", "BJ", "Cotonou", ["nails"], "2000-01-30"),
    ("Mireille", "Kpadonou", "+2290197000106", "BJ", "Porto-Novo", ["sewing"], "1983-09-09"),
    ("Clarisse", "Mensah", "+33612340107", "FR", "Paris", ["skincare", "makeup"], "1991-06-14"),
]

CLIENTS = [
    ("Awa", "Zinsou", "+2290197000201", None, "BJ", "Cotonou", "2001-02-03"),
    ("Fifamè", "Agossou", "+2290196000202", None, "BJ", "Abomey-Calavi", "1999-12-24"),
    ("Inès", "Durand", None, "ines.durand@example.com", "FR", "Lyon", "1996-08-11"),
    ("Grâce", "Tossou", "+33612340204", None, "FR", "Paris", "1989-04-07"),
]


def _date(value: str) -> datetime.date:
    return datetime.date.fromisoformat(value)


class Command(BaseCommand):
    help = "Create realistic demo pros, clients and notifications (development only)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force", action="store_true", help="Run even when DEBUG is off (tests)."
        )

    def handle(self, *args, **options):
        if not settings.DEBUG and not options["force"]:
            raise CommandError("seed_demo is for local development only (DEBUG is off).")
        call_command("seed_core", verbosity=0)
        with transaction.atomic():
            created = self.seed_accounts()
        self.stdout.write(self.style.SUCCESS(f"seed_demo: {created} new demo accounts."))

    def _person(self, first, last, phone, email, country_code, city, birth):
        country = Country.objects.filter(code=country_code).first()
        lookup = {"phone": phone} if phone else {"email": email}
        user = User.objects.filter(**lookup).first()
        if user:
            return user, False
        user = User.objects.create_user(
            phone=phone,
            email=email,
            first_name=first,
            last_name=last,
            country=country,
            city=city,
            preferred_currency=country.default_currency if country else None,
            signup_channel=SignupChannel.PHONE if phone else SignupChannel.EMAIL,
        )
        user.birth_date = _date(birth)
        user.onboarded_at = timezone.now()
        if phone:
            user.phone_verified_at = timezone.now()
        else:
            user.email_verified_at = timezone.now()
        user.save()
        return user, True

    def seed_accounts(self) -> int:
        created_count = 0
        for first, last, phone, country, city, trades, birth in PROS:
            user, created = self._person(first, last, phone, None, country, city, birth)
            if created:
                user.roles = [Role.CLIENT, Role.PRO]
                user.save(update_fields=["roles"])
                profile, _ = ProProfile.objects.get_or_create(user=user)
                profile.trades.set(Trade.objects.filter(key__in=trades))
                notify(user, "account.welcome")
                created_count += 1

        for first, last, phone, email, country, city, birth in CLIENTS:
            user, created = self._person(first, last, phone, email, country, city, birth)
            if created:
                notify(user, "account.welcome")
                created_count += 1

        GuestIdentity.objects.get_or_create(
            phone="+2290197000301", defaults={"first_name": "Bernadette"}
        )
        return created_count
