"""Runs every eval email through the triage and writes results and a report.

python -m evals.run --limit 3        # small paid trial first
python -m evals.run                  # all emails, default model
python -m evals.run --model claude-haiku-4-5
python -m evals.run --model claude-haiku-4-5 --rebuild   # regrade saved answers, no API calls
"""

import argparse
import json
from concurrent.futures import ThreadPoolExecutor
from datetime import date
from pathlib import Path

import anthropic

from triage.classify import make_client, triage_email
from triage.models import DEFAULT_MODEL, MODELS, cost_usd
from triage.schema import Email

from .grade import grade, load_cases
from .report import build_report

RESULTS_DIR = Path(__file__).parent.parent / "results"


def run_case(client: anthropic.Anthropic, case: dict, model: str, effort: str) -> dict:
    email = Email(market=case["market"], subject=case["subject"], body=case["body"])
    result = triage_email(client, email, model=model, effort=effort)
    output = result.triage.model_dump(mode="json") if result.triage else None
    return {
        "id": case["id"],
        "tags": case["tags"],
        "status": result.status,
        "error": result.error,
        "model_requested": result.model_requested,
        "model_served": result.model_served,
        "usage": result.usage,
        # Priced at the model that answered, which can differ after a fallback.
        "cost_usd": cost_usd(result.model_served or model, result.usage) if result.usage else None,
        "latency_s": round(result.latency_s, 2),
        "output": output,
        "grade": grade(case, output),
    }


def write_run(out_dir: Path, cases: list[dict], rows: list[dict], run: dict) -> None:
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "results.jsonl", "w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    (out_dir / "run.json").write_text(json.dumps(run, indent=2) + "\n", encoding="utf-8")
    report = build_report(cases, rows, model=run["model"], effort=run["effort"], date=run["date"])
    (out_dir / "report.md").write_text(report, encoding="utf-8")
    print(report)
    print(f"Saved to {out_dir}")


def rebuild(out_dir: Path, cases: list[dict]) -> None:
    """Regrade and reprice the saved answers of an earlier run. Makes no API calls."""
    by_id = {case["id"]: case for case in cases}
    run = json.loads((out_dir / "run.json").read_text(encoding="utf-8"))
    with open(out_dir / "results.jsonl", encoding="utf-8") as handle:
        rows = [json.loads(line) for line in handle if line.strip()]
    for row in rows:
        row["grade"] = grade(by_id[row["id"]], row["output"])
        row["cost_usd"] = cost_usd(row["model_served"] or run["model"], row["usage"]) if row["usage"] else None
    write_run(out_dir, [by_id[row["id"]] for row in rows], rows, run)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the triage eval. Every run makes paid API calls.")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(MODELS))
    parser.add_argument("--effort", default="low", choices=["low", "medium", "high"])
    parser.add_argument("--limit", type=int, help="Only run the first N emails.")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--rebuild", action="store_true", help="Regrade the saved answers instead of calling the API.")
    args = parser.parse_args()

    cases = load_cases()[: args.limit]
    # A trial run gets its own folder so it does not overwrite a full run.
    out_dir = RESULTS_DIR / (f"{args.model}-first-{args.limit}" if args.limit else args.model)
    if args.rebuild:
        rebuild(out_dir, cases)
        return

    client = make_client()
    with ThreadPoolExecutor(max_workers=args.workers) as pool:
        rows = list(pool.map(lambda case: run_case(client, case, args.model, args.effort), cases))

    # Haiku has no effort setting, so the report should not claim one was used.
    effort = args.effort if MODELS[args.model].supports_effort else "not available for this model"
    write_run(out_dir, cases, rows, {"model": args.model, "effort": effort, "date": date.today().isoformat()})


if __name__ == "__main__":
    main()
