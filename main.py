import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

from checks import check_one

load_dotenv()

app = FastAPI()

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY")

supabase = None
if SUPABASE_URL and SUPABASE_SERVICE_KEY:
    from supabase import create_client

    supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)


@app.get("/")
def home():
    return FileResponse("index.html")


@app.get("/api/hello")
def hello():
    return {"status": "ok"}


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
def create_run(body: CreateRunRequest):
    row = {
        "app_address": body.app_address,
        "question_field_name": body.question_field,
        "answer_field_name": body.answer_field,
        "global_wrong_text": body.global_wrong_text,
    }
    result = supabase.table("runs").insert(row).execute()
    return {"id": result.data[0]["id"]}


@app.post("/api/run-question")
def run_question(body: RunQuestionRequest):
    result = check_one(
        question=body.question,
        app_address=body.app_address,
        question_field=body.question_field,
        answer_field=body.answer_field,
        good_answer_includes=body.good_answer_includes,
        global_wrong_text=body.global_wrong_text,
    )

    if body.run_id:
        try:
            if body.question_id:
                question_id = body.question_id
                supabase.table("questions").update(
                    {
                        "question_text": body.question,
                        "good_answer_includes": body.good_answer_includes,
                    }
                ).eq("id", question_id).execute()
            else:
                question_row = (
                    supabase.table("questions")
                    .insert(
                        {
                            "question_text": body.question,
                            "good_answer_includes": body.good_answer_includes,
                        }
                    )
                    .execute()
                )
                question_id = question_row.data[0]["id"]

            supabase.table("answers").insert(
                {
                    "run_id": body.run_id,
                    "question_id": question_id,
                    "app_answer": result["app_answer"],
                    "pass_fail": result["pass_fail"],
                    "fail_reason": result["fail_reason"],
                }
            ).execute()
            result["saved"] = True
            result["question_id"] = question_id
        except Exception:
            result["saved"] = False

    return result


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = supabase.table("runs").select("*").eq("id", run_id).single().execute()
    answers = supabase.table("answers").select("*").eq("run_id", run_id).execute()
    return {"run": run.data, "answers": answers.data}


@app.get("/api/compare")
def compare_runs(run_a: str, run_b: str):
    if supabase is None:
        raise HTTPException(status_code=503, detail="Database is not configured.")

    try:
        run_a_row = supabase.table("runs").select("id").eq("id", run_a).execute()
        run_b_row = supabase.table("runs").select("id").eq("id", run_b).execute()
    except Exception:
        raise HTTPException(status_code=502, detail="Could not reach the database.")

    if not run_a_row.data:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_a}")
    if not run_b_row.data:
        raise HTTPException(status_code=404, detail=f"Run not found: {run_b}")

    try:
        answers_a = (
            supabase.table("answers").select("*").eq("run_id", run_a).order("created_at").execute().data
        )
        answers_b = (
            supabase.table("answers").select("*").eq("run_id", run_b).order("created_at").execute().data
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
            supabase.table("questions")
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
