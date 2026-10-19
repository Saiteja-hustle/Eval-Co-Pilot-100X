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

## Open
- Check-in 5 "Stored" Green criteria not yet read.
- Third no-go line to be written by Tj.
