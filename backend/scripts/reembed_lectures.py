"""Re-embed existing lectures after an embedding-model change.

Seed text matches workers/embedding.py (summary + key concepts). Run from backend/:

    python -m scripts.reembed_lectures --dry-run
    python -m scripts.reembed_lectures [--limit N]

Sequential on purpose (provider rate limits); safe to re-run.
"""
import argparse
import asyncio
import logging
import sys

from sqlalchemy import select

from core.sql_db import close_sql, session_maker
from models.orm import LectureORM
from repositories.lecture_repository import LectureRepository
from services.ai_service import get_ai_service

logger = logging.getLogger(__name__)


def _seed(materials: dict | None) -> str:
    m = materials or {}
    return " ".join(filter(None, [m.get("summary") or "", " ".join(m.get("key_concepts") or [])])).strip()


async def reembed_all(ai, dry_run: bool = False, limit: int | None = None) -> tuple[int, int, int]:
    """Returns (done, skipped_no_seed, failed)."""
    async with session_maker()() as s:
        rows = (await s.execute(select(LectureORM.id, LectureORM.materials))).all()
    repo = LectureRepository()
    done = skipped = failed = 0
    for lecture_id, materials in rows:
        if limit is not None and done >= limit:
            break
        seed = _seed(materials)
        if not seed:
            skipped += 1
            continue
        if dry_run:
            done += 1
            continue
        try:
            await repo.update_fields(lecture_id, {"embedding": await ai.embed(seed)})
            done += 1
        except Exception as e:  # keep going; failures are reported and re-runnable
            logger.warning("Re-embed failed for %s: %s", lecture_id, str(e)[:200])
            failed += 1
    return done, skipped, failed


async def _main(args) -> int:
    try:
        done, skipped, failed = await reembed_all(get_ai_service(), args.dry_run, args.limit)
    finally:
        await close_sql()
    verb = "would re-embed" if args.dry_run else "re-embedded"
    sys.stdout.write(f"{verb} {done}, skipped (no summary) {skipped}, failed {failed}\n")
    return 1 if failed else 0


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--dry-run", action="store_true")
    p.add_argument("--limit", type=int)
    logging.basicConfig(level=logging.INFO)
    return asyncio.run(_main(p.parse_args()))


if __name__ == "__main__":
    sys.exit(main())
