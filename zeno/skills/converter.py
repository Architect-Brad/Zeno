"""Zeno Unit Converter Skill — converts between common units."""

import re
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

_CONVERSIONS: dict[tuple[str, str], callable] = {
    ("meters", "feet"): lambda v: v * 3.28084,
    ("feet", "meters"): lambda v: v / 3.28084,
    ("centimeters", "inches"): lambda v: v / 2.54,
    ("inches", "centimeters"): lambda v: v * 2.54,
    ("kilometers", "miles"): lambda v: v * 0.621371,
    ("miles", "kilometers"): lambda v: v / 0.621371,
    ("kilograms", "pounds"): lambda v: v * 2.20462,
    ("pounds", "kilograms"): lambda v: v / 2.20462,
    ("grams", "ounces"): lambda v: v * 0.035274,
    ("ounces", "grams"): lambda v: v / 0.035274,
    ("liters", "gallons"): lambda v: v * 0.264172,
    ("gallons", "liters"): lambda v: v / 0.264172,
    ("celsius", "fahrenheit"): lambda v: v * 9 / 5 + 32,
    ("fahrenheit", "celsius"): lambda v: (v - 32) * 5 / 9,
}

_UNIT_ALIASES = {
    "m": "meters", "meter": "meters", "meters": "meters",
    "ft": "feet", "foot": "feet", "feet": "feet",
    "cm": "centimeters", "centimeter": "centimeters", "centimeters": "centimeters",
    "in": "inches", "inch": "inches", "inches": "inches",
    "km": "kilometers", "kilometer": "kilometers", "kilometers": "kilometers",
    "mi": "miles", "mile": "miles", "miles": "miles",
    "kg": "kilograms", "kilogram": "kilograms", "kilograms": "kilograms",
    "lb": "pounds", "lbs": "pounds", "pound": "pounds", "pounds": "pounds",
    "g": "grams", "gram": "grams", "grams": "grams",
    "oz": "ounces", "ounce": "ounces", "ounces": "ounces",
    "l": "liters", "liter": "liters", "liters": "liters",
    "gal": "gallons", "gallon": "gallons", "gallons": "gallons",
    "c": "celsius", "C": "celsius", "celsius": "celsius",
    "f": "fahrenheit", "F": "fahrenheit", "fahrenheit": "fahrenheit",
}


def _normalize_unit(unit: str) -> str | None:
    u = unit.lower().rstrip("s")
    return _UNIT_ALIASES.get(unit, _UNIT_ALIASES.get(u))


def _convert(text: str) -> str | None:
    pat_value_src_dst = re.compile(
        r"(?:convert\s+)?(\d+\.?\d*)\s*(\S+)\s+(?:to|in|as)\s+(\S+)", re.IGNORECASE
    )
    pat_dst_value_src = re.compile(
        r"how\s+many\s+(\S+)\s+(?:in|to|as|is)\s+(\d+\.?\d*)\s*(\S+)", re.IGNORECASE
    )
    m = pat_value_src_dst.search(text)
    if m:
        try:
            value = float(m.group(1))
        except ValueError:
            return None
        src = _normalize_unit(m.group(2))
        dst = _normalize_unit(m.group(3))
        return _apply_conversion(value, src, dst)

    m = pat_dst_value_src.search(text)
    if m:
        try:
            value = float(m.group(2))
        except ValueError:
            return None
        src = _normalize_unit(m.group(3))
        dst = _normalize_unit(m.group(1))
        return _apply_conversion(value, src, dst)

    return None


def _apply_conversion(value: float, src: str | None, dst: str | None) -> str | None:
    if not src or not dst:
        return None
    key = (src, dst)
    fn = _CONVERSIONS.get(key)
    if fn:
        result = fn(value)
        if result == int(result):
            result = int(result)
        else:
            result = round(result, 4)
        return f"{value} {src} = {result} {dst}"
    rev = (dst, src)
    fn = _CONVERSIONS.get(rev)
    if fn:
        result = fn(value)
        if result == int(result):
            result = int(result)
        else:
            result = round(result, 4)
        return f"{value} {dst} = {result} {src}"
    return None


class ConverterSkill(BaseSkill):
    intents = ["unit_convert"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        text = entities.raw.get("text", "")
        result = _convert(text)
        if result:
            return self.say(result)
        return self.say(
            "I can convert length (m, ft, cm, in, km, mi), "
            "weight (kg, lb, g, oz), volume (l, gal), "
            "and temperature (C, F). "
            "Try 'convert 100 cm to inches'."
        )
