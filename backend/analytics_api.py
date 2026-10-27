"""Data for the admin Analytics page (#/admin/analytics): users, topics and live load.

Dates are grouped in the admin's local time: the frontend sends `tz`, the value of
JavaScript's Date.getTimezoneOffset() (minutes, positive west of UTC; Cyprus in summer is -180).
"""
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from flask import Blueprint, jsonify, request
from sqlalchemy import func

from auth import admin_required
from metrics import ACTIVE_WINDOW_MINUTES, answering_now
from models import Message, User, UserActivity, get_db

analytics_bp = Blueprint("analytics", __name__, url_prefix="/admin/analytics")

ASSISTANT_PREFIX = "[assistant] "
TOPIC_ORDER = ["VISA", "TRANSPORT", "REAL_ESTATE", "GENERAL", "OUT_OF_SCOPE"]


def _utc(dt):
    """SQLite hands back naive datetimes; treat them as UTC like Postgres does."""
    if dt is None:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def _range():
    """(local dates in order, UTC start, offset) for ?days=&tz="""
    days = max(1, min(request.args.get("days", default=30, type=int), 365))
    offset = timedelta(minutes=request.args.get("tz", default=0, type=int))
    today = (datetime.now(timezone.utc) - offset).date()
    dates = [today - timedelta(days=i) for i in range(days - 1, -1, -1)]
    start_utc = datetime.combine(dates[0], datetime.min.time(), tzinfo=timezone.utc) + offset
    return dates, start_utc, offset


def _local_date(dt, offset):
    return (_utc(dt) - offset).date()


def _user_questions(db, start_utc, *columns):
    return (db.query(*columns)
            .filter(~Message.message.startswith(ASSISTANT_PREFIX), Message.created_at >= start_utc))


@analytics_bp.route("/users", methods=["GET"])
@admin_required
def users_over_time():
    db = get_db()
    dates, start_utc, offset = _range()
    first = dates[0]

    joined = [_local_date(c, offset) for (c,) in db.query(User.created_at) if c is not None]
    before = sum(1 for d in joined if d < first)
    new_per_day = Counter(d for d in joined if d >= first)

    # A user is active on a day if they asked something or had the app open
    active = defaultdict(set)
    for user_id, created in _user_questions(db, start_utc, Message.user_id, Message.created_at):
        active[_local_date(created, offset)].add(user_id)
    for user_id, minute in (db.query(UserActivity.user_id, UserActivity.minute)
                            .filter(UserActivity.minute >= start_utc)):
        active[_local_date(minute, offset)].add(user_id)

    series, total = [], before
    for d in dates:
        total += new_per_day[d]
        series.append({
            "date":         d.isoformat(),
            "new_users":    new_per_day[d],
            "total_users":  total,
            "active_users": len(active[d]),
        })
    return jsonify({"days": series})


@analytics_bp.route("/topics", methods=["GET"])
@admin_required
def topics_over_time():
    db = get_db()
    dates, start_utc, offset = _range()

    per_day = defaultdict(Counter)
    totals = Counter()
    questions = untagged = 0
    for created, topics in _user_questions(db, start_utc, Message.created_at, Message.topics):
        questions += 1
        if not topics:
            untagged += 1          # asked before topics were recorded, or too short to route
            continue
        d = _local_date(created, offset)
        for label in topics.split(","):
            per_day[d][label] += 1
            totals[label] += 1

    labels = [t for t in TOPIC_ORDER if totals[t]] + sorted(set(totals) - set(TOPIC_ORDER))
    return jsonify({
        "labels":    labels,
        "totals":    {t: totals[t] for t in labels},
        "questions": questions,
        "untagged":  untagged,
        "days":      [{"date": d.isoformat(), **{t: per_day[d][t] for t in labels}} for d in dates],
    })


@analytics_bp.route("/load", methods=["GET"])
@admin_required
def load():
    db = get_db()
    hours = max(1, min(request.args.get("hours", default=6, type=int), 48))
    bucket = timedelta(minutes=5 if hours <= 12 else 15)

    now = datetime.now(timezone.utc)
    start = now - timedelta(hours=hours)
    # Align buckets to the clock (…:00, :05, :10) so they don't shift on every refresh
    step = int(bucket.total_seconds())
    first = datetime.fromtimestamp(int(start.timestamp()) // step * step, tz=timezone.utc)

    per_bucket = defaultdict(set)
    active_now = set()
    window_start = now - timedelta(minutes=ACTIVE_WINDOW_MINUTES)
    for user_id, minute in (db.query(UserActivity.user_id, UserActivity.minute)
                            .filter(UserActivity.minute >= first)):
        minute = _utc(minute)
        per_bucket[int((minute - first) / bucket)].add(user_id)
        # rows are per minute, so the current minute's row counts as "now"
        if minute >= window_start.replace(second=0, microsecond=0):
            active_now.add(user_id)

    count = int((now - first) / bucket) + 1
    series = [{"time": (first + i * bucket).isoformat(), "active": len(per_bucket[i])} for i in range(count)]

    questions_last_hour = (_user_questions(db, now - timedelta(hours=1), func.count(Message.id)).scalar())

    return jsonify({
        "active_now":          len(active_now),
        "window_minutes":      ACTIVE_WINDOW_MINUTES,
        "answering_now":       answering_now(),
        "questions_last_hour": questions_last_hour,
        "bucket_minutes":      int(bucket.total_seconds() // 60),
        "series":              series,
    })
