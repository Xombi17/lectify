# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Users

- Students use Lectify after class to find published lectures, search across course material, review notes, take quizzes, study flashcards, and save important concepts.
- Teachers upload or record lecture audio, monitor asynchronous processing, review generated material, and publish ready lectures to their assigned classes.
- Administrators configure the academic hierarchy, assign teachers, and manage class enrollment infrastructure.

## Product Purpose

Lectify turns lecture recordings into structured study material. A successful session lets a teacher submit a recording without waiting for AI processing, then lets enrolled students return to clean notes, quizzes, flashcards, transcript search, and grounded doubt chat from one lecture workspace.

## Positioning

The product's differentiator is an asynchronous lecture-intelligence pipeline that keeps the teacher's recording as the source while producing exam-relevant study assets for a class-scoped student library.

## Operating Context

Lectify is used in academic institutions across a teacher-to-student workflow. Uploads can be long audio recordings and processing is asynchronous. Students work from a class-filtered library and revisit material in short study sessions. Admins work with a multi-level academic hierarchy and enrollment flows.

## Capabilities and Constraints

- Role-based experiences for admin, teacher, and student.
- Teacher upload flow supports browser-direct object storage uploads with visible progress and a fallback path.
- Processing states include queued/uploaded, processing, ready, and failed/dead-letter states.
- Ready lectures expose cleaned notes, quiz, flashcards, transcript, translation, bookmarks, audio playback, and grounded doubt chat where available.
- Students only see lectures and study data from their enrolled class.
- Keep the existing Next.js App Router, React components, Tailwind CSS, Phosphor icons, and API contracts. Do not migrate the frontend framework as part of the redesign.
- Preserve test IDs and functional behavior while improving the interaction model, responsive layout, accessibility, and visual system.

## Brand Commitments

- Product name: Lectify.
- Existing product language is direct, academic, and operational rather than playful or hype-driven.
- The redesign should feel like a calm, high-trust study workspace with enough personality to be memorable without obscuring tasks.

## Evidence on Hand

- Product and flow specifications in `docs/SPEC_PRODUCT.md` and `docs/SPEC_FLOW.md`.
- Existing role-based screens under `frontend/src/cra-pages/` and shared shell/components under `frontend/src/components/`.
- Existing automated frontend tests under `frontend/src/**/__tests__/`.
- No verified customer logos, testimonials, performance claims, or production photography are available; do not invent them.

## Product Principles

- Make the next useful action obvious.
- Keep asynchronous processing state legible and honest.
- Keep learning content grounded in the lecture and scoped to the student's class.
- Prefer quiet hierarchy and readable study surfaces over decorative UI.
- Preserve keyboard access, responsive behavior, and meaningful empty/error/loading states.

## Accessibility & Inclusion

Use semantic landmarks, visible keyboard focus, labeled form controls, readable contrast, reduced-motion fallbacks, and responsive layouts that remain usable at narrow mobile widths. Avoid relying on color alone for status or action meaning.
