---
version: 1
slug: "frontend"
primary_target: "frontend"
related_targets: []
---

# Lectify frontend surface

## Surface

The entire role-based web application: public landing and auth, student study library, teacher upload and lecture operations, lecture study workspace, review and bookmarks, and admin hierarchy management.

## Mode

Operate

## Audience and job

Students need to find and study lecture material quickly. Teachers need to submit recordings, understand processing state, and publish ready content. Admins need to configure the academic hierarchy without losing context.

## Product truth and constraints

Preserve existing roles, route behavior, API calls, test IDs, asynchronous processing states, class-scoped access, and study tools. Do not invent institutions, customers, testimonials, or metrics. Work inside the current Next.js App Router, React, Tailwind, and Phosphor icon stack.

## Direction contract

### THESIS

A lecture is a working record, not a marketing object. The interface should feel like a well-indexed academic reference desk: dense enough to scan, quiet enough to study, and explicit about what can happen next. It refuses the default stack of floating white cards and vague AI status pills.

### OWN-WORLD

The assigned Japanese high-density web direction is translated into an academic index system: cool paper-white surfaces, graphite type, a single signal-red accent for focus and state, tight hairline rules, compact utility labels, and modular blocks that earn their space. Noto Sans is the humanist workhorse for reading and JetBrains Mono is reserved for timestamps, IDs, and progress. The shell stays standard web navigation; the world contributes type, palette, density, and one signature move only.

### STORY

A student lands in Library and immediately sees the search field, today's study queue, and the lecture set. A teacher sees the queue health and the next upload action before the lecture list. A lecture detail screen makes status and the first useful study action clear before tabs. Empty, processing, and failed states explain recovery rather than hiding it.

### FIRST VIEWPORT

Desktop begins with a slim top utility bar and a compact left rail that carries brand, role, primary destinations, and account action. The content canvas uses an offset page heading with one decisive action, then a two-column work area: the primary dataset or study surface on the left and a narrow contextual rail for status, progress, timetable, or next action on the right. On mobile the rail becomes a horizontal section switcher and the contextual rail moves below the primary task. Signal-red appears in active rules, focused controls, and actionable status; it never decorates every block.

### FORM

Candidate 3 from direction seed `f4d28eea`, raised with the airport wayfinding discipline: every screen must answer “where am I, what is ready, and what is the next decision?” The split-flap challenger contributes state change that preserves row identity: processing rows update in place rather than jumping. The boarding-pass challenger contributes tabular figures and segmented metadata for lecture status, duration, and progress. These are system disciplines, not literal costume.

### FINISH

The finish condition is a coherent role-based app with accessible navigation, readable content, purposeful states, responsive layouts, and no dead links or broken route assumptions. The mechanical detector, build, test suite, and a desktop/mobile visual pass must run before handoff. unreviewed and undocumented is unfinished; this build ends with the finish review, the verdict, DESIGN.md, and every shipping raster carrying its provenance
