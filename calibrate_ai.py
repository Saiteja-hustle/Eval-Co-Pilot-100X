"""Calibration script: runs the real Groq AI over labelled examples in
calibration_examples.json and prints how often check_missing_with_ai's
verdict agrees with the expected label.

Needs GROQ_API_KEY and GROQ_MODEL set in the environment (e.g. via .env).
Makes real network calls - not run as part of the automated test suite.

Usage:
    python3 calibrate_ai.py
"""

import json
import os
import sys

from dotenv import load_dotenv

from ai_check import check_missing_with_ai, groq_llm_call

load_dotenv()


def main():
    if not os.environ.get("GROQ_API_KEY") or not os.environ.get("GROQ_MODEL"):
        print("GROQ_API_KEY and GROQ_MODEL must be set (e.g. in .env) to run calibration.")
        sys.exit(1)

    with open("calibration_examples.json") as f:
        examples = json.load(f)

    agree = 0
    for i, example in enumerate(examples, start=1):
        answer = example["answer"]
        item = example["item"]
        expected_met = example["expected_met"]

        outcome = check_missing_with_ai(answer, [item], groq_llm_call)
        actual_met = any(m["item"] == item for m in outcome["met"])

        matched = actual_met == expected_met
        agree += int(matched)

        quote = next((m["quote"] for m in outcome["met"] if m["item"] == item), None)
        print(
            f"{i}. item={item!r} expected_met={expected_met} actual_met={actual_met} "
            f"quote={quote!r} -> {'AGREE' if matched else 'DISAGREE'}"
        )

    total = len(examples)
    print()
    print(f"Agreement: {agree} of {total} ({100 * agree / total:.0f}%)")


if __name__ == "__main__":
    main()
