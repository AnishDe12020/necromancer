"""Fetch claims for a patent from Google Patents, with an offline fixture fallback."""

from __future__ import annotations

import re
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"
URL = "https://patents.google.com/patent/{pid}/en"


class _ClaimsParser(HTMLParser):
    """Collects the text of each top-level <div class="claim ..."> on a Google Patents page.

    Google nests claim divs (a wrapper div.claim around an inner div.claim with
    id="CLM-000NN"), so only the outermost claim div starts a capture.
    """

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.claims: list[str] = []
        self._depth = 0          # div depth inside the current capture
        self._buf: list[str] = []

    def handle_starttag(self, tag, attrs):
        if tag != "div":
            return
        cls = dict(attrs).get("class") or ""
        if self._depth:
            self._depth += 1
        elif "claim" in cls.split():
            self._depth = 1
            self._buf = []

    def handle_endtag(self, tag):
        if tag != "div" or not self._depth:
            return
        self._depth -= 1
        if self._depth == 0:
            text = re.sub(r"\s+", " ", "".join(self._buf)).strip()
            if text:
                self.claims.append(text)

    def handle_data(self, data):
        if self._depth:
            self._buf.append(data)


def parse_claims_html(html: str) -> list[str]:
    p = _ClaimsParser()
    p.feed(html)
    # Keep only blocks that start with a claim number ("1. A method ...").
    return [c for c in p.claims if re.match(r"^\d+\s*\.", c)]


def fetch_live(pid: str, timeout: float = 20.0) -> list[str]:
    req = urllib.request.Request(URL.format(pid=pid), headers={"User-Agent": "Mozilla/5.0 necro/0.1"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        html = r.read().decode("utf-8", "replace")
    claims = parse_claims_html(html)
    if not claims:
        raise RuntimeError(f"no claims found on page for {pid}")
    return claims


def fixture_path(pid: str) -> Path:
    return FIXTURES / f"{pid}.claims.txt"


def load_fixture(pid: str) -> list[str]:
    raw = fixture_path(pid).read_text()
    body = "\n".join(l for l in raw.splitlines() if not l.lstrip().startswith("#"))
    return [re.sub(r"\s+", " ", b).strip() for b in re.split(r"\n\s*\n", body) if b.strip()]


def get_claims(pid: str, offline: bool = False) -> tuple[list[str], str]:
    """Returns (claims, source). Tries live first unless offline; falls back to fixture."""
    if not offline:
        try:
            claims = fetch_live(pid)
            save_fixture(pid, claims, header=f"# {pid} live claims from Google Patents")
            return claims, "live"
        except Exception as e:  # network blocked, page changed, etc.
            if not fixture_path(pid).exists():
                raise RuntimeError(f"live fetch failed ({e}) and no fixture for {pid}") from e
            print(f"[fetch] live fetch failed ({type(e).__name__}: {e}); using fixture")
    return load_fixture(pid), "fixture"


def save_fixture(pid: str, claims: list[str], header: str = "") -> Path:
    FIXTURES.mkdir(exist_ok=True)
    path = fixture_path(pid)
    path.write_text((header + "\n\n" if header else "") + "\n\n".join(claims) + "\n")
    return path
