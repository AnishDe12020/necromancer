"""necro: expired patent -> claim chart -> failing evals -> build -> judge.

    python -m necro fetch   US7669123B2            # pull claims (live, falls back to fixture)
    python -m necro extract US7669123B2            # claim chart JSON
    python -m necro evalgen US7669123B2            # failing pytest suite + build brief
    python -m necro judge   US7669123B2 --impl impls.us7669123.feed_engine
    python -m necro run     US7669123B2 --impl impls.us7669123.feed_engine   # all of the above + pytest
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

from . import evalgen, extract, fetch, judge

ROOT = Path(__file__).resolve().parent.parent


def out(pid: str) -> Path:
    return ROOT / "out" / pid


def cmd_fetch(a) -> int:
    claims, src = fetch.get_claims(a.pid, offline=a.offline)
    print(f"[fetch] {len(claims)} claims for {a.pid} ({src})")
    return 0


def build_chart(a):
    claims, src = fetch.get_claims(a.pid, offline=a.offline)
    chart = extract.extract(claims)
    o = out(a.pid)
    o.mkdir(parents=True, exist_ok=True)
    (o / "claim_chart.json").write_text(extract.to_json(a.pid, src, chart))
    return chart, src


def print_chart(pid, src, chart):
    canon = extract.canonical(chart)
    total = sum(len(c.elements) for c in chart)
    print(f"[extract] {pid} ({src}): {len(chart)} independent claims, "
          f"{total} elements, {len(canon)} canonical after de-dup")
    for c in chart:
        print(f"  claim {c.number} [{c.category}] {c.preamble[:70]}...")
        for e in c.elements:
            tag = f"  = alias of {e.alias_of}" if e.alias_of else ""
            print(f"    {e.id:<7} {e.slug}{tag}")


def cmd_extract(a) -> int:
    chart, src = build_chart(a)
    print_chart(a.pid, src, chart)
    print(f"[extract] wrote {out(a.pid) / 'claim_chart.json'}")
    return 0


def cmd_evalgen(a) -> int:
    chart, _ = build_chart(a)
    path = evalgen.generate(a.pid, chart, out(a.pid) / "evals")
    impl = a.impl or f"impls.{a.pid.lower()}.impl"
    (out(a.pid) / "BUILD_BRIEF.md").write_text(evalgen.devin_brief(a.pid, chart, path, impl))
    print(f"[evalgen] {len(extract.canonical(chart))} evals -> {path.relative_to(ROOT)}")
    print(f"[evalgen] build brief -> {(out(a.pid) / 'BUILD_BRIEF.md').relative_to(ROOT)}")
    return 0


def cmd_judge(a) -> int:
    chart, _ = build_chart(a)
    text, ok = judge.report(a.pid, a.impl, judge.judge(chart, a.impl))
    print(text)
    return 0 if ok else 1


def cmd_run(a) -> int:
    chart, src = build_chart(a)
    print_chart(a.pid, src, chart)
    cmd_evalgen(a)
    print(f"\n[evals] pytest against {a.impl}")
    env = {**os.environ, "NECRO_IMPL": a.impl, "PYTHONPATH": str(ROOT)}
    r = subprocess.run(
        [sys.executable, "-m", "pytest", "-q", "-p", "no:cacheprovider", "--no-header",
         "-rf", str(out(a.pid) / "evals")],
        env=env, cwd=ROOT,
    )
    print()
    rc = cmd_judge(a)
    return rc or r.returncode


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="necro")
    sub = p.add_subparsers(dest="cmd", required=True)
    for name, fn in [("fetch", cmd_fetch), ("extract", cmd_extract), ("evalgen", cmd_evalgen),
                     ("judge", cmd_judge), ("run", cmd_run)]:
        s = sub.add_parser(name)
        s.add_argument("pid")
        s.add_argument("--offline", action="store_true", help="skip live fetch, use fixture")
        s.add_argument("--impl", required=name in ("judge", "run"), help="implementation module")
        s.set_defaults(fn=fn)
    a = p.parse_args(argv)
    sys.path.insert(0, str(ROOT))
    return a.fn(a)


if __name__ == "__main__":
    raise SystemExit(main())
