"""
Zeno User Profile
Loads and saves the user's persistent identity — name, timezone, prefs, calibration.
Stored locally via the memory store. Never leaves the device.
"""

from dataclasses import dataclass, field
from zeno.memory.store import get_store


@dataclass
class Calibration:
    stt_timeout: float = 15.0       # seconds before STT gives up
    confidence_threshold: float = 0.30
    ambient_noise: float = 0.0       # baseline RMS from calibration
    speech_rate: str = "normal"      # slow / normal / fast
    language: str = "auto"           # auto / en / es / fr / de / hi


@dataclass
class Profile:
    name: str | None = None
    timezone: str | None = None
    location: str | None = None
    owm_api_key: str | None = None
    units: str = "celsius"
    calibration: Calibration = field(default_factory=Calibration)

    @property
    def is_known(self) -> bool:
        return self.name is not None


def load_profile() -> Profile:
    store = get_store()
    cal = Calibration(
        stt_timeout=float(store.get("cal.stt_timeout", "15.0")),
        confidence_threshold=float(store.get("cal.confidence", "0.30")),
        ambient_noise=float(store.get("cal.ambient_noise", "0.0")),
        speech_rate=store.get("cal.speech_rate", "normal"),
        language=store.get("cal.language", "auto"),
    )
    return Profile(
        name=store.get("profile.name"),
        timezone=store.get("profile.timezone"),
        location=store.get("profile.location"),
        owm_api_key=store.get("profile.owm_api_key"),
        units=store.get("profile.units", "celsius"),
        calibration=cal,
    )


def save_name(name: str):
    get_store().set("profile.name", name)


def save_timezone(tz: str):
    get_store().set("profile.timezone", tz)


def save_location(location: str):
    get_store().set("profile.location", location)


def save_owm_key(key: str):
    get_store().set("profile.owm_api_key", key)


def save_units(units: str):
    get_store().set("profile.units", units)


def save_calibration(cal: Calibration):
    store = get_store()
    store.set("cal.stt_timeout", str(cal.stt_timeout))
    store.set("cal.confidence", str(cal.confidence_threshold))
    store.set("cal.ambient_noise", str(cal.ambient_noise))
    store.set("cal.speech_rate", cal.speech_rate)
    store.set("cal.language", cal.language)


def calibrate(speech_samples: list[float] | None = None):
    """
    Run a quick calibration: measure response times, set thresholds.
    Call with sample durations (seconds) of user utterances.
    """
    store = get_store()
    cal = load_profile().calibration

    if speech_samples:
        avg = sum(speech_samples) / len(speech_samples)
        # Slower speech → longer timeout; faster speech → shorter timeout
        if avg < 2.0:
            cal.speech_rate = "fast"
            cal.stt_timeout = 8.0
        elif avg > 5.0:
            cal.speech_rate = "slow"
            cal.stt_timeout = 20.0
        else:
            cal.speech_rate = "normal"
            cal.stt_timeout = 12.0

    # Adjust confidence threshold based on profile knowledge
    profile = load_profile()
    if profile.is_known:
        cal.confidence_threshold = 0.28  # Slightly more lenient for known users

    save_calibration(cal)
    return cal
