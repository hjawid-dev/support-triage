"""Grading for the triage eval. Pure functions, no API calls."""

import json
import re
from collections import Counter
from pathlib import Path

CASES_PATH = Path(__file__).parent / "cases.jsonl"

LABEL_FIELDS = ("language", "category", "escalate")
GRADED_FIELDS = LABEL_FIELDS + ("reply_facts",)


def load_cases(path: Path = CASES_PATH) -> list[dict]:
    with open(path, encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def grade(case: dict, output: dict | None) -> dict | None:
    """Per-field result for one case: True, False, or None when the field is not graded.

    Returns None when there is no output at all. A request that failed is not a wrong answer
    and is counted separately.
    """
    if output is None:
        return None

    expected = case["expected"]
    grades: dict = {}
    for name in LABEL_FIELDS:
        grades[name] = None if expected[name] is None else output.get(name) == expected[name]

    patterns = case["reply_must_match"]
    reply = output.get("draft_reply", "")
    grades["reply_facts"] = all(re.search(pattern, reply, re.IGNORECASE) for pattern in patterns) if patterns else None
    return grades


def tally(rows: list[dict], name: str) -> tuple[int, int]:
    """(correct, graded) for one field over all rows that have a grade for it."""
    values = [row["grade"][name] for row in rows if row.get("grade") and row["grade"][name] is not None]
    return sum(values), len(values)


def majority_baseline(cases: list[dict], name: str) -> tuple[int, int]:
    """(correct, graded) for always answering the most common label."""
    labels = [case["expected"][name] for case in cases if case["expected"][name] is not None]
    return Counter(labels).most_common(1)[0][1], len(labels)


def escalation_counts(cases: list[dict], rows: list[dict]) -> dict:
    expected = {case["id"]: case["expected"]["escalate"] for case in cases}
    counts = {"caught": 0, "missed": 0, "unnecessary": 0, "correctly_left": 0}
    for row in rows:
        if not row.get("grade"):
            continue
        should, did = expected[row["id"]], row["output"]["escalate"]
        if should and did:
            counts["caught"] += 1
        elif should:
            counts["missed"] += 1
        elif did:
            counts["unnecessary"] += 1
        else:
            counts["correctly_left"] += 1
    return counts
