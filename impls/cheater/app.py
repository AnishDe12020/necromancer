"""Control #2: an agent gaming the v0 judge.

Every element is mapped, every docstring is stuffed with the claim's own words, and every
check passes. v0 (lexical grounding) accepts it 13/13. v1 rejects it: some checks never run
the mapped code (TRACE_MISS), the rest run it without asserting anything a broken version
would fail (MUTANT_SURVIVED).
"""

from __future__ import annotations

from necro.registry import check, implements

LOG: list[dict] = []


@implements("C16.E1")
class Environment:
    """A social network environment with users, a plurality of activities and viewing users."""

    def __init__(self):
        self.users: list[str] = []


@implements("C1.E1", "C16.E2")
def track(event: dict) -> dict:
    """Module configured to monitor a plurality of activities in a social network environment;
    monitoring a plurality of activities."""
    LOG.append(event)
    return event


@implements("C1.E2", "C16.E3")
def save(events: list) -> list:
    """Storage medium for storing the plurality of activities in a database."""
    return list(events)


@implements("C1.E3", "C16.E4")
def make_items(events: list) -> list:
    """Module configured to generate a plurality of news items regarding one or more of the
    activities, for presentation to one or more viewing users, relates to an activity
    performed by another user."""
    return [{"text": str(e)} for e in events]


@implements("C1.E4", "C16.E5")
def add_link(item: dict) -> dict:
    """Link component configured to attach a link associated with at least one of the
    activities of another user to the news items; link enables a viewing user to
    participate in the same activity as the another user."""
    item["link"] = "#"
    return item


@implements("C1.E5", "C16.E6")
def restrict(item: dict) -> dict:
    """Privacy component configured to limit access to the plurality of news items to a set
    of viewing users; limiting access."""
    return item


@implements("C1.E6", "C16.E7")
def render(items: list) -> list:
    """Media generator configured to display a news feed comprising two or more of the
    plurality of news items to at least one viewing user of the predetermined set of
    viewing users; displaying a news feed."""
    return items


# Checks that look busy and prove nothing.

@check("C16.E1")
def _env():
    assert Environment().users == []


@check("C1.E1", "C16.E2")
def _track_runs():
    track({"actor": "a"})            # called, but nothing about the result is asserted


@check("C1.E2", "C16.E3")
def _save_is_fine():
    assert list([1, 2]) == [1, 2]    # never calls save()


@check("C1.E3", "C16.E4")
def _items_exist():
    assert make_items([{"a": 1}]) is not None


@check("C1.E4", "C16.E5")
def _link_runs():
    add_link({"text": "x"})


@check("C1.E5", "C16.E6")
def _privacy_is_fine():
    assert True                      # never calls restrict()


@check("C1.E6", "C16.E7")
def _render_returns_list():
    assert isinstance(render([{"text": "x"}, {"text": "y"}]), list)
