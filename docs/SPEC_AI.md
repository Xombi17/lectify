# AI Spec (Production MVP)

## 1) Responsibilities
- Transcribe long lectures
- Remove non-academic content
- Tag exam-relevant information
- Generate notes + quiz + flashcards
- Create embeddings for search

## 2) Pipeline
1) Transcription (parallel chunks)
2) Cleaning (policy filters + AI classification)
3) Importance tagging (exam tips / marking schemes)
4) Study pack generation

## 3) Rules
- Chunk large audio
- Cache outputs
- Never fabricate facts (transcript grounded)
- Fallback to lexical search if embeddings fail

