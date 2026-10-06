"""AI service — single point of contact with the LLM provider.

Today: Google Gemini 3.7 Flash via google-genai SDK.
Tomorrow: swap to Ollama / vLLM by writing a new `AIProvider` subclass
and changing one line in `get_ai_service()`.

Also supports NVIDIA NIM (OpenAI-compatible) for text generation and embeddings.
Select provider via AI_PROVIDER env var ("nim" | "gemini").
"""

import email.utils
import functools
import json
import logging
import re
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.config import get_settings
from models.lecture import Flashcard, QuizQuestion, StudyMaterials

logger = logging.getLogger(__name__)
settings = get_settings()


# ── Prompts ────────────────────────────────────────────────────────────────────

STUDY_PROMPT = """You are an expert academic assistant. Read this lecture transcript and produce a comprehensive study pack.

Return ONLY valid JSON (no markdown fences) matching this exact schema:
{
  "summary": "2-4 sentence overview of the lecture",
  "smart_notes": ["bullet-style cleaned note", "..."],
  "key_concepts": ["concept 1", "concept 2", "..."],
  "quiz": [
    {"question": "...", "options": ["A","B","C","D"], "answer_index": 0, "explanation": "..."}
  ],
  "flashcards": [
    {"front": "question or term", "back": "answer or definition"}
  ]
}

Rules:
- Generate 8-15 smart_notes covering definitions, key explanations, examples.
- Strip filler words, jokes, off-topic chatter; preserve academic depth.
- Generate exactly 5 quiz questions (mix of easy/medium/hard) with 4 options each.
- answer_index is the 0-based index into options.
- Generate 8-12 flashcards covering core terms.
- Use clear, student-friendly language.

TRANSCRIPT:
"""


CHUNK_DIGEST_PROMPT = """You are summarising ONE chunk of a longer lecture for later hierarchical merging.

Return ONLY valid JSON:
{
  "chunk_summary": "3-6 sentence summary of THIS chunk",
  "chunk_notes": ["bullet note", "..."],
  "key_concepts": ["concept", "..."]
}

Rules:
- 6-10 chunk_notes covering definitions, examples, and explanations IN THIS CHUNK ONLY.
- 3-7 key_concepts.
- Skip filler/jokes/off-topic side conversations.

CHUNK TRANSCRIPT:
"""


HIERARCHICAL_MERGE_PROMPT = """You are merging per-chunk digests of a long lecture into ONE final study pack.

Treat the inputs as your source of truth. Deduplicate concepts, prefer breadth + depth, organise notes by topic flow (not by chunk order).

Return ONLY valid JSON matching this schema:
{
  "summary": "4-6 sentence overview of the WHOLE lecture",
  "smart_notes": ["bullet note", "..."],
  "key_concepts": ["concept", "..."],
  "quiz": [
    {"question": "...", "options": ["A","B","C","D"], "answer_index": 0, "explanation": "..."}
  ],
  "flashcards": [{"front": "...", "back": "..."}]
}

Rules:
- 15-25 smart_notes (since the lecture is long).
- 8-15 unique key_concepts.
- Exactly 8 quiz questions (mix easy/medium/hard) with 4 options each.
- 12-18 flashcards.
- Use clear, student-friendly language.

CHUNK DIGESTS (JSON array, in chronological order):
"""

# ── Phase 9: New prompts for lazy-generated content ─────────────────────────────

CHEATSHEET_PROMPT = """You are an expert academic assistant. Create a concise cheatsheet from this lecture transcript.

Return ONLY valid JSON (no markdown fences):
{
  "sections": [
    {
      "heading": "Section Title",
      "points": ["key fact or formula", "another key point", "..."]
    }
  ]
}

Rules:
- 4-8 sections, each with a clear academic heading.
- 3-6 bullet points per section — keep them terse and exam-relevant.
- Prioritise definitions, formulas, theorems, and cause-effect chains.
- Do NOT include conversational filler.

TRANSCRIPT:
"""


