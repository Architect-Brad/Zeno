# Zeno — On-Device Voice Assistant

**Semantic NLU · Cross-Platform Control · Zero Cloud Dependencies**

Built by **The Architect**.

```
                    ⚡
                   /█\
                   / \
```

Zeno is a production-ready voice assistant that runs entirely on your device. It understands natural language using character n-gram semantic classification, controls real system functions (volume, brightness, lock screen, apps, clipboard), manages reminders and timers, and provides weather and calculation skills — all with **no cloud APIs, no ML frameworks, and no data leaving your machine**.

---

## Features

### NLU (Natural Language Understanding)
- **Character n-gram intent classifier** — vectorizes utterances into n-gram frequency vectors (2–4 chars) and finds the closest match via cosine similarity against training examples (k-NN style, not centroid averaging). Pure Python, zero external deps.
- **24 intent classes** — greeting, farewell, time_query, date_query, weather_query, set_alarm, set_timer, set_reminder, open_app, system_lock, volume_up/down/mute, calculate, news_query, identity_query, thanks, affirm, deny, emotional_distress, cancel, fun_request, introduce, unknown.
- **Entity extraction** — time (7am → `07:00 AM`, 6:30 am, 14:00, noon), duration (5 minutes, 30 seconds), dates (today, tomorrow, next monday), numbers, app names, locations, mathematical expressions, reminder targets, user names.
- **Multi-intent detection** — when two intents have similar confidence, both are surfaced (primary + secondary intent).
- **Context-aware slot filling** — multi-turn conversations like "set an alarm" → "what time?" → "7am" → alarm set. Context boost for slot-filling turns (+0.03 confidence). Pronoun resolution across turns ("it", "that").

### Cross-Platform Device Control
- **Termux/Android**: TTS (`termux-tts-speak`), STT (`termux-tts-listen`), notifications, volume, brightness, toast, vibrate, clipboard
- **Windows**: TTS (System.Speech), toast notifications, volume (SAPI COM), brightness (WMI), lock screen (rundll32.exe), app launch (start), clipboard
- **Linux**: TTS (espeak-ng/spd-say/festival), notifications (notify-send/zenity), volume (pactl/amixer), brightness (brightnessctl/xbacklight), lock screen (xdg-screensaver/loginctl), app launch (xdg-open), clipboard (xclip/wl-copy)
- **Dummy/text fallback**: prints to stdout when no platform provider matches

### Skills
| Skill | Intents | Capabilities |
|-------|---------|-------------|
| **TimeSkill** | time_query, date_query | Current time, date, day of week |
| **ConversationSkill** | greeting, farewell, thanks, affirm, deny, identity_query, emotional_distress, cancel, fun_request | Named greetings, distress response, cancellation, identity description |
| **ReminderSkill** | set_alarm, set_timer, set_reminder | Multi-turn scheduling, notification-backend alerts, threading timers |
| **SystemSkill** | open_app, system_lock, volume_up/down/mute | Volume control (0–100), screen lock, app launcher |
| **CalculatorSkill** | calculate | Arithmetic, unit conversions, date math, percentage |
| **WeatherSkill** | weather_query, date_query | Location-aware weather via API (pluggable), current conditions |

### Web Dashboard
- FastAPI backend with REST API and WebSocket endpoint
- Dark-themed responsive chat interface
- Voice input via browser Web Speech API (Chrome, Edge, Safari)
- Settings panel showing platform capabilities
- Conversation history per session (cookie-based)
- Mobile-responsive layout

