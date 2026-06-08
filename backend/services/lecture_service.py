"""Lecture business logic — orchestrates storage + audio chunking + AI."""
import logging
from pathlib import Path

from core.config import get_settings
from models.lecture import LectureDB, StudyMaterials  # noqa: F401  (re-export shape)
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service
from services.transcription_service import (
    GeminiFallbackProvider,
    TranscriptionProvider,
    TranscriptionResult,
    flag_low_confidence_segments,
    log_transcription_cost,
    WhisperProvider,
)
from services.audio_chunker import (
    cleanup_chunks,
    format_timestamp,
    get_duration_seconds,
    split_into_chunks,
)
from services.neo4j_service import get_neo4j_service
from services.storage_service import get_storage

logger = logging.getLogger(__name__)

# Tunables — kept here, not scattered.
CHUNK_THRESHOLD_SECONDS = 30 * 60       # >30 min → use chunked pipeline
CHUNK_LENGTH_SECONDS = 10 * 60          # 10-minute chunks
CHUNK_MIME = "audio/mpeg"               # ffmpeg re-encodes chunks to MP3

ALLOWED_AUDIO_MIME = {
    "audio/mpeg",
    "audio/mp3",
    "audio/wav",
    "audio/x-wav",
    "audio/wave",
    "audio/x-m4a",
    "audio/m4a",
    "audio/mp4",
    "audio/aac",
    "audio/ogg",
    "audio/flac",
}


def _get_transcription_provider() -> TranscriptionProvider:
    """Get the configured transcription provider with fallback."""
    settings = get_settings()

    if settings.TRANSCRIPTION_PROVIDER == "groq" and settings.GROQ_API_KEY:
        primary = WhisperProvider(
            api_key=settings.GROQ_API_KEY,
            model=settings.WHISPER_MODEL,
            language=settings.WHISPER_LANGUAGE,
        )
    else:
        # Use Gemini as primary if Groq not configured
        primary = GeminiFallbackProvider(get_ai_service())

    return primary


def normalize_mime(mime: str, filename: str) -> str | None:
    """Return a canonical audio MIME type or None if the input is not audio."""
    mime = (mime or "").lower()
    if mime in ALLOWED_AUDIO_MIME:
        return mime
    ext = Path(filename).suffix.lower()
    mapping = {
        ".mp3": "audio/mpeg",
        ".wav": "audio/wav",
        ".m4a": "audio/mp4",
        ".aac": "audio/aac",
        ".ogg": "audio/ogg",
        ".flac": "audio/flac",
        ".webm": "audio/webm",
    }
    return mapping.get(ext)


async def _extract_and_store_knowledge_graph(lecture_id: str, lecture: LectureDB, materials: StudyMaterials, repo: LectureRepository) -> None:
    """Extract concepts and relationships from study materials and store in Neo4j."""
    try:
        neo4j = get_neo4j_service()
        
        # Add lecture node
        neo4j.add_lecture_node(
            lecture_id=lecture.id,
            title=lecture.title,
            subject=lecture.subject,
            semester=lecture.semester
        )
        
        # Add concept nodes and connect to lecture
        for concept in materials.key_concepts:
            if concept and concept.strip():
                neo4j.add_concept_node(
                    lecture_id=lecture.id,
                    concept=concept.strip()
                )
        
        # TODO: Extract relationships between concepts
        # For now, we'll add some basic relationships based on co-occurrence
        # In a more advanced implementation, we could use the AI to extract relationships
        concepts = [c.strip() for c in materials.key_concepts if c and c.strip()]
        for i, concept1 in enumerate(concepts):
            for concept2 in concepts[i+1:]:
                # Add a generic RELATED_TO relationship for now
                # In future, we could use AI to determine relationship type
                neo4j.add_relationship_between_concepts(
                    lecture_id=lecture.id,
                    concept1=concept1,
                    concept2=concept2,
                    relationship_type="RELATED_TO"
                )
        
        logger.info("Stored knowledge graph for lecture %s in Neo4j", lecture_id)
        
    except Exception as e:
        logger.exception("Failed to store knowledge graph for lecture %s: %s", lecture_id, e)
        # Don't fail the entire pipeline if knowledge graph storage fails


