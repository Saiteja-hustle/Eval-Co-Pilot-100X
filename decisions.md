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

## Open
- Check-in 5 "Stored" Green criteria not yet read.
- Third no-go line to be written by Tj.
- Vercel Hobby duration vs. check_one's 20s timeout (see Stage 2 note above): confirm the real current limit on vercel.com, then decide whether to shorten the timeout (e.g. to 8–9s) or restructure vercel.json to set `maxDuration`.
- checks.py / check_one was built now as part of this Stage 2 work, not in its own Stage 1 pass — Tj should review it as if Stage 1 just happened (run the 5 PRD test cases against Pratik's real app, per the PRD's own Stage 1 verify steps) before trusting it.
