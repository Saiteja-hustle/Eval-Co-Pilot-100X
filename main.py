import json
import os
from datetime import date
from typing import Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

from ai_check import check_missing_with_ai, groq_llm_call
from checks import check_one

load_dotenv()

app = FastAPI()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_PUBLISHABLE_KEY = os.environ.get("SUPABASE_PUBLISHABLE_KEY")

MISSING_PREFIX = "missing: "

# Per-user cap on AI-checked questions per day. Best effort, in memory only:
# it resets whenever the server process restarts and is not shared across
# multiple server instances.
AI_CHECK_DAILY_LIMIT = 60
_ai_check_counts = {}


def _ai_check_disabled():
    return (
        os.environ.get("AI_CHECK_DISABLED") == "1"
        or not os.environ.get("GROQ_API_KEY")
        or not os.environ.get("GROQ_MODEL")
    )


def _ai_check_allowed(user_id):
    today = date.today()
    entry = _ai_check_counts.get(user_id)
    if entry is None or entry["date"] != today:
        entry = {"date": today, "count": 0}
        _ai_check_counts[user_id] = entry
    if entry["count"] >= AI_CHECK_DAILY_LIMIT:
        return False
    entry["count"] += 1
    return True


class _LLMCallErrorTracker:
    """Wraps groq_llm_call so main.py can tell a real AI error (timeout,
    exception, malformed JSON) apart from the AI cleanly saying "not met",
    without changing check_missing_with_ai's pure, fixed return shape."""

    def __init__(self, real_call):
        self._real_call = real_call
        self.errored = False

    def __call__(self, *args, **kwargs):
        try:
            raw = self._real_call(*args, **kwargs)
        except Exception:
            self.errored = True
            raise
        try:
            json.loads(raw)
        except (TypeError, ValueError):
            self.errored = True
        return raw


def _apply_ai_meaning_check(result, user_id):
    """If check_one failed only because an "includes" word is missing, ask
    the AI whether the answer says it another way, then re-verify in code.
    Only ever upgrades Fail to Pass when the AI's quote is confirmed to
    really appear in the answer."""
    if result["pass_fail"] != "Fail":
        return
    if not result["fail_reason"].startswith(MISSING_PREFIX):
        return
    if not result["app_answer"]:
        return
    if _ai_check_disabled():
        return
    if not _ai_check_allowed(user_id):
        return

    missing_item = result["fail_reason"][len(MISSING_PREFIX):]
    tracker = _LLMCallErrorTracker(groq_llm_call)
    ai_result = check_missing_with_ai(result["app_answer"], [missing_item], tracker)

    if ai_result["met"] and not ai_result["unmet"]:
        result["pass_fail"] = "Pass"
        result["fail_reason"] = ""
        result["match_note"] = "matched by meaning: '{}'".format(ai_result["met"][0]["quote"])
    elif tracker.errored:
        result["fail_reason"] = f"{result['fail_reason']} (AI check unavailable)"


class NotLoggedIn(Exception):
    pass


@app.exception_handler(NotLoggedIn)
def not_logged_in_handler(request: Request, exc: NotLoggedIn):
    return JSONResponse(status_code=401, content={"error": "not logged in"})


def _client_for_token(token: Optional[str] = None):
    """A Supabase client using the publishable key, with the user's access
    token attached so RLS applies. Never uses the secret/service key."""
    if not SUPABASE_URL or not SUPABASE_PUBLISHABLE_KEY:
        return None

    from supabase import create_client

    client = create_client(SUPABASE_URL, SUPABASE_PUBLISHABLE_KEY)
    if token:
        client.postgrest.auth(token)
    return client


def get_current_user(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.lower().startswith("bearer "):
        raise NotLoggedIn()
    token = authorization.split(" ", 1)[1].strip()
    if not token:
        raise NotLoggedIn()

    client = _client_for_token()
    if client is None:
        raise NotLoggedIn()

    try:
        user_response = client.auth.get_user(token)
    except Exception:
        raise NotLoggedIn()

    if not user_response or not user_response.user:
        raise NotLoggedIn()

    return user_response.user.id, token


@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/api/hello")
def hello():
    return {"status": "ok"}


@app.get("/api/config")
def get_config():
    return {
        "SUPABASE_URL": SUPABASE_URL,
        "SUPABASE_PUBLISHABLE_KEY": SUPABASE_PUBLISHABLE_KEY,
    }


class RunQuestionRequest(BaseModel):
    question: str
    app_address: str
    question_field: str
    answer_field: str
    good_answer_includes: str = ""
    global_wrong_text: str = ""
    run_id: Optional[str] = None
    question_id: Optional[str] = None


class CreateRunRequest(BaseModel):
    app_address: str
    question_field: str
    answer_field: str
    global_wrong_text: str = ""


@app.post("/api/runs")
def create_run(body: CreateRunRequest, user=Depends(get_current_user)):
    user_id, token = user
    client = _client_for_token(token)
    row = {
        "app_address": body.app_address,
        "question_field_name": body.question_field,
        "answer_field_name": body.answer_field,
        "global_wrong_text": body.global_wrong_text,
        "user_id": user_id,
    }
    result = client.table("runs").insert(row).execute()
    return {"id": result.data[0]["id"]}


@app.post("/api/run-question")
def run_question(body: RunQuestionRequest, user=Depends(get_current_user)):
    user_id, token = user

    result = check_one(
        question=body.question,
        app_address=body.app_address,
        question_field=body.question_field,
        answer_field=body.answer_field,
        good_answer_includes=body.good_answer_includes,
        global_wrong_text=body.global_wrong_text,
    )

    _apply_ai_meaning_check(result, user_id)

    if body.run_id:
        client = _client_for_token(token)
        try:
            if body.question_id:
                question_id = body.question_id
                client.table("questions").update(
                    {
                        "question_text": body.question,
                        "good_answer_includes": body.good_answer_includes,
                    }
                ).eq("id", question_id).execute()
            else:
                question_row = (
                    client.table("questions")
                    .insert(
                        {
                            "question_text": body.question,
                            "good_answer_includes": body.good_answer_includes,
                            "user_id": user_id,
                        }
                    )
                    .execute()
                )
                question_id = question_row.data[0]["id"]

            client.table("answers").insert(
                {
                    "run_id": body.run_id,
                    "question_id": question_id,
                    "app_answer": result["app_answer"],
                    "pass_fail": result["pass_fail"],
                    "fail_reason": result["fail_reason"],
                    "user_id": user_id,
                }
            ).execute()
            result["saved"] = True
            result["question_id"] = question_id
        except Exception:
            result["saved"] = False

    return result


@app.get("/api/runs/{run_id}")
def get_run(run_id: str, user=Depends(get_current_user)):
    _user_id, token = user
    client = _client_for_token(token)
    if client is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")

    try:
        run = client.table("runs").select("*").eq("id", run_id).execute()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach the database.")

    if not run.data:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_id}")

    try:
        answers = client.table("answers").select("*").eq("run_id", run_id).execute()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach the database.")

    return {"run": run.data[0], "answers": answers.data}


