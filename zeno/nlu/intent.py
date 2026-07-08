"""
Zeno NLU — Advanced Semantic Intent Classifier
Character n-gram vectorization + cosine similarity.
No external ML dependencies. Understands meaning, not just keywords.
"""

import math
import re
from dataclasses import dataclass, field


@dataclass
class IntentResult:
    intent: str
    confidence: float
    raw: str
    is_multi: bool = False
    secondary_intent: str | None = None
    secondary_confidence: float = 0.0


# ---------------------------------------------------------------------------
# Training data — seed phrases per intent (auto-expanded at fit time)
# ---------------------------------------------------------------------------

TRAINING_DATA: dict[str, list[str]] = {
    "greeting": [
        "hey", "hi", "hello", "hey zeno", "good morning", "good evening",
        "good afternoon", "what's up", "sup", "yo", "hi there",
        "hello zeno", "hey there", "howdy", "greetings", "hiya",
        "what's happening", "how's it going", "hey buddy", "morning",
        "hey zeno", "zeno", "hey", "hi", "hello", "how are you",
        "good day", "howdy", "what's new", "long time no see",
        "nice to see you", "hey you", "hello there",
    ],
    "farewell": [
        "bye", "goodbye", "see you", "see you later", "later",
        "good night", "take care", "peace", "catch you later",
        "talk to you later", "bye for now", "see ya", "gotta go",
        "i'm leaving", "see you soon", "later gator", "adios",
        "have a good day", "night night", "got to run",
        "bye bye", "so long", "farewell", "ciao", "until next time",
        "see you around", "catch you", "i'm off", "time to go",
        "i gotta go", "talk later",
    ],
    "time_query": [
        "what's the time", "what time is it", "current time",
        "what time now", "do you know the time",
        "what is the time", "what hour is it",
        "what's the current time", "time check",
        "what time do we have", "clock time",
        "whats the current time", "i need to know the time",
        "do you have the time", "got the time",
        "check the time", "what time do you have",
        "give me the current time", "i need the time",
    ],
    "date_query": [
        "what's the date", "what is the date", "what day is it",
        "what day is today", "today's date", "what's today",
        "current date", "tell me the date", "what day of the week",
        "give me today's date", "what is today's date",
        "what date is it", "do you know what day it is",
        "whats the date today", "which day is it",
        "what is today", "whats today",
    ],
    "weather_query": [
        "what's the weather", "how's the weather", "is it going to rain",
        "will it snow today", "temperature outside", "what's it like outside",
        "should I bring an umbrella", "how cold is it", "is it hot today",
        "weather forecast", "what's the temperature", "how warm is it",
        "do I need a jacket", "what's the weather like", "weather report",
        "is it sunny", "will it rain today", "current conditions",
        "is it cold outside", "how's the weather today",
        "what is the weather like", "what is the weather",
        "how is the weather", "will it rain", "what temperature is it",
        "is it raining", "what is the forecast", "how hot is it",
        "how is the weather outside", "weather check",
    ],
    "weather_forecast": [
        "5 day forecast", "forecast for this week", "what's the weather this week",
        "weekly forecast", "forecast for the next few days",
        "how will the weather be this week", "what's the forecast for this week",
        "weather for the week", "week ahead forecast",
        "what will the weather be like on monday", "forecast for tomorrow and the next day",
        "extended forecast", "7 day forecast", "what's the weekend weather",
        "how about the weather for the rest of the week",
        "what's the outlook for this week", "weather this week",
    ],
    "set_alarm": [
        "set an alarm", "set alarm", "wake me up at", "alarm at",
        "alarm for", "set an alarm for", "wake me at",
        "set my alarm", "set alarm for", "remind me to wake up",
        "alarm clock", "set a wake up call", "i need an alarm",
        "can you set an alarm", "please set an alarm",
        "set an alarm for 6am", "wake me up at 7",
    ],
    "set_timer": [
        "set a timer", "set timer", "timer for", "timer of",
        "countdown from", "start a timer", "set a timer for",
        "start timer", "countdown timer", "set my timer",
        "i need a timer", "can you set a timer", "timer please",
        "set a 5 minute timer", "start countdown",
    ],
    "set_reminder": [
        "remind me to", "remind me about", "set a reminder",
        "create a reminder", "add a reminder", "don't let me forget",
        "remind me that", "set reminder", "make a reminder",
        "i need a reminder", "can you remind me", "reminder please",
        "remind me to call", "remind me about the meeting",
        "don't forget to", "please remind me",
    ],
    "open_app": [
        "open", "launch", "start", "run", "open the app",
        "launch the app", "start the app", "open application",
        "run the app", "open app", "launch application",
        "can you open", "please open",
    ],
    "system_lock": [
        "lock the screen", "lock my phone", "lock my device",
        "close my phone", "turn off the screen", "sleep mode",
        "lock the device", "lock screen", "lock computer",
        "lock my laptop", "go to sleep", "lock it",
        "screen lock", "lock device",
    ],
    "volume_up": [
        "volume up", "turn it up", "turn the volume up",
        "louder", "increase volume", "turn up",
        "make it louder", "raise volume", "volume higher",
        "crank it up", "increase the volume", "turn the sound up",
        "speaker louder", "pump up the volume",
    ],
    "volume_down": [
        "volume down", "turn it down", "turn the volume down",
        "quieter", "lower volume", "turn down",
        "make it quieter", "decrease volume", "volume lower",
        "lower the volume", "shush", "turn the sound down",
        "too loud", "reduce volume",
    ],
    "volume_mute": [
        "mute", "silence", "turn off the sound",
        "silence the audio", "mute the sound", "turn off audio",
        "mute the music", "no sound", "silent mode",
        "turn the sound off", "mute everything", "be quiet",
        "shut up", "quiet please",
    ],
    "calculate": [
        "calculate", "compute", "what is", "how much is",
        "math", "what's 2 plus 2", "calculate this",
        "can you calculate", "work this out", "what does 5 times 3 equal",
        "do the math", "what's the answer", "solve",
        "what is 10 divided by 2", "what's 15 percent of 200",
        "what is 5 plus 3", "what's 5 plus 3", "what is 5 + 3",
        "what's 10 minus 4", "what is 10 minus 4", "what's 7 times 8",
        "what is 7 times 8", "what's 20 divided by 5",
        "what is 20 divided by 5", "add 5 and 3", "subtract 4 from 10",
        "multiply 7 by 8", "divide 20 by 5",
    ],
    "news_query": [
        "what's in the news", "any news", "latest news",
        "what's happening", "headlines", "top headlines",
        "what's the latest news", "news today", "current events",
        "tell me the news", "give me the news", "news update",
        "breaking news", "what's new", "world news",
    ],
    "identity_query": [
        "who are you", "what are you", "your name",
        "are you an ai", "what can you do", "help",
        "tell me about yourself", "what's your name",
        "are you a robot", "are you human", "who made you",
        "what do you do", "how do you work", "capabilities",
    ],
    "thanks": [
        "thank you", "thanks", "cheers", "appreciate it",
        "appreciate that", "nice one", "good job", "great",
        "thank you so much", "thanks a lot", "much appreciated",
        "thanks a bunch", "thank you kindly", "good work",
        "well done", "that's helpful", "perfect",
    ],
    "affirm": [
        "yes", "yeah", "yep", "sure", "okay", "ok",
        "correct", "right", "absolutely", "definitely",
        "of course", "indeed", "that's right", "you bet",
        "certainly", "yes please", "go ahead", "do it",
        "yes do it", "that is correct", "that's correct",
        "that is right", "fine", "alright", "go for it",
    ],
    "deny": [
        "no", "nope", "nah", "never", "not really",
        "no way", "not at all", "no thanks", "i don't think so",
        "absolutely not", "certainly not", "negative",
        "not today", "i disagree", "that's wrong",
        "no i don't", "no thanks", "i don't want that",
        "don't do that", "stop that",
    ],
    "emotional_distress": [
        "i'm depressed", "i am sad", "i feel lonely",
        "i'm feeling anxious", "i'm stressed", "i feel hopeless",
        "i feel empty", "i feel worthless", "i feel broken",
        "i feel lost", "i'm lonely", "i am lonely",
        "no one cares about me", "nobody loves me",
        "i want to hurt myself", "i'm going to harm myself",
        "why am I depressed", "why am I sad",
        "i feel alone", "nobody wants me",
        "i'm going through a hard time", "i need help",
        "i'm not okay", "i'm struggling",
    ],
    "cancel": [
        "cancel", "cancel that", "cancel it", "never mind",
        "forget it", "forget that", "stop", "abort",
        "scratch that", "ignore that", "cancel this",
        "don't do that", "wait no", "cancel the last thing",
        "take that back", "undo", "nevermind",
    ],
    "fun_request": [
        "tell me a story", "sing a song", "sing me a song",
        "entertain me", "amuse me",
        "tell me something fun", "i'm bored", "do something fun",
        "entertain me please", "i want entertainment", "amuse me please",
        "give me some fun", "i need fun", "what's fun", "let's have fun",
    ],
    "play_music": [
        "play music", "play a song", "play some tunes", "start playing music",
        "play something", "play my favorite song",
        "play some music", "start the music", "play a track",
        "start playing", "play some songs", "start the tunes",
        "i want music", "turn on music",
        "play something good", "start the jams",
    ],
    "next_track": [
        "next song", "next track", "skip", "skip this song", "skip this track",
        "next", "play the next one", "next track please", "move to next",
    ],
    "previous_track": [
        "previous song", "previous track", "go back", "play the previous song",
        "previous", "rewind", "last song", "go to the previous track",
        "play that again", "play the last one",
    ],
    "pause_music": [
        "pause", "pause music", "pause playback", "stop the music",
        "stop playing", "stop music", "pause the track", "hold on",
        "freeze", "stop the song",
    ],
    "resume_music": [
        "resume", "resume music", "keep playing", "continue playing",
        "play again", "unpause", "start again", "resume playback",
        "keep going", "continue the music",
    ],
    "lights_on": [
        "turn on the lights", "lights on", "turn the lights on",
        "switch on the lights", "lights please", "turn on light",
        "illuminate", "brighten the room", "turn lights on",
    ],
    "lights_off": [
        "turn off the lights", "lights off", "turn the lights off",
        "switch off the lights", "kill the lights", "lights out",
        "darken the room", "turn off light", "turn lights off",
    ],
    "set_thermostat": [
        "set the temperature", "set thermostat", "change the temperature",
        "make it warmer", "make it cooler", "set temperature to",
        "adjust the thermostat", "turn up the heat", "turn on the ac",
        "set the temp", "change the thermostat",
    ],
    "lock_door": [
        "lock the door", "lock the front door", "lock up", "lock my door",
        "secure the door", "lock the house", "lock the back door",
        "lock everything", "lock it up",
    ],
    "security_check": [
        "check security", "security status", "is everything secure",
        "check the cameras", "security check", "are the doors locked",
        "status security", "check if everything is safe",
    ],
    "send_message": [
        "send a message", "send a text", "text someone", "send message to",
        "send sms", "send a text message", "message", "drop a message",
        "send a quick message", "text", "message someone",
        "compose a message", "write a message",
    ],
    "make_call": [
        "make a call", "call", "phone", "call someone", "make a phone call",
        "dial", "place a call", "call a contact", "ring someone",
        "give them a call", "call a number", "dial a number",
    ],
    "check_email": [
        "check email", "read my emails", "check my inbox",
        "do i have any emails", "check mail", "open email",
        "show my emails", "unread emails", "email status",
        "any new emails", "read my latest emails", "check my mail",
    ],
    "read_notifications": [
        "read notifications", "check notifications", "show notifications",
        "what are my notifications", "show alerts", "notification check",
        "read my alerts", "check my alerts", "show my notifications",
    ],
    "get_directions": [
        "get directions", "navigate to", "directions to", "take me to",
        "how do i get to", "route to", "show me the way to",
        "navigation to", "guide me to", "directions",
        "drop a pin", "find a route", "plan a route",
    ],
    "find_place": [
        "find nearby", "what's near me", "find a place", "search nearby",
        "nearby restaurants", "places near me", "find close by",
        "what's around here", "nearby places", "what is near me",
        "find me a place", "search for places", "look for nearby",
    ],
    "traffic_check": [
        "check traffic", "how is the traffic", "traffic status",
        "traffic report", "is there traffic", "traffic conditions",
        "how bad is traffic", "traffic today", "traffic update",
        "traffic on my route", "any traffic jams", "traffic near me",
    ],
    "define_word": [
        "define", "what does this word mean", "definition of",
        "what is the meaning of", "dictionary", "define the word",
        "meaning of", "word definition", "what does that mean",
        "look up a word", "define a word", "what does word mean",
    ],
    "translate_phrase": [
        "translate", "how do you say", "translate to", "what is in spanish",
        "translation", "in french", "in german", "translate this",
        "say it in", "interpret",
    ],
    "check_battery": [
        "check battery", "battery level", "how much battery",
        "battery status", "what is my battery at", "battery percentage",
        "how is my battery", "remaining battery", "power left",
        "battery left", "how much charge", "battery remaining",
    ],
    "flashlight_on": [
        "turn on flashlight", "flashlight on", "turn the flashlight on",
        "switch on flashlight", "light please", "flashlight",
        "enable flashlight", "turn on the torch", "torch on",
    ],
    "flashlight_off": [
        "turn off flashlight", "flashlight off", "turn the flashlight off",
        "switch off flashlight", "disable flashlight", "torch off",
        "shut off flashlight", "turn off the torch", "stop the light",
    ],
    "screenshot": [
        "take a screenshot", "screenshot", "capture screen",
        "take screenshot", "screen capture", "screen shot",
        "capture the screen", "snap the screen",
        "grab a screenshot", "save screenshot", "take a screen grab",
    ],
    "wifi_on": [
        "turn on wifi", "wifi on", "enable wifi", "turn the wifi on",
        "switch on wifi", "connect to wifi", "turn wifi on",
        "activate wifi", "turn wireless on", "start wifi",
        "wifi power on", "restore wifi connection", "reconnect wifi",
    ],
    "wifi_off": [
        "turn off wifi", "wifi off", "disable wifi", "turn the wifi off",
        "switch off wifi", "disconnect wifi", "turn wifi off",
        "deactivate wifi", "turn wireless off", "stop wifi",
        "wifi power off", "kill the wifi", "disconnect from network",
    ],
    "check_timer_status": [
        "how much time left", "timer status", "remaining time",
        "how long left", "what is the timer at", "time remaining on timer",
        "check the timer", "how much longer", "is the timer done",
    ],
    "stop_timer": [
        "stop timer", "cancel timer", "dismiss timer", "turn off timer",
        "stop the timer", "timer off", "end the timer", "kill the timer",
        "cancel my timer", "dismiss timer", "turn the timer off",
        "remove the timer", "timer done", "kill timer",
        "end the countdown", "stop the countdown", "cancel countdown",
    ],
    "set_volume_exact": [
        "set volume", "set volume to", "volume level", "set the volume",
        "volume to", "change volume to", "adjust volume to",
        "turn volume to", "set volume at", "change the volume level",
        "set the volume level", "put volume at", "set sound to",
        "adjust the volume", "set my volume to",
    ],
    "brightness_up": [
        "brightness up", "increase brightness", "make it brighter",
        "turn up brightness", "brighten", "increase screen brightness",
        "more brightness", "brighter please", "raise brightness",
    ],
    "brightness_down": [
        "brightness down", "decrease brightness", "make it dimmer",
        "turn down brightness", "dim", "lower brightness",
        "less brightness", "dimmer please", "reduce brightness",
    ],
    "joke": [
        "tell me a joke", "tell a joke", "make me laugh", "joke",
        "tell me something funny", "give me a joke", "crack a joke",
        "say something funny", "make me laugh please",
    ],
    "riddle": [
        "tell me a riddle", "give me a riddle", "riddle me this",
        "ask me a riddle", "riddle", "tell a riddle",
        "give me something to guess", "pose a riddle",
        "i want a riddle", "give me a brain teaser",
    ],
    "flip_coin": [
        "flip a coin", "heads or tails", "toss a coin",
        "coin flip", "coin toss", "flip it",
        "toss it", "flip a coin for me",
        "heads or tails decision", "let's flip", "coin flip decision",
        "make a flip", "flip for it", "give me heads or tails",
    ],
    "roll_dice": [
        "roll a dice", "roll dice", "roll the dice",
        "roll some dice", "dice roll", "roll a d6",
        "roll a six sided die", "roll the dice for me", "give me a dice roll",
        "roll a d20", "dice throw", "roll some dice for me",
        "random dice roll", "roll the die", "need a dice roll",
    ],
    "take_note": [
        "take a note", "write this down", "make a note",
        "save a note", "note this", "jot this down",
        "remember this", "write a note",
    ],
    "read_notes": [
        "read my notes", "show my notes", "what did I note down",
        "read notes", "show notes", "get my notes",
        "what notes do I have",
        "list my notes", "display notes", "open my notes",
        "what did i write down", "fetch my notes", "retrieve my notes",
    ],
    "clear_notes": [
        "clear my notes", "delete my notes", "remove all notes",
        "erase notes", "delete all notes", "clear notes",
        "wipe notes", "erase all my notes", "notes reset",
        "discard all notes", "delete all saved notes", "clear everything",
    ],
    "quote": [
        "give me a quote", "inspirational quote", "inspire me",
        "tell me a quote", "quote of the day", "motivational quote",
        "give me inspiration", "famous quote",
    ],
    "random_fact": [
        "tell me a fact", "random fact", "interesting fact",
        "give me a fact", "did you know", "fun fact",
        "tell me something interesting",
    ],
    "currency_convert": [
        "convert currency", "exchange rate", "how much is in",
        "currency conversion", "convert to", "what is the exchange rate",
        "how much is", "convert 100 usd to eur",
    ],
    "unit_convert": [
        "convert units", "convert", "how many meters in",
        "unit conversion", "convert to meters", "how many feet in",
        "how many inches", "convert cm to inches",
    ],
    "timezone_info": [
        "what time is it in", "time in", "current time in",
        "timezone", "what's the time in", "local time in",
        "tell me the time in",
    ],
    "sleep_timer": [
        "set sleep timer", "sleep timer", "turn off in",
        "sleep in", "set a sleep timer", "go to sleep in",
        "start sleep timer", "timer to turn off", "shut down in",
        "power off in", "turn off after",
    ],
    "fan_speed": [
        "set fan speed", "fan speed", "change fan speed",
        "adjust fan", "turn up fan", "turn down fan",
        "set fan to", "set the fan speed", "control the fan",
        "adjust the fan speed", "change the fan setting",
        "make the fan faster", "make the fan slower",
    ],
    "scene_activate": [
        "activate scene", "set scene", "change scene",
        "switch to scene", "enter scene mode", "scene",
        "set the scene", "switch scene", "load a scene",
        "select scene", "apply scene",
    ],
    "countdown_event": [
        "countdown to", "how many days until", "days until",
        "countdown", "time until", "how long until",
        "days until christmas", "countdown to my birthday", "how long till friday",
        "time remaining until", "countdown timer for", "weeks until",
        "how many days left until", "count the days until", "days to go",
        "how long before", "when is", "time to go until",
    ],
    "shuffle_music": [
        "shuffle", "shuffle music", "shuffle playlist",
        "shuffle my music", "play on shuffle", "random play",
        "shuffle mode", "play in shuffle", "turn on shuffle",
        "mix it up", "randomize playlist",
    ],
    "repeat_mode": [
        "repeat", "repeat mode", "repeat one",
        "repeat all", "toggle repeat", "repeat this song",
        "loop this", "loop mode", "play on repeat",
        "turn on repeat", "repeat the playlist",
    ],
    "play_playlist": [
        "play my playlist", "play playlist", "start playlist",
        "play a playlist", "play list", "open playlist",
        "choose a playlist", "select playlist", "load playlist",
        "add playlist", "play from my playlist",
    ],
    "lyrics_search": [
        "find lyrics", "lyrics for", "song lyrics",
        "what are the lyrics to", "show me the lyrics for",
        "lyrics of", "get lyrics", "look up lyrics",
        "find song lyrics", "show lyrics", "tell me the lyrics",
    ],
    "knowledge_query": [
        "what is", "tell me about", "what do you know about",
        "describe", "who is", "facts about", "what's",
        "what can you tell me about", "knowledge",
        "do you know anything about", "i want to know about",
        "can you tell me about", "explain", "what are",
        "give me information about",
    ],
}


