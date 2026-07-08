"""Tests for zeno/nlu/entity.py time extraction, and the downstream
alarm-scheduling bug it fed into.

Regression context: _extract_time used to pre-convert the hour to
24-hour form (e.g. 17 for "5pm") but still append the original "PM"
suffix, producing nonsensical strings like "17:00 PM". This happened to
schedule correctly for most hours because ReminderSkill._schedule_alarm's
own 12h->24h conversion is a no-op once the hour is already >= 12 — but
it was accidental cancellation of two bugs, not correct behavior, and
easy to break with the next unrelated edit.
"""

import datetime
from unittest.mock import patch

from zeno.nlu.entity import extract_entities
from zeno.skills.reminders import ReminderSkill


def test_extract_time_pm_stays_human_readable():
    e = extract_entities("call mom at 5pm")
    assert e.time == "05:00 PM"


def test_extract_time_am_stays_human_readable():
    e = extract_entities("wake me up at 9am")
    assert e.time == "09:00 AM"


def test_extract_time_noon_and_midnight():
    assert extract_entities("set alarm for 12pm").time == "12:00 PM"
    assert extract_entities("set alarm for 12am").time == "12:00 AM"


def test_extract_time_never_contains_24_hour_and_meridiem_together():
    """The specific shape of the old bug: a 24-hour-range hour (13-23)
    combined with an AM/PM suffix. That combination should never occur."""
    samples = ["5pm", "9am", "11pm", "1am", "6pm", "10am"]
    for s in samples:
        e = extract_entities(f"remind me at {s}")
        if e.time and " " in e.time:
            hour_part = e.time.split(":")[0]
            assert int(hour_part) <= 12, f"{s!r} produced 24h-range hour with meridiem: {e.time!r}"


def _seconds_until(skill: ReminderSkill, time_str: str) -> tuple[int, datetime.datetime]:
    before = datetime.datetime.now()
    with patch.object(skill, "_schedule_timer") as mock_sched:
        skill._schedule_alarm(time_str)
        return mock_sched.call_args[0][0], before


def _assert_lands_on_hour(seconds: int, before: datetime.datetime, expected_hour: int):
    # _schedule_alarm truncates seconds_until with int(), which can lose
    # up to ~1 second of precision, and `before` is captured a hair
    # earlier than the `now()` used inside _schedule_alarm itself — so
    # allow the target to land up to 2 seconds either side of the exact
    # hour boundary rather than asserting a microsecond-perfect time.
    for slack in (0, 1, 2):
        target = before + datetime.timedelta(seconds=seconds + slack)
        if target.hour == expected_hour:
            return
    raise AssertionError(
        f"expected hour {expected_hour}, got "
        f"{(before + datetime.timedelta(seconds=seconds)).strftime('%H:%M:%S')}"
    )


def test_schedule_alarm_5pm_lands_on_17_00():
    skill = ReminderSkill()
    seconds, before = _seconds_until(skill, "05:00 PM")
    _assert_lands_on_hour(seconds, before, 17)


def test_schedule_alarm_9am_lands_on_09_00():
    skill = ReminderSkill()
    seconds, before = _seconds_until(skill, "09:00 AM")
    _assert_lands_on_hour(seconds, before, 9)


def test_schedule_alarm_noon_lands_on_12_00():
    skill = ReminderSkill()
    seconds, before = _seconds_until(skill, "12:00 PM")
    _assert_lands_on_hour(seconds, before, 12)


def test_schedule_alarm_midnight_lands_on_00_00():
    skill = ReminderSkill()
    seconds, before = _seconds_until(skill, "12:00 AM")
    _assert_lands_on_hour(seconds, before, 0)


def test_end_to_end_set_alarm_intent_schedules_correct_hour():
    """Full path: extract_entities -> ReminderSkill.handle -> scheduled time."""
    from zeno.core.context import Context

    skill = ReminderSkill()
    entities = extract_entities("set an alarm for 5pm", intent_hint="set_alarm")
    before = datetime.datetime.now()
    with patch.object(skill, "_schedule_timer") as mock_sched:
        result = skill.handle("set_alarm", entities, Context())

    assert "5:00 PM" in result or "05:00 PM" in result
    seconds = mock_sched.call_args[0][0]
    _assert_lands_on_hour(seconds, before, 17)
