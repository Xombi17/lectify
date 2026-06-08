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

## 6) Per-Feature Doc Update Rule (MANDATORY)
After every feature lands — whether by Claude Code delegation, hand edit,
or merge — update **`CLAUDE.md`** `## Status` section in the same commit
with:
- What was added (one bullet, file paths)
- Test counts (new green / total green)
- New graph nodes (run `graphify update <path>` if code files changed,
  then `graphify explain <new symbol>` to confirm it's indexed)
- Next card in the queue (bump pending → in_progress)
CLAUDE.md `## Status` is the single source of truth for project status.
If a feature ships without a CLAUDE.md update, the build is incomplete.

## 7) Graphify-First Context Rule (TOKEN SAVER)
The repo has a pre-built knowledge graph at `graphify-out/graph.json`
(919 nodes, 2517 edges, 81 communities). **Before reading source files
with `Read` or `search_files`, query the graph first.** It is ~100×
cheaper than re-reading code and answers most "where is X", "what calls
X", "what does X depend on" questions in one BFS hop.

Preferred order for codebase questions:
1. `graphify query "<terms>" --budget 800` (BFS by default; `--dfs` for path tracing)
2. `graphify explain "<symbol>"` (single-node deep-dive with degree + neighbors)
3. `graphify path "<A>" "<B>"` (shortest path between two concepts)
4. `graphify affected "<X>" --relation uses --depth 2` (what breaks if I change X)
5. **Only then** read the source file the graph pointed you to

The `graphify claude install` hook makes step 0 automatic — Claude Code
will pre-query the graph on every PreToolUse before touching the
filesystem. See CLAUDE.md `## graphify` section.

Community cheat-sheet for fast navigation:
- C0 academic hierarchy · C1 lecture business logic · C2 routes
- C4 search · C5 audio chunker · C6 storage service · C8 server entrypoint