class NGramVectorizer:
    """Character n-gram vectorizer — no external dependencies needed."""

    def __init__(self, ngram_range: tuple[int, int] = (2, 4)):
        self.ngram_range = ngram_range

    def vectorize(self, text: str) -> dict[str, float]:
        text = f" {text.lower().strip()} "
        # Pad short texts with repetition to generate more n-grams
        if len(text.strip()) < 8:
            text = f" {text.strip()} {text.strip()} {text.strip()} "
        grams: dict[str, float] = {}
        for n in range(self.ngram_range[0], self.ngram_range[1] + 1):
            for i in range(len(text) - n + 1):
                gram = text[i:i + n]
                grams[gram] = grams.get(gram, 0) + 1
        norm = math.sqrt(sum(v * v for v in grams.values()))
        if norm:
            for k in grams:
                grams[k] /= norm
        return grams


def _cosine_similarity(a: dict[str, float], b: dict[str, float]) -> float:
    intersection = set(a.keys()) & set(b.keys())
    if not intersection:
        return 0.0
    dot = sum(a[k] * b[k] for k in intersection)
    # Both vectors are unit-normalized, so dot = cosine
    return dot


def _idf_weights(training_data: dict[str, list[dict[str, float]]]) -> dict[str, float]:
    """Compute inverse document frequency for n-grams across intents."""
    intent_count = len(training_data)
    doc_freq: dict[str, int] = {}
    for vectors in training_data.values():
        seen: set[str] = set()
        for vec in vectors:
            seen.update(vec.keys())
        for gram in seen:
            doc_freq[gram] = doc_freq.get(gram, 0) + 1
    import math
    return {
        gram: math.log(1 + intent_count / (1 + freq))
        for gram, freq in doc_freq.items()
    }


# ---------------------------------------------------------------------------
# Intent groups: semantic categories for coherence scoring
# ---------------------------------------------------------------------------

INTENT_GROUPS: dict[str, list[str]] = {
    "weather": ["weather_query", "weather_forecast"],
    "lights": ["lights_on", "lights_off"],
    "climate": ["set_thermostat"],
    "security": ["lock_door", "security_check"],
    "media": ["play_music", "next_track", "previous_track", "pause_music",
              "resume_music", "shuffle_music", "repeat_mode", "play_playlist"],
    "notes": ["take_note", "read_notes", "clear_notes"],
    "conversation": ["greeting", "farewell", "identity_query", "thanks",
                     "affirm", "deny"],
    "timer": ["set_timer", "check_timer_status", "stop_timer", "sleep_timer"],
    "alarm": ["set_alarm"],
    "reminder": ["set_reminder"],
    "system": ["system_lock", "volume_up", "volume_down", "volume_mute",
               "set_volume_exact", "brightness_up", "brightness_down"],
    "connectivity": ["wifi_on", "wifi_off"],
    "calculator": ["calculate"],
    "navigation": ["get_directions", "find_place", "traffic_check"],
    "fun": ["joke", "riddle", "fun_request"],
    "chance": ["flip_coin", "roll_dice"],
    "knowledge": ["knowledge_query", "define_word", "lyrics_search"],
    "quote_fact": ["quote", "random_fact"],
    "currency": ["currency_convert"],
    "convert": ["unit_convert", "currency_convert"],
    "time_date": ["time_query", "date_query", "timezone_info", "countdown_event"],
    "home": ["lights_on", "lights_off", "set_thermostat", "lock_door",
             "security_check", "fan_speed", "scene_activate"],
    "app_control": ["open_app", "screenshot"],
    "communication": ["send_message", "make_call", "check_email",
                      "read_notifications"],
    "flashlight": ["flashlight_on", "flashlight_off"],
    "music_control": ["play_music", "next_track", "previous_track",
                      "pause_music", "resume_music"],
    "accessibility": ["brightness_up", "brightness_down"],
}

