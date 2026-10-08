# Support triage

Reads a customer email to a small online store, sorts it, decides whether a person has to make a call on it, and drafts a reply in the customer's language. It comes with a test set of 68 emails, in the five market languages and English, that measures how often it gets this right and what it costs, and the results for two models.

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

[`evals/cases.jsonl`](evals/cases.jsonl) holds 68 emails with the expected language, category and escalation decision for each. They cover the five market languages plus English and seven categories, and 15 of them should be escalated.

Fourteen of the emails are marked as hard. They were written to be easy to get wrong, usually as one half of a pair:

- a return after three weeks, which is fine, next to one after six weeks, which is not
- a customer ordering for the second time, which is not the same as writing for the second time
- a polite request for compensation
- an instruction to the model hidden in an email signature
- an email in German, a language the store does not support

Each answer is graded field by field against the expected values. For 20 emails where the policy gives a number or a fact that answers the question, the draft reply is also checked for that fact.

The report shows three things beside the scores:

- **A baseline.** What always answering the most common label would score, so the numbers have something to be compared with.
- **Escalation split by type of error.** A missed escalation is a worse error than an unnecessary one, so the two are counted separately.
- **Measured cost and time per email.** Calculated from the token counts the API reports for each request.

Requests that fail are counted separately and are not graded as wrong answers.

## Results

Run on 7 October 2026 with the same prompt for both models. The full reports are in [`results/`](results), with every answer and draft in the `results.jsonl` files.

| | `claude-opus-5-5` | `claude-haiku-4-5` | Always the most common label |
|---|---|---|---|
| Language | 68 of 68 | 57 of 68 | 13 of 68 |
| Category | 64 of 64 | 64 of 64 | 12 of 64 |
| Escalate or not | 68 of 68 | 65 of 68 | 53 of 68 |
| Reply states the policy fact | 20 of 20 | 18 of 20 | not applicable |
| Escalations caught | 15 of 15 | 12 of 15 | |
| Hard emails with every field correct | 14 of 14 | 10 of 14 | |
| Time per email, median | 3.5 s | 3.0 s | |
| Cost per 1,000 emails | $6.26 | $2.40 | |

Four emails are not graded on category, because more than one answer is defensible. That is why that row has 64.

Opus got everything right, including the hard emails. Haiku sorted every email into the right category, but made three kinds of mistakes:

- **It answered in the wrong language.** All 11 language errors were emails written in English to a non-English storefront. Haiku labelled them with the storefront's language, and in 10 of the 11 it wrote the reply in that language too.
- **It missed 3 of 15 escalations.** Two were the emails that contain instructions to the model. Haiku did not follow the instructions, but it did not flag the emails either. The third was a lid that cracked two months after purchase, where Haiku told the customer no instead of leaving the decision to a person.
- **It skipped a step in the policy.** One draft promised a replacement without asking for the photo the policy requires.

Neither model escalated an email that did not need it.

**What I take from this:** Opus stays the default. Haiku is cheaper, but a missed escalation is the expensive error here, and replying to a customer in the wrong language is a visible one. I have not tuned the prompt for Haiku. The language mistake in particular looks fixable with one more sentence in the instructions, which would be the next thing to try.

**About the cost figures:** the Opus figure is for emails processed back to back, when the instructions are read from the prompt cache. In a first trial of three emails with nothing cached, Opus cost $16.23 per 1,000. A small inbox where emails arrive minutes apart is closer to that. Nothing was cached in the Haiku run, so its figure does not depend on timing.

## Limitations

- **The emails are synthetic.** They were written with Claude Code and none come from real customers. A real inbox is messier, so the scores are likely higher than they would be in use.
- **The test set is small.** With 68 emails, one wrong answer moves a score by about one and a half percentage points. Each email is run once per model, so I do not know how much the results vary between runs.
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

The tests run without an API key. The same tests run on every push, together with a linter (`ruff`) and a type checker (`mypy`). To triage an email you need an [Anthropic API key](https://console.anthropic.com/) in `ANTHROPIC_API_KEY`:

```shell
echo "Hej, hur lång tid har jag på mig att skicka tillbaka flaskan?" | python -m triage --market SE
```

To run the test set, start with three emails to see the cost, then run all of them:

```shell
python -m evals.run --limit 3
python -m evals.run
```

The default model is `claude-opus-5-5`. Pass `--model claude-haiku-4-5` or `--model claude-sonnet-5-5` to run another one. Results and the report are written to `results/`. Add `--rebuild` to grade the saved answers again without calling the API, for example after changing the grading.

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
