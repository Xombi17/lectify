"""CLI entrypoint for running background workers by stage.

Usage:
    python -m workers <stage>

Stages:
    transcribe          TranscriptionWorker
    generate_materials  AIWorker (alias: materials)
    embed               EmbeddingWorker
"""

import asyncio
import sys

from workers.ai import AIWorker
from workers.base import worker_main
from workers.embedding import EmbeddingWorker
from workers.transcription import TranscriptionWorker

STAGE_WORKERS = {
    "transcribe": TranscriptionWorker,
    "generate_materials": AIWorker,
    "materials": AIWorker,
    "embed": EmbeddingWorker,
}


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 1 or argv[0] not in STAGE_WORKERS:
        sys.stderr.write(
            "usage: python -m workers {transcribe|generate_materials|embed}\n"
        )
        return 2

    stage = argv[0]
    worker_class = STAGE_WORKERS[stage]
    asyncio.run(worker_main(worker_class))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