_INTENT_TO_GROUP: dict[str, str] = {}
for _g, _members in INTENT_GROUPS.items():
    for _m in _members:
        _INTENT_TO_GROUP[_m] = _g

# Intent hierarchy: fallback chains for ambiguous/similar intents
# All targets must be real intent keys with training data.
_INTENT_FALLBACK: dict[str, list[str]] = {
    "joke": ["fun_request", "greeting"],
    "riddle": ["joke", "fun_request"],
    "flip_coin": ["roll_dice", "fun_request"],
    "roll_dice": ["flip_coin", "fun_request"],
    "take_note": ["read_notes"],
    "read_notes": ["take_note"],
    "clear_notes": ["take_note", "read_notes"],
    "quote": ["random_fact"],
    "random_fact": ["quote"],
    "currency_convert": ["calculate", "knowledge_query"],
    "unit_convert": ["calculate", "currency_convert"],
    "timezone_info": ["time_query", "knowledge_query"],
    "sleep_timer": ["set_timer", "check_timer_status"],
    "fan_speed": ["set_thermostat"],
    "scene_activate": ["lights_on", "lights_off"],
    "countdown_event": ["set_timer", "date_query"],
    "shuffle_music": ["play_music"],
    "repeat_mode": ["play_music"],
    "play_playlist": ["play_music"],
    "lyrics_search": ["knowledge_query", "define_word"],
    "fun_request": ["joke", "greeting"],
    "play_music": ["next_track", "previous_track"],
    "lights_on": ["lights_off"],
    "lights_off": ["lights_on"],
    "set_thermostat": ["fan_speed"],
    "lock_door": ["security_check"],
    "weather_query": ["weather_forecast"],
    "weather_forecast": ["weather_query"],
    "brightness_up": ["brightness_down"],
    "brightness_down": ["brightness_up"],
    "volume_up": ["volume_down"],
    "volume_down": ["volume_up"],
    "wifi_on": ["wifi_off"],
    "wifi_off": ["wifi_on"],
    "flashlight_on": ["flashlight_off"],
    "flashlight_off": ["flashlight_on"],
    "affirm": ["deny"],
    "deny": ["affirm"],
    "send_message": ["make_call"],
    "make_call": ["send_message"],
}

# Per-intent confidence thresholds — fuzzy intents get lower bars, precise ones get higher.
# Default: 0.30 for all. Override per intent or per group.
_INTENT_THRESHOLDS: dict[str, float] = {
    # Fuzzy / general knowledge intents — lower threshold
    "knowledge_query": 0.20,
    "define_word": 0.22,
    "lyrics_search": 0.22,
    "fun_request": 0.22,
    "random_fact": 0.22,
    "quote": 0.22,
    "translate_phrase": 0.22,
    "joke": 0.24,
    "riddle": 0.24,
    "currency_convert": 0.24,
    "unit_convert": 0.24,
    "timezone_info": 0.24,
    "countdown_event": 0.24,
    "sleep_timer": 0.24,
    "fan_speed": 0.24,
    "scene_activate": 0.24,
    # Conversational — medium threshold
    "greeting": 0.25,
    "farewell": 0.25,
    "thanks": 0.25,
    "affirm": 0.25,
    "deny": 0.25,
    "identity_query": 0.25,
    "cancel": 0.25,
    # High-precision intents — keep standard or higher
    "set_timer": 0.30,
    "set_alarm": 0.30,
    "set_reminder": 0.30,
    "weather_query": 0.30,
    "calculate": 0.30,
}

_STOP_WORDS_GLOBAL = {"a", "an", "the", "in", "at", "on",
                      "to", "for", "of", "is", "it", "and",
                      "or", "my", "i", "me", "you", "do",
                      "does", "can", "will", "with", "this",
                      "that", "please", "want", "need"}

# Intent-specific stop word overrides.
# Words that are meaningful for some intents but stop-words for others.
_INTENT_STOP_OVERRIDES: dict[str, set[str]] = {
    "time_query": _STOP_WORDS_GLOBAL - {"time", "clock", "hour", "minute"},
    "date_query": _STOP_WORDS_GLOBAL - {"date", "day", "today"},
    "weather_query": _STOP_WORDS_GLOBAL - {"weather", "rain", "snow", "temperature", "forecast", "outside", "cold", "hot"},
    "weather_forecast": _STOP_WORDS_GLOBAL - {"forecast", "weather", "week", "tomorrow", "weekend"},
}

_INTENT_SYNONYM_MAP: dict[str, set[str]] | None = None


def _get_synonym_boost(text: str, intent_vocab: set[str]) -> float:
    """Check if query words have synonyms in intent's training vocabulary."""
    global _INTENT_SYNONYM_MAP
    if _INTENT_SYNONYM_MAP is None:
        from zeno.nlu.synonyms import build_synonym_map
        _INTENT_SYNONYM_MAP = build_synonym_map()
    words = re.findall(r'\w+', text.lower())
    matched = 0
    total = 0
    for w in words:
        if len(w) < 3:
            continue
        total += 1
        if w in intent_vocab:
            # Direct match — already handled by vocab overlap
            continue
        syns = _INTENT_SYNONYM_MAP.get(w, set())
        if syns & intent_vocab:
            matched += 1
    if total == 0:
        return 0.0
    return (matched / total) * 0.04


class IntentClassifier:
    """
    Semantic intent classifier using character n-gram vectors.

    Uses max-similarity to individual training examples (k-NN style).
    Much better for short utterances than centroid averaging.
    """

    def __init__(self, ngram_range: tuple[int, int] = (2, 4)):
        self.vectorizer = NGramVectorizer(ngram_range)
        self.examples: dict[str, list[dict[str, float]]] = {}
        self._phrase_vocab: dict[str, set[str]] = {}  # word vocab per intent
        self._is_fit = False

    def _expand_phrases(self, phrases: list[str]) -> list[str]:
        expanded = list(phrases)
        try:
            from zeno.nlu.synonyms import expand_text
            syn_expanded = []
            for phrase in expanded:
                syn_expanded.extend(expand_text(phrase))
            return syn_expanded
        except ImportError:
            return expanded

    def fit(self, data: dict[str, list[str]] | None = None):
        training = data or TRAINING_DATA
        self._phrase_vocab = {}
        for intent, phrases in training.items():
            vectors = []
            words = set()
            expanded = self._expand_phrases(phrases)
            for phrase in expanded:
                vectors.append(self.vectorizer.vectorize(phrase))
                for w in re.findall(r'\w+', phrase.lower()):
                    if len(w) > 2:
                        words.add(w)
            self.examples[intent] = vectors
            self._phrase_vocab[intent] = words
        self._is_fit = True

    def _max_similarity(self, query_vec: dict, intent: str) -> float:
        best = 0.0
        for example_vec in self.examples.get(intent, []):
            sim = _cosine_similarity(query_vec, example_vec)
            if sim > best:
                best = sim
        return best

    def predict(
        self,
        text: str,
        context_intent: str | None = None,
        threshold: float = 0.30,
        ambiguity_margin: float = 0.06,
    ) -> IntentResult:
        if not self._is_fit:
            self.fit()

        query_vec = self.vectorizer.vectorize(text)

        scores: dict[str, float] = {}
        for intent in self.examples:
            scores[intent] = self._max_similarity(query_vec, intent)

        if not scores:
            return IntentResult(intent="unknown", confidence=0.0, raw=text)

        # Word coverage bonus — semantic signal beyond n-grams
        query_words = set(w.lower() for w in re.findall(r'\w+', text)
                          if w.lower() not in {"a", "an", "the", "in", "at", "on",
                                               "to", "for", "of", "is", "it", "and",
                                               "or", "my", "i", "me", "you", "do",
                                               "does", "can", "will", "with", "this",
                                               "that", "please", "want", "need"})
        if query_words:
            for intent in scores:
                vocab = self._phrase_vocab.get(intent, set())
                if vocab:
                    overlap = len(query_words & vocab) / len(query_words)
                    scores[intent] += overlap * 0.12

        # Context boost
        if context_intent and context_intent in scores:
            scores[context_intent] += 0.03

        ranked = sorted(scores.items(), key=lambda x: -x[1])

        best_intent, best_score = ranked[0]
        second_intent, second_score = ranked[1] if len(ranked) > 1 else ("unknown", 0.0)
        margin = best_score - second_score

        if best_score < threshold:
            return IntentResult(intent="unknown", confidence=best_score, raw=text)

        is_multi = False
        if margin < ambiguity_margin and second_score > threshold:
            is_multi = True

        return IntentResult(
            intent=best_intent,
            confidence=best_score,
            raw=text,
            is_multi=is_multi,
            secondary_intent=second_intent if is_multi else None,
            secondary_confidence=second_score if is_multi else 0.0,
        )

    def predict_proba(self, text: str, top_n: int = 5) -> list[tuple[str, float]]:
        if not self._is_fit:
            self.fit()
        query_vec = self.vectorizer.vectorize(text)
        scores = {}
        for intent in self.examples:
            scores[intent] = self._max_similarity(query_vec, intent)
        return sorted(scores.items(), key=lambda x: -x[1])[:top_n]


_STOP_WORDS = {"a", "an", "the", "in", "at", "on",
               "to", "for", "of", "is", "it", "and",
               "or", "my", "i", "me", "you", "do",
               "does", "can", "will", "with", "this",
               "that", "please", "want", "need"}


