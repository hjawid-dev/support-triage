"""Triage one email from a file or from standard input.

python -m triage email.txt --market SE --subject "Where is my order?"
"""

import argparse
import sys

from .classify import make_client, triage_email
from .models import DEFAULT_MODEL, MODELS
from .schema import Email


def main() -> int:
    parser = argparse.ArgumentParser(description="Triage one customer email.")
    parser.add_argument("file", nargs="?", help="Text file with the email body. Reads standard input when omitted.")
    parser.add_argument("--market", default="SE", help="Storefront the email was sent to, for example SE or NL.")
    parser.add_argument("--subject", default="")
    parser.add_argument("--model", default=DEFAULT_MODEL, choices=sorted(MODELS))
    args = parser.parse_args()

    if args.file:
        with open(args.file, encoding="utf-8") as handle:
            body = handle.read()
    else:
        body = sys.stdin.read()

    result = triage_email(
        make_client(),
        Email(market=args.market, subject=args.subject, body=body.strip()),
        model=args.model,
    )
    if result.triage is None:
        print(f"Not triaged ({result.status}): {result.error or 'no output'}", file=sys.stderr)
        return 1

    triage = result.triage
    print(f"Language:  {triage.language.value}")
    print(f"Category:  {triage.category.value}")
    print(f"Escalate:  {'yes, ' + triage.escalate_reason if triage.escalate else 'no'}")
    print(f"Summary:   {triage.summary}")
    print(f"\n{triage.draft_reply}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
