# Zeno — On-Device Voice Assistant

**Semantic NLU · Cross-Platform Control · LAN Sync · Zero Cloud Dependencies**

Built by **The Architect**.

```
                    ⚡
                   /█\
                   / \
```

Zeno is a production-ready voice assistant that runs entirely on your device. It understands natural language using character n-gram semantic classification, controls real system functions, manages reminders and timers, provides weather / calculation / news / search capabilities, controls smart home devices, syncs across your LAN, and supports **9 languages** — all with **no cloud APIs, no ML frameworks, and no data leaving your machine**.

**RAM footprint: ~22 MB** (after import + first classification). Codebase: 794 KB, 5.5k lines across 48 Python files.

![CI](https://github.com/Architect-Brad/Zeno/actions/workflows/ci.yml/badge.svg)

---

## Features

### NLU (Natural Language Understanding)
- **Character n-gram intent classifier** — vectorizes utterances into n-gram frequency vectors (2–4 chars) and finds the closest match via cosine similarity against training examples (k-NN style). Pure Python, zero external deps.
- **54 intent classes** — covers conversation, time/date, weather, alarms/timers/reminders, system controls, media playback, smart home, communications, navigation, utilities, calculators, news, search, emotional distress.
- **9 languages** — English, Spanish, French, German, Hindi, Japanese, Korean, Portuguese, Arabic. Auto-detected from Unicode ranges or explicitly set. All 54 intents translated across every language.
- **Synonym expansion** — 50+ word groups (e.g., "illuminate" → "turn on") auto-expanded at fit time. Bridges semantic gaps without a thesaurus API.
- **Word overlap bonus** — +0.12 confidence for non-stop-word overlap between user input and intent vocabularies.
- **Entity extraction** — time (7am → `07:00 AM`), duration (5 minutes), dates (today, next monday), numbers, app names, locations, math expressions, contact names, user names.
- **Multi-intent splitting** — splits on "and" / "or" / commas, processes each independently with same-skill carry-over.
- **Dialog state machine** — fragment detection ("in London", "tomorrow") carries over last intent and merges entities.
- **Context-aware slot filling** — multi-turn conversations, context boost, pronoun resolution.

### Cross-Platform Device Control
| Platform | TTS | STT | Notifications | Volume | Brightness | Lock | Clipboard |
|----------|-----|-----|---------------|--------|------------|------|-----------|
| **Termux/Android** | ✅ | ✅ | ✅ | ✅ | ✅ | ❌ | ✅ |
| **Windows** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Linux** | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| **Dummy/text** | print | stdin | ❌ | ❌ | ❌ | ❌ | ❌ |

### Skills
| Skill | Intents | Capabilities |
|-------|---------|-------------|
| **TimeSkill** | time_query, date_query | Current time, date, day of week |
| **ConversationSkill** | greeting, farewell, thanks, affirm, deny, identity_query, emotional_distress, cancel, fun_request | Named greetings, distress response, cancellation |
| **ReminderSkill** | set_alarm, set_timer, set_reminder | Multi-turn scheduling, threading timers, notification alerts |
| **SystemSkill** | open_app, system_lock, volume_up/down/mute, check_battery | Volume 0–100, screen lock, app launcher, flashlight, wifi, screenshot |
| **CalculatorSkill** | calculate | Arithmetic, unit conversions, date math, percentages |
| **WeatherSkill** | weather_query, weather_forecast | Open-Meteo (free, no key) + OpenWeatherMap (optional key). 5-day forecast. |
| **NewsSkill** | news_query | RSS/Atom headline reader (stdlib only) |
| **ExtrasSkill** | 30 media/comm/nav/utility intents | Play music, skip track, send message, make call, get directions, define word, translate, flashlight, screenshot, wifi toggle, timer status/stop, exact volume, brightness up/down |
| **SearchSkill** | define_word, translate_phrase | DuckDuckGo Instant Answer + Free Dictionary API. DDG fallback for low-confidence intents. |
| **HomeAssistantSkill** | lights_on/off, set_thermostat, lock_door, security_check | Home Assistant REST API (configurable via `~/.zeno/home_assistant.json`) |
| **Plugin System** | auto-discovered | Drop `.py` files in `~/.zeno/plugins/` — they load automatically. Plugin registry with `--discover`. |

### Voice Modes
| Mode | Flag | Behavior |
|------|------|----------|
| **Text** | (default) | Type at a prompt |
| **Push-to-talk** | `--voice` | Each interaction: listen → process → speak |
| **Wake word** | `--wake` | Keeps listening until "zeno" or "hey" is detected |
| **Native wake** | `--native-wake` | VAD-based wake word using audio level detection (lower latency) |
| **Continuous** | `--continuous` | Listen → process → speak in an endless loop |

### Voice Training & Calibration
- **Profile-based calibration** — STT timeout, confidence threshold, speech rate (slow/normal/fast) stored per user
- **Adaptive thresholds** — known users get slightly more lenient confidence threshold (0.28 vs 0.30)
- **Language auto-detection** — configured per profile or detected per utterance from Unicode ranges

### Cross-Device LAN Sync
- **UDP broadcast discovery** — Zeno instances find each other on your local network (port 49880)
- **REST API sync** — context, profile, and timers push/pull every 30 seconds
- **Smart merging** — deduplicated turns, last-writer-wins profile, imported timers
- **No cloud** — everything stays on your LAN. Zero external services.
- **Live peer list** — web dashboard shows connected devices with online/offline status

### Web Dashboard
- FastAPI backend with REST + WebSocket
- Dark-themed responsive chat interface
- Voice input via browser Web Speech API
- **Live timer panel** — countdown bars, cancel buttons, 1s refresh
- **Settings panel** — device capabilities + editable profile (name, location, OWM key, units, timezone)
- **LAN peers panel** — real-time peer discovery with status indicators
- Conversation history per session (200 turns)
- Mobile-responsive

---

## Architecture

```
zeno/
├── core/                 # Core engine
│   ├── loop.py           # process_input() — multi-intent split, fragment carry-over, NLU→Skills
│   ├── context.py        # Turn history, slot-filling, pronoun resolution, dialog state
│   ├── runner.py         # Async voice loop, text loop, wake/continuous/native-wake modes
│   ├── profile.py        # User identity, location, OWM key, units, voice calibration
│   ├── plugins.py        # Plugin auto-loader from ~/.zeno/plugins/
│   ├── contact_store.py  # JSON address book, find_contact() for messaging/calling
│   ├── discover.py       # Plugin registry with remote + local fallback index
│   └── sync.py           # UDP discovery, REST sync client, ContextMerger
├── nlu/                  # Natural Language Understanding
│   ├── intent.py         # NGramVectorizer, IntentClassifier, 54 intents, 9 languages
│   ├── entity.py         # Time, duration, date, name, location, expression, contact extraction
│   ├── synonyms.py       # 50+ word groups, expand_text(), expand_training_data()
│   └── pipeline.py       # Preprocess → classify → extract entities
├── skills/               # Skill implementations
│   ├── base.py           # BaseSkill abstract class
│   ├── time_skill.py
│   ├── conversation.py
│   ├── reminders.py      # Threading timers + notification-backed alerts
│   ├── system.py
│   ├── calculator.py
│   ├── weather.py        # Open-Meteo (default) + OpenWeatherMap (optional)
│   ├── news.py           # RSS/Atom headline reader (stdlib only)
│   ├── extras.py         # 30 media/comm/nav/utility intents + contact-aware messaging
│   ├── search.py         # DuckDuckGo + Free Dictionary API, DDG confidence fallback
│   └── home_assistant.py # HA REST API for lights, thermostat, lock, security
├── platform/             # Cross-platform abstraction
│   ├── __init__.py       # Auto-detection, unified API (caps, tts_speak, stt_listen, etc.)
│   └── providers/
│       ├── base.py       # PlatformProvider, PlatformCaps
│       ├── termux.py     # Termux/Android (termux-* binaries)
│       ├── windows.py    # Windows (PowerShell COM, WMI)
│       ├── linux.py      # Linux desktop (espeak, notify-send, pactl, brightnessctl)
│       └── dummy.py      # Text-only fallback
├── audio/                # TTS/STT adapters
│   ├── __init__.py
│   ├── tts.py            # Routes to platform TTS or prints to stdout
│   ├── stt.py            # Routes to platform STT or reads stdin
│   └── wake.py           # Native VAD wake word engine (termux-microphone-record + RMS)
├── memory/               # Local persistence
│   └── store.py          # SQLite key-value store
├── response/             # Response engine
│   └── engine.py         # Phrase selection with template variables (randomized)
└── web/                  # Web dashboard
    ├── server.py         # FastAPI/uvicorn entry point
    ├── app.py            # Application factory + sync startup
    ├── routes.py         # REST endpoints (chat, history, timers, sync, profile, contacts, peers)
    ├── handler.py        # WebSocket endpoint
    └── static/           # index.html, style.css, app.js
```

---

## Intent Classification

Character n-grams (size 2–4) with L2-normalized frequency vectors and cosine similarity:

1. Text is lowercased, stripped, padded with spaces
2. Short texts (<8 chars) repeated 3× for sufficient features
3. Query vector compared against **every individual example vector** (k-NN, not centroids — ~5k vectors across 54 intents × 9 languages)
4. Word overlap bonus (+0.12) for non-stop-word matches between query and intent vocabulary
5. Context boost (+0.03) during active slot-filling
6. Ambiguity margin (0.06) triggers multi-intent mode
7. Confidence threshold (0.30) rejects low-quality matches
8. DDG fallback at marginal confidence (0.15–0.30) for general knowledge queries

**All 9 languages merged** into a single classifier (~5k vectors total). RAM after import + first classification: ~22 MB (down from 169 MB after removing redundant 5× training expansion that provided zero accuracy gain).

---

## Quick Start

### Prerequisites
- Python 3.10+
- Platform tools (optional):
  - **Termux/Android**: `pkg install termux-api` + Termux:API app
  - **Linux**: `espeak-ng`, `notify-send`, `pactl`, `brightnessctl`
  - **Windows**: None needed (built-in COM/WMI)

### Install

```bash
git clone https://github.com/Architect-Brad/Zeno.git
cd Zeno/Code

# Web dashboard (optional)
pip install "zeno[web]"    # or: pip install fastapi uvicorn websockets

# Run
python -m zeno.core.runner          # text mode
python -m zeno.web.server           # web UI at http://127.0.0.1:8080
```

### Run Modes

```bash
python -m zeno.core.runner                        # text mode
python -m zeno.core.runner --voice                # push-to-talk
python -m zeno.core.runner --wake                 # wake word activation
python -m zeno.core.runner --native-wake          # VAD-based wake (lower latency)
python -m zeno.core.runner --discover             # browse plugin registry

python -m zeno.web.server                         # web UI (port 8080)
python -m zeno.web.server --host 0.0.0.0 --port 8080
python -m zeno.web.server --no-sync               # disable LAN sync
```

### Example Commands

```
"hey zeno"                    → greet, learn your name
"hallo" / "bonjour"          → greet in German / French
"こんにちは"                  → greet in Japanese
"what time is it"            → current time
"que horas são"              → time in Portuguese
"what's the weather"         → weather with location
"5 day forecast"             → 5-day forecast (Open-Meteo)
"كيف الطقس"                  → weather in Arabic
"set an alarm for 7am"       → alarm
"set a 5 minute timer and a 10 minute timer"  → two timers at once
"remind me to buy groceries" → reminder
"turn up the volume"         → volume +10
"turn on the lights"         → smart home (Home Assistant)
"lock the door"              → smart lock
"lock the screen"            → lock device
"open calculator"            → launch app
"what's 15 * 3 + 7"         → calculator
"define serendipity"         → dictionary lookup
"what's in the news"         → top headlines
"send a message to mom"      → contact-aware messaging
"tell me a joke"             → fun request
"cancel"                     → cancel current operation
```

---

## Plugin System

Drop Python files in `~/.zeno/plugins/`. Any class extending `BaseSkill` is auto-discovered:

```python
# ~/.zeno/plugins/hello.py
from zeno.skills.base import BaseSkill
from zeno.nlu.entity import Entities
from zeno.core.context import Context

class HelloWorldSkill(BaseSkill):
    intents = ["hello_world"]

    def handle(self, intent: str, entities: Entities, context: Context) -> str:
        return "Hello from a plugin!"
```

Browse and install community plugins:

```bash
python -m zeno.core.runner --discover              # list available
python -m zeno.core.runner --discover spotify_control  # install
```

Set `ZENO_PLUGIN_PATH` environment variable for additional plugin directories.

---

## LAN Sync

Zeno instances discover each other automatically on your local network:

```bash
# On device A
python -m zeno.web.server --port 8080

# On device B (same LAN)
python -m zeno.web.server --port 8081
```

- UDP broadcast on port 49880 every 30 seconds
- Context, profile, and timers sync via REST API
- Live peer list visible in web dashboard (peers button)
- Disable with `--no-sync`

---

## Testing

```bash
pip install pytest
pytest test_context.py test_platform.py -v
```

All 53 tests pass consistently:
```
test_alarm_slot_filling              ✓
test_cancel_mid_slot_fill            ✓
test_first_run_name_capture          ✓
test_semantic_intent_classification  ✓
test_entity_extraction_time          ✓
test_entity_extraction_duration      ✓
test_intent_unknown                  ✓
TestDummyProvider (11 tests)         ✓
TestTermuxProvider (10 tests)        ✓
TestLinuxProvider (10 tests)         ✓
TestWindowsProvider (5 tests)        ✓
TestPlatformDetection (4 tests)      ✓
TestPlatformFunctions (2 tests)      ✓
```

---

## Extending

### Add a new intent
1. Add phrases to `TRAINING_DATA` in `zeno/nlu/intent.py`
2. Create/extend a skill in `zeno/skills/` with `intents` list
3. Add translations in `LANGUAGE_PHRASES` for all 9 languages

### Add a new platform
1. Create `zeno/platform/providers/your_os.py` extending `PlatformProvider`
2. Add detection + load in `zeno/platform/__init__.py`
3. Write tests in `test_platform.py` mocking subprocess

### Add a language
1. Add entries to `LANGUAGE_PHRASES` in `zeno/nlu/intent.py` (all 54 intents)
2. Add Unicode detection range in `detect_language()` if non-Latin script

### Write a plugin
Drop a `.py` file in `~/.zeno/plugins/` with a `BaseSkill` subclass. No registration needed.

---

## Architecture Decisions

**Why character n-grams instead of regex?**
Regex breaks on the first utterance it can't match. N-gram similarity degrades gracefully — the model knows how close "set a timer for 10 minutes" is to "set a timer for 5 minutes."

**Why k-NN (max-similarity) instead of centroids?**
Centroid averaging dilutes signal for short utterances. "Hi" averaged with "good morning" produces a vector that matches nothing well. k-NN preserves per-phrase signal. (Centroids reduce accuracy from 98% to 79%.)

**Why no expansion at fit time?**
The original 5× phrase expansion ("can you X", "i want to X", etc.) inflated 1,945 base phrases to 28,860 vectors costing 147 MB — yet n-gram overlap already handles those phrasings naturally. Removing it saved 87% RAM with zero accuracy loss.

**Why Open-Meteo over wttr.in?**
Free, no API key, unlimited requests, supports 5-day forecast. wttr.in was HTTP-only; Open-Meteo uses HTTPS and provides structured JSON.

**Why provider pattern for platforms?**
New platforms are one file. Auto-detection selects the right provider at import time. Callers use `zeno.platform.tts_speak(text)` without knowing which provider is active. 46 tests mock subprocess to verify every method.

**Why UDP broadcast for LAN sync?**
No configuration needed. Zero infrastructure. Devices find each other. Works on any LAN with broadcast support.

**Why FastAPI + vanilla frontend?**
Zero build step. No npm at runtime. Works on any device with a browser.

---

## Security & Privacy

- **Zero cloud dependencies** — all processing on-device
- **No telemetry, no analytics, no data collection**
- **LAN sync never leaves your network** — no external servers
- **User profile in local SQLite** — name, timezone, location, API keys, calibration
- **Weather via Open-Meteo** — free, no API key, no tracking
- **Search via DuckDuckGo** — no tracking, no account needed
- **News via RSS** — direct feed fetching, no intermediaries
- **Contacts stored as local JSON** — never leaves the device
- **Plugin system runs local Python** — same trust model as any installed package
- **All 9 languages process entirely on-device** — no cloud NLU for any language

---

## License

MIT

---

*Zeno is built by **The Architect** — on-device, open-source, private by design.*
