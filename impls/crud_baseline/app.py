"""Control: the generic CRUD app an unsupervised agent builds when it skims the patent.

It tags its functions onto the claim elements it thinks it covers, has a happy-path
check for each, and the judge should still reject it.
"""

from __future__ import annotations

from necro.registry import check, implements

DB: dict[int, dict] = {}


@implements("C1.E2", "C16.E2")
def create(record: dict) -> int:
    """Create a record and save it to the database."""
    rid = len(DB) + 1
    DB[rid] = record
    return rid


@implements("C1.E3", "C16.E3")
def read(rid: int) -> dict:
    """Read a record by id."""
    return DB[rid]


@implements("C1.E7", "C16.E6")
def list_all() -> list[dict]:
    """Return all records as JSON for the frontend."""
    return list(DB.values())


def update(rid: int, record: dict) -> None:
    DB[rid] = record


def delete(rid: int) -> None:
    DB.pop(rid, None)


@check("C1.E2", "C16.E2", "C1.E3", "C16.E3", "C1.E7", "C16.E6")
def _crud_happy_path():
    DB.clear()
    rid = create({"title": "hello"})
    assert read(rid)["title"] == "hello"
    assert len(list_all()) == 1
