# decisions.md (Eval Co-pilot)

Rule: every choice goes here. "Tj decided" = Tj chose it. "AI decided" = Claude proposed or Claude Code chose it. Tj reviews the AI list at each stage and can reverse anything.

## Tj decided
- Verification is by code only; AI never changes a Pass or Fail.
- LLM explanation is built last, only if everything else works.
- One "A good answer includes" box per question; commas; all must appear. No per-question must-not rules tonight.
- One global "wrong if the answer says this" text per run.
- Questions: 10 recommended, not required.
- Three tables only: Question, Run, Answer. Rules table cut for tonight ("store the least").
- Run 2 adds rows and never overwrites Run 1.
- Run 1 and Run 2 shown side by side.
- Tables made from the questions the app must answer, not copied from a template.
- Sketches stay Tj's own; Claude Code builds from them, Tj verifies each stage.
- Download report is cut first if behind.

## Tj decided: Stage 1
- Pratik's app gives different wording on repeat runs (the 3 m2 example sometimes appears, sometimes not), so includes text should use the stable fact (12), not a detail that sometimes appears. Run 1 vs Run 2 can flip from randomness alone. Known limit.

## AI decided (Tj to review)
- App error, timeout or empty answer = Fail with reason, then continue (Tj agreed on 19 Oct 4:20 PM).
- Proposed: timeout 20 seconds (open).
- Proposed: matching ignores case (open).
- Proposed: one question per request to avoid Vercel time limits (open; limit unverified).
- Proposed: plain HTML/JS front end (open).
- Tabled: edited good answers are not snapshotted; Run 1 judged by the old text.
- Field names and global wrong text stored on Run, fail reason stored on Answer.

