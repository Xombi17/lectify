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
- Gemini embeddings: `GEMINI_EMBED_MODEL` (default `gemini-embedding-001`, `output_dimensionality=768`). Vectors are NOT in the same space as the retired `text-embedding-004`; lectures embedded earlier need re-embedding (no re-embed script exists; re-enqueue the `embed` stage per lecture) for good semantic search. Neo4j outages log one WARNING per 60 s and never fail the pipeline.
- `GET /lectures/{id}` returns `processing_seconds` (ready only; first job created_at -> last job updated_at, fallback lecture created_at -> updated_at).

## 4) Providers (Phase 19)
Transcripts may be mixed Hindi+English; study output is English. `STUB_PROVIDERS` bypasses all of this.

**STT chain** `TRANSCRIPTION_PROVIDERS` (default `deepgram,naga,gemini`):
- Deepgram Nova-3, whole file in one request (no chunking), smart_format/paragraphs/utterances/diarize, optional `DEEPGRAM_KEYTERMS`. Limits: 2 GB file, 10-min processing cap (about 3 h of audio at ~70x).
- Naga `whisper-large-v3:free`, per chunk of <= 20 MiB, text only.
- Gemini, last resort.

**LLM chain** `LLM_PROVIDERS` (default `naga,nim,gemini`), free models only: `nemotron-3-super-120b-a12b:free` (Naga), `nvidia/nemotron-3-super-120b-a12b` (NIM). Embeddings stay on `AI_PROVIDER` (no re-embed).

**Failover:** 429 puts the provider in cooldown (honours Retry-After, else `PROVIDER_COOLDOWN_SECONDS`); the `naga` budget is shared by STT and LLM. 5xx, timeout, empty/None content or invalid JSON falls to the next provider. All rate limited raises `ProviderRateLimited`.

**Free limits:** Naga 10 rpm and 100 requests/day account-wide; Deepgram per account credit.

**Env vars (default):** `DEEPGRAM_API_KEY` (empty), `DEEPGRAM_MODEL` (nova-3), `DEEPGRAM_LANGUAGE` (multi, spike winner), `DEEPGRAM_KEYTERMS` (empty), `DEEPGRAM_COST_PER_MINUTE` (0.0043), `DEEPGRAM_TIMEOUT_S` (600), `NAGA_AI_API_KEY` (empty), `NAGA_BASE_URL` (https://api.naga.ac/v1), `NAGA_CHAT_MODEL` (nemotron-3-super-120b-a12b:free), `NAGA_WHISPER_MODEL` (whisper-large-v3:free), `NIM_API_KEY` (empty), `NIM_CHAT_MODEL` (nvidia/nemotron-3-super-120b-a12b), `TRANSCRIPTION_PROVIDERS`, `LLM_PROVIDERS`, `PROVIDER_COOLDOWN_SECONDS` (60), `LLM_TIMEOUT_S` (120).
