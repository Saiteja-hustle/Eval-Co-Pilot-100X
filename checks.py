import requests

TIMEOUT_SECONDS = 20


def check_one(
    question: str,
    app_address: str,
    question_field: str,
    answer_field: str,
    good_answer_includes: str = "",
    global_wrong_text: str = "",
) -> dict:
    try:
        response = requests.post(
            app_address,
            json={question_field: question},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.exceptions.Timeout:
        return _result(question, "", "Fail", "timed out")
    except requests.exceptions.RequestException:
        return _result(question, "", "Fail", "app error")

    if response.status_code != 200:
        return _result(question, "", "Fail", "app error")

    try:
        data = response.json()
    except ValueError:
        return _result(question, "", "Fail", "app error")

    answer = data.get(answer_field)
    if answer is None or not str(answer).strip():
        return _result(question, answer or "", "Fail", "empty answer")

    answer_text = str(answer)
    answer_lower = answer_text.lower()

    if global_wrong_text and global_wrong_text.lower() in answer_lower:
        return _result(question, answer_text, "Fail", "contains wrong text")

    required_words = [
        word.strip() for word in good_answer_includes.split(",") if word.strip()
    ]
    for word in required_words:
        if word.lower() not in answer_lower:
            return _result(question, answer_text, "Fail", f"missing: {word}")

    return _result(question, answer_text, "Pass", None)


def _result(question, app_answer, pass_fail, fail_reason):
    return {
        "question": question,
        "app_answer": app_answer,
        "pass_fail": pass_fail,
        "fail_reason": fail_reason,
    }
