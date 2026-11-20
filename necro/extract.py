"""Claim text -> claim chart.

A claim chart is the list of independent claims, each split into its elements.
Every element becomes one eval. Elements that repeat across claims (a CRM claim
restating the method claim, say) are aliased to the first occurrence so they are
implemented and judged once.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass, field

STOP = set(
    """a an the of to in on for and or with at by from as is are be being been that which
    this these those its it said wherein whereby plurality least one two more same such
    configured comprising comprises having thereon embodied each any""".split()
)

_DEP = re.compile(r"\b(?:of|in|to|by|according to|as recited in|as claimed in)\s+claims?\s+\d+", re.I)
_TRANSITION = re.compile(r"\b(comprising|consisting of|consisting essentially of|including)\s*:", re.I)


@dataclass
class Element:
    id: str              # "C1.E3"
    text: str
    slug: str            # "generating_news_items_regarding_activities"
    alias_of: str | None = None


@dataclass
class Claim:
    number: int
    category: str        # method | system | medium | apparatus
    preamble: str
    elements: list[Element] = field(default_factory=list)


def norm(s: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", " ", s.lower())).strip()


def stem(w: str) -> str:
    for suf in ("ations", "ation", "ings", "ing", "ers", "er", "ed", "es", "s"):
        if len(w) > len(suf) + 3 and w.endswith(suf):
            return w[: -len(suf)]
    return w


def tokens(s: str) -> set[str]:
    return {stem(w) for w in norm(s).split() if w not in STOP and len(w) > 2}


def slugify(text: str, n: int = 5) -> str:
    words = [w for w in norm(text).split() if w not in STOP]
    return "_".join(words[:n]) or "element"


def split_number(raw: str) -> tuple[int, str]:
    m = re.match(r"^\s*(\d+)\s*\.\s*(.*)$", raw, re.S)
    if not m:
        raise ValueError(f"claim has no leading number: {raw[:60]!r}")
    return int(m.group(1)), m.group(2).strip()


def is_dependent(body: str) -> bool:
    # Only the opening of a claim decides dependency ("The method of claim 1, ...").
    return bool(_DEP.search(body[:200]))


def category(preamble: str) -> str:
    p = preamble.lower()
    if re.search(r"(computer|machine)[- ]readable|storage medi|program product", p):
        return "medium"
    if re.search(r"\b(system|apparatus|device)\b", p):
        return "system"
    if re.search(r"\b(method|process)\b", p):
        return "method"
    return "apparatus"


def split_elements(body: str) -> tuple[str, list[str]]:
    # For CRM claims the elements follow the *last* transition ("...the method comprising:").
    matches = list(_TRANSITION.finditer(body))
    if not matches:
        return body, []
    m = matches[-1]
    preamble, rest = body[: m.start()].strip(" ,"), body[m.end():]
    parts = [p.strip() for p in re.split(r";\s*", rest) if p.strip()]
    cleaned = []
    for p in parts:
        p = re.sub(r"^(and|or)\s+", "", p, flags=re.I).rstrip(" .;,")
        if p:
            cleaned.append(p)
    return preamble, cleaned


def extract(claims_raw: list[str]) -> list[Claim]:
    chart: list[Claim] = []
    seen: dict[str, str] = {}          # normalized element text -> first element id
    for raw in claims_raw:
        num, body = split_number(raw)
        if is_dependent(body):
            continue
        preamble, parts = split_elements(body)
        claim = Claim(number=num, category=category(preamble), preamble=preamble)
        for i, text in enumerate(parts, 1):
            eid = f"C{num}.E{i}"
            key = norm(text)
            claim.elements.append(Element(eid, text, slugify(text), alias_of=seen.get(key)))
            seen.setdefault(key, eid)
        chart.append(claim)
    return chart


def canonical(chart: list[Claim]) -> list[Element]:
    return [e for c in chart for e in c.elements if e.alias_of is None]


def to_json(pid: str, source: str, chart: list[Claim]) -> str:
    return json.dumps(
        {"patent": pid, "source": source, "claims": [asdict(c) for c in chart]}, indent=2
    )


def from_json(s: str) -> tuple[str, list[Claim]]:
    d = json.loads(s)
    claims = [
        Claim(c["number"], c["category"], c["preamble"], [Element(**e) for e in c["elements"]])
        for c in d["claims"]
    ]
    return d["patent"], claims
