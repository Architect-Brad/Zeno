"""Zeno CLI — top-level entry point."""
import sys


_GLOBAL_HELP = """\
Zeno — On-Device Voice Assistant
Semantic NLU · Cross-Platform Control · LAN Sync · Zero Cloud Dependencies

Usage:
  zeno [options]           Text/voice/TUI mode (default: text)
  zeno web [options]       Web dashboard

Options (text/voice/TUI):
  --voice, -v              Push-to-talk voice mode
  --wake, -w               Wake word activation
  --continuous, -c         Keep listening after each response
  --native-wake, -n        VAD-based wake word (lower latency)
  --tui                    Terminal UI (Textual framework)
  --daemon                 Start background daemon (web server on port 8080)
  --stop                   Stop the running daemon
  --status                 Show daemon status
  --discover [name]        Browse or install community plugins
  --doctor                 Run diagnostics and report issues
  --version                Show version and exit

Web options:
  --host HOST              Bind address (default: 127.0.0.1)
  --port PORT              Port (default: 8080)
  --no-sync                Disable LAN sync

In text mode, type /help for slash commands and shorthand.

Examples:
  zeno                     Text mode with readline and colors
  zeno --tui               Terminal UI
  zeno --voice             Push-to-talk voice
  zeno --wake              Wake word activation
  zeno web                 Web dashboard at http://127.0.0.1:8080
  zeno web --port 9090     Web dashboard on custom port
  zeno --daemon            Start as background service
"""


def main():
    if len(sys.argv) > 1 and sys.argv[1] == "web":
        from zeno.web.server import main as web_main
        sys.argv.pop(1)
        web_main()
    elif len(sys.argv) == 2 and sys.argv[1] in ("-h", "--help", "help"):
        print(_GLOBAL_HELP)
    else:
        from zeno.core.runner import main as runner_main
        runner_main()


if __name__ == "__main__":
    main()
