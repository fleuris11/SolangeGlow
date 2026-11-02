"""Prints what the load test needs as JSON: people with a token, a seller, a service.

Run inside the backend image, on a database with the demo data (seed_demo):
    python manage.py shell < prepare.py
"""

import datetime
import json

from rest_framework_simplejwt.tokens import AccessToken

from apps.accounts.models import User
from apps.core.models import Country
from apps.pros.models import ProProfile, Service

PEOPLE = 30
SELLER = "gloria"
BOOKING_PRO = "bene-coiffure"
BOOKING_SERVICE = "Brushing"

country = Country.objects.get(code="BJ")
tokens = []
for number in range(PEOPLE):
    user, _ = User.objects.update_or_create(
        email=f"load-{number}@example.com",
        defaults={
            "first_name": f"Load {number}",
            "country": country,
            "city": "Cotonou",
            "birth_date": datetime.date(1995, 4, 12),
        },
    )
    tokens.append(str(AccessToken.for_user(user)))

pro = ProProfile.objects.get(slug=BOOKING_PRO)
service = Service.objects.filter(pro=pro, name__icontains=BOOKING_SERVICE).first()

print(
    "LOADDATA"
    + json.dumps(
        {
            "tokens": tokens,
            "seller_slug": SELLER,
            "booking_slug": BOOKING_PRO,
            "service_id": str(service.pk),
            "words": [
                "tresses",
                "maquillage",
                "coiffure",
                "ongles",
                "Cotonou",
                "mariage",
            ],
        }
    )
)
