"""
Zeno User Profile
Loads and saves the user's persistent identity — name, timezone, prefs.
Stored locally via the memory store. Never leaves the device.
"""

from dataclasses import dataclass
from zeno.memory.store import get_store


@dataclass
class Profile:
    name: str | None = None
    timezone: str | None = None

    @property
    def is_known(self) -> bool:
        return self.name is not None


def load_profile() -> Profile:
    store = get_store()
    return Profile(
        name=store.get("profile.name"),
        timezone=store.get("profile.timezone"),
    )


def save_name(name: str):
    get_store().set("profile.name", name)


def save_timezone(tz: str):
    get_store().set("profile.timezone", tz)
