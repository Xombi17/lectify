"""Worker processes for queue-driven lecture processing.

Worker types:
  - TranscriptionWorker: Speech-to-text (concurrency=3)
  - AIWorker: Study materials generation (concurrency=5)
  - EmbeddingWorker: Embeddings + Neo4j sync (concurrency=10)
"""
from workers.base import BaseWorker, worker_main

__all__ = ["BaseWorker", "worker_main"]
