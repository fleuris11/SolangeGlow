"""Prints a new VAPID key pair, ready to paste in the production .env file."""

from django.core.management.base import BaseCommand

from apps.notifications.vapid import generate


class Command(BaseCommand):
    help = "Generate a VAPID key pair for Web Push (paste the two lines in .env)."

    def handle(self, *args, **options):
        keys = generate()
        private = keys["private_pem"].strip().replace("\n", "\\n")
        self.stdout.write(f"VAPID_PUBLIC_KEY={keys['public_key']}")
        self.stdout.write(f'VAPID_PRIVATE_KEY="{private}"')
