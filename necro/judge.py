"""The judge: map every canonical claim element to code, or reject the build.

For each element it needs:
  1. at least one function decorated @implements(element),
  2. at least one @check(element) that passes against the real code,
  3. grounding: the implementer's name + docstring shares enough vocabulary with
     the element text, so a generic function can't be tagged onto a claim it
     doesn't do.

v0 grounding is lexical and deterministic. The interface is the slot where an
LLM judge that never saw the build session goes later.
"""

from __future__ import annotations

import inspect
import traceback
from dataclasses import dataclass

from . import registry
from .extract import Claim, Element, canonical, tokens

GROUNDING_MIN = 0.30   # fraction of the element's content words the implementers mention


@dataclass
class Verdict:
    element: Element
    status: str          # PASS | UNMAPPED | NO_CHECK | CHECK_FAIL | UNGROUNDED
    implementers: list[str]
    grounding: float
    note: str = ""


def grounding(e: Element, fns) -> float:
    want = tokens(e.text)
    if not want:
        return 1.0
    have: set[str] = set()
    for fn in fns:
        have |= tokens(fn.__name__.replace("_", " "))
        have |= tokens(inspect.getdoc(fn) or "")
    return len(want & have) / len(want)


def judge(chart: list[Claim], impl_module: str) -> list[Verdict]:
    impls, checks = registry.load(impl_module)
    out = []
    for e in canonical(chart):
        fns = impls.get(e.id, [])
        names = [f"{f.__module__.rsplit('.', 1)[-1]}.{f.__name__}" for f in fns]
        g = grounding(e, fns) if fns else 0.0
        if not fns:
            out.append(Verdict(e, "UNMAPPED", names, g, "no function claims this element"))
            continue
        if not checks.get(e.id):
            out.append(Verdict(e, "NO_CHECK", names, g, "mapped but nothing exercises it"))
            continue
        failed = None
        for c in checks[e.id]:
            try:
                c()
            except Exception as ex:  # AssertionError or a crash, both are failures
                failed = f"{type(ex).__name__}: {ex}" or traceback.format_exc(limit=1)
                break
        if failed:
            out.append(Verdict(e, "CHECK_FAIL", names, g, failed))
        elif g < GROUNDING_MIN:
            out.append(Verdict(e, "UNGROUNDED", names, g, "implementer doesn't describe this element"))
        else:
            out.append(Verdict(e, "PASS", names, g))
    return out


def report(pid: str, impl_module: str, verdicts: list[Verdict]) -> tuple[str, bool]:
    ok = all(v.status == "PASS" for v in verdicts)
    w = max(len(v.element.id) for v in verdicts)
    lines = [f"judge  {pid}  impl={impl_module}", ""]
    for v in verdicts:
        mark = "ok " if v.status == "PASS" else "XX "
        impl = ", ".join(v.implementers) or "-"
        lines.append(f"{mark}{v.element.id:<{w}}  {v.status:<10}  ground={v.grounding:.2f}  {impl}")
        lines.append(f"{'':>{w + 3}}  {v.element.text[:96]}{'...' if len(v.element.text) > 96 else ''}")
        if v.note:
            lines.append(f"{'':>{w + 3}}  -> {v.note}")
    passed = sum(v.status == "PASS" for v in verdicts)
    lines += ["", f"{passed}/{len(verdicts)} elements mapped to passing, grounded code",
              f"VERDICT: {'ACCEPT' if ok else 'REJECT (rebuild)'}"]
    return "\n".join(lines), ok
