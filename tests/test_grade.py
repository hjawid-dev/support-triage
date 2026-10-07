from collections import Counter

from evals.grade import GRADED_FIELDS, escalation_counts, grade, load_cases, majority_baseline, tally
from evals.report import build_report

CASES = load_cases()


def make_rows(outputs: dict) -> list[dict]:
    rows = []
    for case in CASES:
        output = outputs[case["id"]]
        rows.append(
            {
                "id": case["id"],
                "tags": case["tags"],
                "status": "ok" if output else "error",
                "model_requested": "claude-opus-5-5",
                "model_served": "claude-opus-5-5" if output else None,
                "usage": {
                    "input_tokens": 900,
                    "output_tokens": 200,
                    "cache_read_input_tokens": 0,
                    "cache_creation_input_tokens": 0,
                },
                "cost_usd": 0.0076 if output else None,
                "latency_s": 2.0,
                "output": output,
                "grade": grade(case, output),
            }
        )
    return rows


def perfect_output(case: dict) -> dict:
    """An answer that matches the labels. The reply simply repeats the required patterns' text."""
    facts = {
        r"\b30\b": "30",
        r"\b12\b": "12",
        r"\b24\b": "24",
        r"\b5\b": "5",
        r"\b500\b": "500",
        r"\b750\b": "750",
        r"\bhand": "by hand",
    }
    reply = " ".join(facts.get(pattern, pattern.split("|")[0]) for pattern in case["reply_must_match"])
    return {**case["expected"], "category": case["expected"]["category"] or "other", "draft_reply": reply}


def test_perfect_answers_score_full_marks():
    rows = make_rows({case["id"]: perfect_output(case) for case in CASES})
    for name in GRADED_FIELDS:
        correct, graded = tally(rows, name)
        assert correct == graded > 0, name


def test_constant_answer_scores_exactly_the_baseline():
    most_common = {
        name: Counter(c["expected"][name] for c in CASES if c["expected"][name] is not None).most_common(1)[0][0]
        for name in ("language", "category", "escalate")
    }
    rows = make_rows({case["id"]: {**most_common, "draft_reply": ""} for case in CASES})
    for name in ("language", "category", "escalate"):
        assert tally(rows, name) == majority_baseline(CASES, name)
    assert tally(rows, "reply_facts")[0] == 0


def test_failed_request_is_not_graded_as_wrong():
    assert grade(CASES[0], None) is None
    outputs = {case["id"]: perfect_output(case) for case in CASES}
    outputs[CASES[0]["id"]] = None
    rows = make_rows(outputs)
    correct, graded = tally(rows, "language")
    assert correct == graded == len(CASES) - 1


def test_ungraded_category_is_skipped():
    injection = next(case for case in CASES if case["expected"]["category"] is None)
    result = grade(
        injection,
        {"language": injection["expected"]["language"], "category": "other", "escalate": True, "draft_reply": ""},
    )
    assert result["category"] is None
    assert result["escalate"] is True


def test_reply_fact_must_be_a_whole_number():
    case = next(case for case in CASES if case["reply_must_match"] == [r"\b30\b"])
    base = {**case["expected"]}
    assert grade(case, {**base, "draft_reply": "Du har 30 dagar på dig."})["reply_facts"] is True
    assert grade(case, {**base, "draft_reply": "Du har 130 dagar på dig."})["reply_facts"] is False
    assert grade(case, {**base, "draft_reply": ""})["reply_facts"] is False


def test_escalation_counts_separate_missed_from_unnecessary():
    outputs = {case["id"]: {**perfect_output(case), "escalate": False} for case in CASES}
    counts = escalation_counts(CASES, make_rows(outputs))
    assert counts["caught"] == 0 and counts["unnecessary"] == 0
    assert counts["missed"] == sum(case["expected"]["escalate"] for case in CASES)


def test_report_lists_wrong_answers_and_counts_failures():
    outputs = {case["id"]: perfect_output(case) for case in CASES}
    outputs["sv-01"] = {**outputs["sv-01"], "category": "other"}
    outputs["sv-02"] = None
    report = build_report(CASES, make_rows(outputs), model="claude-opus-5-5", effort="low", date="2026-01-01")
    assert "| sv-01 | Category | shipping_status | other |" in report
    assert "Not graded: 1 (errors 1" in report
    assert "Cost per 1,000 emails: $7.60" in report
    standard = sum("hard" not in case["tags"] for case in CASES) - 1  # sv-02 failed and is not graded
    hard = sum("hard" in case["tags"] for case in CASES)
    assert f"| Standard | {standard - 1}/{standard} " in report
    assert f"| Hard | {hard}/{hard} (100%) |" in report
