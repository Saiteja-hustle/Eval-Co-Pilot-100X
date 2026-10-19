import requests


def check_one(question, app_address, question_field, answer_field,
              good_answer_includes, global_wrong_text):
    try:
        response = requests.post(
            app_address,
            json={question_field: question},
            timeout=20,
        )
    except requests.exceptions.Timeout:
        return {"app_answer": "", "pass_fail": "Fail", "fail_reason": "timed out"}
    except requests.exceptions.RequestException:
        return {"app_answer": "", "pass_fail": "Fail", "fail_reason": "app error"}

    if response.status_code != 200:
        return {"app_answer": "", "pass_fail": "Fail", "fail_reason": "app error"}

    try:
        data = response.json()
    except ValueError:
        return {"app_answer": "", "pass_fail": "Fail", "fail_reason": "app error"}

    app_answer = data.get(answer_field, "")

    if not app_answer:
        return {"app_answer": app_answer, "pass_fail": "Fail", "fail_reason": "empty answer"}

    answer_lower = app_answer.lower()

    if good_answer_includes:
        words = [w.strip() for w in good_answer_includes.split(",") if w.strip()]
        for word in words:
            if word.lower() not in answer_lower:
                return {"app_answer": app_answer, "pass_fail": "Fail", "fail_reason": f"missing: {word}"}

    if global_wrong_text and global_wrong_text.lower() in answer_lower:
        return {"app_answer": app_answer, "pass_fail": "Fail", "fail_reason": "contains wrong text"}

    return {"app_answer": app_answer, "pass_fail": "Pass", "fail_reason": ""}