### Architecture
```
zeno/
├── core/           # Interaction loop, context manager, profile, runner
│   ├── loop.py     # process_input() — orchestrates NLU → Skills → Response
│   ├── context.py  # Turn history, slot-filling state, pronoun resolution
│   ├── runner.py   # Async voice loop + text loop entry points
│   └── profile.py  # User name/timezone persistence
├── nlu/            # Natural Language Understanding pipeline
│   ├── intent.py   # NGramVectorizer, IntentClassifier, 24 intent training data
│   ├── entity.py   # Entity extraction (time, date, duration, names, expressions)
│   └── pipeline.py # process() — wake-word stripping → classify → extract entities
├── skills/         # Skill implementations
│   ├── base.py     # BaseSkill abstract class with response phrase engine
│   ├── time_skill.py
│   ├── conversation.py
│   ├── reminders.py
│   ├── system.py
│   ├── calculator.py
│   └── weather.py
├── platform/       # Cross-platform abstraction
│   ├── __init__.py # Auto-detection, unified API (tts_speak, caps, show_notification, etc.)
│   └── providers/
│       ├── base.py      # PlatformProvider, PlatformCaps
│       ├── termux.py    # Termux/Android provider
│       ├── windows.py   # Windows provider (COM, WMI)
│       ├── linux.py     # Linux desktop provider
│       └── dummy.py     # Text-only fallback
├── audio/          # TTS/STT adapters
│   ├── tts.py      # speak() — routes to platform TTS or prints
│   └── stt.py      # listen() — routes to platform STT or reads stdin
├── memory/         # Local persistence
│   └── store.py    # Key-value store (SQLite-backed)
├── response/       # Response engine
│   └── engine.py   # Phrase selection with template variables
└── web/            # Web dashboard
    ├── server.py   # FastAPI/uvicorn entry point
    ├── app.py      # Application factory
    ├── routes.py   # REST endpoints (/api/chat, /api/history, /api/health)
    ├── handler.py  # WebSocket endpoint
    └── static/     # Frontend assets (index.html, style.css, app.js)
```

### Intent Classification Details

Zeno's classifier uses **character n-grams** (size 2–4) with **L2-normalized frequency vectors** and **cosine similarity**:

1. Text is lowercased, stripped, and padded with spaces
2. Short texts (<8 chars) are repeated 3× to generate sufficient n-gram features
3. Each training phrase is expanded to 5 variants (`can you X`, `i want to X`, `please X`, `i need to X`, `i'd like to X`) for robust coverage
4. Query vector is compared against **every individual example vector** (not centroids) — max similarity wins
5. Ambiguity margin (default 0.06) triggers multi-intent mode when two intents score closely
6. Context boost (+0.03) during active slot-filling
7. Confidence threshold (default 0.30) rejects low-quality matches as "unknown"

This approach handles short utterances (hi, bye, yes, no) much better than centroid averaging, which dilutes signal for single-word intents.

---

## Quick Start

### Prerequisites
- Python 3.10+
- Platform-specific tools (optional — falls back to text mode):
  - **Termux/Android**: Install Termux:API app + `pkg install termux-api`
  - **Linux**: `espeak-ng`, `notify-send` (libnotify), `pactl` (pulseaudio-utils), `brightnessctl`
  - **Windows**: No additional tools needed (uses built-in COM/WMI)

### Installation

```bash
git clone https://github.com/your-username/zeno.git
cd zeno/Code

# Core (no dependencies beyond stdlib)
python -m zeno.core.runner

# Web dashboard (optional)
pip install fastapi uvicorn websockets
python -m zeno.web.server
```

### Run Modes

```bash
# Text mode — type commands interactively
python -m zeno.core.runner

# Voice mode — speak commands (requires platform STT)
python -m zeno.core.runner --voice

# Web dashboard — open http://127.0.0.1:8080 in browser
python -m zeno.web.server

# Web dashboard with network access
python -m zeno.web.server --host 0.0.0.0 --port 8080
```

### Example Commands
```
"hey zeno"                      → greet, learn your name
"what time is it"               → current time
"what's the weather"            → weather (with location)
"set an alarm for 7am"          → alarm
"set a timer for 5 minutes"     → timer
"remind me to buy groceries"    → reminder
"turn up the volume"            → volume +10
"lock the screen"               → lock device
"open calculator"               → launch app
"what's 15 * 3 + 7"            → calculator
"tell me a joke"                → fun request
"who are you"                   → identity
"cancel"                        → cancel current operation
```

