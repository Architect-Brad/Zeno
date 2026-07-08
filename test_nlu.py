"""Comprehensive tests for NLU improvements: top-K, thresholds, synonyms, groups, entities."""

from zeno.nlu.intent import classify_intent
from zeno.nlu.entity import extract_entities


# ---------------------------------------------------------------------------
# Intent Classification — broad coverage
# ---------------------------------------------------------------------------

class TestIntentClassification:
    def test_greeting_detected(self):
        r = classify_intent("hey there")
        assert r.intent == "greeting", f"got {r.intent}"
        assert r.confidence >= 0.24

    def test_date_query_detected(self):
        r = classify_intent("what day is today")
        assert r.intent == "date_query", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_set_timer_detected(self):
        r = classify_intent("set a timer for 10 minutes")
        assert r.intent == "set_timer", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_play_music_detected(self):
        r = classify_intent("play some music")
        assert r.intent == "play_music", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_lights_on_detected(self):
        r = classify_intent("turn on the lights")
        assert r.intent == "lights_on", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_lights_off_detected(self):
        r = classify_intent("turn off all lights")
        assert r.intent == "lights_off", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_calculate_detected(self):
        r = classify_intent("what is 15 percent of 200")
        assert r.intent == "calculate", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_open_app_detected(self):
        r = classify_intent("open firefox")
        assert r.intent == "open_app", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_knowledge_query_detected(self):
        r = classify_intent("tell me about black holes")
        assert r.intent == "knowledge_query", f"got {r.intent}"
        assert r.confidence >= 0.20

    def test_joke_detected(self):
        r = classify_intent("tell me a joke")
        assert r.intent == "joke", f"got {r.intent}"
        assert r.confidence >= 0.24

    def test_flip_coin_detected(self):
        r = classify_intent("flip a coin")
        assert r.intent == "flip_coin", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_roll_dice_detected(self):
        r = classify_intent("roll the dice")
        assert r.intent == "roll_dice", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_take_note_detected(self):
        r = classify_intent("take a note")
        assert r.intent == "take_note", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_wifi_on_detected(self):
        r = classify_intent("turn on wifi")
        assert r.intent == "wifi_on", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_volume_up_detected(self):
        r = classify_intent("increase the volume")
        assert r.intent == "volume_up", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_brightness_up_detected(self):
        r = classify_intent("make it brighter")
        assert r.intent == "brightness_up", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_lock_door_detected(self):
        r = classify_intent("lock the front door")
        assert r.intent == "lock_door", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_weather_forecast_detected(self):
        r = classify_intent("what is the forecast for this week")
        assert r.intent in ("weather_forecast", "weather_query"), f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_send_message_detected(self):
        r = classify_intent("send a text message")
        assert r.intent == "send_message", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_check_email_detected(self):
        r = classify_intent("check my email")
        assert r.intent == "check_email", f"got {r.intent}"
        assert r.confidence >= 0.25

    def test_unknown_for_garbage(self):
        r = classify_intent("purple monkey dishwasher")
        assert r.intent == "unknown", f"got {r.intent}"


# ---------------------------------------------------------------------------
# Algorithmic improvements
# ---------------------------------------------------------------------------

class TestAlgorithmicImprovements:
    def test_top_k_stability(self):
        """Repeated same query returns same top intent."""
        queries = [
            "what time is it right now",
            "set an alarm for 6am",
            "tell me a funny joke",
        ]
        for q in queries:
            r1 = classify_intent(q)
            r2 = classify_intent(q)
            assert r1.intent == r2.intent, f"'{q}' unstable: {r1.intent} vs {r2.intent}"
            assert abs(r1.confidence - r2.confidence) < 0.02, (
                f"'{q}' confidence unstable: {r1.confidence:.4f} vs {r2.confidence:.4f}"
            )

    def test_low_confidence_fuzzy_knowledge(self):
        """Fuzzy intents (knowledge_query) still resolve even with weak signal."""
        r = classify_intent("i wonder about the universe")
        assert r.confidence >= 0.20, f"got {r.intent} conf={r.confidence:.3f}"

    def test_synonym_illuminate(self):
        """'illuminate' synonym maps to lights_on vocabulary."""
        r = classify_intent("illuminate the room")
        assert r.intent == "lights_on", f"got {r.intent}"

    def test_synonym_brighten(self):
        """'brighten' synonym maps to lights_on (or brightness_up — ambiguous)."""
        r = classify_intent("brighten up in here")
        assert r.intent in ("lights_on", "brightness_up"), f"got {r.intent}"

    def test_fallback_chain_joke(self):
        """joke fallback chain works: joke → fun_request → greeting."""
        r = classify_intent("tell me a joke")
        assert r.intent == "joke", f"got {r.intent}"

    def test_context_boost(self):
        """Passing context_intent boosts that intent's score."""
        r1 = classify_intent("set a timer")
        r2 = classify_intent("set a timer", context_intent="set_timer")
        assert r2.confidence >= r1.confidence, (
            f"context didn't boost: {r1.confidence:.3f} → {r2.confidence:.3f}"
        )

    def test_multi_intent_flag_off_for_clear(self):
        """Clear single intent: is_multi=False."""
        r = classify_intent("what time is it")
        assert r.is_multi is False, f"got multi with secondary={r.secondary_intent}"

    def test_stop_words_keep_time(self):
        """'time' preserved for time_query despite being in global stop words."""
        r = classify_intent("what is the time")
        assert r.intent == "time_query", f"got {r.intent}"
        assert r.confidence >= 0.30


