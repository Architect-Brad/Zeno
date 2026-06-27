# Zeno — On-Device Voice Assistant

**Semantic NLU · Cross-Platform Control · LAN Sync · Zero Cloud Dependencies**

Built by **The Architect**.

```
                    ⚡
                   /█\
                   / \
```

Zeno is a production-ready voice assistant that runs entirely on your device. It understands natural language using character n-gram semantic classification, controls real system functions, manages reminders and timers, provides weather, calculation, and news skills, syncs across your devices over LAN, and supports 5 languages — all with **no cloud APIs, no ML frameworks, and no data leaving your machine**.

![CI](https://github.com/Architect-Brad/Zeno/actions/workflows/ci.yml/badge.svg)

---

## Features

### NLU (Natural Language Understanding)
- **Character n-gram intent classifier** — vectorizes utterances into n-gram frequency vectors (2–4 chars) and finds the closest match via cosine similarity against training examples (k-NN style, not centroid averaging). Pure Python, zero external deps.
- **24 intent classes** — greeting, farewell, time_query, date_query, weather_query, set_alarm, set_timer, set_reminder, open_app, system_lock, volume_up/down/mute, calculate, news_query, identity_query, thanks, affirm, deny, emotional_distress, cancel, fun_request, introduce, unknown.
- **Multi-language** — English, Spanish, French, German, Hindi auto-detected or explicitly set. Translations for 13 intents across all 4 additional languages.
- **Entity extraction** — time (7am → `07:00 AM`), duration (5 minutes), dates (today, next monday), numbers, app names, locations, math expressions, reminder targets, user names.
- **Multi-intent detection** — when two intents have similar confidence, both are surfaced.
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
| **SystemSkill** | open_app, system_lock, volume_up/down/mute | Volume 0–100, screen lock, app launcher |
| **CalculatorSkill** | calculate | Arithmetic, unit conversions, date math, percentages |
| **WeatherSkill** | weather_query | Location-aware weather via wttr.in (no API key) |
| **NewsSkill** | news_query | RSS headline reader (stdlib only, no dependencies) |
| **Plugin System** | auto-discovered | Drop `.py` files in `~/.zeno/plugins/` — they load automatically |

### Voice Modes
| Mode | Flag | Behavior |
|------|------|----------|
| **Text** | (default) | Type at a prompt |
| **Push-to-talk** | `--voice` | Each interaction: listen → process → speak |
| **Wake word** | `--wake` | Keeps listening until "zeno" or "hey" is detected |
| **Continuous** | `--continuous` | Listen → process → speak in an endless loop |

### Voice Training & Calibration
- **Profile-based calibration** — STT timeout, confidence threshold, and speech rate (slow/normal/fast) are stored per user
- **Adaptive thresholds** — known users get a slightly more lenient confidence threshold (0.28 vs 0.30)
- **Language auto-detection** — configured per profile or detected per utterance from Unicode ranges

### Cross-Device LAN Sync
- **UDP broadcast discovery** — Zeno instances find each other on your local network
- **REST API sync** — context, profile, and timers push/pull every 30 seconds
- **Smart merging** — deduplicated turns, last-writer-wins profile, imported timers
- **No cloud** — everything stays on your LAN. Uses zero external services.
- **Live peer list** — web dashboard shows connected devices

### Web Dashboard
- FastAPI backend with REST + WebSocket
- Dark-themed responsive chat interface
- Voice input via browser Web Speech API
- **Live timer panel** — countdown bars, cancel buttons, live refresh
- Settings panel showing platform capabilities
- Conversation history per session
- Peer discovery view
- Mobile-responsive

---

## Architecture

```
zeno/
├── core/               # Core engine
│   ├── loop.py         # process_input() — NLU → Skills → Response orchestration
│   ├── context.py      # Turn history, slot-filling, pronoun resolution
│   ├── runner.py       # Async voice loop, text loop, wake/continuous modes
│   ├── profile.py      # User identity, voice calibration, language preference
│   ├── plugins.py      # Plugin auto-loader from ~/.zeno/plugins/
│   └── sync.py         # LAN discovery, sync client, context merger
├── nlu/                # Natural Language Understanding
│   ├── intent.py       # NGramVectorizer, IntentClassifier, 24 intents, 5 languages
│   ├── entity.py       # Time, duration, date, name, expression extraction
│   └── pipeline.py     # Wake-word stripping → classify → extract
├── skills/             # Skill implementations
│   ├── base.py         # BaseSkill abstract class + phrase engine
│   ├── time_skill.py
│   ├── conversation.py
│   ├── reminders.py    # Threading timers + notification-backed alerts
│   ├── system.py
│   ├── calculator.py
│   ├── weather.py
│   └── news.py         # RSS headline reader (stdlib)
├── platform/           # Cross-platform abstraction
│   ├── __init__.py     # Auto-detection, unified API
│   └── providers/
│       ├── base.py     # PlatformProvider, PlatformCaps
│       ├── termux.py   # Termux/Android
│       ├── windows.py  # Windows (COM, WMI)
│       ├── linux.py    # Linux desktop
│       └── dummy.py    # Text-only fallback
├── audio/              # TTS/STT adapters
│   ├── tts.py          # Routes to platform TTS or prints
│   └── stt.py          # Routes to platform STT or reads stdin
├── memory/             # Local persistence
│   └── store.py        # SQLite key-value store
├── response/           # Response engine
│   └── engine.py       # Phrase selection with template variables
└── web/                # Web dashboard
    ├── server.py       # FastAPI/uvicorn entry point
    ├── app.py          # Application factory + sync startup
    ├── routes.py       # REST endpoints (chat, history, timers, sync, health)
    ├── handler.py      # WebSocket endpoint
    └── static/         # index.html, style.css, app.js
```

---

## Intent Classification

Character n-grams (size 2–4) with L2-normalized frequency vectors and cosine similarity:

1. Text is lowercased, stripped, padded with spaces
2. Short texts (<8 chars) repeated 3× for sufficient features
3. Each training phrase expanded to 5 variants (`can you X`, `i want to X`, etc.)
4. Query vector compared against **every individual example vector** (k-NN, not centroids)
5. Ambiguity margin (0.06) triggers multi-intent mode
6. Context boost (+0.03) during active slot-filling
7. Confidence threshold (0.30) rejects low-quality matches

**Multi-language**: In auto mode, all 5 languages are merged into one classifier. The merged dataset has 4× the training phrases but runs with the same O(n) lookup. All 20 test phrases across Spanish, French, German, Hindi, and English classify correctly at confidence 0.78–1.00.

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
python -m zeno.core.runner                    # text mode
python -m zeno.core.runner --voice            # push-to-talk
python -m zeno.core.runner --wake             # wake word activation
python -m zeno.core.runner --voice --wake     # both flags

python -m zeno.web.server                     # web UI (port 8080)
python -m zeno.web.server --host 0.0.0.0 --port 8080
python -m zeno.web.server --no-sync           # disable LAN sync
```

### Example Commands

```
"hey zeno"                    → greet, learn your name
"hallo" / "bonjour"          → greet in German / French
"what time is it"            → current time
"qué hora es"                → time in Spanish
"what's the weather"         → weather with location
"set an alarm for 7am"       → alarm
"set a timer for 5 minutes"  → timer
"remind me to buy groceries" → reminder
"turn up the volume"         → volume +10
"lock the screen"            → lock device
"open calculator"            → launch app
"what's 15 * 3 + 7"         → calculator
"what's in the news"         → top headlines
"tell me a joke"             → fun request
"who are you"                → identity
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
- Live peer list visible in web dashboard (⏱️ → peers)
- Disable with `--no-sync`

---

## Testing

```bash
pip install pytest
pytest test_context.py -v
```

All 7 tests pass consistently:
```
test_alarm_slot_filling          ✓
test_cancel_mid_slot_fill        ✓
test_first_run_name_capture      ✓
test_semantic_intent_classification  ✓
test_entity_extraction_time      ✓
test_entity_extraction_duration  ✓
test_intent_unknown              ✓
```

---

## Extending

### Add a new intent
1. Add phrases to `TRAINING_DATA` in `zeno/nlu/intent.py`
2. Create/extend a skill in `zeno/skills/` with `intents` list
3. Add translations in `LANGUAGE_PHRASES` for multi-language support

### Add a new platform
1. Create `zeno/platform/providers/your_os.py` extending `PlatformProvider`
2. Add detection in `zeno/platform/__init__.py`

### Add a language
1. Add entries to `LANGUAGE_PHRASES` in `zeno/nlu/intent.py`
2. Add Unicode detection range in `detect_language()` if non-Latin script

### Write a plugin
Drop a `.py` file in `~/.zeno/plugins/` with a `BaseSkill` subclass. No registration needed.

---

## Architecture Decisions

**Why character n-grams instead of regex?**
Regex breaks on the first utterance it can't match. N-gram similarity degrades gracefully — the model knows how close "set a timer for 10 minutes" is to "set a timer for 5 minutes."

**Why max-similarity (k-NN) instead of centroids?**
Centroid averaging dilutes signal for short utterances. "Hi" averaged with "good morning" produces a vector that matches nothing well. k-NN preserves per-phrase signal.

**Why provider pattern for platforms?**
New platforms are one file. Auto-detection selects the right provider at import time. Callers use `zeno.platform.tts_speak(text)` without knowing which provider is active.

**Why UDP broadcast for LAN sync?**
No configuration needed. Zero infrastructure. Devices find each other. Works on any LAN with broadcast support.

**Why FastAPI + vanilla frontend?**
Zero build step. No npm at runtime. Works on any device with a browser.

---

## Security & Privacy

- **Zero cloud dependencies** — all processing on-device
- **No telemetry, no analytics, no data collection**
- **LAN sync never leaves your network** — no external servers
- **User profile in local SQLite** — name, timezone, calibration, language
- **Weather via wttr.in** — no API key needed
- **News via RSS** — direct feed fetching, no intermediaries
- **Plugin system runs local Python** — same trust model as any installed package

---

## License

MIT

---

*Zeno is built by **The Architect** — on-device, open-source, private by design.*