PODCAST_SCRIPT_PROMPT = """You are writing a short podcast narration script for a student audience. Turn this lecture transcript into an engaging 2-3 minute spoken overview.

Return ONLY valid JSON (no markdown fences):
{
  "script": "The full narration text, 300-600 words, written in a conversational but academic tone.",
  "title": "A catchy episode title (under 60 characters)"
}

Rules:
- Open with a hook (question, surprising fact, or real-world analogy).
- Explain 2-4 key concepts in simple language — as if explaining to a classmate.
- Close with a memorable takeaway or study tip.
- Use short sentences and natural transitions suitable for text-to-speech.
- Avoid acronyms that aren't spelled out; avoid complex formulas in speech form.

TRANSCRIPT:
"""


QUIZ_V2_PROMPT = """You are generating a fresh quiz from a lecture transcript. Produce varied, high-quality questions.

Return ONLY valid JSON (no markdown fences):
{
  "questions": [
    {
      "type": "multiple_choice",
      "question": "The question text?",
      "options": ["A", "B", "C", "D"],
      "answer_index": 0,
      "explanation": "Why this is correct.",
      "difficulty": "medium",
      "topic": "The topic this covers"
    }
  ]
}

Rules:
- Exactly 10 questions total:
  - 5 multiple_choice (4 options, answer_index 0-3)
  - 3 true_false (options: ["True", "False"])
  - 2 fill_blank (options: [], answer: "the exact answer string", accepted_answers: ["alt1", "alt2"])
- Mix difficulties: ~3 easy, ~4 medium, ~3 hard.
- Each question must have a clear topic (1-3 words).
- For fill_blank: the question should contain "____" where the answer goes.

TRANSCRIPT:
"""


CONCEPTS_V2_PROMPT = """You are extracting and expanding key concepts from a lecture for deep study.

Return ONLY valid JSON (no markdown fences):
{
  "concepts": [
    {
      "name": "Concept Name",
      "definition": "1-2 sentence definition",
      "explanation": "3-5 sentence deeper explanation with examples",
      "importance": "exam_importance" or "foundational" or "applied",
      "related_concepts": ["Related concept 1", "Related concept 2"]
    }
  ]
}

Rules:
- Extract 6-12 core concepts from the transcript.
- importance must be one of: "exam_importance", "foundational", "applied".
- Each explanation should include at least one example or analogy.
- related_concepts should reference other concepts in this list where possible.
- Order by importance (exam_importance first).

TRANSCRIPT:
"""


# ── ABC ─────────────────────────────────────────────────────────────────────────


class ProviderRateLimited(Exception):
    """Raised when an AI provider returns a 429 Too Many Requests response.

    Carries retry_after (in seconds) when provided by the upstream Retry-After header.
    The worker loop intercepts this to apply in-process backoff (sleep) without
    consuming a queue receive/delivery attempt, honoring Retry-After (D-09).
    """

    def __init__(
        self, message: str = "Provider rate limited", retry_after: float | None = None
    ):
        super().__init__(message)
        self.retry_after = retry_after


def parse_retry_after(value: str | None) -> float | None:
    """Parse a Retry-After header value into seconds (float).

    None/empty -> None; numeric string -> float(max(0, value));
    otherwise tries email.utils.parsedate_to_datetime and returns max(0, seconds until that time)
    using timezone-aware UTC now. On any parse failure returns None.
    """
    if not value or not isinstance(value, str):
        return None
    val = value.strip()
    if not val:
        return None
    try:
        sec = float(val)
        return max(0.0, sec)
    except ValueError:
        pass
    try:
        dt = email.utils.parsedate_to_datetime(val)
        if dt is not None:
            now = datetime.now(timezone.utc)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            delta = (dt - now).total_seconds()
            return max(0.0, delta)
    except Exception:
        pass
    return None


