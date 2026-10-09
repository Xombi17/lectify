# Lectify design system

## Visual world

Lectify is a compact academic index: a calm study surface with the scanability of a well-run reference desk. It uses density and rules to make state legible, not to make the interface feel technical for its own sake.

## Palette

- **Paper:** cool near-white page background (`--background`) for long reading sessions.
- **Card:** white working surface (`--card`) with a single border system.
- **Graphite:** deep blue-black shell and primary text (`--primary`, `--shell-rail`).
- **Signal red:** the only brand accent (`--accent`), reserved for focus, active navigation, primary actions, and attention states.
- **Semantic states:** green for ready/success, amber for queued or processing, red for failed/destructive. Status is always paired with text or an icon.

## Type

Noto Sans is the humanist workhorse for headings and reading text. JetBrains Mono is reserved for timestamps, IDs, percentages, upload progress, and compact utility labels. Headings use tight tracking and balanced wrapping; body copy stays readable and bounded.

## Composition

- Desktop protected surfaces use a 244px graphite rail, a 64px utility header, and a fluid content canvas capped at 1500px.
- Mobile collapses the rail into a horizontal section switcher below the utility header.
- Data-heavy groups use hairline grids and variable-height rows rather than nested card stacks.
- Cards exist only when they clarify a boundary or state. Most content uses grouped panels, rules, and open space.
- Primary pages lead with one clear task and then a primary work area with a contextual rail or state panel.

## Controls and states

Buttons use compact rounded controls with visible active, disabled, and focus states. Inputs are labeled above the field. Loading states preserve final layout shape. Empty states explain what to do next. Processing states show the current stage and progress where the backend provides it. Errors explain the recovery path without exposing backend secrets or implementation details.

## Motion

Motion is brief and purposeful: content enters with a small vertical settle, lecture lists preserve row identity during updates, and the review card flips to reveal an answer. `prefers-reduced-motion` disables non-essential motion.

## Accessibility

Landmarks, skip navigation, keyboard focus, semantic labels, readable contrast, text-plus-icon status, mobile-safe hit targets, and reduced-motion handling are part of the system. No important meaning relies on color alone.
