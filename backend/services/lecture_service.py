"""Lecture business logic — orchestrates storage + audio chunking + AI."""
import logging
from pathlib import Path

from models.lecture import LectureDB, StudyMaterials  # noqa: F401  (re-export shape)
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service
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
    sequence, digested per-chunk, then hierarchically merged into one study
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
    await repo.update_fields(lecture_id, {
        "progress_step": 2,
        "progress_total": 3,
        "progress_label": "Transcribing audio",
    })
    transcript = await ai.transcribe_audio(audio_path, mime)
    if not transcript:
        raise RuntimeError("Empty transcript from AI provider")

    await repo.update_fields(lecture_id, {
        "progress_step": 3,
        "progress_label": "Generating study materials",
    })
    materials = await ai.generate_study_materials(transcript)
    embedding = await _safe_embedding(ai, materials)

    # Store knowledge graph in Neo4j
    lecture = await repo.get_by_id(lecture_id)
    if lecture:
        await _extract_and_store_knowledge_graph(lecture_id, lecture, materials, repo)

    await repo.update_fields(lecture_id, {
        "transcript": transcript,
        "materials": materials,
        "embedding": embedding,
        "status": "ready",
        "error_message": None,
        "progress_step": 3,
        "progress_total": 3,
        "progress_label": "Done",
    })


async def _process_chunked(*, lecture_id, audio_path, duration, ai, repo, chunks_sink):
    logger.info("Long lecture detected (%.1fs); using chunked pipeline", duration)

    # --- Step 2: split ---
    await repo.update_fields(lecture_id, {
        "progress_step": 2,
        "progress_label": "Splitting into chunks",
    })
    chunk_paths = await split_into_chunks(audio_path, CHUNK_LENGTH_SECONDS)
    chunks_sink.extend(chunk_paths)
    chunk_count = len(chunk_paths)

    # progress plan: 1 (probe) + chunk_count (transcribe+digest each) + 1 (merge) + 1 (embed/save)
    total_steps = 2 + chunk_count + 2
    await repo.update_fields(lecture_id, {
        "chunk_count": chunk_count,
        "progress_step": 2,
        "progress_total": total_steps,
        "progress_label": f"Split into {chunk_count} chunks",
    })

    # --- Step 3..N: transcribe + digest each chunk ---
    chunk_transcripts: list[str] = []
    chunk_digests: list[dict] = []
    for idx, chunk_path in enumerate(chunk_paths):
        step = 3 + idx
        offset = idx * CHUNK_LENGTH_SECONDS
        label = f"Transcribing chunk {idx + 1}/{chunk_count} ({format_timestamp(offset)})"
        await repo.update_fields(lecture_id, {
            "progress_step": step,
            "progress_label": label,
        })
        chunk_text = await ai.transcribe_audio(chunk_path, CHUNK_MIME)
        chunk_transcripts.append(chunk_text)

        digest = await ai.digest_chunk(chunk_text)
        digest["chunk_index"] = idx
        digest["start_seconds"] = offset
        chunk_digests.append(digest)

    # Stitch full transcript with timestamps so chat/transcript view stays useful.
    transcript = "\\n\\n".join(
        f"[Chunk {i + 1} · {format_timestamp(i * CHUNK_LENGTH_SECONDS)}]\\n{t.strip()}"
        for i, t in enumerate(chunk_transcripts)
    )

    # --- Merge step ---
    await repo.update_fields(lecture_id, {
        "progress_step": 3 + chunk_count,
        "progress_label": "Hierarchical merge",
    })
    materials = await ai.merge_chunk_digests(chunk_digests)
    embedding = await _safe_embedding(ai, materials)

    # Store knowledge graph in Neo4j
    lecture = await repo.get_by_id(lecture_id)
    if lecture:
        await _extract_and_store_knowledge_graph(lecture_id, lecture, materials, repo)

    # --- Save ---
    await repo.update_fields(lecture_id, {
        "transcript": transcript,
        "materials": materials,
        "embedding": embedding,
        "status": "ready",
        "error_message": None,
        "progress_step": total_steps,
        "progress_total": total_steps,
        "progress_label": "Done",
    })


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