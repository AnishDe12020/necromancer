"""Reference implementation of US7669123B2: a drop-in social activity news feed engine.

Public domain since the patent's term ended. Stdlib only (sqlite3). Each function
declares the claim elements it implements; each @check exercises the real code.
"""

from __future__ import annotations

import math
import sqlite3
import time
from dataclasses import dataclass, field

from necro.registry import check, implements

# ---------------------------------------------------------------- model


@dataclass(frozen=True)
class Activity:
    id: int
    actor: str
    verb: str          # "commented_on", "joined", "friended", ...
    obj: str           # "photo:42", "group:rust-blr", "user:bob"
    ts: float


@dataclass
class NewsItem:
    activity: Activity
    text: str
    link: str | None = None
    audience: frozenset[str] = frozenset()
    score: float = 0.0


@implements("C16.E1")
@dataclass
class FeedEngine:
    """Social network environment: users, friendships between them, per-user privacy
    settings, and the activity store everything else runs against."""

    db: sqlite3.Connection = field(default_factory=lambda: sqlite3.connect(":memory:"))
    friends: dict[str, set[str]] = field(default_factory=dict)
    hidden_verbs: dict[str, set[str]] = field(default_factory=dict)  # user privacy settings
    affinity: dict[tuple[str, str], float] = field(default_factory=dict)

    def __post_init__(self):
        self.db.execute(
            "CREATE TABLE IF NOT EXISTS activities ("
            " id INTEGER PRIMARY KEY, actor TEXT, verb TEXT, obj TEXT, ts REAL)"
        )

    def befriend(self, a: str, b: str, weight: float = 1.0):
        self.friends.setdefault(a, set()).add(b)
        self.friends.setdefault(b, set()).add(a)
        self.affinity[(a, b)] = self.affinity[(b, a)] = weight


VERB_TEXT = {
    "commented_on": "commented on {o}",
    "joined": "joined {o}",
    "friended": "is now friends with {o}",
    "liked": "liked {o}",
    "posted": "posted {o}",
}

# ---------------------------------------------------------------- claim elements


@implements("C1.E1", "C16.E2")
def monitor_activity(eng: FeedEngine, actor: str, verb: str, obj: str, ts: float | None = None) -> Activity:
    """Module configured to monitor a plurality of activities: monitor each activity a user performs in the social network
    environment and hand it to storage. Every activity passes through here."""
    if verb not in VERB_TEXT:
        raise ValueError(f"unknown activity verb {verb!r}")
    return store_activity(eng, actor, verb, obj, ts if ts is not None else time.time())


@implements("C1.E2", "C16.E3")
def store_activity(eng: FeedEngine, actor: str, verb: str, obj: str, ts: float) -> Activity:
    """Storage medium storing the plurality of activities in a database (sqlite activities table)."""
    cur = eng.db.execute(
        "INSERT INTO activities (actor, verb, obj, ts) VALUES (?, ?, ?, ?)", (actor, verb, obj, ts)
    )
    return Activity(cur.lastrowid, actor, verb, obj, ts)


def _activities_by(eng: FeedEngine, users: set[str]) -> list[Activity]:
    if not users:
        return []
    q = ",".join("?" * len(users))
    rows = eng.db.execute(
        f"SELECT id, actor, verb, obj, ts FROM activities WHERE actor IN ({q}) ORDER BY ts DESC", tuple(users)
    )
    return [Activity(*r) for r in rows]


@implements("C1.E3", "C16.E4")
def generate_news_items(eng: FeedEngine, users: set[str]) -> list[NewsItem]:
    """Module configured to generate news items regarding activities performed by another
    user, for presentation to viewing users, rendered as stories ("alice commented on photo:42")."""
    return [
        NewsItem(a, f"{a.actor} {VERB_TEXT[a.verb].format(o=a.obj)}")
        for a in _activities_by(eng, users)
    ]


@implements("C1.E4", "C16.E5")
def attach_informational_link(item: NewsItem) -> NewsItem:
    """Link component: attach a link associated with another user's activity to the news
    item, where the link enables a viewing user to participate in the same activity as the
    another user (comment on the same photo, join the same group)."""
    kind, _, ident = item.activity.obj.partition(":")
    action = {"commented_on": "comment", "joined": "join", "liked": "like",
              "friended": "add_friend", "posted": "view"}[item.activity.verb]
    item.link = f"/{kind}/{ident}?action={action}"
    return item


@implements("C1.E5", "C16.E6")
def limit_access(eng: FeedEngine, item: NewsItem) -> NewsItem:
    """Privacy component: limit access to the news items to a set of viewing users, the
    actor's friends, minus any activity type the actor's privacy settings hide."""
    actor = item.activity.actor
    if item.activity.verb in eng.hidden_verbs.get(actor, set()):
        item.audience = frozenset()
    else:
        item.audience = frozenset(eng.friends.get(actor, set()))
    return item


def assign_order(eng: FeedEngine, viewer: str, items: list[NewsItem], now: float | None = None,
                 half_life_s: float = 6 * 3600) -> list[NewsItem]:
    """Rank news items by viewer-to-user affinity times recency decay.

    Not part of the claims: claim 1 never recites ordering. This is product, not necromancy."""
    now = now if now is not None else time.time()
    for it in items:
        age = max(0.0, now - it.activity.ts)
        it.score = eng.affinity.get((viewer, it.activity.actor), 0.1) * math.exp(-age * math.log(2) / half_life_s)
    return sorted(items, key=lambda i: (-i.score, -i.activity.id))


