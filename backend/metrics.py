"""Live load numbers: who is active, and how many answers are being generated."""
import random
import threading
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects import postgresql, sqlite

from models import UserActivity, engine, get_db

# A user counts as an active session if they made a request (or their open tab sent
# a heartbeat) within this many minutes. The frontend sends a heartbeat every minute.
ACTIVE_WINDOW_MINUTES = 2
ACTIVITY_RETENTION_DAYS = 14

_last_written = {}    # user_id -> minute already recorded by this process
_answering = 0
_lock = threading.Lock()


def record_activity(user_id):
    """Best effort: a failure here must never break the request itself."""
    minute = datetime.now(timezone.utc).replace(second=0, microsecond=0)
    if _last_written.get(user_id) == minute:
        return
    _last_written[user_id] = minute

    dialect = engine.dialect.name
    insert = {"postgresql": postgresql.insert, "sqlite": sqlite.insert}.get(dialect)
    db = get_db()
    try:
        if insert:
            db.execute(insert(UserActivity).values(user_id=user_id, minute=minute).on_conflict_do_nothing())
        elif not db.get(UserActivity, (user_id, minute)):
            db.add(UserActivity(user_id=user_id, minute=minute))
        # Roughly once per 200 writes, drop old rows so the table stays small
        if random.random() < 0.005:
            cutoff = minute - timedelta(days=ACTIVITY_RETENTION_DAYS)
            db.query(UserActivity).filter(UserActivity.minute < cutoff).delete()
        db.commit()
    except Exception as exc:   # noqa: BLE001
        db.rollback()
        print(f"Could not record activity for user {user_id}: {exc}")


@contextmanager
def answering():
    """Wrap /ask so the admin page can show how many answers are in progress.

    Counted per server process. With several worker processes, each reports its own.
    """
    global _answering
    with _lock:
        _answering += 1
    try:
        yield
    finally:
        with _lock:
            _answering -= 1


def answering_now():
    return _answering
