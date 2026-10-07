# Eval report: claude-haiku-4-5

- Run on 2026-10-07, 68 emails. Effort setting: not available for this model.
- Graded: 68. Not graded: 0 (errors 0, refusals 0, truncated 0).
- Answered by another model than the one requested: 0.

## Accuracy

| Field | Correct | Always answering the most common label |
|---|---|---|
| Language | 57/68 (84%) | 13/68 (19%) |
| Category | 64/64 (100%) | 12/64 (19%) |
| Escalate or not | 65/68 (96%) | 53/68 (78%) |
| Reply states the policy fact | 18/20 (90%) | not applicable |

## Escalation

| Outcome | Emails |
|---|---|
| Should escalate and did | 12 |
| Should escalate and did not | 3 |
| Escalated without need | 0 |
| Correctly not escalated | 53 |

## Category by language

| Language | Correct |
|---|---|
| da | 11/11 (100%) |
| en | 10/10 (100%) |
| fi | 9/9 (100%) |
| nl | 11/11 (100%) |
| no | 9/9 (100%) |
| other | 1/1 (100%) |
| sv | 13/13 (100%) |

## Emails with every field correct

| Emails | Correct |
|---|---|
| Standard | 46/54 (85%) |
| Hard | 10/14 (71%) |

## Cost and speed

- Cost per 1,000 emails: $2.40 (measured total $0.1629).
- Time per email: median 3.0 s, 90th percentile 3.8 s.
- Tokens per email, median: 1674 in, 142 out.

## Wrong answers

| Email | Field | Expected | Got |
|---|---|---|---|
| en-01 | Language | en | nl |
| en-02 | Language | en | sv |
| en-03 | Language | en | da |
| en-03 | Reply states the policy fact | policy fact | missing |
| en-04 | Language | en | no |
| en-05 | Language | en | fi |
| en-05 | Reply states the policy fact | policy fact | missing |
| en-06 | Language | en | sv |
| en-08 | Language | en | da |
| en-09 | Language | en | sv |
| en-09 | Escalate or not | True | False |
| da-10 | Escalate or not | True | False |
| en-10 | Language | en | no |
| en-11 | Language | en | da |
| en-11 | Escalate or not | True | False |
| en-12 | Language | en | sv |
