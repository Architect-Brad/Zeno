"""Zeno Contact Store — address book backed by ~/.zeno/contacts.json."""

import json
import os
from pathlib import Path

_CONTACTS_PATH = Path.home() / ".zeno" / "contacts.json"


def _ensure_dir():
    _CONTACTS_PATH.parent.mkdir(parents=True, exist_ok=True)


def load_contacts() -> dict[str, dict[str, str]]:
    _ensure_dir()
    if not _CONTACTS_PATH.exists():
        return {}
    try:
        with open(_CONTACTS_PATH) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def save_contacts(contacts: dict[str, dict[str, str]]):
    _ensure_dir()
    with open(_CONTACTS_PATH, "w") as f:
        json.dump(contacts, f, indent=2)


def find_contact(name: str) -> dict[str, str] | None:
    name_lower = name.strip().lower()
    contacts = load_contacts()
    for stored_name, info in contacts.items():
        if stored_name.lower() == name_lower:
            return info
    return None


def get_contact_names() -> list[str]:
    return list(load_contacts().keys())
