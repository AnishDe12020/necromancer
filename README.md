# necromancer

Expired patents, raised from the dead. **The claims are the spec. The patent is the eval.**

```
patent id ──fetch──▶ claims ──extract──▶ claim chart ──evalgen──▶ failing tests + build brief
                                                                       │
                                                       build agent (Devin) implements
                                                                       │
                                     judge: every element ──▶ code that passes + is grounded
                                                                       │
                                                         ACCEPT, or REJECT and rebuild
```

The build agent never reads 40 pages of legalese. It gets one line per claim element,
a failing test per element, and a judge that rejects any element it can't trace to
real, passing code. A generic CRUD app can't fake its way through.

## Run it

Python 3.10+, stdlib only, plus `pytest`.

```bash
pip install pytest
./run_demo.sh                 # live claims from Google Patents, falls back to the fixture
OFFLINE=1 ./run_demo.sh       # fixture only
```

Expected ending:

```
13/13 elements mapped to passing, grounded code
VERDICT: ACCEPT
...
1/13 elements mapped to passing, grounded code
VERDICT: REJECT (rebuild)

DEMO OK: reference accepted, CRUD rejected
```

Full output of an offline run is in [`docs/sample_run.txt`](docs/sample_run.txt).

## First target: US7669123B2, the Facebook News Feed patent

"Dynamically providing a news feed about a user of a social network". Filed 2006-08-11,
Zuckerberg among the inventors. Google Patents lists the adjusted expiry as 2026-08-22.

- 3 independent claims (method 1, system 16, storage medium 24) → 19 elements → **13 canonical**
  (claim 24 restates claim 1 word for word, so its elements are aliased, not built twice)
- `impls/us7669123/feed_engine.py`: a small working feed engine. Activity monitoring, a sqlite
  activity store, story generation, "join the same activity" links, and friend-scoped privacy with
  per-user hidden activity types. All 13 elements map to it and pass. It also ranks by affinity ×
  recency, which goes beyond the patent: claim 1 never recites ordering.
- `impls/crud_baseline/app.py`: the control. A CRUD app that tags itself onto 3 elements and
  passes its own happy-path checks. pytest gives it 6/13; the judge gives it 1/13 and rejects it.

## Commands

```bash
python -m necro fetch   US7669123B2                 # pull claims (saves to fixtures/)
python -m necro extract US7669123B2                 # out/<id>/claim_chart.json
python -m necro evalgen US7669123B2 --impl <mod>    # out/<id>/evals/ + BUILD_BRIEF.md
python -m necro judge   US7669123B2 --impl <mod>    # exit 0 only on ACCEPT
python -m necro run     US7669123B2 --impl <mod>    # all of it, plus pytest on the evals
```

`--offline` skips the network everywhere.

## How the pieces work

**Extract** (`necro/extract.py`). Drops dependent claims ("The method of claim 1, ..."), classifies
each independent claim as method / system / medium, splits on the last transition phrase
(`comprising:`), then on `;`, stripping the trailing `and`. Identical elements across claims are
aliased to their first occurrence.

**Evalgen** (`necro/evalgen.py`). One pytest test per canonical element, named after the
element, with the claim text as the docstring. Each fails with `UNIMPLEMENTED C1.E5: <claim text>`
until the implementation registers a passing check. It also writes `BUILD_BRIEF.md`, the
task you hand the build agent.

**Contract** (`necro/registry.py`). Implementations declare coverage in code:

```python
@implements("C1.E5", "C16.E5")
def limit_access(eng, item):
    """Privacy component: limit access to the news item to a predetermined set of viewing users..."""

@check("C1.E5", "C16.E5")
def _non_friends_and_hidden_verbs_are_blocked(): ...
```

**Judge** (`necro/judge.py`). Per element: needs an implementer, needs a check, the check must
pass against the real code, and the implementer's name + docstring must cover at least 30% of
the element's content words. Statuses: `PASS`, `UNMAPPED`, `NO_CHECK`, `CHECK_FAIL`, `UNGROUNDED`.

## Honest limitations (v0)

- **Fixtures are live snapshots.** `fixtures/US7669123B2.claims.txt` is the granted claim text as
  pulled by `python -m necro fetch`. The first draft ran on claims reconstructed from press excerpts,
  which had claim 1 reciting "assigning an order" to news items. The real claim doesn't. That's the
  point of fetching: build to the claims, not to what people say the patent covers.
- **Grounding is lexical.** It catches a CRUD app tagging `read()` onto "generating news items",
  but an agent could stuff docstrings with claim words. The judge interface is the slot for an
  LLM judge that never saw the build session and has to cite the line of code for each element.
- **Checks are written by the builder.** The next step is having the extractor agent write the
  behavioural checks from the claim chart *before* the build, so the builder can't grade itself.
- **Claim parsing is regex-level.** Fine for well-formed US claims; nested sub-elements
  ("wherein ... comprising: (a) ...; (b) ...") need a real parser.

## Layout

```
necro/            extractor, evalgen, registry, judge, CLI
fixtures/         claim text per patent (live fetch overwrites)
impls/us7669123/  reference build for the News Feed patent
impls/crud_baseline/  control that must be rejected
out/US7669123B2/  generated claim chart, evals, build brief
tests/            extractor + Google Patents HTML parser tests
docs/sample_run.txt
```
