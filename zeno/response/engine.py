"""
Zeno Response Engine — response selection utilities.
Expanded template library for varied, intent-specific responses.

Two layers of variety, on top of the plain template pools below:

1. Every pick() cycles through its whole pool before repeating (see
   zeno/core/no_repeat.py), instead of plain random.choice — a pool of
   even a dozen items has better-than-even odds of an immediate repeat
   otherwise.

2. For the handful of categories a person hears most often (greetings,
   farewells, thanks), responses are assembled from small interchangeable
   fragments (an opener + an optional tag) rather than picked whole from
   a fixed list of full sentences. Each fragment slot cycles
   independently, so two responses rarely repeat in the same
   combination — combinatorial variety instead of just a longer list.
   This is NOT text generation: every fragment is still hand-written;
   only the combining is dynamic.
"""

from zeno.core.no_repeat import pick_no_repeat

_AM_PM_TEMPLATES: dict[str, list[str]] = {
    "morning": [
        "Good morning", "Morning", "Hey, good morning", "Rise and shine",
        "Good morning to you", "Top of the morning",
    ],
    "afternoon": [
        "Good afternoon", "Hey there", "Hi", "Hello",
    ],
    "evening": [
        "Good evening", "Evening", "Hey, good evening",
    ],
}


def _time_aware_greeting() -> str:
    import time
    hour = time.localtime().tm_hour
    if hour < 12:
        key = "morning"
    elif hour < 18:
        key = "afternoon"
    else:
        key = "evening"
    templates = _AM_PM_TEMPLATES.get(key, ["Hello"])
    return pick_no_repeat(f"response.greeting.{key}", templates)


# ---------------------------------------------------------------------------
# Fragment grammars — an opener plus an optional short tag, combined.
# Only used for kwargs-free, high-frequency conversational categories;
# everything with {placeholders} (weather reports, timer confirmations,
# etc.) stays as plain template picks below, since splicing fragments
# around a format placeholder risks producing grammatically broken output
# for very little added benefit on things people hear less often.
# ---------------------------------------------------------------------------

_FRAGMENTS: dict[str, dict] = {
    "greeting": {
        "opener": ["Hey", "Hi", "Hello", "Hey there", "Hi there", "Yo", "Howdy"],
        "tag": ["", "", "", ", what's up?", ", how can I help?", "!"],
    },
    "farewell": {
        "opener": ["Bye", "See you", "Take care", "Later", "Goodbye",
                   "Catch you later", "Talk soon", "Farewell"],
        "tag": ["", "", "!", ", stay safe.", "— stay in touch.", "for now."],
    },
    "thanks": {
        "opener": ["You're welcome", "No problem", "Happy to help", "Anytime",
                  "My pleasure", "Glad I could help", "Of course", "Sure thing"],
        "tag": ["", "", "!", "— that's what I'm here for."],
    },
}


def _compose(key: str) -> str | None:
    grammar = _FRAGMENTS.get(key)
    if not grammar:
        return None
    opener = pick_no_repeat(f"response.{key}.opener", grammar["opener"])
    tag = pick_no_repeat(f"response.{key}.tag", grammar["tag"])
    if not tag:
        return opener
    if tag[0] in ",!.?":
        return opener + tag
    return f"{opener} {tag}"