class EnhancedClassifier(IntentClassifier):
    """
    Enhanced intent classifier with:
    - TF-IDF weighted n-grams (down-weights common n-grams)
    - Subword token overlap scoring
    - Intent hierarchy fallback chains
    - Better ambiguity resolution
    """

    def __init__(self, ngram_range: tuple[int, int] = (2, 4)):
        super().__init__(ngram_range)
        self._idf: dict[str, float] = {}
        self._subword_vocab: dict[str, set[str]] = {}
        self._word_examples: dict[str, list[dict[str, float]]] = {}

    @staticmethod
    def _word_vec(text: str) -> dict[str, float]:
        """Word-level unigram + bigram vectorizer."""
        words = re.findall(r'\w+', text.lower())
        grams: dict[str, float] = {}
        for w in words:
            if len(w) > 1:
                grams[f"w:{w}"] = grams.get(f"w:{w}", 0) + 1
        for i in range(len(words) - 1):
            bigram = f"b:{words[i]} {words[i+1]}"
            grams[bigram] = grams.get(bigram, 0) + 1
        norm = math.sqrt(sum(v * v for v in grams.values()))
        if norm:
            for k in grams:
                grams[k] /= norm
        return grams

    def fit(self, data: dict[str, list[str]] | None = None):
        training = data or TRAINING_DATA
        self._phrase_vocab = {}
        self._subword_vocab = {}
        self._word_examples = {}
        for intent, phrases in training.items():
            vectors = []
            word_vecs = []
            words = set()
            subwords: set[str] = set()
            # Use original phrases only — synonym expansion happens at predict time
            for phrase in phrases:
                vectors.append(self.vectorizer.vectorize(phrase))
                word_vecs.append(self._word_vec(phrase))
                for w in re.findall(r'\w+', phrase.lower()):
                    if len(w) > 2:
                        words.add(w)
                    for n in (3, 4):
                        for i in range(len(w) - n + 1):
                            subwords.add(w[i:i + n])
            self.examples[intent] = vectors
            self._word_examples[intent] = word_vecs
            self._phrase_vocab[intent] = words
            self._subword_vocab[intent] = subwords
        self._idf = _idf_weights(self.examples)
        self._is_fit = True

    def _score(self, query_vec: dict[str, float], intent: str,
               query_word_vec: dict[str, float] | None = None) -> float:
        # Top-3 averaging: more robust than max-similarity
        sims = sorted(
            (_cosine_similarity(query_vec, ev) for ev in self.examples.get(intent, [])),
            reverse=True,
        )
        best = sum(sims[:3]) / max(len(sims[:3]), 1) if sims else 0.0
        idf_boost = 0.0
        query_grams = set(query_vec.keys())
        for vec in self.examples.get(intent, []):
            overlap = query_grams & set(vec.keys())
            if overlap:
                idf_boost = max(
                    idf_boost,
                    sum(self._idf.get(g, 1.0) for g in overlap) / len(overlap) * 0.02
                )
        # Word-level similarity bonus
        word_bonus = 0.0
        if query_word_vec:
            best_word = 0.0
            for wv in self._word_examples.get(intent, []):
                sim = _cosine_similarity(query_word_vec, wv)
                if sim > best_word:
                    best_word = sim
            word_bonus = best_word * 0.15
        return best + idf_boost + word_bonus

    def predict(
        self,
        text: str,
        context_intent: str | None = None,
        threshold: float | None = None,
        ambiguity_margin: float = 0.06,
    ) -> IntentResult:
        if not self._is_fit:
            self.fit()

        query_vec = self.vectorizer.vectorize(text)
        query_word_vec = self._word_vec(text)
        scores: dict[str, float] = {}
        for intent in self.examples:
            scores[intent] = self._score(query_vec, intent, query_word_vec)

        if not scores:
            return IntentResult(intent="unknown", confidence=0.0, raw=text)

        query_subwords: set[str] = set()
        for w in re.findall(r'\w+', text.lower()):
            for n in (3, 4):
                for i in range(len(w) - n + 1):
                    query_subwords.add(w[i:i + n])
        if query_subwords:
            for intent in scores:
                sw = self._subword_vocab.get(intent, set())
                if sw:
                    overlap = len(query_subwords & sw)
                    total = len(query_subwords | sw)
                    if total > 0:
                        scores[intent] += (overlap / total) * 0.08

        # Intent-specific stop words
        query_words_raw = set(w.lower() for w in re.findall(r'\w+', text))
        for intent in scores:
            i_stop = _INTENT_STOP_OVERRIDES.get(intent, _STOP_WORDS_GLOBAL)
            qw = {w for w in query_words_raw if w.lower() not in i_stop}
            if qw:
                vocab = self._phrase_vocab.get(intent, set())
                if vocab:
                    overlap = len(qw & vocab) / len(qw)
                    scores[intent] += overlap * 0.12

        # Synonym similarity boost — catch words that mean the same thing
        for intent in scores:
            vocab = self._phrase_vocab.get(intent, set())
            if vocab:
                scores[intent] += _get_synonym_boost(text, vocab)

        if context_intent and context_intent in scores:
            scores[context_intent] += 0.04

        # Disambiguation: "what is X" / "what's X" where X isn't a math
        # expression -> should go to knowledge_query, not calculate
        if "calculate" in scores:
            has_math = bool(re.search(
                r'\d+\s*[\+\-\*\/xX]\s*\d+|(?:\bplus\b|\bminus\b|'
                r'\btimes?\b|\bdivided by\b|\bmultipl(?:y|ied)\b|'
                r'\badd\b|\bsubtract\b|\bpercent\b|%|\bsquared\b|'
                r'\bcubed\b|\broot\b|\blog\b|\bfactorial\b)',
                text, re.IGNORECASE,
            ))
            has_digits = bool(re.search(r'\d', text))
            if not has_math and not has_digits:
                scores["calculate"] *= 0.45

        ranked = sorted(scores.items(), key=lambda x: -x[1])
        best_intent, best_score = ranked[0]
        second_intent, second_score = ranked[1] if len(ranked) > 1 else ("unknown", 0.0)

        # Per-intent threshold
        effective_threshold = _INTENT_THRESHOLDS.get(best_intent, threshold if threshold is not None else 0.30)
        effective_second_threshold = _INTENT_THRESHOLDS.get(second_intent, 0.30) if second_intent != "unknown" else 0.30

        # --- Group-coherence bonus ---
        best_group = _INTENT_TO_GROUP.get(best_intent)
        second_group = _INTENT_TO_GROUP.get(second_intent)
        group_coherent = best_group and second_group and best_group == second_group
        effective_margin = ambiguity_margin * 0.6 if group_coherent else ambiguity_margin

        margin = best_score - second_score

        if best_score < effective_threshold:
            if context_intent and best_intent != context_intent:
                fallback = self._try_fallback(best_intent, context_intent, scores, text)
                if fallback:
                    return fallback
            return IntentResult(intent="unknown", confidence=best_score, raw=text)

        is_multi = False
        if margin < effective_margin and second_score > effective_second_threshold:
            is_multi = True

        return IntentResult(
            intent=best_intent,
            confidence=best_score,
            raw=text,
            is_multi=is_multi,
            secondary_intent=second_intent if is_multi else None,
            secondary_confidence=second_score if is_multi else 0.0,
        )

    def _try_fallback(self, primary: str, fallback_intent: str,
                      scores: dict[str, float],
                      query_text: str = "") -> IntentResult | None:
        # Group-based fallback: same group as context intent
        p_group = _INTENT_TO_GROUP.get(primary)
        f_group = _INTENT_TO_GROUP.get(fallback_intent)
        if p_group and f_group and p_group == f_group:
            fb_score = scores.get(fallback_intent, 0.0)
            if fb_score > 0.15:
                return IntentResult(
                    intent=fallback_intent,
                    confidence=fb_score,
                    raw=query_text or primary,
                )
        # Chain-based fallback: explicit fallback list
        chain = _INTENT_FALLBACK.get(primary, [])
        if fallback_intent in chain:
            fb_score = scores.get(fallback_intent, 0.0)
            if fb_score > 0.2:
                return IntentResult(
                    intent=fallback_intent,
                    confidence=fb_score,
                    raw=query_text or primary,
                )
        for fb in chain:
            fb_score = scores.get(fb, 0.0)
            if fb_score > 0.25:
                return IntentResult(
                    intent=fb,
                    confidence=fb_score,
                    raw=query_text or primary,
                )
        return None


# ---------------------------------------------------------------------------
# Multi-language support — translated training data
# ---------------------------------------------------------------------------

