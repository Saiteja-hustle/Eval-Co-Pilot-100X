from checks import check_one

APP_ADDRESS = "https://knowledge-retriever-mvp.vercel.app/api/ans_fact"
QUESTION_FIELD = "text"
ANSWER_FIELD = "answer"


def run_case(label, expected_pass_fail, expected_reason_contains, **kwargs):
    result = check_one(**kwargs)
    actual_pass_fail = result["pass_fail"]
    actual_reason = result["fail_reason"]

    ok = actual_pass_fail == expected_pass_fail
    if expected_reason_contains:
        ok = ok and expected_reason_contains in actual_reason

    expected_str = f"{expected_pass_fail}" + (f" ({expected_reason_contains})" if expected_reason_contains else "")
    actual_str = f"{actual_pass_fail} ({actual_reason})" if actual_reason else actual_pass_fail

    print(f"{label}: expected={expected_str} actual={actual_str} app_answer={result['app_answer']!r} -> {'OK' if ok else 'MISMATCH'}")


run_case(
    "1. Birch daylight question, includes 3, 12",
    "Pass", None,
    question="What is the daylight requirement for Birch?",
    app_address=APP_ADDRESS,
    question_field=QUESTION_FIELD,
    answer_field=ANSWER_FIELD,
    good_answer_includes="12",
    global_wrong_text="",
)

run_case(
    "2. fresh air question, global wrong text",
    "Fail", "contains wrong text",
    question="fresh air",
    app_address=APP_ADDRESS,
    question_field=QUESTION_FIELD,
    answer_field=ANSWER_FIELD,
    good_answer_includes="",
    global_wrong_text="No reliable answer found",
)

run_case(
    "3. any question, includes 99999",
    "Fail", "missing: 99999",
    question="What is the daylight requirement for Birch?",
    app_address=APP_ADDRESS,
    question_field=QUESTION_FIELD,
    answer_field=ANSWER_FIELD,
    good_answer_includes="99999",
    global_wrong_text="",
)

run_case(
    "4. wrong app address",
    "Fail", "app error",
    question="What is the daylight requirement for Birch?",
    app_address="https://knowledge-retriever-mvp.vercel.app/api/does-not-exist",
    question_field=QUESTION_FIELD,
    answer_field=ANSWER_FIELD,
    good_answer_includes="",
    global_wrong_text="",
)