async def process_lecture_background(lecture_id: str) -> None:
    """Run the full AI pipeline. Catch errors and persist them on the doc.

    Long lectures (>30 min) are split into ~10-min chunks, transcribed in
    parallel, digested per-chunk, then hierarchically merged into one study
    pack. Short lectures take the single-shot path.
    """
    repo = LectureRepository()
    storage = get_storage()

    lecture = await repo.get_by_id(lecture_id)
    if lecture is None:
        logger.error("Lecture %s not found in background task", lecture_id)
        return

    chunks_made: list[Path] = []

    try:
        ai = get_ai_service()

        # --- Step 1: probe duration ---
        await repo.update_fields(lecture_id, {
            "status": "processing",
            "progress_step": 1,
            "progress_total": 3,
            "progress_label": "Analyzing audio",
        })

        async with storage.open_local(lecture.audio_object_key) as audio_path:
            try:
                duration = await get_duration_seconds(audio_path)
            except Exception:
                logger.exception("Could not probe duration; falling back to single-shot path")
                duration = 0.0
            await repo.update_fields(lecture_id, {"duration_seconds": duration})

            if duration and duration > CHUNK_THRESHOLD_SECONDS:
                await _process_chunked(
                    lecture_id=lecture_id,
                    audio_path=audio_path,
                    duration=duration,
                    ai=ai,
                    repo=repo,
                    chunks_sink=chunks_made,
                )
            else:
                await _process_single_shot(
                    lecture_id=lecture_id,
                    audio_path=audio_path,
                    mime=lecture.audio_mime,
                    ai=ai,
                    repo=repo,
                )

        logger.info("Lecture %s processed", lecture_id)
    except Exception as exc:  # noqa: BLE001
        logger.exception("Failed to process lecture %s", lecture_id)
        await repo.update_fields(
            lecture_id,
            {"status": "error", "error_message": str(exc)[:500]},
        )
    finally:
        if chunks_made:
            cleanup_chunks(chunks_made)


async def _process_single_shot(*, lecture_id, audio_path, mime, ai, repo):
    provider = _get_transcription_provider()

    await repo.update_fields(lecture_id, {
        "progress_step": 2,
        "progress_total": 3,
        "progress_label": "Transcribing audio",
    })

    settings = get_settings()
    try:
        result = await provider.transcribe(audio_path, mime)
    except Exception as e:
        # Fallback to Gemini if Groq Whisper fails
        if settings.TRANSCRIPTION_FALLBACK_PROVIDER == "gemini":
            logger.warning("Groq Whisper failed (%s), falling back to Gemini", e)
            fallback = GeminiFallbackProvider(ai)
            result = await fallback.transcribe(audio_path, mime)
        else:
            raise

    if not result.text:
        raise RuntimeError("Empty transcript from transcription provider")

    # Flag low-confidence segments
    flagged = flag_low_confidence_segments(result)

    await repo.update_fields(lecture_id, {
        "progress_step": 3,
        "progress_label": "Generating study materials",
    })
    materials = await ai.generate_study_materials(result.text)
    embedding = await _safe_embedding(ai, materials)

    lecture = await repo.get_by_id(lecture_id)
    if lecture:
        await _extract_and_store_knowledge_graph(lecture_id, lecture, materials, repo)

    await repo.update_fields(lecture_id, {
        "transcript": result.text,
        "transcription_confidence": result.confidence,
        "transcription_language": result.language,
        "transcription_cost_usd": result.cost_usd,
        "low_confidence_segments": flagged,
        "materials": materials,
        "embedding": embedding,
        "status": "ready",
        "error_message": None,
        "progress_step": 3,
        "progress_total": 3,
        "progress_label": "Done",
    })

    log_transcription_cost(
        lecture_id=lecture_id,
        provider=result.provider,
        duration_seconds=result.duration_seconds,
        cost_usd=result.cost_usd,
        chunks=1,
    )