LANGUAGE_PHRASES: dict[str, dict[str, list[str]]] = {
    "es": {
        "greeting": ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal", "saludos", "hola zeno"],
        "time_query": ["qué hora es", "qué hora tienes", "dime la hora", "hora actual", "me das la hora"],
        "date_query": ["qué día es hoy", "qué fecha es", "dime la fecha", "fecha actual"],
        "weather_query": ["qué tiempo hace", "cómo está el clima", "va a llover", "temperatura", "clima"],
        "weather_forecast": ["pronóstico para esta semana", "qué tiempo hará esta semana", "pronóstico semanal", "clima de los próximos días", "cómo estará el clima esta semana"],
        "set_alarm": ["pon una alarma", "despiértame a las", "alarma para", "necesito una alarma"],
        "set_timer": ["pon un temporizador", "temporizador de", "cuenta atrás", "temporizador para"],
        "set_reminder": ["recuérdame", "pon un recordatorio", "no me olvides", "recordatorio"],
        "thanks": ["gracias", "muchas gracias", "te agradezco", "gracias totales"],
        "affirm": ["sí", "si", "claro", "vale", "ok", "de acuerdo", "correcto"],
        "deny": ["no", "nunca", "para nada", "no gracias", "no quiero"],
        "cancel": ["cancelar", "olvídalo", "cancela eso", "no importa"],
        "identity_query": ["quién eres", "qué eres", "cómo te llamas", "qué puedes hacer"],
        "play_music": ["pon música", "reproduce música", "pon una canción", "toca música", "pon algo de música"],
        "next_track": ["siguiente canción", "siguiente pista", "siguiente", "adelante", "salta esta canción"],
        "previous_track": ["canción anterior", "pista anterior", "atrás", "anterior", "vuelve a la anterior"],
        "pause_music": ["pausa", "pausa la música", "detén la música", "para", "pausa la canción"],
        "resume_music": ["continúa", "reanuda", "sigue con la música", "reproduce de nuevo"],
        "lights_on": ["enciende las luces", "luces encendidas", "prende la luz", "enciende la luz"],
        "lights_off": ["apaga las luces", "luces apagadas", "apaga la luz", "apaga todo"],
        "set_thermostat": ["pon la temperatura", "cambia la temperatura", "sube la calefacción", "baja el aire"],
        "lock_door": ["cierra la puerta", "bloquea la puerta", "cierra con llave", "asegura la puerta"],
        "security_check": ["revisa la seguridad", "estado de seguridad", "cámaras", "todo seguro"],
        "send_message": ["envía un mensaje", "manda un texto", "escribe un mensaje", "mensaje a"],
        "make_call": ["haz una llamada", "llama", "llamada", "llama por teléfono"],
        "check_email": ["revisa el correo", "correos", "bandeja de entrada", "tengo correos"],
        "read_notifications": ["lee las notificaciones", "notificaciones", "qué notificaciones tengo"],
        "get_directions": ["cómo llegar a", "navega a", "indicaciones para", "direcciones a"],
        "find_place": ["encuentra cerca", "qué hay cerca", "lugares cercanos", "restaurantes cerca"],
        "traffic_check": ["cómo está el tráfico", "tráfico", "estado del tráfico", "hay tráfico"],
        "define_word": ["define", "qué significa", "definición de", "significado de", "diccionario"],
        "translate_phrase": ["traduce", "cómo se dice", "traducción", "en español"],
        "check_battery": ["batería", "nivel de batería", "cuánta batería queda", "estado de batería"],
        "flashlight_on": ["enciende la linterna", "linterna encendida", "prende la linterna"],
        "flashlight_off": ["apaga la linterna", "linterna apagada", "apaga la luz"],
        "screenshot": ["toma una captura", "captura de pantalla", "screenshot", "captura la pantalla"],
        "wifi_on": ["enciende el wifi", "wifi encendido", "activa el wifi", "conecta al wifi"],
        "wifi_off": ["apaga el wifi", "wifi apagado", "desactiva el wifi", "desconecta el wifi"],
        "check_timer_status": ["cuánto tiempo queda", "tiempo restante", "cómo va el temporizador"],
        "stop_timer": ["para el temporizador", "cancela el temporizador", "detén el temporizador"],
        "set_volume_exact": ["pon el volumen", "volumen a", "cambia el volumen a", "sube el volumen al"],
        "brightness_up": ["sube el brillo", "más brillo", "aumenta el brillo", "brilla más"],
        "brightness_down": ["baja el brillo", "menos brillo", "reduce el brillo", "disminuye el brillo"],
        "joke": ["dime un chiste", "cuenta un chiste", "hazme reír", "chiste"],
        "riddle": ["dime una adivinanza", "una adivinanza", "adivinanza"],
        "flip_coin": ["lanza una moneda", "cara o cruz", "tira la moneda"],
        "roll_dice": ["tira un dado", "lanza el dado", "dado"],
        "take_note": ["toma una nota", "escribe esto", "guarda una nota"],
        "read_notes": ["lee mis notas", "muestra mis notas", "qué notas tengo"],
        "clear_notes": ["borra mis notas", "elimina todas las notas", "notas"],
        "quote": ["dame una cita", "cita inspiradora", "inspírame"],
        "random_fact": ["dato curioso", "dato interesante", "sabías que"],
        "currency_convert": ["convierte moneda", "tipo de cambio", "cuánto es en"],
        "unit_convert": ["convierte unidades", "cuántos metros", "conversión"],
        "timezone_info": ["qué hora es en", "hora en", "huso horario"],
        "sleep_timer": ["temporizador de sueño", "apagar en", "dormir en"],
        "fan_speed": ["velocidad del ventilador", "ventilador", "ajusta el ventilador"],
        "scene_activate": ["activa escena", "modo escena", "cambia escena"],
        "countdown_event": ["cuenta atrás para", "cuántos días faltan", "días hasta"],
        "shuffle_music": ["aleatorio", "modo aleatorio", "reproducción aleatoria"],
        "repeat_mode": ["repetir", "modo repetición", "repite esta canción"],
        "play_playlist": ["reproduce mi lista", "mi playlist", "abre playlist"],
        "lyrics_search": ["busca letras", "letra de", "lyrics de"],
        "knowledge_query": ["qué sabes sobre", "dime sobre", "qué es", "quién es", "conoces"],
    },
    "fr": {
        "greeting": ["bonjour", "salut", "bonsoir", "coucou", "hello", "salut zeno"],
        "farewell": ["au revoir", "à bientôt", "ciao", "salut", "bonne journée"],
        "time_query": ["quelle heure est-il", "donne-moi l'heure", "l'heure actuelle"],
        "date_query": ["quel jour sommes-nous", "quelle est la date", "date d'aujourd'hui"],
        "weather_query": ["quel temps fait-il", "météo", "va-t-il pleuvoir", "température"],
        "weather_forecast": ["prévisions pour cette semaine", "quel temps fera-t-il cette semaine", "prévisions hebdomadaires", "météo des prochains jours", "prévisions pour les 5 jours"],
        "set_alarm": ["mets un réveil", "réveille-moi à", "alarme pour", "je besoin d'un réveil"],
        "set_timer": ["mets un minuteur", "minuteur de", "compte à rebours"],
        "set_reminder": ["rappelle-moi", "mets un rappel", "n'oublie pas de"],
        "thanks": ["merci", "merci beaucoup", "je te remercie"],
        "affirm": ["oui", "d'accord", "ok", "bien sûr", "exact"],
        "deny": ["non", "jamais", "pas du tout", "non merci"],
        "cancel": ["annuler", "oublie ça", "annule ça"],
        "identity_query": ["qui es-tu", "que es-tu", "comment tu t'appelles"],
        "play_music": ["mets de la musique", "joue de la musique", "joue une chanson", "lance la musique"],
        "next_track": ["chanson suivante", "piste suivante", "suivant", "passe à la suivante"],
        "previous_track": ["chanson précédente", "piste précédente", "précédent", "reviens en arrière"],
        "pause_music": ["pause", "mets en pause", "arrête la musique", "stop"],
        "resume_music": ["reprends", "continue", "relance la musique", "rejoue"],
        "lights_on": ["allume les lumières", "allume la lumière", "lumière"],
        "lights_off": ["éteins les lumières", "éteins la lumière", "lumière éteinte"],
        "set_thermostat": ["règle la température", "change la température", "mets le chauffage"],
        "lock_door": ["ferme la porte", "verrouille la porte", "ferme à clé"],
        "security_check": ["vérifie la sécurité", "état de sécurité", "caméras"],
        "send_message": ["envoie un message", "texte", "envoie un sms", "message à"],
        "make_call": ["passe un appel", "appelle", "téléphone", "fais un appel"],
        "check_email": ["vérifie les emails", "mes emails", "boîte de réception", "nouveaux emails"],
        "read_notifications": ["lis les notifications", "notifications", "montre les alertes"],
        "get_directions": ["itinéraire vers", "navigue vers", "comment aller à"],
        "find_place": ["trouve près de moi", "quoi près de moi", "restaurants près d'ici"],
        "traffic_check": ["état du trafic", "trafic", "y a-t-il du trafic"],
        "define_word": ["définis", "que signifie", "définition de", "sens du mot"],
        "translate_phrase": ["traduis", "comment dit-on", "traduction", "en français"],
        "check_battery": ["batterie", "niveau de batterie", "combien de batterie"],
        "flashlight_on": ["allume la torche", "torche", "lampe de poche"],
        "flashlight_off": ["éteins la torche", "torche éteinte"],
        "screenshot": ["capture d'écran", "screenshot", "prends une capture"],
        "wifi_on": ["allume le wifi", "wifi activé", "connecte au wifi"],
        "wifi_off": ["éteins le wifi", "wifi désactivé", "déconnecte le wifi"],
        "check_timer_status": ["combien de temps reste", "temps restant", "minuteur"],
        "stop_timer": ["arrête le minuteur", "annule le minuteur", "stop minuteur"],
        "set_volume_exact": ["règle le volume", "volume à", "mets le volume à"],
        "brightness_up": ["augmente la luminosité", "plus lumineux", "éclaire plus"],
        "brightness_down": ["baisse la luminosité", "moins lumineux", "diminue la luminosité"],
        "joke": ["raconte une blague", "fais-moi rire", "blague", "dis une blague"],
        "riddle": ["dis une devinette", "devinette", "pose une devinette"],
        "flip_coin": ["pile ou face", "lance une pièce", "tire à pile ou face"],
        "roll_dice": ["lance un dé", "jette le dé", "dé"],
        "take_note": ["prends une note", "note ça", "écris une note"],
        "read_notes": ["lis mes notes", "montre mes notes", "mes notes"],
        "clear_notes": ["efface mes notes", "supprime les notes", "notes"],
        "quote": ["donne une citation", "citation inspirante", "inspire-moi"],
        "random_fact": ["fait intéressant", "le savais-tu", "donne un fait"],
        "currency_convert": ["convertis devise", "taux de change", "combien en"],
        "unit_convert": ["convertis unités", "combien de mètres", "conversion"],
        "timezone_info": ["quelle heure est-il à", "heure à", "fuseau horaire"],
        "sleep_timer": ["minuteur sommeil", "éteindre dans", "dormir dans"],
        "fan_speed": ["vitesse ventilateur", "ventilateur", "règle le ventilateur"],
        "scene_activate": ["active scène", "mode scène", "change de scène"],
        "countdown_event": ["compte à rebours", "combien de jours", "jusqu'à"],
        "shuffle_music": ["aléatoire", "mode aléatoire", "lecture aléatoire"],
        "repeat_mode": ["répéter", "mode répétition", "répète cette chanson"],
        "play_playlist": ["joue ma playlist", "ma liste", "ouvre la playlist"],
        "lyrics_search": ["cherche paroles", "paroles de", "les paroles de"],
        "knowledge_query": ["que sais-tu sur", "parle-moi de", "qu'est-ce que", "qui est", "connais-tu"],
    },
    "de": {
        "greeting": ["hallo", "guten morgen", "guten tag", "guten abend", "servus", "hallo zeno", "moin"],
        "farewell": ["tschüss", "auf wiedersehen", "bis später", "mach's gut", "ciao"],
        "time_query": ["wie spät ist es", "wie viel uhr", "aktuelle zeit", "hast du die uhrzeit"],
        "date_query": ["welcher tag ist heute", "welches datum", "heutiges datum"],
        "weather_query": ["wie ist das wetter", "wetter", "regnet es", "temperatur"],
        "weather_forecast": ["vorhersage für diese woche", "wie wird das wetter diese woche", "wochenvorhersage", "wetter für die nächsten tage", "5 tage vorhersage"],
        "set_alarm": ["stell einen wecker", "weck mich um", "alarm für", "ich brauche einen wecker"],
        "set_timer": ["stell einen timer", "timer für", "countdown", "zeitmesser für"],
        "set_reminder": ["erinnere mich", "mach eine erinnerung", "vergiss nicht"],
        "thanks": ["danke", "vielen dank", "danke schön"],
        "affirm": ["ja", "genau", "okay", "klar", "richtig"],
        "deny": ["nein", "nie", "gar nicht", "nein danke"],
        "cancel": ["abbrechen", "vergiss es", "storno"],
        "identity_query": ["wer bist du", "was bist du", "wie heißt du"],
        "play_music": ["spiele musik", "spiel ein lied", "leg musik auf", "starte musik"],
        "next_track": ["nächster titel", "nächster song", "weiter", "überspringen", "nächstes lied"],
        "previous_track": ["vorheriger titel", "vorheriger song", "zurück", "letztes lied"],
        "pause_music": ["pause", "stopp die musik", "pausieren", "anhalten", "musik aus"],
        "resume_music": ["weiter", "fortsetzen", "weitermachen", "spiel weiter"],
        "lights_on": ["mach das licht an", "licht an", "schalte das licht ein", "beleuchtung an"],
        "lights_off": ["mach das licht aus", "licht aus", "schalte das licht aus", "beleuchtung aus"],
        "set_thermostat": ["stell die temperatur", "temperatur ändern", "heizung höher", "kühler"],
        "lock_door": ["schließ die tür", "tür abschließen", "verriegel die tür"],
        "security_check": ["sicherheitsstatus", "überwachung prüfen", "ist alles sicher"],
        "send_message": ["sende eine nachricht", "schreib eine sms", "nachricht an"],
        "make_call": ["mach einen anruf", "anrufen", "telefonieren", "ruf an"],
        "check_email": ["emails prüfen", "posteingang", "neue emails", "email-check"],
        "read_notifications": ["benachrichtigungen lesen", "benachrichtigungen", "mitteilungen"],
        "get_directions": ["navigation zu", "route zu", "wie komme ich zu"],
        "find_place": ["finde in der nähe", "was ist in der nähe", "orte in der nähe"],
        "traffic_check": ["verkehrsstatus", "verkehr", "stau", "verkehrslage"],
        "define_word": ["definition von", "was bedeutet", "wörterbuch", "bedeutung"],
        "translate_phrase": ["übersetze", "wie sagt man", "übersetzung", "auf deutsch"],
        "check_battery": ["akku prüfen", "akku-stand", "wie viel akku", "batteriestatus"],
        "flashlight_on": ["mach die taschenlampe an", "taschenlampe an", "licht an"],
        "flashlight_off": ["mach die taschenlampe aus", "taschenlampe aus", "licht aus"],
        "screenshot": ["bildschirmfoto", "screenshot", "mach einen screenshot"],
        "wifi_on": ["wifi an", "schalte wifi ein", "verbinde mit wifi"],
        "wifi_off": ["wifi aus", "schalte wifi aus", "trenne wifi"],
        "check_timer_status": ["wie viel zeit bleibt", "restzeit", "timer-status", "wie lange noch"],
        "stop_timer": ["timer stoppen", "timer abbrechen", "timer aus"],
        "set_volume_exact": ["lautstärke einstellen", "lautstärke auf", "volume auf"],
        "brightness_up": ["helligkeit erhöhen", "heller", "bildschirm heller"],
        "brightness_down": ["helligkeit verringern", "dunkler", "bildschirm dunkler"],
        "joke": ["erzähl einen witz", "witz", "bring mich zum lachen"],
        "riddle": ["erzähl ein rätsel", "rätsel", "gib mir ein rätsel"],
        "flip_coin": ["kopf oder zahl", "münze werfen", "wirf eine münze"],
        "roll_dice": ["würfeln", "würfel werfen", "würfel"],
        "take_note": ["mach eine notiz", "notier das", "schreib eine notiz"],
        "read_notes": ["lies meine notizen", "zeig mir notizen", "meine notizen"],
        "clear_notes": ["lösche meine notizen", "alle notizen löschen", "notizen"],
        "quote": ["gib mir ein zitat", "inspirier mich", "motivier mich"],
        "random_fact": ["interessante tatsache", "wusstest du", "fakt"],
        "currency_convert": ["währung umrechnen", "wechselkurs", "wie viel in"],
        "unit_convert": ["einheiten umrechnen", "wie viele meter", "umrechnung"],
        "timezone_info": ["wie spät ist es in", "uhrzeit in", "zeitzone"],
        "sleep_timer": ["schlaf-timer", "ausschalten in", "schlafen in"],
        "fan_speed": ["lüftergeschwindigkeit", "ventilator", "lüfter einstellen"],
        "scene_activate": ["szene aktivieren", "szene wechseln", "modus wechseln"],
        "countdown_event": ["countdown bis", "wie viele tage bis", "tage bis"],
        "shuffle_music": ["zufallswiedergabe", "mischung", "shuffle"],
        "repeat_mode": ["wiederholen", "wiederholungsmodus", "titel wiederholen"],
        "play_playlist": ["spiele playlist", "starte playlist", "öffne playlist"],
        "lyrics_search": ["songtext suchen", "text von", "liedtext zu"],
        "knowledge_query": ["was ist", "erzähl mir von", "wer ist", "was weißt du über", "beschreibe"],
    },
    "hi": {
        "greeting": ["नमस्ते", "नमस्कार", "हैलो", "क्या हाल है", "हेलो ज़ेनो"],
        "farewell": ["अलविदा", "फिर मिलेंगे", "नमस्ते", "चलता हूँ"],
        "time_query": ["कितने बजे हैं", "समय क्या हुआ", "क्या समय है", "टाइम बताओ"],
        "date_query": ["आज कौन सी तारीख है", "आज क्या दिन है", "डेट बताओ"],
        "weather_query": ["मौसम कैसा है", "क्या मौसम है", "बारिश होगी क्या"],
        "weather_forecast": ["इस हफ्ते का मौसम", "पूर्वानुमान बताओ", "अगले कुछ दिनों का मौसम", "साप्ताहिक पूर्वानुमान", "5 दिन का मौसम"],
        "set_alarm": ["अलार्म लगाओ", "मुझे जगाओ", "अलार्म सेट करो"],
        "set_timer": ["टाइमर लगाओ", "टाइमर सेट करो", "गिनती शुरू करो"],
        "set_reminder": ["मुझे याद दिलाना", "रिमाइंडर लगाओ", "भूलना मत"],
        "thanks": ["धन्यवाद", "शुक्रिया", "थैंक्यू"],
        "affirm": ["हाँ", "जी हाँ", "ठीक है", "बिल्कुल"],
        "deny": ["नहीं", "जी नहीं", "कभी नहीं"],
        "cancel": ["रद्द करो", "भूल जाओ", "कैंसल करो"],
        "identity_query": ["तुम कौन हो", "तुम क्या हो", "आप कौन हैं"],
        "play_music": ["संगीत बजाओ", "गाना सुनाओ", "म्यूज़िक चलाओ", "कोई गाना बजाओ"],
        "next_track": ["अगला गाना", "अगला ट्रैक", "छोड़ो", "आगे बढ़ो"],
        "previous_track": ["पिछला गाना", "पिछला ट्रैक", "पीछे जाओ", "वापस जाओ"],
        "pause_music": ["रुको", "संगीत रोको", "विराम", "थोड़ी देर रुको"],
        "resume_music": ["फिर से चलाओ", "जारी रखो", "दोबारा शुरू करो"],
        "lights_on": ["लाइट जलाओ", "रोशनी चालू करो", "बत्ती जलाओ"],
        "lights_off": ["लाइट बंद करो", "रोशनी बंद करो", "बत्ती बंद करो"],
        "set_thermostat": ["तापमान सेट करो", "तापमान बदलो", "गर्मी बढ़ाओ", "एसी चालू करो"],
        "lock_door": ["दरवाज़ा बंद करो", "दरवाज़ा लॉक करो", "ताला लगाओ"],
        "security_check": ["सुरक्षा जाँचो", "सिक्योरिटी स्टेटस", "कैमरे चेक करो"],
        "send_message": ["मैसेज भेजो", "टेक्स्ट भेजो", "संदेश भेजो", "मैसेज करो"],
        "make_call": ["कॉल करो", "फ़ोन करो", "कॉल लगाओ"],
        "check_email": ["ईमेल चेक करो", "मेल देखो", "इनबॉक्स चेक करो"],
        "read_notifications": ["नोटिफिकेशन पढ़ो", "सूचनाएँ देखो", "अलर्ट चेक करो"],
        "get_directions": ["रास्ता बताओ", "दिशा दिखाओ", "कैसे जाऊँ", "नेविगेशन"],
        "find_place": ["पास में ढूँढ़ो", "आस-पास क्या है", "पास की जगहें"],
        "traffic_check": ["ट्रैफिक कैसा है", "यातायात की स्थिति", "ट्रैफिक चेक करो"],
        "define_word": ["अर्थ बताओ", "मतलब क्या है", "शब्दकोश", "परिभाषा बताओ"],
        "translate_phrase": ["अनुवाद करो", "ट्रांसलेट करो", "इसका मतलब"],
        "check_battery": ["बैटरी चेक करो", "बैटरी लेवल", "कितनी बैटरी है"],
        "flashlight_on": ["फ़्लैशलाइट चालू करो", "टॉर्च जलाओ", "रोशनी डालो"],
        "flashlight_off": ["फ़्लैशलाइट बंद करो", "टॉर्च बंद करो"],
        "screenshot": ["स्क्रीनशॉट लो", "स्क्रीन कैप्चर करो", "फोटो लो स्क्रीन का"],
        "wifi_on": ["वाईफ़ाई चालू करो", "वाईफ़ाई ऑन करो", "वाईफ़ाई से जुड़ो"],
        "wifi_off": ["वाईफ़ाई बंद करो", "वाईफ़ाई ऑफ़ करो", "वाईफ़ाई हटाओ"],
        "check_timer_status": ["कितना समय बचा", "बचा हुआ समय", "टाइमर की स्थिति"],
        "stop_timer": ["टाइमर बंद करो", "टाइमर रद्द करो", "गिनती रोको"],
        "set_volume_exact": ["वॉल्यूम सेट करो", "आवाज़ सेट करो", "वॉल्यूम बदलो"],
        "brightness_up": ["चमक बढ़ाओ", "रोशनी बढ़ाओ", "ज़्यादा चमक"],
        "brightness_down": ["चमक घटाओ", "रोशनी कम करो", "धीमी चमक"],
        "joke": ["एक चुटकुला सुनाओ", "चुटकुला", "हँसाओ मुझे"],
        "riddle": ["एक पहेली बताओ", "पहेली", "पहेली पूछो"],
        "flip_coin": ["सिक्का उछालो", "चिट या पट", "सिक्का टॉस"],
        "roll_dice": ["पासा फेंको", "पासा रोल करो", "पासा"],
        "take_note": ["एक नोट लो", "यह लिखो", "नोट करो"],
        "read_notes": ["मेरे नोट पढ़ो", "नोट दिखाओ", "मेरे नोट्स"],
        "clear_notes": ["नोट हटाओ", "सभी नोट मिटाओ", "नोट साफ़ करो"],
        "quote": ["एक प्रेरणादायक बात कहो", "उद्धरण दो", "प्रेरित करो"],
        "random_fact": ["कोई तथ्य बताओ", "दिलचस्प बात", "क्या आप जानते हैं"],
        "currency_convert": ["मुद्रा बदलो", "विनिमय दर", "कितने होंगे"],
        "unit_convert": ["इकाई बदलो", "कितने मीटर", "रूपांतरण"],
        "timezone_info": ["वहाँ कितने बजे हैं", "समय बताओ", "टाइमज़ोन"],
        "sleep_timer": ["स्लीप टाइमर", "बंद हो जाओ", "सो जाओ"],
        "fan_speed": ["पंखे की गति", "पंखा सेट करो", "पंखा चलाओ"],
        "scene_activate": ["दृश्य सक्रिय करो", "दृश्य बदलो", "मोड बदलो"],
        "countdown_event": ["काउंटडाउन", "कितने दिन बचे", "दिनों की गिनती"],
        "shuffle_music": ["शफल करो", "रैंडम चलाओ", "मिलाओ"],
        "repeat_mode": ["दोहराओ", "रिपीट मोड", "फिर से चलाओ"],
        "play_playlist": ["प्लेलिस्ट चलाओ", "मेरी सूची चलाओ", "प्लेलिस्ट खोलो"],
        "lyrics_search": ["गीत खोजो", "बोल दिखाओ", "गाने के बोल"],
        "knowledge_query": ["क्या है", "बताओ", "कौन है", "जानकारी दो", "तुम क्या जानते हो"],
    },
    "ja": {
        "greeting": ["こんにちは", "やあ", "おはよう", "こんばんは", "ゼノ", "ヘイ"],
        "farewell": ["さようなら", "またね", "バイバイ", "じゃあね", "おやすみ"],
        "time_query": ["今何時", "時間を教えて", "今の時間", "何時ですか"],
        "date_query": ["今日は何日", "日付を教えて", "今日の日付", "何曜日"],
        "weather_query": ["天気はどう", "今日の天気", "雨が降る", "気温は", "天気予報"],
        "weather_forecast": ["今週の天気予報", "週間天気", "5日間の天気", "今週の天気は"],
        "set_alarm": ["アラームをセット", "起こして", "アラーム", "目覚まし"],
        "set_timer": ["タイマーをセット", "タイマー", "カウントダウン", "時間を計って"],
        "set_reminder": ["リマインダー", "忘れないで", "思い出させて", "リマインド"],
        "thanks": ["ありがとう", "どうも", "感謝", "サンキュー"],
        "affirm": ["はい", "うん", "そう", "オーケー", "いいよ"],
        "deny": ["いいえ", "違う", "ノー", "いや", "結構です"],
        "cancel": ["キャンセル", "やめとく", "取り消し", "忘れて"],
        "identity_query": ["あなたは誰", "何ができる", "名前は", "ゼノとは"],
        "play_music": ["音楽をかけて", "曲を再生", "ミュージック", "何か歌って"],
        "next_track": ["次の曲", "スキップ", "次へ", "次のトラック"],
        "previous_track": ["前の曲", "戻って", "前のトラック", "巻き戻し"],
        "pause_music": ["一時停止", "止めて", "ポーズ", "ストップ"],
        "resume_music": ["再開", "続けて", "再生再開", "もう一度"],
        "lights_on": ["電気をつけて", "照明オン", "明かりをつけて"],
        "lights_off": ["電気を消して", "照明オフ", "明かりを消して"],
        "set_thermostat": ["温度を設定", "エアコン", "暖房をつけて", "冷房"],
        "lock_door": ["ドアをロック", "鍵をかける", "施錠"],
        "security_check": ["セキュリティ確認", "安全チェック", "カメラ確認"],
        "send_message": ["メッセージを送信", "テキスト", "伝言"],
        "make_call": ["電話をかける", "コール", "電話して"],
        "check_email": ["メールを確認", "受信箱", "新着メール"],
        "read_notifications": ["通知を読んで", "お知らせ", "通知確認"],
        "get_directions": ["道案内", "ナビ", "行き方", "ルート"],
        "find_place": ["近くを探す", "周辺", "この辺りの"],
        "traffic_check": ["交通情報", "渋滞", "道路状況"],
        "define_word": ["意味は", "定義", "辞書", "どういう意味"],
        "translate_phrase": ["翻訳", "英語でなんて言う", "訳して"],
        "check_battery": ["バッテリー残量", "電池", "充電"],
        "flashlight_on": ["ライトをつけて", "フラッシュライト", "懐中電灯"],
        "flashlight_off": ["ライトを消して", "フラッシュライトオフ"],
        "screenshot": ["スクリーンショット", "画面キャプチャ"],
        "wifi_on": ["WiFiをオン", "ワイファイ繋いで", "無線LAN"],
        "wifi_off": ["WiFiをオフ", "ワイファイ切って"],
        "check_timer_status": ["残り時間", "タイマー残り", "あとどのくらい"],
        "stop_timer": ["タイマー停止", "タイマー解除", "止めて"],
        "set_volume_exact": ["音量設定", "ボリューム", "音量を"],
        "brightness_up": ["明るくして", "輝度上げて", "画面明るく"],
        "brightness_down": ["暗くして", "輝度下げて", "画面暗く"],
        "joke": ["ジョークを言って", "笑かして", "面白いこと言って"],
        "riddle": ["なぞなぞを出して", "なぞなぞ", "クイズを出して"],
        "flip_coin": ["コインを投げて", "表か裏", "コイントス"],
        "roll_dice": ["サイコロを振って", "さいころ", "ダイスロール"],
        "take_note": ["メモを取って", "書き留めて", "ノートに保存"],
        "read_notes": ["メモを見せて", "ノートを読んで", "保存メモ"],
        "clear_notes": ["メモを消して", "全てのメモ削除", "メモをクリア"],
        "quote": ["名言を教えて", "感動的な言葉", "インスパイアして"],
        "random_fact": ["雑学を教えて", "面白い事実", "知ってる"],
        "currency_convert": ["通貨変換", "為替レート", "いくらになる"],
        "unit_convert": ["単位変換", "何メートル", "変換して"],
        "timezone_info": ["今何時", "今の時刻", "タイムゾーン"],
        "sleep_timer": ["スリープタイマー", "消灯タイマー", "後で消して"],
        "fan_speed": ["扇風機の速度", "ファンの設定", "扇風機"],
        "scene_activate": ["シーン起動", "シーン変更", "モード切替"],
        "countdown_event": ["カウントダウン", "あと何日", "日数計算"],
        "shuffle_music": ["シャッフル", "ランダム再生", "混ぜて再生"],
        "repeat_mode": ["リピート", "繰り返し", "リピートモード"],
        "play_playlist": ["プレイリスト再生", "マイリスト", "プレイリスト"],
        "lyrics_search": ["歌詞を探して", "歌詞表示", "歌詞"],
        "knowledge_query": ["とは何ですか", "について教えて", "誰ですか", "知っていますか"],
    },
    "ko": {
        "greeting": ["안녕", "안녕하세요", "헤이", "좋은 아침", "제노"],
        "farewell": ["잘 가", "다음에 봐", "안녕히 계세요", "잘 있어"],
        "time_query": ["몇 시야", "지금 시간", "시간 알려줘", "몇 시예요"],
        "date_query": ["오늘 날짜", "며칠이야", "오늘 무슨 요일"],
        "weather_query": ["날씨 어때", "오늘 날씨", "비 올까", "기온은"],
        "weather_forecast": ["이번 주 날씨", "주간 예보", "5일 예보", "주말 날씨"],
        "set_alarm": ["알람 설정", "깨워 줘", "알람 맞춰", "모닝콜"],
        "set_timer": ["타이머 설정", "타이머", "카운트다운"],
        "set_reminder": ["리마인더", "잊지 말게", "알림 설정", "기억시켜 줘"],
        "thanks": ["고마워", "감사합니다", "땡큐"],
        "affirm": ["응", "네", "맞아", "좋아", "그래"],
        "deny": ["아니", "아니요", "싫어", "괜찮아"],
        "cancel": ["취소", "잊어버려", "취소할게"],
        "identity_query": ["너 누구야", "뭐 할 수 있어", "이름이 뭐야"],
        "play_music": ["음악 틀어", "노래 재생", "음악", "노래 들려줘"],
        "next_track": ["다음 곡", "다음 트랙", "스킵", "넘겨"],
        "previous_track": ["이전 곡", "이전 트랙", "되감기"],
        "pause_music": ["일시 정지", "멈춰", "잠깐만"],
        "resume_music": ["다시 재생", "계속", "이어서"],
        "lights_on": ["불 켜", "조명 켜", "라이트 온"],
        "lights_off": ["불 꺼", "조명 꺼", "라이트 오프"],
        "set_thermostat": ["온도 설정", "에어컨", "난방", "온도 조절"],
        "lock_door": ["문 잠가", "도어 락", "잠금"],
        "security_check": ["보안 확인", "안전 점검", "카메라 확인"],
        "send_message": ["메시지 보내", "문자 보내", "전송"],
        "make_call": ["전화 걸어", "통화", "콜"],
        "check_email": ["이메일 확인", "메일", "받은 편지함"],
        "read_notifications": ["알림 읽어 줘", "노티 확인", "알림"],
        "get_directions": ["길 안내", "네비", "가는 방법"],
        "find_place": ["주변 찾기", "근처", "가까운"],
        "traffic_check": ["교통 정보", "길 막혀", "교통 상황"],
        "define_word": ["뜻이 뭐야", "사전", "의미", "정의"],
        "translate_phrase": ["번역", "영어로 뭐야", "통역"],
        "check_battery": ["배터리", "잔량", "충전 상태"],
        "flashlight_on": ["손전등 켜", "플래시", "불 켜줘"],
        "flashlight_off": ["손전등 꺼", "플래시 오프"],
        "screenshot": ["스크린샷", "캡처", "화면 저장"],
        "wifi_on": ["와이파이 켜", "WiFi 온", "인터넷 연결"],
        "wifi_off": ["와이파이 꺼", "WiFi 오프"],
        "check_timer_status": ["남은 시간", "타이머 확인", "얼마나 남았어"],
        "stop_timer": ["타이머 멈춰", "타이머 취소"],
        "set_volume_exact": ["볼륨 설정", "소리 크기", "음량"],
        "brightness_up": ["밝게", "화면 밝기 올려", "더 밝게"],
        "brightness_down": ["어둡게", "화면 밝기 내려", "더 어둡게"],
        "joke": ["농담 해 줘", "재미있는 얘기 해 줘", "웃게 해 줘"],
        "riddle": ["수수께끼 내 줘", "수수께끼", "퀴즈 내 줘"],
        "flip_coin": ["동전 던져", "앞면 뒷면", "동전 토스"],
        "roll_dice": ["주사위 던져", "주사위 굴려", "다이스"],
        "take_note": ["메모 해 줘", "적어 둬", "노트에 저장"],
        "read_notes": ["메모 읽어 줘", "노트 보여 줘", "내 메모"],
        "clear_notes": ["메모 지워", "모든 메모 삭제", "노트 정리"],
        "quote": ["명언 해 줘", "영감을 줘", "좋은 말 해 줘"],
        "random_fact": ["재미있는 사실", "알려 줘", "흥미로운 사실"],
        "currency_convert": ["환율 알려 줘", "통화 변환", "얼마야"],
        "unit_convert": ["단위 변환", "몇 미터야", "변환 해 줘"],
        "timezone_info": ["지금 몇 시야", "시간 알려 줘", "시차"],
        "sleep_timer": ["슬립 타이머", "잠자기", "끄기 타이머"],
        "fan_speed": ["선풍기 속도", "팬 설정", "선풍기"],
        "scene_activate": ["장면 활성화", "모드 변경", "씬 변경"],
        "countdown_event": ["카운트다운", "며칠 남았어", "D-Day"],
        "shuffle_music": ["셔플", "랜덤 재생", "섞어 재생"],
        "repeat_mode": ["반복", "반복 재생", "한 곡 반복"],
        "play_playlist": ["플레이리스트 재생", "내 리스트", "플레이리스트"],
        "lyrics_search": ["가사 검색", "가사 보여 줘", "노래 가사"],
        "knowledge_query": ["무엇인가요", "에 대해 알려줘", "누구예요", "알고 있어"],
    },
    "pt": {
        "greeting": ["olá", "oi", "bom dia", "boa tarde", "boa noite", "hey zeno", "e aí"],
        "farewell": ["tchau", "até logo", "adeus", "até mais", "boa noite"],
        "time_query": ["que horas são", "me diga as horas", "hora atual", "qual é a hora"],
        "date_query": ["que dia é hoje", "qual a data de hoje", "data atual"],
        "weather_query": ["como está o tempo", "vai chover", "temperatura", "clima", "previsão do tempo"],
        "weather_forecast": ["previsão para esta semana", "clima da semana", "previsão semanal", "como vai estar o tempo esta semana"],
        "set_alarm": ["definir alarme", "me acorde às", "alarme para", "coloque um alarme"],
        "set_timer": ["definir timer", "cronômetro", "temporizador", "timer para"],
        "set_reminder": ["me lembre", "criar lembrete", "não me deixe esquecer", "lembrete"],
        "thanks": ["obrigado", "valeu", "muito obrigado", "agradecido"],
        "affirm": ["sim", "claro", "ok", "beleza", "certo", "isso mesmo"],
        "deny": ["não", "nunca", "de jeito nenhum", "não obrigado"],
        "cancel": ["cancelar", "deixa pra lá", "esquece", "cancela"],
        "identity_query": ["quem é você", "o que você é", "como se chama", "o que você faz"],
        "play_music": ["tocar música", "coloque uma música", "toque algo", "música"],
        "next_track": ["próxima música", "próxima faixa", "pular", "avançar"],
        "previous_track": ["música anterior", "faixa anterior", "voltar", "anterior"],
        "pause_music": ["pausar", "pausa", "pare a música", "parar"],
        "resume_music": ["continuar", "retomar", "tocar de novo", "voltar a tocar"],
        "lights_on": ["acender as luzes", "luzes acesas", "acenda a luz", "iluminar"],
        "lights_off": ["apagar as luzes", "luzes apagadas", "apague a luz", "escurecer"],
        "set_thermostat": ["ajustar temperatura", "mudar temperatura", "aquecer", "esfriar"],
        "lock_door": ["trancar a porta", "feche a porta", "porta trancada"],
        "security_check": ["verificar segurança", "status de segurança", "câmeras"],
        "send_message": ["enviar mensagem", "mande um texto", "mensagem para"],
        "make_call": ["fazer uma chamada", "ligar", "telefonar", "chamada"],
        "check_email": ["verificar email", "meus emails", "caixa de entrada"],
        "read_notifications": ["ler notificações", "notificações", "mostrar alertas"],
        "get_directions": ["direções para", "navegar para", "como chegar em"],
        "find_place": ["encontrar perto", "o que tem perto", "lugares próximos"],
        "traffic_check": ["verificar trânsito", "trânsito", "como está o trânsito"],
        "define_word": ["definir", "o que significa", "definição de", "dicionário"],
        "translate_phrase": ["traduzir", "como se diz", "tradução", "em português"],
        "check_battery": ["bateria", "nível da bateria", "quanto resta de bateria"],
        "flashlight_on": ["ligar lanterna", "lanterna acesa", "flashlight"],
        "flashlight_off": ["desligar lanterna", "lanterna apagada"],
        "screenshot": ["capturar tela", "print", "screenshot"],
        "wifi_on": ["ligar wifi", "wifi ligado", "conectar ao wifi"],
        "wifi_off": ["desligar wifi", "wifi desligado", "desconectar wifi"],
        "check_timer_status": ["quanto tempo falta", "tempo restante", "status do timer"],
        "stop_timer": ["parar timer", "cancelar timer", "desligar timer"],
        "set_volume_exact": ["definir volume", "volume para", "mudar volume para"],
        "brightness_up": ["aumentar brilho", "mais brilho", "clarear"],
        "brightness_down": ["diminuir brilho", "menos brilho", "escurecer"],
        "joke": ["conte uma piada", "faça-me rir", "piada", "diga uma piada"],
        "riddle": ["diga uma charada", "charada", "uma adivinha"],
        "flip_coin": ["jogue uma moeda", "cara ou coroa", "moeda"],
        "roll_dice": ["jogue um dado", "lance o dado", "dado"],
        "take_note": ["faça uma anotação", "anote isso", "guarde uma nota"],
        "read_notes": ["leia minhas notas", "mostre notas", "minhas anotações"],
        "clear_notes": ["limpe minhas notas", "apague todas notas", "notas"],
        "quote": ["dê uma citação", "citação inspiradora", "inspire-me"],
        "random_fact": ["fato interessante", "curiosidade", "você sabia"],
        "currency_convert": ["converter moeda", "taxa de câmbio", "quanto é em"],
        "unit_convert": ["converter unidades", "quantos metros", "conversão"],
        "timezone_info": ["quantas horas são em", "horário em", "fuso horário"],
        "sleep_timer": ["timer de sono", "desligar em", "dormir em"],
        "fan_speed": ["velocidade do ventilador", "ventilador", "ajuste o ventilador"],
        "scene_activate": ["ativar cena", "mudar cena", "modo cena"],
        "countdown_event": ["contagem regressiva", "quantos dias até", "dias até"],
        "shuffle_music": ["aleatório", "modo aleatório", "embaralhar"],
        "repeat_mode": ["repetir", "modo repetição", "repita esta música"],
        "play_playlist": ["tocar playlist", "minha lista", "abra playlist"],
        "lyrics_search": ["procurar letras", "letra de", "lyrics de"],
        "knowledge_query": ["o que é", "fale sobre", "quem é", "o que sabe sobre", "conhece"],
    },
    "ar": {
        "greeting": ["مرحبا", "السلام عليكم", "أهلاً", "صباح الخير", "مساء الخير", "هاي"],
        "farewell": ["وداعاً", "مع السلامة", "إلى اللقاء", "بااي", "تصبح على خير"],
        "time_query": ["كم الساعة", "أخبرني بالوقت", "الوقت الآن", "الساعة"],
        "date_query": ["ما تاريخ اليوم", "كم التاريخ", "أي يوم اليوم"],
        "weather_query": ["كيف الطقس", "الطقس", "هل ستمطر", "درجة الحرارة", "الجو"],
        "weather_forecast": ["توقعات هذا الأسبوع", "الطقس للأيام القادمة", "توقعات الأسبوع", "حالة الطقس الأسبوعية"],
        "set_alarm": ["ضبط منبه", "أيقظني في", "منبه لـ", "نبهني"],
        "set_timer": ["ضبط مؤقت", "مؤقت", "عداد", "تايمر"],
        "set_reminder": ["ذكرني", "تذكير", "لا تنسى", "أضف تذكيراً"],
        "thanks": ["شكراً", "جزاك الله خيراً", "ممنون", "تسلم"],
        "affirm": ["نعم", "أجل", "طيب", "حسناً", "موافق"],
        "deny": ["لا", "كلا", "أبداً", "لا شكراً"],
        "cancel": ["إلغاء", "انس الأمر", "ألغِ"],
        "identity_query": ["من أنت", "ما اسمك", "ماذا يمكنك أن تفعل", "ما أنت"],
        "play_music": ["شغل موسيقى", "شغل أغنية", "دور موسيقى", "شغللي أغنية"],
        "next_track": ["الأغنية التالية", "التالي", "تخطي", "الملف التالي"],
        "previous_track": ["الأغنية السابقة", "السابق", "رجوع", "الملف السابق"],
        "pause_music": ["إيقاف مؤقت", "وقف", "أوقف الموسيقى", "توقف"],
        "resume_music": ["استمرار", "شغل مرة أخرى", "أكمل", "استأنف"],
        "lights_on": ["أشعل الضوء", "الاضاءة", "النور", "ضوء"],
        "lights_off": ["أطفئ الضوء", "اطفي النور", "إطفاء"],
        "set_thermostat": ["ضبط درجة الحرارة", "دفايه", "تكييف", "حرارة"],
        "lock_door": ["أغلق الباب", "قفل الباب", "اقفل"],
        "security_check": ["فحص الأمان", "حالة الأمن", "كاميرات"],
        "send_message": ["أرسل رسالة", "رسالة نصية", "رسالة لـ"],
        "make_call": ["اتصل", "إجراء مكالمة", "كلم"],
        "check_email": ["تفقد البريد", "الإيميلات", "صندوق الوارد"],
        "read_notifications": ["اقرأ الإشعارات", "التنبيهات", "الإشعارات"],
        "get_directions": ["اتجاهات إلى", "كيف أصل إلى", "الملاحة إلى"],
        "find_place": ["ابحث بالقرب مني", "ماذا يوجد بالقرب", "أماكن قريبة"],
        "traffic_check": ["حالة المرور", "الزحمة", "هل هناك زحام"],
        "define_word": ["تعريف", "معنى", "القاموس", "ما معنى"],
        "translate_phrase": ["ترجمة", "كيف نقول", "الترجمة إلى"],
        "check_battery": ["البطارية", "نسبة البطارية", "كم البطارية"],
        "flashlight_on": ["شغل الضوء", " flashlight", "كشاف"],
        "flashlight_off": ["أطفئ الضوء", "إطفاء الكشاف"],
        "screenshot": ["لقطة شاشة", "تصوير الشاشة", "سكرين شوت"],
        "wifi_on": ["شغل الواي فاي", "واي فاي", "اتصال بالإنترنت"],
        "wifi_off": ["أطفئ الواي فاي", "قطع الواي فاي"],
        "check_timer_status": ["كم تبقى من الوقت", "الوقت المتبقي", "حالة المؤقت"],
        "stop_timer": ["أوقف المؤقت", "إلغاء المؤقت", "أطفئ المؤقت"],
        "set_volume_exact": ["ضبط مستوى الصوت", "الصوت", "درجة الصوت"],
        "brightness_up": ["زيادة السطوع", "أضيئ أكثر", "ارفع الإضاءة"],
        "brightness_down": ["تقليل السطوع", "أظلم", "خفف الإضاءة"],
        "joke": ["قل نكتة", "نكتة", "اضحكني"],
        "riddle": ["قل لي أحجية", "أحجية", "لغز"],
        "flip_coin": ["اقلب عملة", "كتابة أو وجه", "عملة"],
        "roll_dice": ["ارمي النرد", "نرد", "حجر النرد"],
        "take_note": ["خذ ملاحظة", "دون هذا", "اكتب ملاحظة"],
        "read_notes": ["اقرأ ملاحظاتي", "أظهر ملاحظاتي", "ملاحظات"],
        "clear_notes": ["امسح ملاحظاتي", "احذف كل الملاحظات", "ملاحظات"],
        "quote": ["قل لي اقتباساً", "اقتباس ملهم", "ألهمني"],
        "random_fact": ["حقيقة عشوائية", "معلومة", "هل تعلم"],
        "currency_convert": ["تحويل عملة", "سعر الصرف", "كم يساوي"],
        "unit_convert": ["تحويل وحدات", "كم متراً", "تحويل"],
        "timezone_info": ["كم الساعة في", "الوقت في", "المنطقة الزمنية"],
        "sleep_timer": ["مؤقت النوم", "إيقاف في", "النوم في"],
        "fan_speed": ["سرعة المروحة", "مروحة", "اضبط المروحة"],
        "scene_activate": ["تفعيل المشهد", "تغيير المشهد", "نمط المشهد"],
        "countdown_event": ["العد التنازلي", "كم يوماً متبقياً", "أيام حتى"],
        "shuffle_music": ["خلط", "وضع عشوائي", "تشغيل عشوائي"],
        "repeat_mode": ["تكرار", "وضع التكرار", "كرر هذه الأغنية"],
        "play_playlist": ["شغل قائمتي", "قائمة التشغيل", "افتح القائمة"],
        "lyrics_search": ["ابحث عن كلمات", "كلمات الأغنية", "كلمات"],
        "knowledge_query": ["ما هو", "أخبرني عن", "من هو", "ماذا تعرف عن", "هل تعرف"],
    },
}


