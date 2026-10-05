"""CLI entrypoint for running background workers by stage.

Usage:
    python -m workers <stage>

Stages:
    transcribe          TranscriptionWorker
    generate_materials  AIWorker (alias: materials)
    embed               EmbeddingWorker
    all                 Run all 3 workers concurrently in one process
"""

import asyncio
import logging
import signal
import sys
from typing import Any, Callable, Sequence

from workers.ai import AIWorker
from workers.base import worker_main
from workers.embedding import EmbeddingWorker
from workers.transcription import TranscriptionWorker

logger = logging.getLogger(__name__)

STAGE_WORKERS = {
    "transcribe": TranscriptionWorker,
    "generate_materials": AIWorker,
    "materials": AIWorker,
    "embed": EmbeddingWorker,
}


async def run_all(
    worker_classes: Sequence[Any] | None = None,
    restart_delay: float = 5.0,
    sleep: Callable[[float], Any] = asyncio.sleep,
) -> None:
    """Run all three workers concurrently in one process, sharing one drain event.

    Each worker runs inside a supervisor loop that restarts crashed workers
    after `restart_delay` seconds without aborting peer workers.
    """
    logging.basicConfig(level=logging.INFO)

    if worker_classes is None:
        worker_classes = [TranscriptionWorker, AIWorker, EmbeddingWorker]

    shutdown_event = asyncio.Event()

    def _signal_handler() -> None:
        logger.info("Received termination signal, draining active jobs across all workers...")
        shutdown_event.set()

    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        try:
            loop.add_signal_handler(sig, _signal_handler)
        except (NotImplementedError, RuntimeError):
            pass

    workers = [cls() if isinstance(cls, type) else cls for cls in worker_classes]

    async def _supervise(worker: Any) -> None:
        worker_name = worker.__class__.__name__
        while not shutdown_event.is_set():
            try:
                await worker.run_forever(shutdown_event)
                break
            except asyncio.CancelledError:
                break
            except Exception as e:
                if shutdown_event.is_set():
                    break
                logger.exception(
                    "Worker %s crashed, restarting in %ss: %s",
                    worker_name,
                    restart_delay,
                    e,
                )
                try:
                    await sleep(restart_delay)
                except asyncio.CancelledError:
                    break

    await asyncio.gather(*[_supervise(w) for w in workers])


def main(argv: list[str] | None = None) -> int:
    if argv is None:
        argv = sys.argv[1:]

    if len(argv) != 1 or (argv[0] not in STAGE_WORKERS and argv[0] != "all"):
        sys.stderr.write(
            "usage: python -m workers {transcribe|generate_materials|embed|all}\n"
        )
        return 2

    stage = argv[0]
    if stage == "all":
        asyncio.run(run_all())
    else:
        worker_class = STAGE_WORKERS[stage]
        asyncio.run(worker_main(worker_class))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
