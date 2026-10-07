"""Builds the Markdown report from graded result rows."""

from collections import defaultdict
from statistics import median

from .grade import GRADED_FIELDS, escalation_counts, majority_baseline, tally

FIELD_TITLES = {
    "language": "Language",
    "category": "Category",
    "escalate": "Escalate or not",
    "reply_facts": "Reply states the policy fact",
}


def share(correct: int, total: int) -> str:
    return f"{correct}/{total} ({correct / total:.0%})" if total else "none graded"


def build_report(cases: list[dict], rows: list[dict], *, model: str, effort: str, date: str) -> str:
    graded = [row for row in rows if row.get("grade")]
    by_status: dict[str, int] = defaultdict(int)
    for row in rows:
        by_status[row["status"]] += 1
    not_graded = len(rows) - len(graded)
    other_model = sum(1 for row in graded if row["model_served"] != row["model_requested"])

    lines = [
        f"# Eval report: {model}",
        "",
        f"- Run on {date} with effort `{effort}`, {len(rows)} emails.",
        f"- Graded: {len(graded)}. Not graded: {not_graded} "
        f"(errors {by_status['error']}, refusals {by_status['refusal']}, truncated {by_status['truncated']}).",
        f"- Answered by another model than the one requested: {other_model}.",
        "",
        "## Accuracy",
        "",
        "| Field | Correct | Always answering the most common label |",
        "|---|---|---|",
    ]
    for name in GRADED_FIELDS:
        baseline = share(*majority_baseline(cases, name)) if name != "reply_facts" else "not applicable"
        lines.append(f"| {FIELD_TITLES[name]} | {share(*tally(graded, name))} | {baseline} |")

    counts = escalation_counts(cases, graded)
    lines += [
        "",
        "## Escalation",
        "",
        "| Outcome | Emails |",
        "|---|---|",
        f"| Should escalate and did | {counts['caught']} |",
        f"| Should escalate and did not | {counts['missed']} |",
        f"| Escalated without need | {counts['unnecessary']} |",
        f"| Correctly not escalated | {counts['correctly_left']} |",
        "",
        "## Category by language",
        "",
        "| Language | Correct |",
        "|---|---|",
    ]
    by_language = defaultdict(list)
    for row in graded:
        by_language[row["tags"][0]].append(row)
    for language in sorted(by_language):
        lines.append(f"| {language} | {share(*tally(by_language[language], 'category'))} |")

    costs = [row["cost_usd"] for row in graded if row["cost_usd"] is not None]
    latencies = sorted(row["latency_s"] for row in graded)
    lines += ["", "## Cost and speed", ""]
    if costs:
        lines.append(
            f"- Cost per 1,000 emails: ${sum(costs) / len(costs) * 1000:.2f} (measured total ${sum(costs):.4f})."
        )
    if latencies:
        p90 = latencies[min(len(latencies) - 1, int(len(latencies) * 0.9))]
        lines.append(f"- Time per email: median {median(latencies):.1f} s, 90th percentile {p90:.1f} s.")
        tokens_in = median(
            row["usage"]["input_tokens"]
            + row["usage"]["cache_read_input_tokens"]
            + row["usage"]["cache_creation_input_tokens"]
            for row in graded
        )
        tokens_out = median(row["usage"]["output_tokens"] for row in graded)
        lines.append(f"- Tokens per email, median: {tokens_in:.0f} in, {tokens_out:.0f} out.")

    expected = {case["id"]: case["expected"] for case in cases}
    wrong = [
        (row["id"], name, expected[row["id"]].get(name, "policy fact"), row["output"].get(name, "missing"))
        for row in graded
        for name in GRADED_FIELDS
        if row["grade"][name] is False
    ]
    lines += ["", "## Wrong answers", ""]
    if wrong:
        lines += ["| Email | Field | Expected | Got |", "|---|---|---|---|"]
        lines += [f"| {case_id} | {FIELD_TITLES[name]} | {want} | {got} |" for case_id, name, want, got in wrong]
    else:
        lines.append("None.")

    return "\n".join(lines) + "\n"