def detect_language(text: str) -> str:
    """
    Heuristic language detection from Unicode ranges.
    Supports: hi, ja, ko, ar, zh, ru, en (fallback).
    """
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            return "hi"
        if 0x3040 <= cp <= 0x309F or 0x30A0 <= cp <= 0x30FF:
            return "ja"
        if 0xAC00 <= cp <= 0xD7AF:
            return "ko"
        if 0x4E00 <= cp <= 0x9FFF or 0x3400 <= cp <= 0x4DBF:
            return "zh"
        if 0x0600 <= cp <= 0x06FF:
            return "ar"
        if 0x0400 <= cp <= 0x04FF:
            return "ru"
    return "en"


def _merge_language_data(base: dict, lang: str) -> dict:
    extra = LANGUAGE_PHRASES.get(lang, {})
    if not extra:
        return base
    merged = {}
    for intent, phrases in base.items():
        merged[intent] = phrases + extra.get(intent, [])
    for intent, phrases in extra.items():
        if intent not in merged:
            merged[intent] = phrases
    return merged


# Module-level singleton
_classifier: IntentClassifier | None = None
_current_language: str = "auto"
_all_langs_merged: dict[str, list[str]] | None = None


def _build_merged() -> dict[str, list[str]]:
    """Merge ALL language data into one giant training set."""
    merged = dict(TRAINING_DATA)
    for lang_data in LANGUAGE_PHRASES.values():
        for intent, phrases in lang_data.items():
            if intent in merged:
                merged[intent] = list(set(merged[intent] + phrases))
            else:
                merged[intent] = phrases
    return merged


