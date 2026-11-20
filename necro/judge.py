"""The judge: map every canonical claim element to code, or reject the build.

Gates per element, in order (v0 runs 1-4, v1 runs all):

  1. MAPPED     some function or class is decorated @implements(element)
  2. CHECKED    some @check(element) exists
  3. PASSES     every check passes against the real code
  4. GROUNDED   the implementer's name + docstring covers >= 30% of the element's content words
  5. TRACED     (v1) running the checks actually executes the mapped code
  6. MUTANTS    (v1) break each mapped function (return None, return an argument unchanged);
                the element's checks must fail on every mutant. A mutant that survives means
                the checks weren't testing that code.

v0's lexical grounding can be gamed by stuffing claim words into docstrings. Gates 5 and 6
can't: tracing catches checks that never touch the mapped code, mutation catches checks that
touch it without asserting anything about what it does.
"""

from __future__ import annotations

import inspect
import sys
from dataclasses import dataclass, field

from . import registry
from .extract import Claim, Element, canonical, tokens

GROUNDING_MIN = 0.30


@dataclass
class Verdict:
    element: Element
    status: str          # PASS | UNMAPPED | NO_CHECK | CHECK_FAIL | UNGROUNDED | TRACE_MISS | MUTANT_SURVIVED
    implementers: list[str]
    grounding: float
    note: str = ""
    mutants: tuple[int, int] = (0, 0)     # (killed, total)


# ------------------------------------------------------------------ helpers


def _name(obj) -> str:
    return f"{obj.__module__.rsplit('.', 1)[-1]}.{obj.__qualname__}"


def grounding(e: Element, objs) -> float:
    want = tokens(e.text)
    if not want:
        return 1.0
    have: set[str] = set()
    for o in objs:
        have |= tokens(o.__name__.replace("_", " "))
        have |= tokens(inspect.getdoc(o) or "")
    return len(want & have) / len(want)


def _run(checks) -> str | None:
    """Run checks; return a failure description or None if all passed."""
    for c in checks:
        try:
            c()
        except BaseException as ex:  # noqa: BLE001 - any failure counts, including SystemExit from a bad mutant
            if isinstance(ex, KeyboardInterrupt):
                raise
            return f"{type(ex).__name__}: {ex}"[:160]
    return None


def _executed_code(checks) -> set:
    """Code objects called while the checks run."""
    seen: set = set()

    def prof(frame, event, arg):
        if event == "call":
            seen.add(frame.f_code)

    old = sys.getprofile()
    sys.setprofile(prof)
    try:
        _run(checks)
    finally:
        sys.setprofile(old)
    return seen


def _traced(obj, seen: set) -> bool:
    if inspect.isclass(obj):
        # any method defined on the class ran (init, __post_init__, a method...)
        prefix = obj.__qualname__ + "."
        file = inspect.getsourcefile(obj)
        return any(c.co_filename == file and c.co_qualname.startswith(prefix) for c in seen)
    return getattr(obj, "__code__", None) in seen


def _mutants(fn):
    """Yield (label, mutant) pairs: return None, and return each positional argument unchanged."""
    params = [p for p in inspect.signature(fn).parameters.values()
              if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)]

    def ret_none(*a, **k):
        return None
    yield "return None", ret_none

    for i, p in enumerate(params):
        def ret_arg(*a, _i=i, _n=p.name, **k):
            return a[_i] if len(a) > _i else k.get(_n)
        yield f"return {p.name}", ret_arg


def _mutation_test(fn, checks) -> tuple[int, int, list[str]]:
    """Swap fn for each mutant in its module and rerun the checks. Returns (killed, total, survivors)."""
    mod = sys.modules[fn.__module__]
    attr = fn.__name__
    if getattr(mod, attr, None) is not fn:
        return 0, 0, [f"{attr} is not a module-level name, can't mutate"]
    killed, total, survivors = 0, 0, []
    try:
        for label, m in _mutants(fn):
            total += 1
            setattr(mod, attr, m)
            if _run(checks) is not None:
                killed += 1
            else:
                survivors.append(f"{attr}: {label}")
    finally:
        setattr(mod, attr, fn)
    return killed, total, survivors


# ------------------------------------------------------------------ judge


def judge(chart: list[Claim], impl_module: str, level: str = "v1") -> list[Verdict]:
    impls, checks = registry.load(impl_module)
    out = []
    for e in canonical(chart):
        objs = impls.get(e.id, [])
        names = [_name(o) for o in objs]
        g = grounding(e, objs) if objs else 0.0
        cks = checks.get(e.id, [])

        if not objs:
            out.append(Verdict(e, "UNMAPPED", names, g, "no function claims this element"))
            continue
        if not cks:
            out.append(Verdict(e, "NO_CHECK", names, g, "mapped but nothing exercises it"))
            continue
        if (fail := _run(cks)) is not None:
            out.append(Verdict(e, "CHECK_FAIL", names, g, fail))
            continue
        if g < GROUNDING_MIN:
            out.append(Verdict(e, "UNGROUNDED", names, g, "implementer doesn't describe this element"))
            continue
        if level == "v0":
            out.append(Verdict(e, "PASS", names, g))
            continue

        seen = _executed_code(cks)
        missed = [_name(o) for o in objs if not _traced(o, seen)]
        if missed:
            out.append(Verdict(e, "TRACE_MISS", names, g, f"checks never execute {', '.join(missed)}"))
            continue

        killed = total = 0
        survivors: list[str] = []
        for o in objs:
            if inspect.isclass(o):
                continue   # classes are traced, not mutated
            k, t, s = _mutation_test(o, cks)
            killed, total, survivors = killed + k, total + t, survivors + s
        if survivors:
            out.append(Verdict(e, "MUTANT_SURVIVED", names, g,
                               "checks still pass with " + "; ".join(survivors), (killed, total)))
        else:
            out.append(Verdict(e, "PASS", names, g, mutants=(killed, total)))
    return out


def report(pid: str, impl_module: str, verdicts: list[Verdict], level: str = "v1") -> tuple[str, bool]:
    ok = all(v.status == "PASS" for v in verdicts)
    w = max(len(v.element.id) for v in verdicts)
    lines = [f"judge {level}  {pid}  impl={impl_module}", ""]
    for v in verdicts:
        mark = "ok " if v.status == "PASS" else "XX "
        impl = ", ".join(v.implementers) or "-"
        mut = f"  mutants={v.mutants[0]}/{v.mutants[1]}" if v.mutants[1] else ""
        lines.append(f"{mark}{v.element.id:<{w}}  {v.status:<15} ground={v.grounding:.2f}{mut}  {impl}")
        lines.append(f"{'':>{w + 3}}  {v.element.text[:96]}{'...' if len(v.element.text) > 96 else ''}")
        if v.note:
            lines.append(f"{'':>{w + 3}}  -> {v.note}")
    passed = sum(v.status == "PASS" for v in verdicts)
    killed = sum(v.mutants[0] for v in verdicts)
    total = sum(v.mutants[1] for v in verdicts)
    lines += ["", f"{passed}/{len(verdicts)} elements mapped to passing, grounded code"
              + (f", {killed}/{total} mutants killed" if level == "v1" and total else "")]
    lines.append(f"VERDICT: {'ACCEPT' if ok else 'REJECT (rebuild)'}")
    return "\n".join(lines), ok
