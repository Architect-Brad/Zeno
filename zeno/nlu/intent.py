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
        "tell me a joke", "tell me a story", "sing a song",
        "sing me a song", "make me laugh", "tell me something funny",
        "tell me a riddle", "entertain me", "amuse me",
        "crack a joke", "say something funny",
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


class IntentClassifier:
    """
    Semantic intent classifier using character n-gram vectors.

    Uses max-similarity to individual training examples (k-NN style).
    Much better for short utterances than centroid averaging.
    """

    def __init__(self, ngram_range: tuple[int, int] = (2, 4)):
        self.vectorizer = NGramVectorizer(ngram_range)
        self.examples: dict[str, list[dict[str, float]]] = {}
        self._is_fit = False

    def _expand_phrases(self, phrases: list[str]) -> list[str]:
        expanded = []
        skip_expand_prefixes = ("what", "how", "who", "why", "when", "which")
        for phrase in phrases:
            expanded.append(phrase)
            lowered = phrase.lower()
            if not lowered.startswith(skip_expand_prefixes):
                expanded.append(f"i want to {lowered}")
                expanded.append(f"i need to {lowered}")
                expanded.append(f"can you {lowered}")
                expanded.append(f"please {lowered}")
                expanded.append(f"i'd like to {lowered}")
        return expanded

    def fit(self, data: dict[str, list[str]] | None = None):
        training = data or TRAINING_DATA
        for intent, phrases in training.items():
            vectors = []
            expanded = self._expand_phrases(phrases)
            for phrase in expanded:
                vectors.append(self.vectorizer.vectorize(phrase))
            self.examples[intent] = vectors
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


# ---------------------------------------------------------------------------
# Multi-language support — translated training data
# ---------------------------------------------------------------------------

