"""
Zeno Runner — async voice interaction loop.
Orchestrates: listen → process → speak.
Gracefully handles Termux API absence (falls back to text I/O).
"""

import asyncio
import sys
from zeno.core.context import Context
from zeno.core.loop import process_input
from zeno.audio.stt import listen
from zeno.audio.tts import speak
from zeno.memory.store import get_store

_WAKE_WORDS = ("zeno", "hey")


async def listen_async(timeout: int = 15) -> str | None:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, listen, timeout)


async def speak_async(text: str) -> bool:
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, speak, text)


async def listen_for_wake(timeout: int = 15) -> str | None:
    """
    Keep listening until the wake word is detected.
    Returns the full utterance with wake word stripped.
    Returns None if listening fails or is interrupted.
    """
    while True:
        text = await listen_async(timeout=timeout)
        if not text:
            continue

        lower = text.lower()
        if any(ww in lower for ww in _WAKE_WORDS):
            return text

        print(".", end="", flush=True)


async def run_voice_interaction(context: Context, require_wake: bool = False) -> str | None:
    if require_wake:
        text = await listen_for_wake()
    else:
        text = await listen_async()

    if not text:
        return None

    lower = text.lower()
    if not any(ww in lower for ww in _WAKE_WORDS):
        text = f"hey zeno {text}"

    response = process_input(text, context)
    await speak_async(response)
    return response


async def run_voice_loop(require_wake: bool = False):
    context = Context()
    mode = "wake word" if require_wake else "push-to-talk"
    print(f"[Zeno] Voice assistant ready. Mode: {mode}. Press Ctrl+C to exit.")
    sys.stdout.flush()

    while True:
        try:
            response = await run_voice_interaction(context, require_wake=require_wake)
            if response is None:
                continue
        except (EOFError, KeyboardInterrupt):
            print("\n[Zeno] Goodbye!")
            break
        except Exception as e:
            print(f"[Zeno] Error: {e}")
            continue


def run_text_loop():
    context = Context()
    print("[Zeno] Text mode. Type 'exit' to quit.")

    while True:
        try:
            text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[Zeno] Goodbye!")
            break

        if not text:
            continue
        if text.lower() in ("exit", "quit", "q"):
            print("[Zeno] Goodbye!")
            break

        response = process_input(text, context)
        print(f"[Zeno] {response}")


if __name__ == "__main__":
    args = set(sys.argv[1:])
    wake = "--wake" in args or "-w" in args
    voice = "--voice" in args or "-v" in args
    continuous = "--continuous" in args or "-c" in args

    if continuous or voice or wake:
        asyncio.run(run_voice_loop(require_wake=wake))
    else:
        run_text_loop()