def handle_rate_limit(func):
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except ProviderRateLimited:
            raise
        except Exception as e:
            status = getattr(e, "status_code", None) or getattr(e, "code", None)
            if status == 429 or type(e).__name__ == "RateLimitError":
                raw_headers = getattr(getattr(e, "response", None), "headers", None)
                retry_header = None
                if raw_headers is not None:
                    try:
                        retry_header = raw_headers.get(
                            "retry-after"
                        ) or raw_headers.get("Retry-After")
                    except Exception:
                        pass
                retry_after = parse_retry_after(retry_header)
                raise ProviderRateLimited(
                    f"Provider rate limited: {e}", retry_after=retry_after
                ) from e
            raise

    return wrapper


class AIProvider(ABC):
    @abstractmethod
    async def transcribe_audio(self, audio_path: Path, mime_type: str) -> str: ...

    @abstractmethod
    async def generate_study_materials(self, transcript: str) -> StudyMaterials: ...

    @abstractmethod
    async def digest_chunk(self, chunk_transcript: str) -> dict: ...

    @abstractmethod
    async def merge_chunk_digests(self, digests: list[dict]) -> StudyMaterials: ...

    @abstractmethod
    async def chat(
        self, transcript: str, history: list[dict], question: str
    ) -> str: ...

    @abstractmethod
    async def translate_pack(self, pack: dict, target_language: str) -> dict: ...

    @abstractmethod
    async def embed(self, text: str) -> list[float]: ...

    # Phase 9: lazy-generated content methods (not abstract — default raises)
    async def generate_cheatsheet(self, transcript: str) -> dict:
        """Lazy-generated cheatsheet. Override in provider subclasses."""
        raise NotImplementedError(
            "Cheatsheet generation not supported by this provider"
        )

    async def generate_podcast_script(self, transcript: str) -> dict:
        """Lazy-generated podcast narration script. Override in provider subclasses."""
        raise NotImplementedError(
            "Podcast script generation not supported by this provider"
        )

    async def generate_quiz_v2(self, transcript: str) -> list[dict]:
        """Lazy-generated v2 quiz questions (MC/TF/fill-blank). Override in provider subclasses."""
        raise NotImplementedError("Quiz v2 generation not supported by this provider")

    async def generate_concepts_v2(self, transcript: str) -> list[dict]:
        """Lazy-generated v2 concept deep-dives. Override in provider subclasses."""
        raise NotImplementedError(
            "Concepts v2 generation not supported by this provider"
        )


# ── Gemini Provider ────────────────────────────────────────────────────────────


