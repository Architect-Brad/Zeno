"""
Zeno Daemon Manager — start/stop/status for the background web service.
Manages PID file, log file, and lifecycle of the uvicorn server process.
"""

import os
import re
import signal
import subprocess
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

ZENO_DIR = Path.home() / ".zeno"
PID_FILE = ZENO_DIR / "daemon.pid"
LOG_FILE = ZENO_DIR / "daemon.log"


def is_running() -> bool:
    if not PID_FILE.exists():
        return False
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        return True
    except (ValueError, OSError, ProcessLookupError):
        PID_FILE.unlink(missing_ok=True)
        return False


def _pid() -> int | None:
    if not PID_FILE.exists():
        return None
    try:
        return int(PID_FILE.read_text().strip())
    except (ValueError, OSError):
        return None


def start(port: int = 8080, sync: bool = True) -> tuple[bool, str]:
    running_pid = _pid()
    if running_pid is not None:
        try:
            os.kill(running_pid, 0)
            return False, f"Daemon already running (PID {running_pid})"
        except ProcessLookupError:
            PID_FILE.unlink(missing_ok=True)

    ZENO_DIR.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "zeno.web.server", "--port", str(port)]
    if not sync:
        cmd.append("--no-sync")

    log_f = open(LOG_FILE, "a")
    log_f.write(f"\n--- Starting daemon at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
    log_f.flush()

    proc = subprocess.Popen(
        cmd,
        stdout=log_f,
        stderr=subprocess.STDOUT,
        stdin=subprocess.DEVNULL,
        start_new_session=True,
    )

    PID_FILE.write_text(str(proc.pid))

    for _ in range(10):
        time.sleep(0.3)
        if proc.poll() is not None:
            PID_FILE.unlink(missing_ok=True)
            return False, "Daemon failed to start (check ~/.zeno/daemon.log)"
        if _check_health(port):
            return True, f"Daemon started (PID {proc.pid}, port {port})"

    return True, f"Daemon started (PID {proc.pid}, port {port})"


def stop() -> tuple[bool, str]:
    pid = _pid()
    if pid is None:
        return False, "Daemon is not running"

    try:
        os.kill(pid, signal.SIGTERM)
        for _ in range(15):
            time.sleep(0.2)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                PID_FILE.unlink(missing_ok=True)
                return True, f"Daemon (PID {pid}) stopped"
        os.kill(pid, signal.SIGKILL)
        PID_FILE.unlink(missing_ok=True)
        return True, f"Daemon (PID {pid}) force killed"
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        return True, "Daemon was not running"
    except PermissionError:
        return False, f"No permission to stop PID {pid}"
    except OSError as e:
        PID_FILE.unlink(missing_ok=True)
        return False, f"Error stopping daemon: {e}"


def restart(port: int = 8080, sync: bool = True) -> tuple[bool, str]:
    stop()
    time.sleep(0.5)
    return start(port, sync)


def status() -> dict:
    running = is_running()
    result: dict = {"running": running}
    if running:
        pid = _pid()
        result["pid"] = pid
        result["port"] = _detect_port(pid)
        result["healthy"] = _check_alive(result["port"] or 8080)
    return result


def _detect_port(pid: int | None = None) -> int | None:
    if LOG_FILE.exists():
        try:
            for line in open(LOG_FILE).readlines():
                m = re.search(r"Uvicorn running on http://127\.0\.0\.1:(\d+)", line)
                if m:
                    return int(m.group(1))
        except Exception:
            pass
    return None


def _check_alive(port: int) -> bool:
    """Check if the server is responding (any status code is fine)."""
    try:
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/health", timeout=2
        )
        return True
    except urllib.error.HTTPError:
        return True  # Server responded with an error — it's still alive
    except (urllib.error.URLError, OSError):
        return False


def proxy_request(text: str, port: int | None = None) -> str | None:
    if port is None:
        port = _detect_port(None) or 8080
    if not _check_alive(port):
        return None
    import json
    data = json.dumps({"text": text}).encode()
    try:
        resp = urllib.request.urlopen(
            f"http://127.0.0.1:{port}/api/chat",
            data=data,
            timeout=10,
        )
        result = json.loads(resp.read())
        return result.get("response", "")
    except (urllib.error.URLError, OSError, json.JSONDecodeError):
        return None
