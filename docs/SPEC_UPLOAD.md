# SPEC_UPLOAD — Browser-Direct Presigned Upload (Phase 16)

## Endpoints

### POST /api/lectures/upload-url (teacher/admin)
Request JSON:
`{title, class_id, timetable_slot_id?, subject?, semester?, filename, content_type, size}`.
Auth: `require_teacher_or_admin` plus active `TeacherAssignment` check for
non-admin callers (403 otherwise). Validation: `size > 200 MB` → 413;
`normalize_mime` + `ALLOWED_AUDIO_MIME` → 400 on mismatch.
Creates a `LectureDB` with `status="uploading"` and a server-built key
`classes/{class_id}/lectures/{lecture_id}/recording/{safe_filename}`
(the client never supplies the key). Returns
`{lecture_id, url, fields, key, expires_in: 900}` from
`storage.presign_post`. Returns 501 on `LocalStorage` (frontend falls back
to multipart `POST /api/lectures`).

### POST /api/lectures/{id}/upload-complete (uploader or admin)
Idempotent finalize. 404 when the lecture is missing; 403 when the caller is
neither the uploader nor admin. When `status` is already
`queued`/`processing`/`ready` it returns the lecture without re-enqueueing.
Otherwise it calls `storage.head_object(key)`:
- missing → 409 `Object not uploaded`
- size 0 or > 200 MB → 413, and the object is deleted
- content-type mismatch vs the row → 400

On success it sets `status="queued"`, records `presigned_upload`, and
enqueues one `transcribe` job (v1). A second call is a no-op returning the
lecture. Responds 202 like the legacy upload route.

### GET /api/lectures/{id}/audio-url (class-gated)
Runs `verify_lecture_access` first, then returns `{url, expires_in: 900}`
from `storage.presign_get`. Returns 501 on `LocalStorage` (frontend falls
back to the authed blob `GET /api/lectures/{id}/audio` stream).

## Status lifecycle
`uploading` (new pre-queue state) → `queued` → `processing`/`retrying` →
`ready`, with `error`/`dead_letter` as terminal failure states.
`uploading` maps to `queued` in `job-status` polling so the UI spinner
starts immediately. Abandoned `uploading` rows are tolerated: the S3
lifecycle rule expires `classes/` recordings; no sweeper is added.

## Limits
- Object size: `content-length-range` 1..200 MB, exact `Content-Type`
  condition on the presigned POST; re-verified server-side via `head_object`.
- Expiry: presigned POST and GET both expire in 900 s (≤ 15 min, STOR-03).

## Failure & redrive
After `maxReceiveCount=5` the message lands in the shared `lectify-dlq`
and the job + lecture rows are marked `dead_letter` (see
`infra/cdk/README.md` §10 for the operator redrive with
`infra/cdk/scripts/redrive-dlq.sh` plus `POST /lectures/{id}/retry`
admin reset). A deterministic test hook `FORCE_FAIL_LECTURE_ID` forces the
transcribe handler to raise; it is honored only when `ENV` is
`aws`/`demo`/`staging` and is inert in prod or when unset.

## Operator-only SNS limitation (Phase 14 D-16)
Lecture-ready email goes to operator addresses (`ready_emails`) only; each
recipient must confirm the AWS subscription email. Per-student delivery is
deferred to v2. In-app status remains the primary ready signal.

## Live verification record (VER-01 / VER-02, operator steps)
1. Upload a short real recording via the ALB `/teacher/upload` page
   (deployed with `APP_ORIGIN=http://<AlbDnsName>` for the browser S3 POST).
2. Watch `transcribe → materials → embed → ready`; confirm the in-app Ready
   pill and the operator SNS email.
3. Force a failure: set `FORCE_FAIL_LECTURE_ID=<lecture-id>` on the worker
   (non-prod env), upload again, confirm the lecture/job reach `dead_letter`
   after 5 deliveries.
4. Redrive: `bash scripts/redrive-dlq.sh --dest lectify-transcribe`, then
   `POST /lectures/{id}/retry` as admin; confirm depth zero and the lecture
   reprocesses to `ready`.