## AI decided — Stage 1
- check_one lives in its own file, checks.py, with no other code (no Pydantic, no FastAPI) — Stage 1 is only the function, per the PRD.
- Both a connection/timeout exception from `requests` AND a non-200 HTTP status code are treated as "app error" — the PRD says "errors (error code)" so a 404/500 counts as an error, not a crash.
- Non-JSON response body (`response.json()` raises `ValueError`) is also "app error", since the PRD groups "returns non-JSON" under app error.
- `good_answer_includes` is split on commas, each piece `.strip()`-ed, and empty pieces (e.g. from a trailing comma) are dropped — this satisfies the PRD's "If the includes box has a trailing comma?" test without a separate rule.
- All matching (`good_answer_includes` words and `global_wrong_text`) is done by lower-casing both sides — case-insensitive, confirming the "proposed" item in the PRD.
- Check order is: transport/HTTP/JSON error -> empty answer -> missing included word(s) -> global wrong text -> Pass. Empty answer is checked before the includes/wrong-text checks so a genuinely empty string never spuriously "passes" when includes is empty.
- requests.txt: added `requests` (needed for check_one's POST call).
- test_checks.py prints one line per case as `label: expected=... actual=... app_answer=... -> OK/MISMATCH` rather than using assert, so all 4 cases always run and report, per "print one line per case with expected vs actual".
- Could not run test_checks.py against the live app from this sandbox: the environment's outbound network policy blocks `knowledge-retriever-mvp.vercel.app` (proxy returned 403 connect_rejected). Code is written per spec but the 5 Stage-1 PRD verify steps are unverified until network access is allowed and the tests are re-run.

## AI decided — Stage 0
- requirements.txt holds only fastapi and uvicorn (nothing else needed for a hello route).
- vercel.json uses the `@vercel/python` builder pointed at main.py, routing every path to it — the minimal config for FastAPI on Vercel, nothing project-specific added.
- .env.example lists SUPABASE_URL and SUPABASE_SERVICE_KEY with empty values only, per the no-real-keys rule.
- Single main.py at repo root (no api/ folder) since Stage 0 is one route; can be reorganized later if a stage needs it.

## AI decided — Stage 1 (built now, out of order — see note under Stage 2)
- `checks.py` did not exist in the repo before this change. Stage 1 ("One function") in the PRD was never built — only Stage 0 was committed. Since Stage 2 requires an API that wraps `check_one`, there was nothing to wrap. Built the minimal `check_one` exactly per PRD section 8 so Stage 2 has something real to call. Flagging this clearly: normally Claude Code builds one stage at a time and nothing else — this is the one exception, because Stage 2 is impossible without it.
- `check_one(question, app_address, question_field, answer_field, good_answer_includes, global_wrong_text)` posts `{question_field: question}` to `app_address` with `requests.post(..., timeout=20)`, per the Stage 1 "Proposed: timeout 20 seconds" item above.
- Any network exception, or a non-200 response, or a response body that isn't JSON → Fail "app error". A timeout specifically → Fail "timed out". These are separate reasons so Tj can tell "their server broke" from "their server didn't answer at all" — PRD only names both as required Fail cases, doesn't say whether to merge them.
- Missing or blank answer field → Fail "empty answer".
- Global wrong text is checked before the per-word checks, case-insensitive substring match, per the Stage 1 "matching ignores case" proposal above.
- `good_answer_includes` is split on commas, each piece trimmed, empty pieces dropped (handles a trailing comma or blank box) — first missing word wins and is the fail reason, e.g. "missing: 300", matching the PRD's own example.
- If `good_answer_includes` is empty, the loop over required words never runs, so only the global-wrong-text and always-on (error/timeout/empty) checks apply — matches "If the includes box is empty, only the global and always-on checks run."
- Return shape is a plain dict (`question`, `app_answer`, `pass_fail`, `fail_reason`) — no Pydantic model here since nothing in Stage 1 or 2 asks for response validation, only request validation.

## AI decided — Stage 2
- Added `POST /api/run-question` to `main.py`. Request body is a Pydantic model `RunQuestionRequest` with the six fields the task specified; `good_answer_includes` and `global_wrong_text` default to `""` since the PRD says the includes box and the global text are both optional. The other four fields have no default, so a request missing any of them gets FastAPI's automatic 422 with a `detail` list naming exactly which fields are missing — no extra validation code needed, verified locally (see below).
- The route body is just a call into `check_one` and returns its dict as JSON — no extra logic, per "Build ONLY the stage described."
- Kept `GET /api/hello` untouched.
- `requirements.txt`: added `requests` (needed by `checks.py`; nothing else was missing — `pydantic` ships as a FastAPI dependency already).
- `vercel.json` needed no change: it already builds `main.py` with `@vercel/python` and routes every path to it, which covers the new route automatically since both endpoints live on the same FastAPI app object.
- Verified locally (not yet on Vercel, since this session has no deploy access): `GET /api/hello` → 200; `POST /api/run-question` with fields missing → 422 listing each missing field; `POST /api/run-question` with a bad `app_address` → 200 with `{"pass_fail": "Fail", "fail_reason": "app error"}`, no crash and no 500.
- Vercel time-limit finding (task requirement #5): Vercel's own Hobby (free) plan docs (`vercel.com/docs/plans/hobby`, cross-checked against a Vercel community thread and a Vercel guide on function timeouts) state serverless function duration on Hobby defaults to **10 seconds** and can be raised via `maxDuration` to a **maximum of 60 seconds**. I could not load vercel.com directly from this container (DNS blocked the live docs page) so this is from search-result excerpts of Vercel's docs, not a direct fetch — flagging that it's not independently re-verified. Some third-party 2026 blog posts claim a newer "Fluid Compute" default of 300s now applies to Hobby too; those conflict with the plan-page figures the search surfaced, so Tj should open `vercel.com/docs/functions/configuring-functions/duration` himself to confirm before relying on either number.
- This matters because `check_one`'s `requests.post(..., timeout=20)` means one slow-but-live app could take up to 20 seconds to answer, which would exceed Hobby's 10-second default (though it fits under the 60-second configurable max). Current `vercel.json` sets no `maxDuration`, so it will run at Hobby's 10s default. Did not change `vercel.json`'s format to add `maxDuration` because it currently uses the legacy `builds`/`routes` schema, and Vercel does not allow mixing that with the `functions` config key needed to set `maxDuration` — changing the whole config format is bigger than "API plus deploy" and risks breaking the existing deploy. Leaving this as an open item below instead of guessing.

## AI decided — Stage 4
- Built strictly the minimal Stage 4 scope: one static page (`index.html`) served at `GET /`, plain HTML/CSS/JS in a single file, no build step, no framework. `checks.py` and `POST /api/run-question` were not touched — the page calls that existing endpoint as-is.
- `main.py` gained one new route: `GET /` returns `FileResponse("index.html")`. Nothing else in `main.py` changed.
- Setup section fields: app address, question field name (default `question`), answer field name (default `answer`), and the global "If the answer says this, it's wrong" text — matches the PRD's screen 2 layout, laid out as a 2-column grid since there are exactly four fields.
- Question rows start at 3 empty rows per the spec. "+ Add question" appends a row with the same two inputs (question, good-answer-includes) plus the helper line "Separate with commas. All of them must appear." Each row has its own "Delete" button; deleting is just removing that row's DOM node — no confirmation dialog, since this is pre-run editing, not a destructive action on saved data.
- "We recommend 10 questions. Fewer works too." is a static note under the rows, not tied to any validation — the Run button never blocks on row count (the PRD doesn't ask for a minimum/maximum).
- Run button: rows with a blank question are skipped (so a stray empty row never fires a request); if every row is blank, a message is shown instead of calling the API.
- Requests run strictly one at a time, in row order, with `await` between them (not `Promise.all`), per requirement 4. The status line updates to "Running N of TOTAL..." before each call, matching the exact phrasing in the task description.
- If `fetch` throws (network error) or the response status isn't 200, the row is treated as `{pass_fail: "Fail", fail_reason: "app error"}` and the loop continues to the next row — the run never stops early on one bad row. This mirrors `checks.py`'s own "app error" wording so the UI and backend agree on vocabulary.
- Report table shows the app's answer truncated to the first 80 characters with `...` appended if longer, per requirement 5; the full, untruncated answer is only shown when a row is clicked, appended below the table.
- Score line reads "`N` of `TOTAL` passed", counting rows whose `pass_fail` is exactly `"Pass"`.
- All text inserted into the table/report (question, answer, fail reason) is escaped via `textContent`/`innerHTML` round-trip (`escapeHtml`) before being written into the page, since the question and answer text originates from user input and from an arbitrary third-party app's response — this prevents a malicious answer string from injecting HTML/script into the report.
- No database, no login, no new dependencies — confirmed `requirements.txt` needs no changes since this stage adds no server-side code beyond one static-file route already covered by FastAPI.
- Verified manually: started the app locally with `uvicorn`, confirmed `GET /` returns the page (200) and `GET /api/hello` still works; used a headless-browser script (Playwright, dev-only, not added as a dependency) to click through add-row, delete-row, Run, and click-a-report-row, confirming the status message, the "N of N run" / "N of N passed" text, and the full-answer panel appearing after a click — then stopped the test browser and local server.

## AI decided — Stage 4 restyle (styling only, no functionality change)
- Scope: `index.html` only — CSS and minor wrapper markup. `main.py`, `checks.py`, `requirements.txt`, `vercel.json`, `PRD.md.docx` untouched. The `<script>` block is byte-for-byte unchanged; no element id, class used by JS, event listener, API call, field name, or visible label/helper/button/table-header/message text was touched.
- Added Google Fonts `Inter` via `<link>` tags in `<head>`, with system sans-serif fallback in the `font-family` stack.
- Replaced the old hard-coded colors with CSS custom properties on `:root` matching the brand palette given: `--color-primary #3B3F9E`, `--color-primary-tint #EEF0FF`, `--color-pass #1F8A4C`, `--color-fail #C73A3A`, `--color-text #1B1D2A`, `--color-text-muted #6B6F85`, plus a light grey-blue `--color-page-bg #F4F6FB` for the page background (white cards sit on top via existing `.card` class, unchanged selector).
- Card radius set to 12px, input/button radius to 8px, per the spec; added a subtle box-shadow on `.card`.
- Inputs: added a visible focus ring (indigo, `box-shadow`) and muted placeholder color; no change to input types, ids, names, or default values.
- Replaced `<h1>Eval Co-Pilot</h1>` with a `<header class="site-header">` containing the product name "Eval Co-pilot" and the one-line description "Test someone else's AI app with your own questions." — this is new header content called for explicitly in the task's "Look and feel" section, not one of the listed do-not-touch texts (labels, helper lines, buttons, table headers, messages), all of which are unchanged.
- `.pass`/`.fail` are now rendered as small colored pills (`border-radius: 999px`, tinted background, colored text) — pure CSS on the same class names the JS already sets via `className`/template string; the JS still only ever writes `class="pass"` or `class="fail"` on the `<td>`, nothing else changed there.
- Table: tinted header row (`--color-primary-tint`), lighter row-divider color, hover state on `.report-row` using the same tint — same `id`s/`class`es (`reportTable`, `reportBody`, `report-row`) the JS already uses.
- Added one new wrapper, `<div class="table-scroll">`, around the existing `<table id="reportTable">` only, to allow horizontal scrolling on narrow screens; the table itself, its id, and its children are untouched.
- Added a `@media (max-width: 600px)` block: the setup grid collapses to one column and card/button padding shrinks; no layout-breaking changes to element structure.
- Removed the now-orphaned `h1 { ... }` CSS rule since the `<h1>` element itself was replaced by the new header (dead CSS otherwise).
- Verified: div open/close tag counts balance (17/17), and both `main.py` and `checks.py` still `py_compile` cleanly (confirming no stray edits leaked into those files).

## AI decided — Stage 3
- `schema.sql`: three tables exactly as the task listed (which matches PRD section 10 plus a `created_at` on `questions` and `answers` that the PRD's own table didn't name but the task asked for explicitly). Every table has a nullable `user_id uuid` column, no default, no foreign key to `auth.users` yet — Stage 6 (login/RLS) is what fills it in and turns RLS on. `id` columns use `uuid primary key default gen_random_uuid()`, which needs the `pgcrypto` extension; the schema turns that extension on with `create extension if not exists pgcrypto` since Supabase doesn't always have it on by default. `answers.run_id` and `answers.question_id` are foreign keys to `runs(id)` / `questions(id)`, per the PRD's "Answer points to Run, Answer points to Question" arrow. No RLS statement anywhere in the file, per the task's explicit "do NOT turn on RLS yet".
- `requirements.txt`: added `supabase` (the Python client) and `python-dotenv` (loads `.env` locally). Nothing else changed.
- `main.py` calls `load_dotenv()` once at import time, then reads `SUPABASE_URL` / `SUPABASE_SERVICE_KEY` from `os.environ`. If both are set, it builds one `supabase` client at startup and reuses it for every request; if either is missing (e.g. a fresh clone with no `.env` yet), `supabase` stays `None` instead of crashing the whole app on import — only the routes that actually need the database fail, and only when called.
- `POST /api/runs` is new: takes `app_address`, `question_field`, `answer_field`, `global_wrong_text`, inserts exactly one row into `runs`, and returns that row's generated `id`. It does not touch `questions` or `answers` — those are per-question, not per-run.
- `POST /api/run-question` got one new **optional** field, `run_id` (defaults to `None`/absent, so every existing caller that doesn't send it behaves byte-for-byte as before). `check_one(...)` still runs first and its Pass/Fail result is computed and ready to return no matter what happens next. Only if `run_id` is present does the route also try to save: one `questions` row (`question_text`, `good_answer_includes` — a fresh row per answer, not deduplicated, since the PRD's 3-table model doesn't ask for question reuse across runs) and then one `answers` row linking that question and that run to the Pass/Fail outcome. That whole save is wrapped in one `try/except Exception`, so a Supabase outage, a bad `run_id`, missing credentials, or any other DB error can never turn a working check into a 500 — the same `result` dict goes out either way, with `result["saved"]` set to `True` on success or `False` on any failure (including when `supabase` is `None`). This directly implements the task's "A database error must never stop the check" rule.
- `GET /api/runs/{run_id}` fetches the one `runs` row (`.single()`, since `run_id` is a primary key and there's exactly one or none) plus every `answers` row whose `run_id` matches, and returns both under `{"run": ..., "answers": ...}`. This is intentionally the simplest shape that answers PRD test query 1 ("every answer in one run with pass_fail and fail_reason") — no join, no extra fields, nothing the task didn't ask for.
- `index.html`: the only JavaScript change is inside the existing `runBtn` click handler, right before the per-question loop starts. It now does one `POST /api/runs` call with the four setup fields already read off the page, and keeps the returned `id` in a new `runId` variable (`null` if the call fails or Supabase isn't configured, exactly like the existing network-error handling pattern already in this file). That `run_id` is then added as one new key in the JSON body already being sent to `/api/run-question` on every loop iteration. No other markup, styling, id, class, event listener, or visible text in the page was touched — this is the "smallest change needed" the task asked for.
- Did not add a `user_id` anywhere in the request bodies or the Python code (frontend or backend) — the task says `user_id` is nullable "for now" and nothing in Stage 3 asks for a value to be supplied yet. The column exists in the schema so Stage 6 doesn't need a migration, but it's left `NULL` on every insert until login exists.
- Verified locally (no real Supabase project connected in this sandbox): `GET /api/hello` → 200 unchanged; `GET /` → 200 unchanged; `POST /api/run-question` with no `run_id` → identical response shape to before (no `saved` key); same call with a `run_id` but no Supabase credentials configured → still returns the correct Pass/Fail result, plus `"saved": false`, with no crash and no 500. Could not verify the actual table writes (row counts in Supabase Table Editor, `run_id`/`question_id` correctness, "Run 2 never overwrites Run 1") from this sandbox since no real Supabase project/keys exist here — that part of Stage 3's own verify steps is still Tj's to run after pasting real keys into `.env` or Vercel.

## Open
- Check-in 5 "Stored" Green criteria not yet read.
- Third no-go line to be written by Tj.
- Vercel Hobby duration vs. check_one's 20s timeout (see Stage 2 note above): confirm the real current limit on vercel.com, then decide whether to shorten the timeout (e.g. to 8–9s) or restructure vercel.json to set `maxDuration`.
- checks.py / check_one was built now as part of this Stage 2 work, not in its own Stage 1 pass — Tj should review it as if Stage 1 just happened (run the 5 PRD test cases against Pratik's real app, per the PRD's own Stage 1 verify steps) before trusting it.
