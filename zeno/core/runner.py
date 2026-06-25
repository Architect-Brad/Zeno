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


async def listen_async(timeout: int = 15) -> str | None:
    """Async wrapper around STT."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, listen, timeout)


async def speak_async(text: str) -> bool:
    """Async wrapper around TTS."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, speak, text)


async def run_voice_interaction(context: Context) -> str | None:
    """
    Single voice interaction: listen → process → speak.
    Returns the response text, or None if no input.
    """
    text = await listen_async()
    if not text:
        return None

    # Prepend wake word for the NLU if not present
    if not any(ww in text.lower() for ww in ("zeno", "hey")):
        text = f"hey zeno {text}"

    response = process_input(text, context)
    await speak_async(response)
    return response


async def run_voice_loop():
    """
    Continuous voice interaction loop.
    Runs until KeyboardInterrupt.
    """
    context = Context()
    print("[Zeno] Voice assistant ready. Say 'Hey Zeno' or press Enter to start.")
    print("[Zeno] Press Ctrl+C to exit.")
    sys.stdout.flush()

    while True:
        try:
            response = await run_voice_interaction(context)
            if response is None:
                continue
        except (EOFError, KeyboardInterrupt):
            print("\n[Zeno] Goodbye!")
            break
        except Exception as e:
            print(f"[Zeno] Error: {e}")
            continue


def run_text_loop():
    """
    Simple text-only interaction loop for testing/dev.
    Type commands at the prompt.
    """
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
    import sys
    if "--voice" in sys.argv:
        asyncio.run(run_voice_loop())
    else:
        run_text_loop()
