import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from utils.rule_based_insert_print import rule_based_instrument_method


ROOT = Path(__file__).resolve().parents[1]
CORPUS_PATH = ROOT / "data" / "bug_info" / "bug_info.json"
REPRESENTATIVE_BUGS = [
    "Chart-1",
    "Closure-17",
    "Closure-61",
    "Csv-10",
    "Gson-13",
    "Lang-61",
    "Math-26",
    "Math-84",
    "Math-86",
]


def load_corpus():
    return json.loads(CORPUS_PATH.read_text(encoding="utf-8"))


def instrument(source: str) -> str:
    return rule_based_instrument_method(
        SimpleNamespace(buggy_method=source),
        "// START_DEBUG",
        "// END_DEBUG",
    )


@pytest.mark.parametrize("bug_id", REPRESENTATIVE_BUGS)
def test_representative_repository_method_round_trips_through_javaparser(bug_id):
    source = load_corpus()[bug_id]["buggy"]

    result = instrument(source)

    assert result.strip()
    assert "// START_DEBUG" in result


@pytest.mark.full_corpus
@pytest.mark.skipif(
    os.environ.get("DEBUGREPAIR_FULL_CORPUS") != "1",
    reason="set DEBUGREPAIR_FULL_CORPUS=1 to run all 483 Java methods",
)
def test_every_repository_method_round_trips_through_javaparser():
    failures = []
    corpus = load_corpus()

    for bug_id, record in corpus.items():
        source = (record.get("buggy") or "").strip()
        if not source:
            continue
        try:
            instrument(source)
        except Exception as exc:
            failures.append(f"{bug_id}: {type(exc).__name__}: {exc}")

    assert len(corpus) == 483
    assert failures == [], "\n" + "\n\n".join(failures)
