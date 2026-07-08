"""Tests for SystemSkill: battery status and flashlight/torch control."""

from unittest.mock import patch, MagicMock

from zeno.skills.system import SystemSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context


def _skill():
    return SystemSkill()


def _caps(**overrides):
    from zeno.platform.providers.base import PlatformCaps
    return PlatformCaps(**overrides)


def test_battery_query_reports_percentage_and_state():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(battery=True)), \
         patch("zeno.skills.system.battery_status",
               return_value={"percentage": 73, "plugged": False, "status": "discharging"}):
        result = skill.handle("check_battery", Entities(), Context())
    assert "73%" in result
    assert "battery" in result.lower()


def test_battery_query_warns_when_low_and_unplugged():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(battery=True)), \
         patch("zeno.skills.system.battery_status",
               return_value={"percentage": 10, "plugged": False, "status": "discharging"}):
        result = skill.handle("check_battery", Entities(), Context())
    assert "10%" in result
    assert "plug in" in result.lower()


def test_battery_query_no_low_warning_when_charging():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(battery=True)), \
         patch("zeno.skills.system.battery_status",
               return_value={"percentage": 10, "plugged": True, "status": "charging"}):
        result = skill.handle("check_battery", Entities(), Context())
    assert "plug in" not in result.lower()


def test_battery_query_unavailable_platform():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(battery=False)):
        result = skill.handle("check_battery", Entities(), Context())
    assert "can't" in result.lower() or "cannot" in result.lower()


def test_battery_query_handles_read_failure():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(battery=True)), \
         patch("zeno.skills.system.battery_status", return_value=None):
        result = skill.handle("check_battery", Entities(), Context())
    assert "couldn't" in result.lower()


def test_torch_on_success():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(torch=True)), \
         patch("zeno.skills.system.set_torch", return_value=True) as mock_set:
        result = skill.handle("flashlight_on", Entities(), Context())
    mock_set.assert_called_once_with(True)
    assert "on" in result.lower()


def test_torch_off_success():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(torch=True)), \
         patch("zeno.skills.system.set_torch", return_value=True) as mock_set:
        result = skill.handle("flashlight_off", Entities(), Context())
    mock_set.assert_called_once_with(False)
    assert "off" in result.lower()


def test_torch_unavailable_platform():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(torch=False)):
        result = skill.handle("flashlight_on", Entities(), Context())
    assert "don't have" in result.lower()


def test_torch_reports_failure_from_provider():
    skill = _skill()
    with patch("zeno.skills.system.caps", return_value=_caps(torch=True)), \
         patch("zeno.skills.system.set_torch", return_value=False):
        result = skill.handle("flashlight_on", Entities(), Context())
    assert "couldn't" in result.lower()


def test_battery_and_torch_registered_in_intents():
    skill = _skill()
    assert "check_battery" in skill.intents
    assert "flashlight_on" in skill.intents
    assert "flashlight_off" in skill.intents