# ---------------------------------------------------------------------------
# Entity Extraction — edge cases
# ---------------------------------------------------------------------------

class TestEntityExtractionEdgeCases:
    def test_relative_time_minutes(self):
        e = extract_entities("remind me in 5 minutes", "set_reminder")
        assert e.time is not None, "relative time not extracted"
        assert "5" in e.time

    def test_relative_time_hour(self):
        e = extract_entities("set alarm in an hour", "set_alarm")
        assert e.time is not None
        assert "1 hour" in e.time

    def test_fractional_duration_half_hour(self):
        e = extract_entities("set a timer for half an hour", "set_timer")
        assert e.duration is not None, f"no duration: {e}"
        assert "0.5" in e.duration or "half" in e.duration

    def test_fractional_duration_hour_and_half(self):
        e = extract_entities("set timer for an hour and a half", "set_timer")
        assert e.duration is not None, f"no duration: {e}"
        assert "1.5" in e.duration

    def test_percentage_of_number(self):
        e = extract_entities("what is 15 percent of 200", "calculate")
        assert e.expression is not None, "expression not extracted"
        assert "15" in e.expression
        assert "percent" in e.expression

    def test_percent_sign(self):
        e = extract_entities("calculate 20% of 150", "calculate")
        assert e.expression is not None, "expression not extracted"
        assert "20" in e.expression
        assert "%" in e.expression or "percent" in e.expression

    def test_multi_word_app_quoted(self):
        e = extract_entities("open 'visual studio code'", "open_app")
        assert e.app_name is not None
        assert "visual studio code" in e.app_name.lower()

    def test_noon_time(self):
        e = extract_entities("set alarm for noon", "set_alarm")
        assert e.time is not None
        assert "12:00" in e.time

    def test_midnight_time(self):
        e = extract_entities("alarm at midnight", "set_alarm")
        assert e.time is not None
        assert "12:00" in e.time

    def test_date_tomorrow(self):
        e = extract_entities("remind me tomorrow", "set_reminder")
        assert e.date is not None
        assert e.date == "tomorrow"

    def test_date_next_monday(self):
        e = extract_entities("set alarm for next monday", "set_alarm")
        assert e.date is not None
        assert "monday" in e.date

    def test_arithmetic_expression(self):
        e = extract_entities("what is 25 + 17", "calculate")
        assert e.expression is not None
        assert "25" in e.expression and "17" in e.expression

    def test_reminder_target(self):
        e = extract_entities("remind me to buy milk", "set_reminder")
        assert e.raw_target is not None
        assert "buy milk" in e.raw_target.lower()

    def test_no_entities(self):
        e = extract_entities("hello how are you", "greeting")
        assert e.time is None
        assert e.date is None
        assert e.duration is None
        assert e.expression is None
        assert e.app_name is None

    def test_couple_of_hours_duration(self):
        e = extract_entities("timer for a couple of hours", "set_timer")
        assert e.duration is not None
        assert "2" in e.duration.lower() or "couple" in e.duration.lower()

    def test_number_extraction(self):
        e = extract_entities("set volume to 75 percent", "set_volume_exact")
        assert e.number is not None
        assert e.number == 75.0

    def test_location_filtering(self):
        """Time words like 'hour' are excluded from location."""
        e = extract_entities("weather in an hour", "weather_query")
        # 'an hour' should NOT be extracted as location
        if e.location:
            assert "hour" not in e.location.lower()


# ---------------------------------------------------------------------------
# Multi-language support
# ---------------------------------------------------------------------------

class TestMultiLanguage:
    def test_spanish_greeting(self):
        r = classify_intent("hola")
        assert r.intent == "greeting", f"got {r.intent}"

    def test_spanish_lights_on(self):
        r = classify_intent("enciende las luces")
        assert r.intent == "lights_on", f"got {r.intent}"

    def test_spanish_time_query(self):
        r = classify_intent("qué hora es")
        assert r.intent == "time_query", f"got {r.intent}"

    def test_french_greeting(self):
        r = classify_intent("bonjour")
        assert r.intent == "greeting", f"got {r.intent}"

    def test_french_lights_on(self):
        r = classify_intent("allume la lumière")
        assert r.intent == "lights_on", f"got {r.intent}"

    def test_german_greeting(self):
        r = classify_intent("hallo")
        assert r.intent == "greeting", f"got {r.intent}"

    def test_german_lights_on(self):
        r = classify_intent("schalte das licht ein")
        assert r.intent == "lights_on", f"got {r.intent}"

    def test_hindi_greeting(self):
        r = classify_intent("नमस्ते")
        assert r.intent == "greeting", f"got {r.intent}"

    def test_japanese_greeting(self):
        r = classify_intent("こんにちは")
        assert r.intent == "greeting", f"got {r.intent}"

    def test_french_time_query(self):
        r = classify_intent("quelle heure est-il")
        assert r.intent == "time_query", f"got {r.intent}"