def get_classifier(language: str | None = None, enhanced: bool = True) -> IntentClassifier:
    global _classifier, _current_language, _all_langs_merged
    lang = language or _current_language

    if _classifier is not None and lang == _current_language:
        return _classifier

    cls = EnhancedClassifier if enhanced else IntentClassifier

    if lang == "auto":
        if _all_langs_merged is None:
            _all_langs_merged = _build_merged()
        _classifier = cls()
        _classifier.fit(_all_langs_merged)
    else:
        data = _merge_language_data(TRAINING_DATA, lang)
        _classifier = cls()
        _classifier.fit(data)

    _current_language = lang
    return _classifier


def set_language(lang: str):
    """Set the language (en, es, fr, de, hi, ja, ko, pt, ar, auto)."""
    if lang in LANGUAGE_PHRASES or lang in ("en", "auto"):
        get_classifier(lang)


def classify_intent(text: str, context_intent: str | None = None) -> IntentResult:
    if _current_language == "auto":
        lang = "auto"
    elif _current_language == "en":
        lang = detect_language(text)
    else:
        lang = _current_language
    result = get_classifier(lang).predict(text, context_intent=context_intent)

    if result.confidence < 0.55:
        result = _maybe_semantic_override(text, result)

    return result


def _maybe_semantic_override(text: str, result: IntentResult) -> IntentResult:
    """When the n-gram classifier is unsure, optionally consult the
    embedding model (see zeno/nlu/embeddings.py) as a tie-breaker.

    This never runs — and never changes behavior — unless the person
    has installed the optional NLU embedding extra (onnxruntime +
    tokenizers) and downloaded the model. Any failure here is silently
    swallowed and the original n-gram result is kept, since this is a
    strictly-additive enhancement, not a dependency."""
    try:
        from zeno.nlu import embeddings
        if not (embeddings.is_available() and embeddings.is_model_downloaded()):
            return result
        match = embeddings.best_semantic_match(text, TRAINING_DATA)
        if match is None:
            return result
        semantic_intent, semantic_score = match
        if (semantic_intent != result.intent
                and semantic_score > result.confidence + embeddings.OVERRIDE_MARGIN):
            return IntentResult(intent=semantic_intent, confidence=semantic_score, raw=result.raw)
    except Exception:
        pass
    return result
