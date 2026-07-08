"""
Zeno Proactive Engine
Schedules background checks for context-aware suggestions.
Triggers on: time, weather, routine detection, idle state.
"""

import random
import threading
import time
from datetime import datetime
from typing import Callable

from zeno.core.personalise import get_personaliser, Personaliser
from zeno.core.profile import load_profile
from zeno.memory.graph import get_graph


class ProactiveEngine:
    def __init__(self):
        self.personaliser = get_personaliser()
        self.graph = get_graph()
        self._triggers: list[tuple[str, Callable[[], str | None], float]] = []
        self._last_triggered: dict[str, float] = {}
        self._timer: threading.Timer | None = None
        self._running = False

    def register(self, name: str, trigger_fn: Callable[[], str | None],
                 cooldown: float = 3600):
        """Register a proactive trigger.
        trigger_fn returns a suggestion string or None.
        cooldown: minimum seconds between firings.
        """
        self._triggers.append((name, trigger_fn, cooldown))

    def check(self) -> str | None:
        """Run all triggers, return the first non-None suggestion."""
        if not self.personaliser.should_proactive():
            return None
        for name, fn, cooldown in self._triggers:
            last = self._last_triggered.get(name, 0.0)
            if time.time() - last < cooldown:
                continue
            try:
                result = fn()
                if result:
                    self._last_triggered[name] = time.time()
                    return result
            except Exception:
                continue
        return None

    def start(self, interval: float = 60.0):
        """Start background polling at `interval` seconds."""
        self._running = True
        self._schedule(interval)

    def _schedule(self, interval: float):
        if not self._running:
            return
        self._timer = threading.Timer(interval, self._tick, [interval])
        self._timer.daemon = True
        self._timer.start()

    def _tick(self, interval: float):
        try:
            self.check()
        except Exception:
            pass
        self._schedule(interval)

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None


def _time_based_suggestion() -> str | None:
    """Suggest based on time of day and user routines."""
    hour = datetime.now().hour
    profile = load_profile()
    name = profile.name or ""

    # Morning: suggest weather if routine shows it
    if 7 <= hour <= 9:
        stats = get_graph().get_usage_stats(top_n=5)
        weather_queries = [s for s in stats if "weather" in s[0]]
        if weather_queries:
            return "Good morning! The weather forecast is available — want to hear it?"

    # Evening: suggest winding down
    if 21 <= hour <= 23:
        return "It's getting late. Would you like me to set a sleep timer or alarm for tomorrow?"

    return None


def _usage_based_suggestion() -> str | None:
    """Suggest based on frequently-used features the user hasn't tried lately."""
    stats = get_graph().get_usage_stats(top_n=10)
    if not stats:
        return None

    frequent = [s for s in stats if s[1] >= 3]
    if not frequent:
        return None

    # Suggest an unused feature
    feature_suggestions = {
        "joke": "Want to hear a joke? I've got a few good ones.",
        "quote": "I could share an inspirational quote if you'd like.",
        "fact": "I know some interesting facts — want to hear one?",
        "riddle": "Up for a riddle?",
    }
    used = {s[0] for s in frequent}
    available = [k for k in feature_suggestions if k not in used]
    if available:
        pick = random.choice(available)
        return feature_suggestions[pick]
    return None


def _idle_suggestion() -> str | None:
    """Offer help after a period of inactivity, tailored to known features."""
    profile = load_profile()
    if not profile.is_known:
        return "I'm Zeno — I can help with weather, timers, alarms, calculations, and smart home controls. What do you need?"
    return None


_engine: ProactiveEngine | None = None


def get_engine() -> ProactiveEngine:
    global _engine
    if _engine is None:
        _engine = ProactiveEngine()
        _engine.register("time_based", _time_based_suggestion, cooldown=7200)
        _engine.register("usage_based", _usage_based_suggestion, cooldown=3600)
        _engine.register("idle", _idle_suggestion, cooldown=86400)
    return _engine
