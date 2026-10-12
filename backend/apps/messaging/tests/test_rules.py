"""Who may write to whom: pros, mutual follows, requests, blocks, young accounts, sanctions."""

import pytest

from apps.core.tests.factories import PlatformSettingFactory
from apps.messaging import errors, services
from apps.messaging.models import Conversation, ConversationMember
from apps.moderation import services as moderation
from apps.moderation.models import Sanction

from .factories import adult, follow, minor, pro

pytestmark = pytest.mark.django_db
Status = ConversationMember.Status


def statuses(conversation):
    return {m.user.first_name: m.status for m in conversation.members.select_related("user")}


def test_a_client_writes_to_a_pro_directly():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    assert conversation.kind == Conversation.Kind.DIRECT
    assert statuses(conversation) == {"Awa": Status.ACTIVE, "Aïcha": Status.ACTIVE}


def test_two_people_share_one_conversation():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    first = services.start_direct(awa, aicha)
    assert services.start_direct(aicha, awa) == first
    assert Conversation.objects.count() == 1


def test_pros_write_to_each_other():
    conversation = services.start_direct(pro("Aïcha Tresses"), pro("Gloria Nails"))
    assert set(statuses(conversation).values()) == {Status.ACTIVE}


def test_two_clients_need_to_follow_each_other():
    awa, ines = adult("Awa"), adult("Inès")
    with pytest.raises(errors.MutualFollowNeeded):
        services.start_direct(awa, ines)
    follow(awa, ines)
    with pytest.raises(errors.MutualFollowNeeded):
        services.start_direct(awa, ines)
    follow(ines, awa)
    assert services.start_direct(awa, ines).kind == Conversation.Kind.DIRECT


def test_a_pro_writing_to_a_stranger_sends_a_request():
    aicha, awa = pro("Aïcha Tresses"), adult("Awa")
    conversation = services.start_direct(aicha, awa)
    assert statuses(conversation)["Awa"] == Status.REQUESTED

    services.send(aicha, conversation.pk, text="Bonjour, je fais des tresses à domicile")
    # One message only until she accepts.
    with pytest.raises(errors.RequestPending):
        services.send(aicha, conversation.pk, text="Tu as vu mon message ?")

    services.accept_request(awa, conversation.pk)
    services.send(aicha, conversation.pk, text="Merci !")


def test_a_client_following_the_pro_gets_her_messages_directly():
    aicha, awa = pro("Aïcha Tresses"), adult("Awa")
    follow(awa, aicha)
    assert statuses(services.start_direct(aicha, awa))["Awa"] == Status.ACTIVE


def test_answering_a_request_accepts_it():
    aicha, awa = pro("Aïcha Tresses"), adult("Awa")
    conversation = services.start_direct(aicha, awa)
    services.send(aicha, conversation.pk, text="Bonjour")
    services.send(awa, conversation.pk, text="Bonjour !")
    assert statuses(conversation)["Awa"] == Status.ACTIVE


def test_a_declined_request_stops_the_sender():
    aicha, awa = pro("Aïcha Tresses"), adult("Awa")
    conversation = services.start_direct(aicha, awa)
    services.send(aicha, conversation.pk, text="Bonjour")
    services.decline_request(awa, conversation.pk)
    with pytest.raises(errors.RequestDeclined):
        services.send(aicha, conversation.pk, text="Encore moi")
    with pytest.raises(errors.RequestDeclined):
        services.start_direct(aicha, awa)


def test_young_accounts_only_hear_from_people_they_follow():
    lina, aicha = minor("Lina"), pro("Aïcha Tresses")
    with pytest.raises(errors.ProtectedAccount):
        services.start_direct(aicha, lina)
    follow(lina, aicha)
    assert services.start_direct(aicha, lina)


def test_the_admin_can_open_young_accounts_to_strangers():
    PlatformSettingFactory(
        key="accounts.minors_receive_messages_from_strangers", value="true", value_type="boolean"
    )
    assert services.start_direct(pro("Aïcha Tresses"), minor("Lina"))


def test_blocked_people_cannot_write():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    moderation.block(aicha, awa)
    with pytest.raises(errors.Blocked):
        services.send(awa, conversation.pk, text="Bonjour ?")
    with pytest.raises(errors.Blocked):
        services.start_direct(awa, aicha)


def test_a_muted_person_cannot_send_messages():
    awa, aicha = adult("Awa"), pro("Aïcha Tresses")
    conversation = services.start_direct(awa, aicha)
    Sanction.objects.create(user=awa, level=Sanction.Level.MUTE)
    with pytest.raises(errors.Restricted):
        services.send(awa, conversation.pk, text="Bonjour")


def test_nobody_writes_to_herself_or_reads_others_conversations():
    awa = adult("Awa")
    with pytest.raises(errors.CannotWriteYourself):
        services.start_direct(awa, awa)
    conversation = services.start_direct(adult("Inès"), pro("Aïcha Tresses"))
    with pytest.raises(errors.ConversationNotFound):
        services.send(awa, conversation.pk, text="Coucou")


def test_group_rooms_for_other_modules():
    buyer, seller, agent = adult("Awa"), pro("Aïcha Tresses"), adult("Solange")
    room = services.create_group(
        None,
        [buyer, seller],
        title="Litige commande 42",
        purpose=Conversation.Purpose.DISPUTE,
        context_type="dispute",
        staff=[agent],
    )
    assert room.members.count() == 3
    assert room.members.get(user=agent).role == ConversationMember.Role.STAFF
    services.send_system(room, "Litige ouvert")
    services.send(buyer, room.pk, text="Le colis est arrivé abîmé")
    assert room.messages.count() == 2


def test_groups_have_a_size_limit():
    PlatformSettingFactory(key="messaging.group_max_members", value="2", value_type="integer")
    with pytest.raises(errors.TooManyMembers):
        services.create_group(None, [adult("A"), adult("B"), adult("C")], title="Trop")
