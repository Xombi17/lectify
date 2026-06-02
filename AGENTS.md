# AGENTS.md — Project Context & Agent Rules (Lectify)

Single source of truth for AI agents working in this repo.

## 1) Product Scope (Production MVP)
- Recording upload
- Transcription
- Transcript cleaning
- Exam importance tagging
- Notes + quiz + flashcards
- Search + student dashboard
- Admin academic hierarchy
- QR enrollment

## 2) Optimization Rule (Non-Negotiable)
- Write optimized code by default. Avoid designs that require later refactors.

## 3) Source of Truth Order
1) AGENTS.md
2) CLAUDE.md
3) docs/README.md (single source-of-truth index)
4) docs/PRODUCTION_MVP_PLAN.md
5) docs/SPEC_* files
6) README
7) Current user request

## 4) Execution Rules
- Read before edit.
- No secrets in code or docs.
- Keep changes minimal and scoped.
- Update specs when behavior changes.
- Run tests or a sanity check for runtime changes.

## 5) AI Rules
- Chunk long lectures
- Hierarchical summarization
- Transcript-grounded chat
- Cache outputs