@implements("C1.E6", "C16.E7")
def display_news_feed(eng: FeedEngine, viewer: str, limit: int = 20, now: float | None = None) -> list[NewsItem]:
    """Media generator: display a news feed comprising two or more news items to a viewing
    user in the predetermined set of viewing users. The full pipeline end to end."""
    items = generate_news_items(eng, eng.friends.get(viewer, set()))
    items = [limit_access(eng, attach_informational_link(i)) for i in items]
    visible = [i for i in items if viewer in i.audience]
    return assign_order(eng, viewer, visible, now=now)[:limit]


# ---------------------------------------------------------------- checks (behavioural)


def _world(now: float = 1_000_000.0) -> FeedEngine:
    e = FeedEngine()
    e.befriend("alice", "bob", 1.0)
    e.befriend("alice", "carol", 0.2)
    e.befriend("bob", "dave", 1.0)
    monitor_activity(e, "bob", "commented_on", "photo:42", ts=now - 60)
    monitor_activity(e, "carol", "joined", "group:rust-blr", ts=now - 30)
    monitor_activity(e, "bob", "liked", "post:7", ts=now - 7200)
    monitor_activity(e, "dave", "posted", "post:9", ts=now - 10)
    return e


@check("C1.E1", "C16.E2")
def _monitor_rejects_unknown_and_records_known():
    e = FeedEngine()
    a = monitor_activity(e, "x", "joined", "group:g", ts=1.0)
    assert a.id == 1 and a.verb == "joined"
    try:
        monitor_activity(e, "x", "teleported", "moon:1")
    except ValueError:
        pass
    else:
        raise AssertionError("unknown activity must not be monitored silently")


@check("C1.E2", "C16.E3")
def _activities_persist_in_db():
    e = _world()
    (n,) = e.db.execute("SELECT COUNT(*) FROM activities").fetchone()
    assert n == 4
    assert e.db.execute("SELECT actor FROM activities WHERE obj='photo:42'").fetchone() == ("bob",)


@check("C1.E3", "C16.E4")
def _news_items_describe_activities():
    items = generate_news_items(_world(), {"bob"})
    texts = {i.text for i in items}
    assert texts == {"bob commented on photo:42", "bob liked post:7"}, texts


@check("C1.E4", "C16.E5")
def _link_lets_viewer_join_same_activity():
    it = attach_informational_link(generate_news_items(_world(), {"carol"})[0])
    assert it.link == "/group/rust-blr?action=join"


@check("C1.E5", "C16.E6")
def _non_friends_and_hidden_verbs_are_blocked():
    e = _world()
    bob_items = [limit_access(e, i) for i in generate_news_items(e, {"bob"})]
    assert all(i.audience == {"alice", "dave"} for i in bob_items)
    assert all("carol" not in i.audience for i in bob_items)
    e.hidden_verbs["bob"] = {"liked"}
    liked = [limit_access(e, i) for i in generate_news_items(e, {"bob"}) if i.activity.verb == "liked"]
    assert liked and liked[0].audience == frozenset()


@check("C1.E6", "C16.E7")
def _order_uses_affinity_and_recency():
    now = 1_000_000.0
    e = _world(now)
    ranked = assign_order(e, "alice", generate_news_items(e, {"bob", "carol"}), now=now)
    order = [i.text for i in ranked]
    # carol's join is the newest item, but alice barely knows carol: a 2h-old like from
    # close friend bob still outranks it. Pure recency sort would get this wrong.
    assert order == ["bob commented on photo:42", "bob liked post:7", "carol joined group:rust-blr"], order
    # and decay is real: push bob's like back a week and carol overtakes it.
    e.db.execute("UPDATE activities SET ts = ? WHERE obj = 'post:7'", (now - 7 * 86400,))
    order = [i.text for i in assign_order(e, "alice", generate_news_items(e, {"bob", "carol"}), now=now)]
    assert order[-1] == "bob liked post:7", order


@check("C1.E6", "C16.E7")
def _feed_shows_two_plus_permitted_items_only():
    now = 1_000_000.0
    e = _world(now)
    feed = display_news_feed(e, "alice", now=now)
    assert len(feed) >= 2
    assert all("alice" in i.audience and i.link for i in feed)
    assert "dave posted post:9" not in {i.text for i in feed}   # dave isn't alice's friend
    assert display_news_feed(e, "nobody", now=now) == []
    # items relate to activities performed by *another* user: alice never sees her own
    monitor_activity(e, "alice", "posted", "post:1", ts=now)
    assert all(i.activity.actor != "alice" for i in display_news_feed(e, "alice", now=now))


@check("C16.E1")
def _environment_holds_users_relationships_and_settings():
    e = _world()
    assert e.friends["alice"] == {"bob", "carol"} and e.friends["bob"] == {"alice", "dave"}
    e.hidden_verbs["carol"] = {"joined"}
    assert "carol joined group:rust-blr" not in {i.text for i in display_news_feed(e, "alice")}
