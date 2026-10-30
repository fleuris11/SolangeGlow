import pytest
from django.contrib.auth import get_user_model

from apps.backoffice import demo
from apps.backoffice.models import Prospect
from apps.backoffice.services import team, twofactor
from apps.content.models import Banner, Ticket

pytestmark = pytest.mark.django_db


def test_demo_team_signs_in_with_the_known_secret():
    assert demo.seed_backoffice()["prospects"] == 3
    assert demo.seed_backoffice()["prospects"] == 0  # once only
    owner = get_user_model().objects.get(email=demo.OWNER_EMAIL)
    assert owner.is_superuser and twofactor.is_set_up(owner)
    code = twofactor.code_at(demo.DEMO_SECRET, twofactor.current_step())
    assert twofactor.verify(owner, code) is True
    moderator = get_user_model().objects.get(email=demo.MODERATOR_EMAIL)
    assert sorted(team.roles_of(moderator)) == ["moderation", "support"]
    assert Prospect.objects.count() == 3
    assert Ticket.objects.count() == 2 and Banner.objects.count() == 1
