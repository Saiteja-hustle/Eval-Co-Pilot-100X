from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel

from checks import check_one

app = FastAPI()


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


@app.post("/api/run-question")
def run_question(body: RunQuestionRequest):
    return check_one(
        question=body.question,
        app_address=body.app_address,
        question_field=body.question_field,
        answer_field=body.answer_field,
        good_answer_includes=body.good_answer_includes,
        global_wrong_text=body.global_wrong_text,
    )
