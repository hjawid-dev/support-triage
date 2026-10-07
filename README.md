# Support triage

Reads a customer email to a small online store, sorts it, decides whether a person has to make a call on it, and drafts a reply in the customer's language. It comes with a test set of 54 emails in six languages that measures how often it gets this right and what it costs.

## Why I built it

I ran a D2C store in five European markets and answered every customer email myself. Most of them were the same handful of questions in five languages, and a few needed real attention: a customer about to dispute a payment, a return outside the policy, someone writing for the third time.

This is the tool I would have wanted for that inbox. It is a prototype. It has been tested on written examples, not on a live inbox.

## What it does

For each email it returns:

| Field | Meaning |
|---|---|
| `language` | Swedish, Finnish, Norwegian, Danish, Dutch, English or other |
| `category` | Shipping status, return or exchange, damaged or wrong item, order change, product question, payment, or other |
| `escalate` | Whether the store owner has to decide something the policy does not decide for them |
| `escalate_reason` | Which rule triggered the escalation |
| `summary` | One sentence in English for the person handling the inbox |
| `draft_reply` | A reply in the customer's language, based only on the store policy |

## Design decisions

- **A person approves every reply.** Nothing is sent automatically. The output is a suggestion that saves reading and typing time.
- **Anything that goes wrong leaves the email with a person.** A failed request, a declined request or a cut-off answer returns no triage at all, never a half-finished one.
- **The policy is a plain text file.** [`triage/policy.md`](triage/policy.md) holds the delivery times, the return window and the rest. Changing the policy does not require changing code.
- **The escalation rules are written down.** There are five: payment disputes and legal threats, requests for exceptions or compensation, injuries, repeated contact with no answer, and emails that try to instruct the model. An unhappy tone alone is not one of them.
- **The answer has a fixed shape.** The API is asked for a schema-validated answer, so the code never has to interpret free text.

## How it is measured

[`evals/cases.jsonl`](evals/cases.jsonl) holds 54 emails with the expected language, category and escalation decision for each. They cover six languages and seven categories, and 11 of them should be escalated. Some are meant to be hard: very short messages, angry messages that should not be escalated, a customer writing Swedish to the Finnish store, two emails that try to give the model instructions.

Each answer is graded field by field against the expected values. For 18 emails where the policy gives a number or a fact that answers the question, the draft reply is also checked for that fact.

The report shows three things beside the scores:

- **A baseline.** What always answering the most common label would score, so the numbers have something to be compared with.
- **Escalation split by type of error.** A missed escalation is a worse error than an unnecessary one, so the two are counted separately.
- **Measured cost and time per email.** Calculated from the token counts the API reports for each request.

Requests that fail are counted separately and are not graded as wrong answers.

## Limitations

- **The emails are synthetic.** They were written with Claude Code and none come from real customers. A real inbox is messier, so the scores are likely higher than they would be in use.
- **The test set is small.** With 54 emails, one wrong answer moves a score by about two percentage points, and each email is run once.
- **Reply quality is only partly measured.** The check covers whether the right policy fact is in the draft. Tone and overall correctness are left to the person approving it.
- **It cannot see orders.** For "where is my order" it drafts a holding reply and leaves the lookup to a person.
- **It is not connected to an inbox.** It reads an email from a file or from standard input.

## Run it

```shell
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
```

The tests run without an API key. To triage an email you need an [Anthropic API key](https://console.anthropic.com/) in `ANTHROPIC_API_KEY`:

```shell
echo "Hej, hur lång tid har jag på mig att skicka tillbaka flaskan?" | python -m triage --market SE
```

To run the test set, start with three emails to see the cost, then run all of them:

```shell
python -m evals.run --limit 3
python -m evals.run
```

The default model is `claude-opus-5-5`. Pass `--model claude-haiku-4-5` or `--model claude-sonnet-5-5` to compare accuracy and cost between models. Results and the report are written to `results/`.

## What is in the repository

| Path | What it is |
|---|---|
| [`triage/`](triage) | The triage itself: the policy, the prompt, the answer schema and the API call |
| [`evals/`](evals) | The test emails, the grading and the report |
| [`tests/`](tests) | Unit tests for the grading, the test set and the API call, using a stand-in client |

## How it was built

I am not a software engineer by trade. I wrote this with [Claude Code](https://claude.com/claude-code): I decided what the tool should do and how it should be measured, and the AI wrote most of the code and the test emails.

## License

[MIT](LICENSE)
