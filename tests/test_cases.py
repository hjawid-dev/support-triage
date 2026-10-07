"""Checks that the eval emails themselves are well-formed."""

import re
from collections import Counter

from evals.grade import load_cases
from triage.schema import Category, Email, Language

CASES = load_cases()


def test_ids_and_bodies_are_unique():
    assert len({case["id"] for case in CASES}) == len(CASES)
    assert len({case["body"] for case in CASES}) == len(CASES)


def test_labels_are_valid():
    languages = {language.value for language in Language}
    categories = {category.value for category in Category}
    for case in CASES:
        expected = case["expected"]
        assert expected["language"] in languages, case["id"]
        assert expected["category"] is None or expected["category"] in categories, case["id"]
        assert isinstance(expected["escalate"], bool), case["id"]
        Email(market=case["market"], subject=case["subject"], body=case["body"])


def test_reply_patterns_compile():
    for case in CASES:
        for pattern in case["reply_must_match"]:
            re.compile(pattern)


def test_first_tag_is_the_language():
    for case in CASES:
        assert case["tags"][0] == case["expected"]["language"], case["id"]


def test_every_language_and_category_is_covered():
    languages = Counter(case["expected"]["language"] for case in CASES)
    categories = Counter(case["expected"]["category"] for case in CASES if case["expected"]["category"])
    assert set(languages) == {"sv", "fi", "no", "da", "nl", "en"}
    assert min(languages.values()) >= 8
    assert set(categories) == {category.value for category in Category}
    assert min(categories.values()) >= 5


def test_both_escalation_outcomes_are_well_represented():
    escalate = Counter(case["expected"]["escalate"] for case in CASES)
    assert escalate[True] >= 10
    assert escalate[False] >= 10
