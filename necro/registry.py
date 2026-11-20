"""How an implementation declares which claim elements it covers.

    @implements("C1.E2", "C16.E2")
    def store_activity(...): '''Store the activity in the database.'''

    @check("C1.E2")
    def _(): ...behavioural assertion against the real code...

The judge only trusts a mapping when the element has an implementer, a check,
the check passes, and the implementer actually talks about the element.
"""

from __future__ import annotations

import importlib
import sys
from collections import defaultdict
from typing import Callable

IMPLS: dict[str, list[Callable]] = defaultdict(list)
CHECKS: dict[str, list[Callable]] = defaultdict(list)


def implements(*eids: str):
    def deco(fn):
        for e in eids:
            IMPLS[e].append(fn)
        fn.__necro_elements__ = eids
        return fn
    return deco


def check(*eids: str):
    def deco(fn):
        for e in eids:
            CHECKS[e].append(fn)
        return fn
    return deco


def load(module: str) -> tuple[dict, dict]:
    IMPLS.clear()
    CHECKS.clear()
    if module in sys.modules:
        importlib.reload(sys.modules[module])  # re-run decorators after clear()
    else:
        importlib.import_module(module)
    return dict(IMPLS), dict(CHECKS)
