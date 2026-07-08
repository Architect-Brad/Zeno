"""Tests for ExtrasSkill's send_message/make_call: confirm-then-act flow,
and that it's honest about success/failure instead of always claiming
the message was sent or the call was placed."""

from unittest.mock import patch

from zeno.skills.extras import ExtrasSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


def _skill():
    return ExtrasSkill()


def _caps(**overrides):
    from zeno.platform.providers.base import PlatformCaps
    return PlatformCaps(**overrides)


CONTACT = {"phone": "+15551234567"}


# ---------------------------------------------------------------------------
# send_message
# ---------------------------------------------------------------------------

def test_send_message_no_contact_name_lists_known_contacts():
    skill = _skill()
    with patch("zeno.skills.extras.get_contact_names", return_value=["Alex", "Sam"]):
        entities = Entities()
        entities.contact_name = None
        result = skill.handle("send_message", entities, Context())
    assert "Alex" in result and "Sam" in result


def test_send_message_unknown_contact():
    skill = _skill()
    with patch("zeno.skills.extras.find_contact", return_value=None):
        entities = Entities()
        entities.contact_name = "Ghost"
        result = skill.handle("send_message", entities, Context())
    assert "Ghost" in result
    assert "don't have contact info" in result.lower()


def test_send_message_contact_without_phone():
    skill = _skill()
    with patch("zeno.skills.extras.find_contact", return_value={"nickname": "Al"}):
        entities = Entities()
        entities.contact_name = "Alex"
        result = skill.handle("send_message", entities, Context())
    assert "no phone number" in result.lower()


def test_send_message_unavailable_platform_is_honest():
    skill = _skill()
    with patch("zeno.skills.extras.find_contact", return_value=CONTACT), \
         patch("zeno.skills.extras.caps", return_value=_caps(sms=False)):
        entities = Entities()
        entities.contact_name = "Alex"
        result = skill.handle("send_message", entities, Context())
    assert "can't" in result.lower()
    assert "sent" not in result.lower()  # must not claim success


def test_send_message_asks_for_confirmation_first():
    skill = _skill()
    context = Context()
    with patch("zeno.skills.extras.find_contact", return_value=CONTACT), \
         patch("zeno.skills.extras.caps", return_value=_caps(sms=True)), \
         patch("zeno.skills.extras.send_sms") as mock_send:
        entities = Entities()
        entities.contact_name = "Alex"
        result = skill.handle("send_message", entities, context)

    # Must NOT have sent anything yet
    mock_send.assert_not_called()
    assert "confirm" in result.lower() or "sure" in result.lower()
    assert context.awaiting() is not None
    assert context.awaiting().slot == "confirm_message"
    assert context.get_pending("message_target") == {"name": "Alex", "phone": "+15551234567"}


def test_send_message_confirmed_actually_sends():
    skill = _skill()
    context = Context()
    context.set_pending("message_target", {"name": "Alex", "phone": "+15551234567"})
    context.await_slot("send_message", "confirm_message")

    with patch("zeno.skills.extras.send_sms", return_value=True) as mock_send:
        result = skill.fill_slot("confirm_message", "yes", context)

    mock_send.assert_called_once_with("+15551234567", "Message from Alex via Zeno")
    assert "sent" in result.lower()
    assert context.awaiting() is None


def test_send_message_declined_does_not_send():
    skill = _skill()
    context = Context()
    context.set_pending("message_target", {"name": "Alex", "phone": "+15551234567"})
    context.await_slot("send_message", "confirm_message")

    with patch("zeno.skills.extras.send_sms") as mock_send:
        result = skill.fill_slot("confirm_message", "no", context)

    mock_send.assert_not_called()
    assert "not sending" in result.lower()


def test_send_message_confirmed_but_provider_fails_is_honest():
    skill = _skill()
    context = Context()
    context.set_pending("message_target", {"name": "Alex", "phone": "+15551234567"})
    context.await_slot("send_message", "confirm_message")

    with patch("zeno.skills.extras.send_sms", return_value=False):
        result = skill.fill_slot("confirm_message", "yes", context)

    assert "sent" not in result.lower() or "couldn't" in result.lower()
    assert "didn't go through" in result.lower() or "couldn't" in result.lower()


# ---------------------------------------------------------------------------
# make_call
# ---------------------------------------------------------------------------

def test_make_call_asks_for_confirmation_first():
    skill = _skill()
    context = Context()
    with patch("zeno.skills.extras.find_contact", return_value=CONTACT), \
         patch("zeno.skills.extras.caps", return_value=_caps(call=True)), \
         patch("zeno.skills.extras.make_call") as mock_call:
        entities = Entities()
        entities.contact_name = "Sam"
        result = skill.handle("make_call", entities, context)

    mock_call.assert_not_called()
    assert context.awaiting().slot == "confirm_call"
    assert context.get_pending("call_target") == {"name": "Sam", "phone": "+15551234567"}


def test_make_call_confirmed_actually_calls():
    skill = _skill()
    context = Context()
    context.set_pending("call_target", {"name": "Sam", "phone": "+15551234567"})
    context.await_slot("make_call", "confirm_call")

    with patch("zeno.skills.extras.make_call", return_value=True) as mock_call:
        result = skill.fill_slot("confirm_call", "yes please", context)

    mock_call.assert_called_once_with("+15551234567")
    assert "calling" in result.lower()


def test_make_call_declined_does_not_call():
    skill = _skill()
    context = Context()
    context.set_pending("call_target", {"name": "Sam", "phone": "+15551234567"})
    context.await_slot("make_call", "confirm_call")

    with patch("zeno.skills.extras.make_call") as mock_call:
        result = skill.fill_slot("confirm_call", "no don't", context)

    mock_call.assert_not_called()
    assert "not calling" in result.lower()


def test_make_call_unavailable_platform_is_honest():
    skill = _skill()
    with patch("zeno.skills.extras.find_contact", return_value=CONTACT), \
         patch("zeno.skills.extras.caps", return_value=_caps(call=False)):
        entities = Entities()
        entities.contact_name = "Sam"
        result = skill.handle("make_call", entities, Context())
    assert "can't" in result.lower()
    assert "calling sam" not in result.lower()  # must not claim success


def test_confirm_flow_survives_ambiguous_reply_without_crashing():
    skill = _skill()
    context = Context()
    context.set_pending("call_target", {"name": "Sam", "phone": "+15551234567"})
    context.await_slot("make_call", "confirm_call")

    with patch("zeno.skills.extras.make_call") as mock_call:
        result = skill.fill_slot("confirm_call", "maybe later idk", context)

    mock_call.assert_not_called()
    assert isinstance(result, str) and result