async def _process_chunked(*, lecture_id, audio_path, duration, ai, repo, chunks_sink):
    provider = _get_transcription_provider()
    settings = get_settings()

    logger.info("Long lecture detected (%.1fs); using chunked pipeline", duration)

    # --- Step 2: split ---
    await repo.update_fields(lecture_id, {
        "progress_step": 2,
        "progress_label": "Splitting into chunks",
    })
    chunk_paths = await split_into_chunks(audio_path, CHUNK_LENGTH_SECONDS)
    chunks_sink.extend(chunk_paths)
    chunk_count = len(chunk_paths)

    # progress plan: 1 (probe) + 1 (split) + chunk_count (transcribe only) + 1 (merge) + 1 (embed/save)
    total_steps = 2 + chunk_count + 2
    await repo.update_fields(lecture_id, {
        "chunk_count": chunk_count,
        "progress_step": 2,
        "progress_total": total_steps,
        "progress_label": f"Split into {chunk_count} chunks",
    })

    # --- Step 3..N: transcribe all chunks in parallel ---
    chunk_pairs = [(cp, CHUNK_MIME) for cp in chunk_paths]
    try:
        results = await provider.transcribe_chunks(
            chunk_pairs,
            max_concurrent=settings.WHISPER_MAX_CONCURRENT,
        )
    except Exception as e:
        # Fallback to sequential Gemini transcription
        if settings.TRANSCRIPTION_FALLBACK_PROVIDER == "gemini":
            logger.warning("Groq Whisper parallel failed (%s), falling back to Gemini sequential", e)
            fallback = GeminiFallbackProvider(ai)
            results = []
            for cp in chunk_paths:
                result = await fallback.transcribe(cp, CHUNK_MIME)
                results.append(result)
        else:
            raise

    # Collect transcripts and confidence data
    chunk_transcripts = [r.text for r in results]
    all_flagged = []
    total_cost = 0.0

    for idx, result in enumerate(results):
        flagged = flag_low_confidence_segments(result)
        for f in flagged:
            f["chunk_index"] = idx
        all_flagged.extend(flagged)
        total_cost += result.cost_usd

    # Stitch transcript with timestamps
    transcript = "\n\n".join(
        f"[Chunk {i + 1} · {format_timestamp(i * CHUNK_LENGTH_SECONDS)}]\n{t.strip()}"
        for i, t in enumerate(chunk_transcripts)
    )

    # --- Digest each chunk ---
    chunk_digests: list[dict] = []
    for idx, chunk_text in enumerate(chunk_transcripts):
        step = 3 + idx
        label = f"Digesting chunk {idx + 1}/{chunk_count}"
        await repo.update_fields(lecture_id, {
            "progress_step": step,
            "progress_label": label,
        })
        digest = await ai.digest_chunk(chunk_text)
        digest["chunk_index"] = idx
        digest["start_seconds"] = idx * CHUNK_LENGTH_SECONDS
        chunk_digests.append(digest)

    # --- Merge step ---
    merge_step = 3 + chunk_count
    await repo.update_fields(lecture_id, {
        "progress_step": merge_step,
        "progress_label": "Hierarchical merge",
    })
    materials = await ai.merge_chunk_digests(chunk_digests)
    embedding = await _safe_embedding(ai, materials)

    # Store knowledge graph in Neo4j
    lecture = await repo.get_by_id(lecture_id)
    if lecture:
        await _extract_and_store_knowledge_graph(lecture_id, lecture, materials, repo)

    # --- Save with confidence data ---
    avg_confidence = sum(r.confidence for r in results) / len(results) if results else 0.0
    detected_language = results[0].language if results else None

    await repo.update_fields(lecture_id, {
        "transcript": transcript,
        "transcription_confidence": avg_confidence,
        "transcription_language": detected_language,
        "transcription_cost_usd": total_cost,
        "low_confidence_segments": all_flagged,
        "materials": materials,
        "embedding": embedding,
        "status": "ready",
        "error_message": None,
        "progress_step": total_steps,
        "progress_total": total_steps,
        "progress_label": "Done",
    })

    log_transcription_cost(
        lecture_id=lecture_id,
        provider=results[0].provider if results else "unknown",
        duration_seconds=duration,
        cost_usd=total_cost,
        chunks=len(results),
    )


async def _safe_embedding(ai, materials) -> list[float] | None:
    seed = " ".join(filter(None, [
        materials.summary or "",
        " ".join(materials.key_concepts or []),
    ]))
    if not seed.strip():
        return None
    try:
        return await ai.embed(seed)
    except Exception:  # noqa: BLE001
        logger.exception("Embedding failed; semantic search will use lexical only")
        return None