LANGUAGE_PHRASES: dict[str, dict[str, list[str]]] = {
    "es": {
        "greeting": ["hola", "buenos días", "buenas tardes", "buenas noches", "hey", "qué tal", "saludos", "hola zeno"],
        "farewell": ["adiós", "hasta luego", "nos vemos", "cuídate", "bye", "hasta pronto"],
        "time_query": ["qué hora es", "qué hora tienes", "dime la hora", "hora actual", "me das la hora"],
        "date_query": ["qué día es hoy", "qué fecha es", "dime la fecha", "fecha actual"],
        "weather_query": ["qué tiempo hace", "cómo está el clima", "va a llover", "temperatura", "clima"],
        "set_alarm": ["pon una alarma", "despiértame a las", "alarma para", "necesito una alarma"],
        "set_timer": ["pon un temporizador", "temporizador de", "cuenta atrás", "temporizador para"],
        "set_reminder": ["recuérdame", "pon un recordatorio", "no me olvides", "recordatorio"],
        "thanks": ["gracias", "muchas gracias", "te agradezco", "gracias totales"],
        "affirm": ["sí", "si", "claro", "vale", "ok", "de acuerdo", "correcto"],
        "deny": ["no", "nunca", "para nada", "no gracias", "no quiero"],
        "cancel": ["cancelar", "olvídalo", "cancela eso", "no importa"],
        "identity_query": ["quién eres", "qué eres", "cómo te llamas", "qué puedes hacer"],
    },
    "fr": {
        "greeting": ["bonjour", "salut", "bonsoir", "coucou", "hello", "salut zeno"],
        "farewell": ["au revoir", "à bientôt", "ciao", "salut", "bonne journée"],
        "time_query": ["quelle heure est-il", "donne-moi l'heure", "l'heure actuelle"],
        "date_query": ["quel jour sommes-nous", "quelle est la date", "date d'aujourd'hui"],
        "weather_query": ["quel temps fait-il", "météo", "va-t-il pleuvoir", "température"],
        "set_alarm": ["mets un réveil", "réveille-moi à", "alarme pour", "je besoin d'un réveil"],
        "set_timer": ["mets un minuteur", "minuteur de", "compte à rebours"],
        "set_reminder": ["rappelle-moi", "mets un rappel", "n'oublie pas de"],
        "thanks": ["merci", "merci beaucoup", "je te remercie"],
        "affirm": ["oui", "d'accord", "ok", "bien sûr", "exact"],
        "deny": ["non", "jamais", "pas du tout", "non merci"],
        "cancel": ["annuler", "oublie ça", "annule ça"],
        "identity_query": ["qui es-tu", "que es-tu", "comment tu t'appelles"],
    },
    "de": {
        "greeting": ["hallo", "guten morgen", "guten tag", "guten abend", "servus", "hallo zeno", "moin"],
        "farewell": ["tschüss", "auf wiedersehen", "bis später", "mach's gut", "ciao"],
        "time_query": ["wie spät ist es", "wie viel uhr", "aktuelle zeit", "hast du die uhrzeit"],
        "date_query": ["welcher tag ist heute", "welches datum", "heutiges datum"],
        "weather_query": ["wie ist das wetter", "wetter", "regnet es", "temperatur"],
        "set_alarm": ["stell einen wecker", "weck mich um", "alarm für", "ich brauche einen wecker"],
        "set_timer": ["stell einen timer", "timer für", "countdown", "zeitmesser für"],
        "set_reminder": ["erinnere mich", "mach eine erinnerung", "vergiss nicht"],
        "thanks": ["danke", "vielen dank", "danke schön"],
        "affirm": ["ja", "genau", "okay", "klar", "richtig"],
        "deny": ["nein", "nie", "gar nicht", "nein danke"],
        "cancel": ["abbrechen", "vergiss es", "storno"],
        "identity_query": ["wer bist du", "was bist du", "wie heißt du"],
    },
    "hi": {
        "greeting": ["नमस्ते", "नमस्कार", "हैलो", "क्या हाल है", "हेलो ज़ेनो"],
        "farewell": ["अलविदा", "फिर मिलेंगे", "नमस्ते", "चलता हूँ"],
        "time_query": ["कितने बजे हैं", "समय क्या हुआ", "क्या समय है", "टाइम बताओ"],
        "date_query": ["आज कौन सी तारीख है", "आज क्या दिन है", "डेट बताओ"],
        "weather_query": ["मौसम कैसा है", "क्या मौसम है", "बारिश होगी क्या"],
        "set_alarm": ["अलार्म लगाओ", "मुझे जगाओ", "अलार्म सेट करो"],
        "set_timer": ["टाइमर लगाओ", "टाइमर सेट करो", "गिनती शुरू करो"],
        "set_reminder": ["मुझे याद दिलाना", "रिमाइंडर लगाओ", "भूलना मत"],
        "thanks": ["धन्यवाद", "शुक्रिया", "थैंक्यू"],
        "affirm": ["हाँ", "जी हाँ", "ठीक है", "बिल्कुल"],
        "deny": ["नहीं", "जी नहीं", "कभी नहीं"],
        "cancel": ["रद्द करो", "भूल जाओ", "कैंसल करो"],
        "identity_query": ["तुम कौन हो", "तुम क्या हो", "आप कौन हैं"],
    },
}


def detect_language(text: str) -> str:
    """
    Heuristic language detection from Unicode ranges.
    Returns 'hi' for Devanagari, 'zh' for CJK, 'ar' for Arabic, 'en' as fallback.
    """
    for ch in text:
        cp = ord(ch)
        if 0x0900 <= cp <= 0x097F:
            return "hi"
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


def get_classifier(language: str | None = None) -> IntentClassifier:
    global _classifier, _current_language, _all_langs_merged
    lang = language or _current_language

    if _classifier is not None and lang == _current_language:
        return _classifier

    if lang == "auto":
        if _all_langs_merged is None:
            _all_langs_merged = _build_merged()
        _classifier = IntentClassifier()
        _classifier.fit(_all_langs_merged)
    else:
        data = _merge_language_data(TRAINING_DATA, lang)
        _classifier = IntentClassifier()
        _classifier.fit(data)

    _current_language = lang
    return _classifier


def set_language(lang: str):
    """Set the language for intent classification (en, es, fr, de, hi, auto)."""
    if lang in LANGUAGE_PHRASES or lang in ("en", "auto"):
        get_classifier(lang)


def classify_intent(text: str, context_intent: str | None = None) -> IntentResult:
    if _current_language == "auto":
        lang = "auto"
    elif _current_language == "en":
        lang = detect_language(text)
    else:
        lang = _current_language
    return get_classifier(lang).predict(text, context_intent=context_intent)