---

## Platform Compatibility

| Capability     | Termux | Windows | Linux | Fallback |
|----------------|--------|---------|-------|---------|
| TTS            | ✅     | ✅      | ✅    | text    |
| STT            | ✅     | ✅      | ✅    | stdin   |
| Notifications  | ✅     | ✅      | ✅    | ❌      |
| Volume Control | ✅     | ✅      | ✅    | ❌      |
| Brightness     | ✅     | ✅      | ✅    | ❌      |
| Lock Screen    | ❌     | ✅      | ✅    | ❌      |
| Open App       | ✅     | ✅      | ✅    | ❌      |
| Toast          | ✅     | ❌      | ❌    | ❌      |
| Vibrate        | ✅     | ❌      | ❌    | ❌      |
| Clipboard      | ✅     | ✅      | ✅    | ❌      |

---

## Testing

```bash
# Install pytest (if not present)
pip install pytest

# Run all tests
pytest test_context.py -v

# Tests cover:
# - Intent classification (all 24 intents)
# - Entity extraction (time, duration, names)
# - Slot-filling (alarm, timer, reminder)
# - Cancel mid-slot-fill
# - Name capture on first run
# - Unknown intent rejection
```

All 7 tests pass:
```
test_alarm_slot_filling ... OK
test_cancel_mid_slot_fill ... OK
test_first_run_name_capture ... OK
test_semantic_intent_classification ... OK
test_entity_extraction_time ... OK
test_entity_extraction_duration ... OK
test_intent_unknown ... OK
```

---

## Architecture Decisions

**Why character n-grams instead of regex?**
Regex breaks on the first utterance it can't match. N-gram similarity degrades gracefully — the model knows how close "set a timer for 5 minutes" is to "set a timer for 10 minutes." This gives us semantic understanding without ML dependencies.

**Why max-similarity (k-NN) instead of centroids?**
Centroid averaging dilutes signal for short utterances. "Hi" averaged with "good morning" and "what's up" produces a vector that matches nothing well. k-NN against individual examples preserves per-phrase signal and achieves much higher accuracy on short inputs.

**Why provider pattern for platforms?**
New platforms are added by writing one file. The auto-detection in `zeno/platform/__init__.py` selects the right provider at import time. Consumers call `zeno.platform.tts_speak(text)` without knowing which provider is active.

**Why FastAPI + static frontend instead of a SPA framework?**
Zero build step. No npm required at runtime. The frontend is vanilla HTML/JS/CSS served by FastAPI with htmx-style interactivity via REST + WebSocket. Works on any device with a browser.

---

## Extending

### Adding a New Intent
1. Add training phrases to `TRAINING_DATA` in `zeno/nlu/intent.py`
2. Create or extend a skill in `zeno/skills/` with the intent name in `intents`
3. Add routing in `zeno/core/loop.py` `_SKILLS` list or `_INTENT_MAP`

### Adding a New Platform
1. Create `zeno/platform/providers/{name}.py` extending `PlatformProvider`
2. Implement desired methods
3. Add detection in `zeno/platform/__init__.py` `detect_platform()` and `_load_provider()`

### Adding a New Response Phrase
Add entries to `_PHRASES` in `zeno/response/engine.py`, then use `pick("your_key")` from any skill.

---

## Security & Privacy

- **Zero cloud dependencies** — all processing happens on-device
- **No data collection** — no telemetry, analytics, or external calls (except optional weather API)
- **User profile** stored in local SQLite — name, timezone, preferences
- **All permissions** are platform-native (Termux:API, system COM/WMI, etc.)

---

## License

MIT

---

*Zeno is built by **The Architect** — on-device, open-source, private by design.*