class GeminiProvider(AIProvider):
    def __init__(self, api_key: str, model: str, fallback_models: list | None = None):
        from google import genai  # imported lazily so the app boots without a key

        self._client = genai.Client(api_key=api_key)
        self._model = model
        self._models = [model, *(fallback_models or [])]

    @staticmethod
    def _is_overloaded(e: Exception) -> bool:
        status = getattr(e, "status_code", None) or getattr(e, "code", None)
        if status in (429, 500, 502, 503):
            return True
        msg = str(e).lower()
        return "overload" in msg or "unavailable" in msg or "rate limit" in msg

    def _generate(self, *, contents, config=None):
        """Call generate_content with ordered model failover.

        429/5xx/overload and 404 (unknown model id) fall through to the next
        model. Anything else fails fast. If every model is overloaded, raise
        ProviderRateLimited so workers back off instead of burning retries.
        Single-model behavior is unchanged.
        """
        last_error: Exception | None = None
        for i, name in enumerate(self._models):
            try:
                if config is None:
                    return self._client.models.generate_content(model=name, contents=contents)
                return self._client.models.generate_content(
                    model=name, contents=contents, config=config
                )
            except Exception as e:  # noqa: BLE001 — classified below
                status = getattr(e, "status_code", None) or getattr(e, "code", None)
                if (self._is_overloaded(e) or status == 404) and i < len(self._models) - 1:
                    logger.warning("Model %s failed (%s); failing over", name, e)
                    last_error = e
                    continue
                if self._is_overloaded(e):
                    raise ProviderRateLimited(
                        f"All Gemini models overloaded (tried {len(self._models)}): {e}"
                    ) from e
                raise
        # Unreachable: loop either returns or raises.
        assert last_error is not None
        raise ProviderRateLimited(f"All Gemini models overloaded: {last_error}")

    @handle_rate_limit
    async def transcribe_audio(self, audio_path: Path, mime_type: str) -> str:
        from google.genai import types

        logger.info("Uploading audio to Gemini: %s (%s)", audio_path, mime_type)
        uploaded = self._client.files.upload(
            file=str(audio_path),
            config=types.UploadFileConfig(mime_type=mime_type),
        )
        prompt = (
            "Transcribe this lecture audio verbatim into clean readable English text. "
            "Use proper punctuation and paragraph breaks. Do NOT include timestamps."
        )
        response = self._generate(contents=[prompt, uploaded])
        return (response.text or "").strip()

    @handle_rate_limit
    async def generate_study_materials(self, transcript: str) -> StudyMaterials:
        from google.genai import types

        prompt = STUDY_PROMPT + transcript[:120_000]  # safety guard
        response = self._generate(
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = (response.text or "").strip()
        data = _parse_json_lenient(raw)
        return StudyMaterials(
            summary=data.get("summary"),
            smart_notes=list(data.get("smart_notes") or []),
            key_concepts=list(data.get("key_concepts") or []),
            quiz=[
                QuizQuestion(**q) for q in (data.get("quiz") or []) if _valid_quiz(q)
            ],
            flashcards=[
                Flashcard(**c) for c in (data.get("flashcards") or []) if _valid_card(c)
            ],
        )

    @handle_rate_limit
    async def digest_chunk(self, chunk_transcript: str) -> dict:
        from google.genai import types

        prompt = CHUNK_DIGEST_PROMPT + chunk_transcript[:60_000]
        response = self._generate(
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return _parse_json_lenient(response.text or "{}")

    @handle_rate_limit
    async def merge_chunk_digests(self, digests: list[dict]) -> StudyMaterials:
        from google.genai import types

        prompt = HIERARCHICAL_MERGE_PROMPT + json.dumps(digests, ensure_ascii=False)
        response = self._generate(
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        raw = (response.text or "").strip()
        data = _parse_json_lenient(raw)
        return StudyMaterials(
            summary=data.get("summary"),
            smart_notes=list(data.get("smart_notes") or []),
            key_concepts=list(data.get("key_concepts") or []),
            quiz=[
                QuizQuestion(**q) for q in (data.get("quiz") or []) if _valid_quiz(q)
            ],
            flashcards=[
                Flashcard(**c) for c in (data.get("flashcards") or []) if _valid_card(c)
            ],
        )

    @handle_rate_limit
    async def chat(self, transcript: str, history: list[dict], question: str) -> str:
        """RAG-style Q&A bound to the lecture transcript."""
        system = (
            "You are LectureMind, a study assistant. Answer the student's question using "
            "ONLY the lecture transcript below. If the transcript doesn't contain the "
            "answer, say so honestly. Be concise, accurate, and student-friendly. "
            "Use markdown formatting for lists and emphasis when helpful.\n\n"
            f"--- LECTURE TRANSCRIPT ---\n{transcript[:80_000]}\n--- END TRANSCRIPT ---"
        )
        # Render history + question as a single prompt (simple and provider-agnostic)
        convo_lines = [system, ""]
        for m in history[-10:]:  # keep last 10 turns
            role = "Student" if m.get("role") == "user" else "Assistant"
            convo_lines.append(f"{role}: {m.get('content', '').strip()}")
        convo_lines.append(f"Student: {question.strip()}")
        convo_lines.append("Assistant:")
        prompt = "\n".join(convo_lines)
        response = self._generate(contents=prompt)
        return (response.text or "").strip()

    @handle_rate_limit
    async def translate_pack(self, pack: dict, target_language: str) -> dict:
        """Translate summary/notes/concepts/flashcards into `target_language`.

        Preserves technical terms (formulas, code, proper nouns) where possible.
        Returns dict matching `pack` shape.
        """
        from google.genai import types

        prompt = (
            f"Translate the following JSON object into {target_language}. "
            "Preserve technical terminology, mathematical formulas, code, and proper "
            "nouns. Keep the JSON structure identical — only translate string VALUES, "
            "never keys. Output ONLY the translated JSON with no commentary.\n\n"
            f"{json.dumps(pack, ensure_ascii=False)}"
        )
        response = self._generate(
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return _parse_json_lenient(response.text or "{}")

    @handle_rate_limit
    async def embed(self, text: str) -> list[float]:
        """Lightweight text embedding for semantic search."""
        resp = self._client.models.embed_content(
            model="text-embedding-004",
            contents=text[:8_000],
        )
        # google-genai returns .embeddings (list) each with .values
        emb = resp.embeddings[0]
        return list(emb.values)

    # Phase 9 overrides for Gemini
    @handle_rate_limit
    async def _generate_json(self, prompt: str, max_tokens: int = 4096) -> dict:
        """Shared helper: call Gemini with JSON mode."""
        from google.genai import types

        response = self._generate(
            contents=prompt,
            config=types.GenerateContentConfig(response_mime_type="application/json"),
        )
        return _parse_json_lenient(response.text or "{}")

    async def generate_cheatsheet(self, transcript: str) -> dict:
        return await self._generate_json(CHEATSHEET_PROMPT + transcript[:100_000])

    async def generate_podcast_script(self, transcript: str) -> dict:
        return await self._generate_json(PODCAST_SCRIPT_PROMPT + transcript[:100_000])

    async def generate_quiz_v2(self, transcript: str) -> list[dict]:
        data = await self._generate_json(QUIZ_V2_PROMPT + transcript[:120_000])
        return data.get("questions", [])

    async def generate_concepts_v2(self, transcript: str) -> list[dict]:
        data = await self._generate_json(CONCEPTS_V2_PROMPT + transcript[:100_000])
        return data.get("concepts", [])


# ── NVIDIA NIM Provider ─────────────────────────────────────────────────────────


class NIMProvider(AIProvider):
    """OpenAI-compatible provider using NVIDIA NIM API.

    Handles text generation and embeddings. Delegates transcription to
    the Gemini fallback provider (NIM has no audio models).
    """

    def __init__(self, api_key: str, base_url: str, chat_model: str, embed_model: str):
        from openai import AsyncOpenAI  # lazy import

        self._client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self._chat_model = chat_model
        self._embed_model = embed_model
        self._gemini: GeminiProvider | None = None

    def _get_gemini(self) -> GeminiProvider:
        """Lazy-initialise a Gemini client for transcription fallback."""
        if self._gemini is None:
            if not settings.GEMINI_API_KEY:
                raise RuntimeError(
                    "NIM provider requires GEMINI_API_KEY as transcription fallback. "
                    "Set GEMINI_API_KEY in backend/.env."
                )
            self._gemini = GeminiProvider(
                settings.GEMINI_API_KEY, settings.GEMINI_MODEL
            )
        return self._gemini

    # ── Transcription (delegated to Gemini) ────────────────────────────────────

    async def transcribe_audio(self, audio_path: Path, mime_type: str) -> str:
        """NIM has no audio models — delegate to Gemini."""
        logger.info("NIM: delegating transcription to Gemini fallback")
        return await self._get_gemini().transcribe_audio(audio_path, mime_type)

    # ── Core AI methods ────────────────────────────────────────────────────────

    @handle_rate_limit
    async def _chat_completion(
        self, prompt: str, json_mode: bool = False, max_tokens: int = 4096
    ) -> str:
        """Shared helper: call NIM chat completion."""
        kwargs: dict = {
            "model": self._chat_model,
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": max_tokens,
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        response = await self._client.chat.completions.create(**kwargs)
        return (response.choices[0].message.content or "").strip()

    async def generate_study_materials(self, transcript: str) -> StudyMaterials:
        prompt = STUDY_PROMPT + transcript[:120_000]
        raw = await self._chat_completion(prompt, json_mode=True, max_tokens=4096)
        data = _parse_json_lenient(raw)
        return StudyMaterials(
            summary=data.get("summary"),
            smart_notes=list(data.get("smart_notes") or []),
            key_concepts=list(data.get("key_concepts") or []),
            quiz=[
                QuizQuestion(**q) for q in (data.get("quiz") or []) if _valid_quiz(q)
            ],
            flashcards=[
                Flashcard(**c) for c in (data.get("flashcards") or []) if _valid_card(c)
            ],
        )

    async def digest_chunk(self, chunk_transcript: str) -> dict:
        prompt = CHUNK_DIGEST_PROMPT + chunk_transcript[:60_000]
        raw = await self._chat_completion(prompt, json_mode=True)
        return _parse_json_lenient(raw)

    async def merge_chunk_digests(self, digests: list[dict]) -> StudyMaterials:
        prompt = HIERARCHICAL_MERGE_PROMPT + json.dumps(digests, ensure_ascii=False)
        raw = await self._chat_completion(prompt, json_mode=True, max_tokens=4096)
        data = _parse_json_lenient(raw)
        return StudyMaterials(
            summary=data.get("summary"),
            smart_notes=list(data.get("smart_notes") or []),
            key_concepts=list(data.get("key_concepts") or []),
            quiz=[
                QuizQuestion(**q) for q in (data.get("quiz") or []) if _valid_quiz(q)
            ],
            flashcards=[
                Flashcard(**c) for c in (data.get("flashcards") or []) if _valid_card(c)
            ],
        )

    async def chat(self, transcript: str, history: list[dict], question: str) -> str:
        """RAG-style Q&A bound to the lecture transcript."""
        system = (
            "You are LectureMind, a study assistant. Answer the student's question using "
            "ONLY the lecture transcript below. If the transcript doesn't contain the "
            "answer, say so honestly. Be concise, accurate, and student-friendly. "
            "Use markdown formatting for lists and emphasis when helpful."
        )
        messages: list[dict] = [
            {
                "role": "system",
                "content": system
                + f"\n\n--- LECTURE TRANSCRIPT ---\n{transcript[:80_000]}\n--- END TRANSCRIPT ---",
            },
        ]
        for m in history[-10:]:
            messages.append(
                {"role": m.get("role", "user"), "content": m.get("content", "").strip()}
            )
        messages.append({"role": "user", "content": question.strip()})
        response = await self._client.chat.completions.create(
            model=self._chat_model,
            messages=messages,
            max_tokens=1024,
        )
        return (response.choices[0].message.content or "").strip()

    async def translate_pack(self, pack: dict, target_language: str) -> dict:
        prompt = (
            f"Translate the following JSON object into {target_language}. "
            "Preserve technical terminology, mathematical formulas, code, and proper "
            "nouns. Keep the JSON structure identical — only translate string VALUES, "
            "never keys. Output ONLY the translated JSON with no commentary.\n\n"
            f"{json.dumps(pack, ensure_ascii=False)}"
        )
        raw = await self._chat_completion(prompt, json_mode=True, max_tokens=4096)
        return _parse_json_lenient(raw)

    @handle_rate_limit
    async def embed(self, text: str) -> list[float]:
        """Text embedding via NIM embedding model."""
        response = await self._client.embeddings.create(
            model=self._embed_model,
            input=text[:8_000],
        )
        return list(response.data[0].embedding)

    # ── Phase 9: Lazy-generated content ─────────────────────────────────────────

    async def generate_cheatsheet(self, transcript: str) -> dict:
        raw = await self._chat_completion(
            CHEATSHEET_PROMPT + transcript[:100_000], json_mode=True, max_tokens=4096
        )
        return _parse_json_lenient(raw)

    async def generate_podcast_script(self, transcript: str) -> dict:
        raw = await self._chat_completion(
            PODCAST_SCRIPT_PROMPT + transcript[:100_000],
            json_mode=True,
            max_tokens=2048,
        )
        return _parse_json_lenient(raw)

    async def generate_quiz_v2(self, transcript: str) -> list[dict]:
        raw = await self._chat_completion(
            QUIZ_V2_PROMPT + transcript[:120_000], json_mode=True, max_tokens=4096
        )
        data = _parse_json_lenient(raw)
        return data.get("questions", [])

    async def generate_concepts_v2(self, transcript: str) -> list[dict]:
        raw = await self._chat_completion(
            CONCEPTS_V2_PROMPT + transcript[:100_000], json_mode=True, max_tokens=4096
        )
        data = _parse_json_lenient(raw)
        return data.get("concepts", [])


# ── Shared helpers ─────────────────────────────────────────────────────────────


def _parse_json_lenient(raw: str) -> dict:
    """Parse JSON even if the model wraps it in code fences or trailing text."""
    raw = raw.strip()
    # strip markdown code fences
    fence = re.match(r"^```(?:json)?\s*(.+?)\s*```$", raw, re.DOTALL)
    if fence:
        raw = fence.group(1)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # find first { ... last }
        start = raw.find("{")
        end = raw.rfind("}")
        if start != -1 and end != -1:
            return json.loads(raw[start : end + 1])
        raise


def _valid_quiz(q: dict) -> bool:
    return (
        isinstance(q, dict)
        and isinstance(q.get("question"), str)
        and isinstance(q.get("options"), list)
        and len(q["options"]) >= 2
        and isinstance(q.get("answer_index"), int)
        and 0 <= q["answer_index"] < len(q["options"])
    )


def _valid_card(c: dict) -> bool:
    return (
        isinstance(c, dict)
        and isinstance(c.get("front"), str)
        and isinstance(c.get("back"), str)
    )


# ── Factory ────────────────────────────────────────────────────────────────────

_provider: Optional[AIProvider] = None


def get_ai_service() -> AIProvider:
    """Lazy singleton — selects provider based on AI_PROVIDER env var.

    - "nim"  → NIMProvider (requires NIM_API_KEY; GEMINI_API_KEY for transcription fallback)
    - "gemini" (default) → GeminiProvider (requires GEMINI_API_KEY)
    """
    global _provider
    if _provider is None:
        provider_name = settings.AI_PROVIDER.lower()

        if provider_name == "nim":
            if not settings.NIM_API_KEY:
                raise RuntimeError(
                    "AI_PROVIDER=nim but NIM_API_KEY is not set. "
                    "Set it in backend/.env or switch to AI_PROVIDER=gemini."
                )
            _provider = NIMProvider(
                api_key=settings.NIM_API_KEY,
                base_url=settings.NIM_BASE_URL,
                chat_model=settings.NIM_CHAT_MODEL,
                embed_model=settings.NIM_EMBED_MODEL,
            )
            logger.info(
                "AI provider: NVIDIA NIM (chat=%s, embed=%s)",
                settings.NIM_CHAT_MODEL,
                settings.NIM_EMBED_MODEL,
            )

        elif provider_name == "gemini":
            if not settings.GEMINI_API_KEY:
                raise RuntimeError(
                    "AI_PROVIDER=gemini but GEMINI_API_KEY is not set. "
                    "Set it in backend/.env to enable AI processing."
                )
            _provider = GeminiProvider(
                settings.GEMINI_API_KEY,
                settings.GEMINI_MODEL,
                fallback_models=settings.GEMINI_FALLBACK_MODELS,
            )
            chain = ", ".join([settings.GEMINI_MODEL, *settings.GEMINI_FALLBACK_MODELS])
            logger.info("AI provider: Gemini (%s)", chain)

        else:
            raise RuntimeError(
                f"Unknown AI_PROVIDER '{provider_name}'. Must be 'nim' or 'gemini'."
            )
    return _provider


def reset_ai_service() -> None:
    """Reset the singleton (useful for tests or hot-reload)."""
    global _provider
    _provider = None