_PHRASES: dict[str, list[str]] = {
    # ── Greetings ──
    "greeting": [
        "Hey", "Hello", "Hi", "Hey there", "Hi there",
        "What's up", "Howdy",
    ],
    "greeting_morning": [
        "Good morning", "Morning", "Hey, good morning",
        "Rise and shine", "Good morning to you",
    ],
    "greeting_evening": [
        "Good evening", "Evening", "Hey, good evening",
    ],

    # ── Farewell ──
    "farewell": [
        "Bye", "See you", "Take care", "Later", "Goodbye",
        "See you later", "Catch you later", "Talk soon",
        "Until next time", "Have a good one", "Peace out",
        "Bye for now", "See you around", "Take it easy",
    ],

    # ── Gratitude ──
    "thanks": [
        "You're welcome", "No problem", "Happy to help", "Anytime",
        "My pleasure", "Glad I could help", "Don't mention it",
        "That's what I'm here for", "Of course", "Sure thing",
        "Any time", "Happy to assist",
    ],

    # ── Affirmation / Denial ──
    "affirm_received": [
        "Got it", "Okay", "Sure", "Alright", "On it",
        "Consider it done", "Right away", "You got it",
        "Will do", "On it", "Coming right up",
        "Absolutely", "Let me take care of that",
    ],
    "deny_received": [
        "Okay, no problem", "Alright", "Fair enough", "Got it",
        "No worries", "As you wish", "Sure thing",
        "Understood", "Alright then", "I won't",
    ],

    # ── Cancel ──
    "cancel": [
        "Cancelled", "Alright, forget it", "Consider it done — or not done",
        "Never mind then", "Scratch that", "Cancelled, no problem",
        "Alright, dropping that", "Forget it", "Aborted",
        "Cancelled as requested",
    ],

    # ── Identity ──
    "identity": [
        "I'm Zeno, your local voice assistant. I can handle timers, alarms, reminders, weather, calculations, and system controls. Everything stays on your device.",
        "I'm Zeno — an on-device voice assistant. I run locally with no cloud dependencies. Ask me about the weather, set timers, control your devices, or just chat.",
        "Zeno at your service. I can manage timers, alarms, weather checks, math, smart home controls, and more. All processing is done right here on your machine.",
    ],

    # ── Distress ──
    "distress_response": [
        "I hear you. You're not alone. Please reach out to someone you trust. You can also contact a crisis helpline — they're free, confidential, and available 24/7.",
        "I'm here with you. What you're feeling matters. Please talk to someone you trust or reach out to a crisis support line — there are people who want to listen.",
        "Thank you for sharing that with me. You matter. Please consider reaching out to a trusted friend, family member, or professional who can provide the support you deserve.",
    ],

    # ── Low confidence / Unknown ──
    "unknown": [
        "I'm not sure about that one", "I don't understand",
        "Could you rephrase that", "Not sure what you mean",
        "I didn't quite catch that", "I'm drawing a blank on that one",
        "That went over my head — can you rephrase?",
        "I'm not following, sorry", "That's outside what I know",
        "Hmm, I don't have an answer for that",
        "I'm not equipped to handle that query",
        "Can you ask that differently?",
        "I don't know how to respond to that yet",
    ],
    "low_confidence": [
        "Did you mean '{intent}'?", "Not sure I caught that — were you asking about {intent}?",
        "I'm a bit fuzzy on that — are you looking for {intent}?",
        "Are you trying to ask about {intent}?",
        "I think you might be asking about {intent} — is that right?",
        "I'm not entirely sure, but did you mean {intent}?",
        "Best guess: are you looking for something related to {intent}?",
        "Could you clarify — is this about {intent}?",
    ],

    # ── Weather ──
    "weather_report": [
        "It's {temp}{unit} and {conditions} in {location}.",
        "Currently {temp}{unit} with {conditions} in {location}.",
        "The weather in {location} is {temp}{unit} and {conditions}.",
        "{location} is seeing {conditions} with a temperature of {temp}{unit}.",
        "Right now in {location} it's {temp}{unit} and {conditions}.",
        "Over in {location} it's {temp}{unit} with {conditions}.",
    ],
    "weather_no_location": [
        "I don't know where. Tell me a city or set your location in settings.",
        "Where should I check the weather for?",
        "I need a location to check the weather. You can set one in settings or tell me a city name.",
        "Which city should I look up the weather for?",
    ],
    "weather_unavailable": [
        "Couldn't fetch the weather right now.",
        "Weather data is not available at the moment.",
        "I wasn't able to reach the weather service. Try again later.",
        "Weather lookup failed — the service might be down.",
    ],

    # ── Search / Knowledge ──
    "definition": [
        "{word}: {definition}",
        "Here's what I found: {word} means {definition}",
        "According to DuckDuckGo, {word} is {definition}",
        "I looked up {word} — it means: {definition}",
        "{word} is defined as: {definition}",
    ],
    "ddg_answer": [
        "{answer}",
        "Here's what I found: {answer}",
        "I found this: {answer}",
        "According to my search: {answer}",
    ],
    "ddg_no_result": [
        "I couldn't find anything on that.",
        "DuckDuckGo didn't return any results for that.",
        "No results found for that query.",
        "I searched but came up empty on that one.",
        "Nothing came back for that search.",
    ],
    "translation": [
        "{translation}",
        "That translates to: {translation}",
        "In the target language, that's: {translation}",
        "Here's the translation: {translation}",
    ],
    "news_headline": [
        "{headline}",
        "Here's a headline: {headline}",
        "I found: {headline}",
        "Latest: {headline}",
    ],
    "place_result": [
        "I found {name} — {description}",
        "{name}: {description}",
        "There's {name} — {description}",
    ],

    # ── Time / Date ──
    "time_report": [
        "It's {time}.",
        "The time is {time}.",
        "Currently {time}.",
        "Right now it's {time}.",
        "It's exactly {time}.",
    ],
    "date_report": [
        "Today is {date}.",
        "It's {date}.",
        "Today's date is {date}.",
        "The date is {date}.",
    ],

    # ── Timer / Alarm / Reminder ──
    "timer_set": [
        "Timer set for {duration}.",
        "{duration} timer started.",
        "I've set a {duration} timer.",
        "Timer is running for {duration}.",
        "Starting a {duration} timer now.",
    ],
    "alarm_set": [
        "Alarm set for {time}.",
        "I'll wake you at {time}.",
        "Alarm scheduled for {time}.",
        "{time} alarm is set.",
    ],
    "reminder_set": [
        "Reminder set.",
        "I'll remind you about that.",
        "Reminder saved.",
        "Got it, I'll remind you.",
        "Consider yourself reminded.",
    ],
    "timer_status": [
        "There {count} active timer{timer_plural}. {details}",
        "You have {count} timer{timer_plural} running. {details}",
        "{details}",
    ],
    "timer_cancelled": [
        "Timer cancelled.",
        "Stopped the timer.",
        "Timer has been dismissed.",
        "Cancelled the timer.",
    ],

    # ── System Actions ──
    "system_volume": [
        "Volume set to {level}.",
        "Volume is now at {level}.",
        "I've adjusted the volume to {level}.",
        "Volume changed to {level}.",
    ],
    "system_mute": [
        "Muted.",
        "Sound is off.",
        "Audio muted.",
        "Everything is silent now.",
    ],
    "system_unmute": [
        "Unmuted.",
        "Sound is back on.",
        "Audio restored.",
        "Volume restored.",
    ],
    "system_lock": [
        "Screen locked.",
        "Device is locked.",
        "Locking the screen now.",
        "Screen secured.",
    ],
    "system_brightness": [
        "Brightness set to {level}.",
        "Screen brightness adjusted to {level}.",
        "Brightness changed to {level}.",
    ],
    "system_battery": [
        "Battery at {level}%.",
        "You have {level}% battery remaining.",
        "Battery level is {level}%.",
        "{level}% battery left.",
    ],
    "app_launched": [
        "Opening {app}.",
        "Launching {app}.",
        "Starting {app}.",
        "{app} is opening.",
    ],
    "screenshot_taken": [
        "Screenshot taken.",
        "Captured the screen.",
        "Screen captured.",
        "Screenshot saved.",
    ],

    # ── Connectivity ──
    "wifi_on": [
        "Wi-Fi turned on.",
        "Wi-Fi is now enabled.",
        "Connected to Wi-Fi.",
        "Wi-Fi activated.",
    ],
    "wifi_off": [
        "Wi-Fi turned off.",
        "Wi-Fi is now disabled.",
        "Disconnected from Wi-Fi.",
        "Wi-Fi deactivated.",
    ],

    # ── Smart Home ──
    "lights_on": [
        "Lights on.",
        "Turning the lights on.",
        "Lights are now on.",
        "Illuminating the room.",
        "Lights activated.",
    ],
    "lights_off": [
        "Lights off.",
        "Turning the lights off.",
        "Lights are now off.",
        "Going dark.",
        "Lights deactivated.",
    ],
    "thermostat_set": [
        "Temperature set to {temp}.",
        "Thermostat adjusted to {temp}.",
        "Setting temperature to {temp}.",
        "Climate control set to {temp}.",
    ],
    "fan_set": [
        "Fan speed set to {speed}.",
        "Fan adjusted to {speed}.",
        "Changing fan to {speed}.",
    ],
    "scene_set": [
        "Scene activated.",
        "Switching to that scene.",
        "Scene changed.",
        "Scene is now active.",
    ],

    # ── Media ──
    "media_play": [
        "Playing music.",
        "Starting your music.",
        "Let's get the tunes going.",
        "Music on.",
    ],
    "media_pause": [
        "Paused.",
        "Music paused.",
        "Playback paused.",
        "Stopping the music.",
    ],
    "media_resume": [
        "Resuming.",
        "Playing again.",
        "Back to the music.",
        "Continuing playback.",
    ],
    "media_next": [
        "Skipping to the next track.",
        "Next song.",
        "Moving to the next track.",
    ],
    "media_previous": [
        "Going back.",
        "Previous track.",
        "Back to the previous song.",
    ],
    "media_shuffle": [
        "Shuffle mode on.",
        "Playing on shuffle.",
        "Shuffling your music.",
        "Random play activated.",
    ],
    "media_repeat": [
        "Repeat mode on.",
        "Looping.",
        "Repeat activated.",
        "Playing on repeat.",
    ],
    "media_playlist": [
        "Playing your playlist.",
        "Starting the playlist.",
        "Playlist loaded.",
    ],
    "lyrics_found": [
        "Here are the lyrics: {lyrics}",
        "I found the lyrics: {lyrics}",
        "Lyrics for that song: {lyrics}",
    ],

    # ── Communication ──
    "message_sent": [
        "Message sent.",
        "Your message has been sent.",
        "Sent.",
        "Message delivered.",
    ],
    "call_initiated": [
        "Calling now.",
        "Placing the call.",
        "Dialing.",
        "Call initiated.",
    ],
    "email_checked": [
        "You have {count} unread email{plural}.",
        "Inbox check: {count} unread.",
        "{count} unread message{plural} in your inbox.",
    ],

    # ── Navigation ──
    "directions_found": [
        "Here are the directions to {destination}. {distance} {duration}.",
        "Routing to {destination}. {distance}, about {duration}.",
        "Directions to {destination}: {distance}, approximately {duration}.",
    ],
    "places_found": [
        "I found some places nearby. {places}",
        "Nearby options: {places}",
        "There are {count} places near you: {places}",
    ],
    "traffic_report": [
        "Traffic is {status}. {details}",
        "Current traffic: {status}. {details}",
        "Traffic conditions: {status}. {details}",
    ],

    # ── Calculator / Converter ──
    "calculation_result": [
        "The answer is {result}.",
        "That equals {result}.",
        "{result}.",
        "The result is {result}.",
        "Comes out to {result}.",
    ],
    "conversion_result": [
        "{result}.",
        "That converts to {result}.",
        "The conversion is {result}.",
    ],

    # ── Fun / Entertainment ──
    "joke_delivery": [
        "Here's one: {joke}",
        "{joke}",
        "How about this: {joke}",
        "Got one: {joke}",
    ],
    "riddle_delivery": [
        "Here's a riddle: {riddle}",
        "See if you can solve this: {riddle}",
        "Riddle time: {riddle}",
    ],
    "coin_flip": [
        "It's {result}.",
        "You got {result}.",
        "{result}.",
    ],
    "dice_roll": [
        "You rolled a {result}.",
        "Rolled a {result}.",
        "The dice shows {result}.",
        "It's a {result}.",
    ],
    "quote_delivery": [
        "Here's a quote: '{quote}' — {author}",
        "'{quote}' — {author}",
        "As {author} once said: '{quote}'",
        "Quote: '{quote}' — {author}",
    ],
    "fact_delivery": [
        "Did you know? {fact}",
        "Here's an interesting fact: {fact}",
        "Fun fact: {fact}",
        "{fact}",
    ],

    # ── Notes ──
    "note_saved": [
        "Note saved.",
        "I've written that down.",
        "Noted.",
        "Saved.",
    ],
    "notes_read": [
        "Here are your notes: {notes}",
        "Your notes: {notes}",
        "I found these notes: {notes}",
    ],
    "notes_cleared": [
        "All notes cleared.",
        "Notes deleted.",
        "Removed all notes.",
        "Notes have been wiped.",
    ],
}


def pick(phrase_key: str, **kwargs) -> str:
    if phrase_key == "greeting":
        return _time_aware_greeting()

    composed = _compose(phrase_key)
    if composed is not None:
        phrase = composed
    else:
        phrases = _PHRASES.get(phrase_key, ["I'm not sure about that"])
        phrase = pick_no_repeat(f"response.{phrase_key}", phrases)

    if kwargs:
        phrase = phrase.format(**kwargs)
    return phrase