@app.get("/api/runs")
def list_runs(user=Depends(get_current_user)):
    _user_id, token = user
    client = _client_for_token(token)
    if client is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")

    try:
        runs = (
            client.table("runs")
            .select("id, created_at")
            .order("created_at", desc=True)
            .limit(20)
            .execute()
            .data
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach the database.")

    run_ids = [r["id"] for r in runs]
    counts = {}
    if run_ids:
        try:
            answers = (
                client.table("answers")
                .select("run_id, pass_fail")
                .in_("run_id", run_ids)
                .execute()
                .data
            )
        except Exception:
            answers = []
        for a in answers:
            c = counts.setdefault(a["run_id"], {"passed": 0, "total": 0})
            c["total"] += 1
            if a["pass_fail"] == "Pass":
                c["passed"] += 1

    return [
        {
            "id": r["id"],
            "created_at": r["created_at"],
            "passed": counts.get(r["id"], {"passed": 0, "total": 0})["passed"],
            "total": counts.get(r["id"], {"passed": 0, "total": 0})["total"],
        }
        for r in runs
    ]


@app.get("/api/compare")
def compare_runs(run_a: str, run_b: str, user=Depends(get_current_user)):
    _user_id, token = user
    client = _client_for_token(token)
    if client is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")

    try:
        run_a_row = client.table("runs").select("id").eq("id", run_a).execute()
        run_b_row = client.table("runs").select("id").eq("id", run_b).execute()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach the database.")

    if not run_a_row.data:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_a}")
    if not run_b_row.data:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_b}")

    try:
        answers_a = (
            client.table("answers").select("*").eq("run_id", run_a).order("created_at").execute().data
        )
        answers_b = (
            client.table("answers").select("*").eq("run_id", run_b).order("created_at").execute().data
        )
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach the database.")

    by_question_a = {a["question_id"]: a for a in answers_a}
    by_question_b = {b["question_id"]: b for b in answers_b}

    question_order = []
    seen = set()
    for a in answers_a:
        if a["question_id"] not in seen:
            question_order.append(a["question_id"])
            seen.add(a["question_id"])
    for b in answers_b:
        if b["question_id"] not in seen:
            question_order.append(b["question_id"])
            seen.add(b["question_id"])

    questions = {}
    if question_order:
        q_rows = (
            client.table("questions")
            .select("id, question_text")
            .in_("id", question_order)
            .execute()
            .data
        )
        questions = {q["id"]: q["question_text"] for q in q_rows}

    def side(answer):
        if not answer:
            return None
        return {
            "pass_fail": answer["pass_fail"],
            "fail_reason": answer.get("fail_reason"),
            "app_answer": answer.get("app_answer"),
        }

    rows = []
    fixed = broke = same = 0
    for question_id in question_order:
        a = by_question_a.get(question_id)
        b = by_question_b.get(question_id)

        if a and b:
            if a["pass_fail"] == "Fail" and b["pass_fail"] == "Pass":
                status = "Fixed"
                fixed += 1
            elif a["pass_fail"] == "Pass" and b["pass_fail"] == "Fail":
                status = "Broke"
                broke += 1
            else:
                status = "Same"
                same += 1
        elif a and not b:
            status = "Only in Run 1"
        else:
            status = "Only in Run 2"

        rows.append(
            {
                "question_id": question_id,
                "question_text": questions.get(question_id, ""),
                "run_a": side(a),
                "run_b": side(b),
                "status": status,
            }
        )

    def score(answers):
        total = len(answers)
        passed = sum(1 for x in answers if x["pass_fail"] == "Pass")
        return {"passed": passed, "total": total}

    return {
        "rows": rows,
        "summary": {
            "run_a_score": score(answers_a),
            "run_b_score": score(answers_b),
            "fixed": fixed,
            "broke": broke,
            "same": same,
        },
    }
