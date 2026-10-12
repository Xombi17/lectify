"""Opt-in live provider smoke (Deepgram, Naga, NIM). Inert unless LIVE_PROVIDER_TESTS=1.

    LIVE_PROVIDER_TESTS=1 python -m scripts.smoke_providers [--audio PATH] [--skip-naga]

Without --audio only the LLM chat checks run. WARNING: every Naga check (chat or
whisper) spends 1 of the 100/day account-wide free requests; use --skip-naga to avoid it.
Prints provider, PASS/FAIL, latency and a short detail. Never prints keys.
"""
import argparse
import asyncio
import json
import mimetypes
import os
import sys
import time
from pathlib import Path

from core.config import get_settings

MAX_NAGA_BYTES = 20 * 1024 * 1024
PROMPT = 'Reply with only this JSON object: {"ok": true}'


def _line(name: str, ok, secs: float, detail: str) -> None:
    print(f"{name}: {'PASS' if ok else 'FAIL'} {secs:.2f}s {detail}")


async def _check(name: str, coro_fn, results: list) -> None:
    t = time.monotonic()
    try:
        detail = await coro_fn()
        _line(name, True, time.monotonic() - t, detail)
        results.append(True)
    except Exception as e:  # report every upstream failure, never crash
        _line(name, False, time.monotonic() - t, f"{type(e).__name__}: {str(e)[:120]}")
        results.append(False)


async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--audio")
    ap.add_argument("--skip-naga", action="store_true")
    args = ap.parse_args()
    s = get_settings()
    results: list = []

    audio = Path(args.audio) if args.audio else None
    mime = (mimetypes.guess_type(str(audio))[0] or "audio/mpeg") if audio else ""

    def skip(name: str, why: str = "no key") -> None:
        print(f"{name}: SKIP ({why})")

    def stt_detail(r) -> str:
        return f"{r.word_count} words, {r.duration_seconds:.0f}s audio, {r.text[:80]!r}"

    if audio:
        from services.transcription_service import DeepgramProvider, NagaWhisperProvider

        if s.DEEPGRAM_API_KEY:
            p = DeepgramProvider(s.DEEPGRAM_API_KEY, s.DEEPGRAM_MODEL, s.DEEPGRAM_LANGUAGE,
                                 s.DEEPGRAM_KEYTERMS, s.DEEPGRAM_TIMEOUT_S)
            await _check("deepgram", lambda: _stt(p, audio, mime, stt_detail), results)
        else:
            skip("deepgram")
        if args.skip_naga:
            skip("naga-whisper", "--skip-naga")
        elif not s.NAGA_AI_API_KEY:
            skip("naga-whisper")
        elif audio.stat().st_size > MAX_NAGA_BYTES:
            skip("naga-whisper", "file > 20 MiB")
        else:
            p = NagaWhisperProvider(s.NAGA_AI_API_KEY, s.NAGA_BASE_URL, s.NAGA_WHISPER_MODEL)
            await _check("naga-whisper", lambda: _stt(p, audio, mime, stt_detail), results)

    from services.ai_service import NIMProvider

    async def chat(p) -> str:
        reply = await p._chat_completion(PROMPT, json_mode=True, max_tokens=50)
        json.loads(reply)
        return "valid JSON"

    if args.skip_naga:
        skip("naga-chat", "--skip-naga")
    elif not s.NAGA_AI_API_KEY:
        skip("naga-chat")
    else:
        p = NIMProvider(s.NAGA_AI_API_KEY, s.NAGA_BASE_URL, s.NAGA_CHAT_MODEL, "", label="naga")
        await _check("naga-chat", lambda: chat(p), results)
    if s.NIM_API_KEY:
        p = NIMProvider(s.NIM_API_KEY, s.NIM_BASE_URL, s.NIM_CHAT_MODEL, s.NIM_EMBED_MODEL, label="nim")
        await _check("nim-chat", lambda: chat(p), results)
    else:
        skip("nim-chat")

    return 0 if all(results) else 1


async def _stt(provider, audio: Path, mime: str, fmt) -> str:
    return fmt(await provider.transcribe(audio, mime))


if __name__ == "__main__":
    if os.environ.get("LIVE_PROVIDER_TESTS") != "1":
        print("SKIP: set LIVE_PROVIDER_TESTS=1 to call live providers")
        sys.exit(0)
    sys.exit(asyncio.run(main()))
