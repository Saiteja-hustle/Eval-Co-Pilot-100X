import os
from typing import Optional

from dotenv import load_dotenv
from fastapi import FastAPI
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
        except Exception:
            result["saved"] = False

    return result


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = supabase.table("runs").select("*").eq("id", run_id).single().execute()
    answers = supabase.table("answers").select("*").eq("run_id", run_id).execute()
    return {"run": run.data, "answers": answers.data}
