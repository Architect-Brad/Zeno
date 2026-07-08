"""
Zeno Textual TUI — terminal-based chat interface.
"""

import asyncio
import time

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal
from textual.reactive import reactive
from textual.widgets import (
    Header, Footer, Input, RichLog, Static, Button,
)
from textual.screen import Screen
from textual import work

from zeno.core.context import Context
from zeno.core.loop import process_input
from zeno.core.runner import (
    _parse_slash_command, _try_shorthand, _print_slash_help,
    _SLASH_TO_PHRASE,
)
from zeno.skills.reminders import ReminderSkill
from zeno.core.term import strip_ansi


def _get_timers_info() -> list[dict]:
    now = time.time()
    active = []
    for t in ReminderSkill._timer_meta:
        remaining = int(t["seconds"] - (now - t["started"]))
        if remaining > 0:
            active.append({
                "label": t["label"],
                "remaining": remaining,
                "is_alarm": t["is_alarm"],
            })
    return active


class ZenoTUI(App):
    TITLE = "Zeno"
    SUB_TITLE = "On-Device Voice Assistant"
    CSS = """
    Screen {
        background: #0d1117;
    }

    #chat-view {
        height: 1fr;
        border: none;
        padding: 1;
        background: #0d1117;
    }

    #chat-view RichLog {
        height: 100%;
        background: #0d1117;
        color: #c9d1d9;
    }

    #input-row {
        dock: bottom;
        height: 3;
        padding: 0 1;
        background: #161b22;
        border-top: solid #30363d;
    }

    #message-input {
        width: 1fr;
        background: #0d1117;
        color: #c9d1d9;
        border: solid #30363d;
        padding: 0 1;
    }

    #message-input:focus {
        border: solid #58a6ff;
    }

    #send-btn {
        width: 8;
        height: 100%;
        background: #238636;
        color: #ffffff;
        margin-left: 1;
        border: none;
    }

    #send-btn:hover {
        background: #2ea043;
    }

    #timer-panel {
        width: 30;
        height: 100%;
        background: #161b22;
        border-left: solid #30363d;
        padding: 1;
        display: none;
    }

    #timer-panel.visible {
        display: block;
    }

    #timer-panel Static {
        color: #8b949e;
    }

    #timer-panel .timer-entry {
        color: #c9d1d9;
        margin-bottom: 1;
    }

    #timer-panel .timer-label {
        color: #58a6ff;
    }

    #timer-panel .timer-bar {
        color: #238636;
    }

    #status-bar {
        dock: bottom;
        height: 1;
        background: #161b22;
        color: #8b949e;
        padding: 0 1;
    }

    .zeno-msg {
        color: #7ee787;
    }

    .user-msg {
        color: #c9d1d9;
    }

    .error-msg {
        color: #f85149;
    }

    .timestamp {
        color: #484f58;
    }

    WelcomeScreen {
        align: center middle;
    }

    WelcomeScreen #welcome-box {
        width: 60;
        height: auto;
        padding: 2 4;
        background: #161b22;
        border: solid #30363d;
    }

    WelcomeScreen #welcome-title {
        text-style: bold;
        color: #58a6ff;
        text-align: center;
    }

    WelcomeScreen Button {
        width: 20;
        margin-top: 1;
    }
    """

    BINDINGS = [
        ("ctrl+t", "toggle_timers", "Timers"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("ctrl+q", "quit", "Quit"),
        ("escape", "focus_input", "Input"),
    ]

    timer_panel_visible = reactive(False)

    def __init__(self):
        super().__init__()
        self.context = Context()
        self._processing = False

    def compose(self) -> ComposeResult:
        yield Header()
        yield Footer()
        with Container(id="chat-view"):
            yield RichLog(id="chat-log", highlight=True, markup=True, max_lines=1000)
        with Horizontal(id="input-row"):
            yield Input(id="message-input", placeholder="Type a message or /help...")
            yield Button("Send", id="send-btn", variant="success")
        with Container(id="timer-panel"):
            yield Static("[bold]⏱ Timers & Alarms[/bold]", id="timer-title")
            yield Static("", id="timer-list")
        yield Static("", id="status-bar")

    def on_mount(self) -> None:
        self.query_one("#message-input", Input).focus()
        self.set_interval(1, self._update_timers)
        self.set_interval(1, self._update_status)
        log = self.query_one("#chat-log", RichLog)
        log.write("[bold #58a6ff]⚡ Zeno v1.0.0[/bold #58a6ff]")
        log.write("[dim]  ┌─┐        ┌─┐[/dim]")
        log.write("[dim]  └─┤ Zeno  ├─┘[/dim]")
        log.write("[dim]     └─┘[/dim]")
        log.write("")
        log.write("[italic dim]Your on-device voice assistant[/italic dim]")
        log.write("[dim]Type /help for commands · Ctrl+T: Timers · Ctrl+Q: Quit[/dim]")
        log.write("")

    def on_input_submitted(self, event: Input.Submitted) -> None:
        self._handle_input(event.value)
        event.input.clear()

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            inp = self.query_one("#message-input", Input)
            if inp.value.strip():
                self._handle_input(inp.value)
                inp.clear()

    def action_toggle_timers(self) -> None:
        panel = self.query_one("#timer-panel")
        self.timer_panel_visible = not self.timer_panel_visible
        panel.set_class(self.timer_panel_visible, "visible")

    def action_clear_chat(self) -> None:
        self.query_one("#chat-log", RichLog).clear()
        self.query_one("#chat-log", RichLog).write("[dim]Chat cleared[/dim]")

    def action_focus_input(self) -> None:
        self.query_one("#message-input", Input).focus()

    def watch_timer_panel_visible(self, visible: bool) -> None:
        btn = self.query_one("#send-btn", Button)
        if visible:
            btn.label = "Hide Timers"
        else:
            btn.label = "Send"

    @work(exclusive=True, thread=True)
    async def _process_async(self, text: str) -> str:
        response = process_input(text, self.context)
        return response

    def _write_zeno(self, text: str) -> None:
        self.query_one("#chat-log", RichLog).write(
            f"[bold #58a6ff]{time.strftime('%H:%M')}[/bold #58a6ff] [zeno-msg]◈ {text}[/zeno-msg]"
        )

    def _write_help(self) -> None:
        log = self.query_one("#chat-log", RichLog)
        log.write("")
        log.write("[bold #58a6ff]Slash Commands:[/bold #58a6ff]")
        log.write("  [dim]/w [city][/dim]    Weather    [dim]/t[/dim]    Time    [dim]/d[/dim]    Date")
        log.write("  [dim]/a <time>[/dim]    Alarm      [dim]/timer[/dim]  Timer")
        log.write("  [dim]/v <0-100>[/dim]   Volume     [dim]/m[/dim]    Mute")
        log.write("  [dim]/b+ /b-[/dim]      Brightness [dim]/lock[/dim]  Lock")
        log.write("  [dim]/lights[/dim]      Lights     [dim]/open[/dim]  App")
        log.write("  [dim]/n[/dim]           News       [dim]/s[/dim]     Search")
        log.write("")
        log.write("[bold #58a6ff]Shorthand:[/bold #58a6ff]")
        log.write("  [dim]5m pizza[/dim]   5-min timer 'pizza'")
        log.write("  [dim]7am wake[/dim]   Alarm at 7:00 AM 'wake'")
        log.write("")

    def _handle_input(self, raw: str) -> None:
        if not raw.strip():
            return
        if self._processing:
            return

        log = self.query_one("#chat-log", RichLog)
        log.write(f"[bold #58a6ff]{time.strftime('%H:%M')}[/bold #58a6ff] [user-msg]▸ {raw}[/user-msg]")

        text = raw.strip()

        if text.lower() in ("exit", "quit", "q", "/exit"):
            log.write("[dim]Goodbye![/dim]")
            self.exit()
            return

        if text == "/help":
            self._write_help()
            return

        intent_or_none, remainder, cmd = _parse_slash_command(text)
        if intent_or_none is not None:
            if intent_or_none == "cancel":
                from zeno.response.engine import pick
                response = pick("cancel")
                self.context.clear_awaiting()
                self._write_zeno(response)
                return
            phrase = _SLASH_TO_PHRASE.get(cmd, intent_or_none.replace("_", " "))
            if remainder:
                full = f"{phrase} {remainder}"
            else:
                full = phrase
            self._process_and_show(full)
            return

        if text.startswith("/"):
            self._write_zeno("Unknown slash command. Type /help for available commands.")
            return

        if not self.context.awaiting():
            shorthand_intent, normalized, _ = _try_shorthand(text)
            if shorthand_intent and normalized:
                self._process_and_show(normalized)
                return

        self._process_and_show(text)

    @work(exclusive=False, thread=False)
    async def _process_and_show(self, text: str) -> None:
        self._processing = True
        log = self.query_one("#chat-log", RichLog)
        log.write("[dim]...[/dim]")

        response = await asyncio.get_event_loop().run_in_executor(
            None, process_input, text, self.context
        )

        log.write(f"[bold #58a6ff]{time.strftime('%H:%M')}[/bold #58a6ff] [zeno-msg]◈ {response}[/zeno-msg]")
        self._processing = False
        self.query_one("#message-input", Input).focus()

    def _update_timers(self) -> None:
        timers = _get_timers_info()
        timer_list = self.query_one("#timer-list", Static)
        if not timers:
            timer_list.update("[dim]No active timers[/dim]")
            return

        lines = []
        for t in timers:
            mins, secs = divmod(t["remaining"], 60)
            icon = "⏰" if t["is_alarm"] else "⏱"
            bar_len = min(20, max(1, t["remaining"] // 10))
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(
                f"[#58a6ff]{icon} {t['label']}[/#58a6ff]\n"
                f"[#238636]{bar}[/#238636] [dim]{mins:02d}:{secs:02d}[/dim]"
            )
        timer_list.update("\n\n".join(lines))

    def _update_status(self) -> None:
        timers = _get_timers_info()
        timer_count = len(timers)
        bar = self.query_one("#status-bar", Static)
        bar.update(
            f"  [dim]⚡ Text mode  │  ⏱ {timer_count} timer{'s' if timer_count != 1 else ''}"
            f"  │  /help  │  Ctrl+T: Timers  │  Ctrl+Q: Quit[/dim]"
        )
