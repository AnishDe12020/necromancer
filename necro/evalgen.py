"""Claim chart -> failing pytest suite. One test per canonical claim element.

The suite is generated before any implementation exists; it fails with the
element's own text until something registers a passing @check for it.
"""

from __future__ import annotations

import textwrap
from pathlib import Path

from .extract import Claim, canonical

CONFTEST = '''\
import os, sys
from pathlib import Path
import pytest

sys.path.insert(0, __ROOT__)
from necro import registry

@pytest.fixture(scope="session")
def checks():
    mod = os.environ.get("NECRO_IMPL")
    if not mod:
        pytest.fail("set NECRO_IMPL=<module> to the implementation under test")
    _, checks = registry.load(mod)
    return checks

@pytest.fixture
def element(checks):
    def run(eid, text):
        fns = checks.get(eid)
        if not fns:
            pytest.fail(f"UNIMPLEMENTED {eid}: {text}", pytrace=False)
        for fn in fns:
            fn()
    return run
'''


def generate(pid: str, chart: list[Claim], out_dir: Path) -> Path:
    out_dir.mkdir(parents=True, exist_ok=True)
    root = Path(__file__).resolve().parent.parent
    depth = len(out_dir.resolve().relative_to(root).parts)  # conftest -> repo root, kept relative
    (out_dir / "conftest.py").write_text(
        CONFTEST.replace("__ROOT__", f"str(Path(__file__).resolve().parents[{depth}])")
    )
    lines = [
        f'"""Generated claim evals for {pid}. Do not edit; regenerate with `python -m necro evalgen`."""',
        "",
    ]
    for e in canonical(chart):
        name = f"test_{e.id.replace('.', '_')}_{e.slug}"
        lines += [
            "",
            f"def {name}(element):",
            f"    {e.text!r}",
            f"    element({e.id!r}, {e.text!r})",
        ]
    path = out_dir / f"test_{pid.lower()}_claims.py"
    path.write_text("\n".join(lines) + "\n")
    return path


def devin_brief(pid: str, chart: list[Claim], evals: Path, impl_module: str) -> str:
    """The task handed to the build agent: the claim chart is the spec, the evals are done-ness."""
    root = Path(__file__).resolve().parent.parent
    ev = evals.parent.resolve().relative_to(root)
    rows = "\n".join(f"- `{e.id}` {e.text}" for e in canonical(chart))
    return textwrap.dedent(f"""\
    # Build brief: {pid}

    Implement the invention in `{impl_module.replace('.', '/')}.py`.

    ## Spec (one line per claim element)
    {{rows}}

    ## Rules
    - Decorate each implementing function with `@implements("<element id>", ...)` and give it a docstring
      describing what it does in the claim's own terms.
    - Register at least one behavioural `@check("<element id>")` per element that exercises the real code.
    - Done means both commands exit 0:
        NECRO_IMPL={impl_module} pytest {ev}
        python -m necro judge {pid} --impl {impl_module}
    - Do not edit the generated evals. A generic CRUD app will not pass the judge.
    """).replace("{rows}", rows)
