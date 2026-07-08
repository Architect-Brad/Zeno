# Zeno — On-Device Voice Assistant

**Semantic NLU · Cross-Platform Control · LAN Sync · Zero Cloud Dependencies**

Built by **The Architect**.

```
                    ⚡
                   /█\
                   / \
```

Zeno is a production-ready voice assistant that runs entirely on your device. It understands natural language using character n-gram semantic classification, controls real system functions, manages reminders and timers, provides weather / calculation / news / search capabilities, controls smart home devices, syncs across your LAN, and supports **9 languages** — all with **no cloud APIs, no ML frameworks, and no data leaving your machine**.

**RAM footprint: ~22 MB** (after import + first classification). Codebase: ~900 KB, 6k+ lines across 56 Python files.

![CI](https://github.com/Architect-Brad/Zeno/actions/workflows/ci.yml/badge.svg)

---

## Features

### NLU (Natural Language Understanding)
- **Hybrid n-gram intent classifier** — combines character n-grams (2–4 chars) with word-level unigram+bigram features for deeper semantic discrimination. Uses L2-normalized frequency vectors and cosine similarity (k-NN style). Pure Python, zero external deps.
- **74 merged intent classes** — covers conversation, time/date, weather, alarms/timers/reminders, system controls, media playback, smart home, communications, navigation, utilities, calculators, news, search, emotional distress, knowledge query, battery check, and more.
- **9 languages** — English, Spanish, French, German, Hindi, Japanese, Korean, Portuguese, Arabic. Auto-detected from Unicode ranges or explicitly set. All 74 intents translated across every language.
- **INTENT_GROUPS** — 20 semantic groups (e.g., Weather, Media, System) reduce the ambiguity margin from 0.06 to 0.036 when top-2 candidates share a group, making related-intent classification 40% more stable.
- **Group-coherence fallback** — when a top candidate is Unknown, the fallback checks the next-highest candidate's group first before falling through the intent chain, reducing false Unknowns for related intents.
- **Fixed INTENT_FALLBACK chain** — all 30+ fallback targets point to real intents with training data, eliminating dead-end Unknown responses.
- **Synonym matching** — 100+ word groups (e.g., "illuminate" → "turn on") used during entity extraction and context boosting, but NOT at fit time — pure training data prevents cross-intent contamination.
- **Word overlap bonus** — +0.12 confidence for non-stop-word overlap between user input and intent vocabularies.
- **Entity extraction** — time (7am → `07:00 AM`), duration (5 minutes, "half an hour" → 0.5h), dates (today, next monday), numbers, app names (including multi-word quoted names), locations (filtered to exclude time/duration words), math expressions, contact names, user names, percentage expressions ("15% of 200"), relative time ("in 5 minutes").
- **Multi-intent splitting** — splits on "and" / "or" / commas, processes independently with same-skill carry-over.
- **Dialog state machine** — fragment detection ("in London", "tomorrow") carries over last intent and merges entities.
- **Context-aware slot filling** — multi-turn conversations, context boost, pronoun resolution.

### Knowledge Graph
- **SQLite triple-store** (`zeno/memory/graph.py`) — stores entity-relation-entity triples for persistent knowledge
- Query patterns: "what is X", "who is X", "where is X", "tell me about X"
- Built-in entities: user name, location, contacts, device info, app list
- Extensible — skills and plugins can add triples via `context.graph.add(subj, rel, obj)`
- Co-references resolved against triple store (e.g., "she" → "Alice" if `Alice is_a contact`)

### Personalisation Engine
- **Usage pattern learning** (`zeno/core/personalise.py`) — tracks per-user interaction patterns: most-used skills, time-of-day preferences, common entity values
- Implicit adaptation — no explicit training mode; the engine learns from natural usage
- Used to bias intent ranking for individual users over time

### Proactive Suggestions
- **Context-aware prompts** (`zeno/core/proactive.py`) — after certain intents, Zeno may suggest follow-up actions based on usage history and current context
- Non-intrusive — suggestions are light hints, not commands, and can be declined by saying "no" or "not now"

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
| **KnowledgeSkill** | knowledge_query | Query the local triple-store knowledge graph (who/what/where/tell me about). Built-in entities: user name, location, contacts. |
| **Plugin System** | auto-discovered | Drop `.py` files in `~/.zeno/plugins/` — they load automatically. Plugin registry with `--discover`. |

### Voice Modes
| Mode | Flag | Behavior |
|------|------|----------|
| **Text** | (default) | Type at a prompt |
| **Push-to-talk** | `--voice` | Each interaction: listen → process → speak |
| **Wake word** | `--wake` | Keeps listening until "zeno" or "hey" is detected |
| **Native wake** | `--native-wake` | VAD-based wake word using audio level detection (lower latency) |
| **Continuous** | `--continuous` | Listen → process → speak in an endless loop |

### Local Whisper STT (Optional)
- **whisper.cpp integration** (`zeno/audio/whisper_stt.py`) — offline speech-to-text using whisper.cpp
- **PipeWire audio capture** (`zeno/audio/pipewire.py`) — low-latency microphone capture on Linux desktop
- Drop-in replacement for platform STT; enabled automatically when `whisper_cpp` executable is on `$PATH`
- Supports all whisper.cpp models (tiny/base/small/medium/large)

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
    │   ├── context.py        # Turn history, slot-filling, pronoun resolution, dialog state, graph reference
    │   ├── runner.py         # Async voice loop, text loop, wake/continuous/native-wake modes
    │   ├── term.py           # ANSI terminal colors, styles, width detection
    │   ├── profile.py        # User identity, location, OWM key, units, voice calibration
    │   ├── plugins.py        # Plugin auto-loader from ~/.zeno/plugins/
    │   ├── contact_store.py  # JSON address book, find_contact() for messaging/calling
    │   ├── discover.py       # Plugin registry with remote + local fallback index
    │   ├── personalise.py    # Usage pattern learning, per-user skill bias
    │   ├── proactive.py      # Context-aware follow-up suggestions
    │   └── sync.py           # UDP discovery, REST sync client, ContextMerger
    ├── nlu/                  # Natural Language Understanding
    │   ├── intent.py         # Hybrid n-gram classifier (chars + words), 74 merged intents, 9 languages, INTENT_GROUPS, group-coherence fallback
    │   ├── entity.py         # Time, duration (fractional), date, name, location (filtered), expression, percentage, relative time, contact extraction
    │   ├── synonyms.py       # 100+ word groups, expand_text()
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
    │   ├── home_assistant.py # HA REST API for lights, thermostat, lock, security
    │   └── knowledge.py      # Knowledge graph query skill (who/what/where/tell me about)
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
    │   ├── wake.py           # Native VAD wake word engine (termux-microphone-record + RMS)
    │   ├── whisper_stt.py    # Optional offline STT via whisper.cpp
    │   └── pipewire.py       # PipeWire audio capture for Linux desktop
    ├── memory/               # Local persistence
    │   ├── store.py          # SQLite key-value store
    │   └── graph.py          # SQLite triple-store knowledge graph
├── response/             # Response engine
│   └── engine.py         # Phrase selection with template variables (randomized)
├── tui/                  # Textual terminal UI
│   └── app.py           # TUI app: chat log, input bar, timer panel, status bar
    └── web/                  # Web dashboard
        ├── server.py         # FastAPI/uvicorn entry point
        ├── app.py            # Application factory + sync startup
        ├── routes.py         # REST endpoints (chat, history, timers, sync, profile, contacts, peers)
        ├── handler.py        # WebSocket endpoint
        └── static/           # chat.html, index.html, style.css, app.js
```

---

## Intent Classification

Hybrid n-gram vectorizer combining character n-grams (size 2–4) with word-level unigram and bigram features, L2-normalized frequency vectors, and cosine similarity:

1. Text is lowercased, stripped, padded with spaces
2. Short texts (<8 chars) repeated 3× for sufficient features
3. Character n-grams (2–4) extracted character-by-character; word unigrams and bigrams extracted from tokenized text
4. Feature vectors concatenated: char n-grams (weight 0.6) + word n-grams (weight 0.4) for balanced shallow/deep semantic coverage
5. Query vector compared against **every individual example vector** (k-NN, not centroids — ~7k vectors across 74 intents × 9 languages)
6. Word overlap bonus (+0.12) for non-stop-word matches between query and intent vocabulary
7. Context boost (+0.03) during active slot-filling
8. **Group-coherence check** — if top-2 candidates share an INTENT_GROUP, margin reduces from 0.06 to 0.036 (60% of standard) for 40% more stable related-intent decisions
9. **Group-based fallback** — if top candidate is Unknown, fallback checks same-group intents before falling through the full chain
10. Fixed INTENT_FALLBACK chain — all 30+ targets point to real intents with training data
11. Confidence threshold (0.30) rejects low-quality matches
12. DDG fallback at marginal confidence (0.15–0.30) for general knowledge queries

**All 9 languages merged** into a single classifier (~7k vectors total). RAM after import + first classification: ~22 MB.

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

# Editable install (recommended)
pip install -e .

# Optional extras
pip install "zeno[web]"    # web dashboard (fastapi + uvicorn)
pip install "zeno[tui]"    # terminal UI (textual)

# Run (after pip install -e .)
zeno                                # text mode (readline + colors)
zeno --tui                          # terminal UI mode
zeno web                            # web UI at http://127.0.0.1:8080
```

### Run Modes

```bash
zeno                                         # text mode (readline + ANSI colors)
zeno --voice                                 # push-to-talk
zeno --wake                                  # wake word activation
zeno --native-wake                           # VAD-based wake (lower latency)
zeno --tui                                   # terminal UI (Textual)
zeno --discover                              # browse plugin registry
zeno --help                                  # show all flags
zeno --version                               # show version

zeno web                                     # web UI (port 8080)
zeno web --host 0.0.0.0 --port 8080
zeno web --no-sync                           # disable LAN sync

# Legacy (still works)
python -m zeno.core.runner [options]
python -m zeno.web.server [options]
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

### Slash Commands (Text Mode + TUI)

```
/help                        → show all slash commands and shorthand
/w London                    → weather in London
/f Paris                     → 5-day forecast for Paris
/t                           → current time
/d                           → current date
/a 7am wake up               → alarm at 7:00 AM called "wake up"
/timer 5m pizza              → 5-minute timer called "pizza"
/remind buy groceries        → reminder to buy groceries
/v 75                        → set volume to 75
/v+ /v-                      → volume up / down
/m                           → mute
/b+ /b-                      → brightness up / down
/lock                        → lock screen
/open calculator             → open the calculator app
/lights on /lights off       → smart home lights
/n                           → news headlines
/s what is the capital of France  → DuckDuckGo search
```

### Shorthand Syntax

```
5m pizza                     → 5-minute timer "pizza"
10min                        → 10-minute timer (no label)
7am wake up                  → alarm at 07:00 AM "wake up"
1h30m backup                 → 1.5-hour timer "backup"
```

### CLI Flags

| Flag | Description |
|------|-------------|
| (none) | Text mode with readline history, ANSI colors, tab completion |
| `--voice` / `-v` | Push-to-talk voice mode |
| `--wake` / `-w` | Wake word activation (STT polling) |
| `--native-wake` / `-n` | VAD-based wake word (lower latency) |
| `--continuous` / `-c` | Keep listening after each response |
| `--tui` | Terminal UI (Textual) with chat log + timer panel |
| `--discover [name]` | Browse or install community plugins |
| `--version` | Show version and exit |
| `--help` | Show help message with examples |
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
pytest test_context.py test_platform.py test_nlu.py -v
```

All 109 tests pass consistently:
```
test_context.py         7 tests  ✓  (context, intents, entities)
test_platform.py       46 tests  ✓  (Dummy, Termux, Linux, Windows, detection)
test_nlu.py            56 tests  ✓  (intent coverage, algorithmic, entities, i18n)
Total                 109 tests  ✓
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
