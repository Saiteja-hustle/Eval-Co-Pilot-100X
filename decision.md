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

## AI decided — Stage 0
- requirements.txt holds only fastapi and uvicorn (nothing else needed for a hello route).
- vercel.json uses the `@vercel/python` builder pointed at main.py, routing every path to it — the minimal config for FastAPI on Vercel, nothing project-specific added.
- .env.example lists SUPABASE_URL and SUPABASE_SERVICE_KEY with empty values only, per the no-real-keys rule.
- Single main.py at repo root (no api/ folder) since Stage 0 is one route; can be reorganized later if a stage needs it.

## Open
- Check-in 5 "Stored" Green criteria not yet read.
- Third no-go line to be written by Tj.
