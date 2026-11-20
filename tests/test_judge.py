from collections import Counter

import pytest

from necro.extract import extract
from necro.fetch import load_fixture
from necro.judge import judge


@pytest.fixture(scope="module")
def chart():
    return extract(load_fixture("US7669123B2"))


def statuses(chart, impl, level):
    return Counter(v.status for v in judge(chart, impl, level))


def test_reference_passes_v1_and_kills_every_mutant(chart):
    vs = judge(chart, "impls.us7669123.feed_engine", "v1")
    assert all(v.status == "PASS" for v in vs), [(v.element.id, v.status, v.note) for v in vs]
    assert all(v.mutants[0] == v.mutants[1] for v in vs)
    assert sum(v.mutants[1] for v in vs) > 0


def test_crud_control_rejected_by_both(chart):
    for level in ("v0", "v1"):
        assert statuses(chart, "impls.crud_baseline.app", level)["PASS"] <= 1


def test_cheater_fools_v0_but_not_v1(chart):
    assert statuses(chart, "impls.cheater.app", "v0") == Counter({"PASS": 13})
    v1 = statuses(chart, "impls.cheater.app", "v1")
    assert v1["TRACE_MISS"] > 0 and v1["MUTANT_SURVIVED"] > 0
    assert v1["PASS"] <= 1


def test_mutation_restores_original_functions(chart):
    import inspect
    import sys
    from necro import registry

    judge(chart, "impls.us7669123.feed_engine", "v1")
    mod = sys.modules["impls.us7669123.feed_engine"]
    for fns in registry.IMPLS.values():
        for f in fns:
            if inspect.isfunction(f):
                assert getattr(mod, f.__name__) is f, f"{f.__name__} left mutated"
