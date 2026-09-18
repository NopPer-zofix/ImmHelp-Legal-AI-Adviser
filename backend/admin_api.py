"""Admin API used by the frontend's admin pages (#/admin, #/admin/ads).

Every route requires a valid token for a user with role "admin" (see auth.py).
"""
import json
import re
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

from flask import Blueprint, g, jsonify, request
from sqlalchemy import func

from auth import admin_required
from models import Advertiser, Message, User, get_db

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")

ASSISTANT_PREFIX = "[assistant] "


def _iso(dt):
    return dt.isoformat() if dt else None


def _is_user_message():
    return ~Message.message.startswith(ASSISTANT_PREFIX)


# -----------------------------
# DASHBOARD
# -----------------------------
@admin_bp.route("/stats", methods=["GET"])
@admin_required
def stats():
    db = get_db()
    week_ago = datetime.now(timezone.utc) - timedelta(days=7)

    users  = db.query(func.count(User.id)).scalar()
    banned = db.query(func.count(User.id)).filter(User.is_banned.is_(True)).scalar()
    total  = db.query(func.count(Message.id)).filter(_is_user_message()).scalar()
    recent = (db.query(func.count(Message.id))
              .filter(_is_user_message(), Message.created_at >= week_ago).scalar())

    return jsonify({
        "users":          users,
        "active_users":   users - banned,
        "banned_users":   banned,
        "messages_7d":    recent,
        "messages_total": total,
    })


def _normalise(text):
    text = re.sub(r"[^\w\s]", "", text.lower())
    return " ".join(text.split())


@admin_bp.route("/top-questions", methods=["GET"])
@admin_required
def top_questions():
    """User questions grouped by wording, ignoring case and punctuation.

    Grouping happens in Python, which is fine for thousands of messages. For much
    more, move it into SQL or store a normalised column when the message is saved.
    """
    db    = get_db()
    days  = request.args.get("days", default=7, type=int)
    limit = min(request.args.get("limit", default=10, type=int), 50)

    query = db.query(Message.message).filter(_is_user_message())
    if days > 0:
        query = query.filter(Message.created_at >= datetime.now(timezone.utc) - timedelta(days=days))

    counts   = Counter()
    spelling = defaultdict(Counter)   # most common original wording per group, for display
    for (text,) in query:
        key = _normalise(text)
        if len(key) < 10:
            continue
        counts[key] += 1
        spelling[key][text.strip()] += 1

    return jsonify([
        {"question": spelling[key].most_common(1)[0][0], "count": count}
        for key, count in counts.most_common(limit)
    ])


# -----------------------------
# USERS AND BANS
# -----------------------------
def _user_row(user, message_count=0, last_active=None):
    return {
        "id":             user.id,
        "email":          user.email,
        "username":       user.username,
        "role":           user.role,
        "created_at":     _iso(user.created_at),
        "message_count":  message_count,
        "last_active_at": _iso(last_active),
        "is_banned":      bool(user.is_banned),
        "banned_reason":  user.banned_reason,
        "banned_at":      _iso(user.banned_at),
    }


@admin_bp.route("/users", methods=["GET"])
@admin_required
def list_users():
    db = get_db()

    activity = {
        user_id: (count, last)
        for user_id, count, last in (
            db.query(Message.user_id, func.count(Message.id), func.max(Message.created_at))
            .filter(_is_user_message())
            .group_by(Message.user_id)
        )
    }

    users = db.query(User).order_by(User.id).all()
    return jsonify([_user_row(u, *activity.get(u.id, (0, None))) for u in users])


@admin_bp.route("/users/<int:user_id>/ban", methods=["POST"])
@admin_required
def ban_user(user_id):
    db   = get_db()
    user = db.get(User, user_id)
    data = request.get_json(silent=True) or {}

    if not user:
        return jsonify({"error": "User not found."}), 404
    if user.id == g.user.id:
        return jsonify({"error": "You can't ban your own account."}), 400
    if user.role == "admin":
        return jsonify({"error": "Admins can't be banned. Remove the admin role first."}), 400

    user.is_banned     = True
    user.banned_reason = (str(data.get("reason") or "").strip() or None)
    user.banned_at     = datetime.now(timezone.utc)
    db.commit()
    return jsonify({"ok": True})


@admin_bp.route("/users/<int:user_id>/unban", methods=["POST"])
@admin_required
def unban_user(user_id):
    db   = get_db()
    user = db.get(User, user_id)

    if not user:
        return jsonify({"error": "User not found."}), 404

    user.is_banned     = False
    user.banned_reason = None
    user.banned_at     = None
    db.commit()
    return jsonify({"ok": True})


# -----------------------------
# ADVERTISERS
# -----------------------------
# Keep in sync with the frontend's src/lib/advertisers.js
CATEGORIES_NEEDING_LICENCE = {"law_firm", "real_estate", "insurance"}
CATEGORIES = CATEGORIES_NEEDING_LICENCE | {"relocation", "transport", "education", "other"}
TOPICS = {"VISA", "TRANSPORT", "REAL_ESTATE"}

EDITABLE = ["company", "reg_number", "website", "category", "licence_number",
            "contact_name", "contact_email", "contact_phone", "notes"]

# Changing any of these on an approved advertiser sends it back to review
REVIEWED_FIELDS = {"company", "reg_number", "category", "licence_number", "website"}

# status -> statuses it may move to
TRANSITIONS = {
    "pending":   {"approved", "rejected"},
    "approved":  {"suspended"},
    "suspended": {"approved"},
    "rejected":  {"pending"},
}

EMAIL_RE   = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
WEBSITE_RE = re.compile(r"^https?://[^\s.]+\.\S+$", re.I)


def _required_checks(category):
    checks = ["registration", "website"]
    if category in CATEGORIES_NEEDING_LICENCE:
        checks.append("licence")
    return checks


def _approval_blocker(adv):
    if adv.category in CATEGORIES_NEEDING_LICENCE and not adv.licence_number.strip():
        return "Add the licence number first."
    checks = json.loads(adv.checks or "{}")
    if not all(checks.get(c) for c in _required_checks(adv.category)):
        return "Tick every check to approve."
    return None


def _advertiser_json(adv, names):
    return {
        "id":             adv.id,
        "company":        adv.company,
        "reg_number":     adv.reg_number,
        "website":        adv.website,
        "category":       adv.category,
        "licence_number": adv.licence_number,
        "contact_name":   adv.contact_name,
        "contact_email":  adv.contact_email,
        "contact_phone":  adv.contact_phone,
        "topics":         [t for t in adv.topics.split(",") if t],
        "notes":          adv.notes,
        "status":         adv.status,
        "status_reason":  adv.status_reason,
        "checks":         json.loads(adv.checks or "{}"),
        "created_at":     _iso(adv.created_at),
        "created_by":     names.get(adv.created_by_id),
        "reviewed_at":    _iso(adv.reviewed_at),
        "reviewed_by":    names.get(adv.reviewed_by_id),
    }


def _names(db, advertisers):
    ids = {i for a in advertisers for i in (a.created_by_id, a.reviewed_by_id) if i}
    if not ids:
        return {}
    return dict(db.query(User.id, User.username).filter(User.id.in_(ids)))


def _validate(data, partial):
    """Clean the editable fields. Returns (values, error)."""
    values = {}
    for field in EDITABLE:
        if field in data:
            values[field] = str(data[field] or "").strip()

    if "topics" in data:
        topics = data["topics"] if isinstance(data["topics"], list) else []
        if not topics or not set(topics) <= TOPICS:
            return None, "Choose at least one topic: VISA, TRANSPORT or REAL_ESTATE."
        values["topics"] = ",".join(t for t in ["VISA", "TRANSPORT", "REAL_ESTATE"] if t in topics)
    elif not partial:
        return None, "Choose at least one topic."

    if "checks" in data:
        checks = data["checks"] if isinstance(data["checks"], dict) else {}
        values["checks"] = json.dumps({k: bool(v) for k, v in checks.items()})

    required = ["company", "reg_number", "website", "category", "contact_name", "contact_email"]
    for field in required:
        if (field in values or not partial) and not values.get(field):
            return None, f"{field.replace('_', ' ').capitalize()} is required."

    if "category" in values and values["category"] not in CATEGORIES:
        return None, "Unknown category."
    if "website" in values and not WEBSITE_RE.match(values["website"]):
        return None, "Website must be a full address, e.g. https://example.com"
    if "contact_email" in values and not EMAIL_RE.match(values["contact_email"]):
        return None, "Contact email isn't valid."
    return values, None


@admin_bp.route("/advertisers", methods=["GET"])
@admin_required
def list_advertisers():
    db  = get_db()
    ads = db.query(Advertiser).order_by(Advertiser.created_at.desc(), Advertiser.id.desc()).all()
    names = _names(db, ads)
    return jsonify([_advertiser_json(a, names) for a in ads])


@admin_bp.route("/advertisers", methods=["POST"])
@admin_required
def create_advertiser():
    db = get_db()
    values, error = _validate(request.get_json(silent=True) or {}, partial=False)
    if error:
        return jsonify({"error": error}), 400

    values.pop("checks", None)   # checks start empty; they're ticked during review
    adv = Advertiser(**values, status="pending", checks="{}", created_by_id=g.user.id)
    db.add(adv)
    db.commit()
    db.refresh(adv)
    return jsonify(_advertiser_json(adv, _names(db, [adv]))), 201


@admin_bp.route("/advertisers/<int:adv_id>", methods=["PATCH"])
@admin_required
def update_advertiser(adv_id):
    db  = get_db()
    adv = db.get(Advertiser, adv_id)
    if not adv:
        return jsonify({"error": "Advertiser not found."}), 404

    values, error = _validate(request.get_json(silent=True) or {}, partial=True)
    if error:
        return jsonify({"error": error}), 400

    changed = {k for k, v in values.items() if getattr(adv, k) != v}
    back_to_review = adv.status == "approved" and bool(changed & REVIEWED_FIELDS)

    for key, value in values.items():
        setattr(adv, key, value)
    if back_to_review:
        adv.status        = "pending"
        adv.checks        = "{}"
        adv.status_reason = "Details changed after approval"
    db.commit()

    result = _advertiser_json(adv, _names(db, [adv]))
    result["sent_back_to_review"] = back_to_review
    return jsonify(result)


@admin_bp.route("/advertisers/<int:adv_id>/status", methods=["POST"])
@admin_required
def set_advertiser_status(adv_id):
    db   = get_db()
    adv  = db.get(Advertiser, adv_id)
    data = request.get_json(silent=True) or {}
    if not adv:
        return jsonify({"error": "Advertiser not found."}), 404

    status = data.get("status")
    reason = str(data.get("reason") or "").strip()

    if status not in TRANSITIONS.get(adv.status, set()):
        return jsonify({"error": f"Can't move from {adv.status} to {status}."}), 400

    if isinstance(data.get("checks"), dict):
        adv.checks = json.dumps({k: bool(v) for k, v in data["checks"].items()})

    if status == "approved":
        blocker = _approval_blocker(adv)
        if blocker:
            db.rollback()
            return jsonify({"error": blocker}), 400
    if status in ("rejected", "suspended") and not reason:
        db.rollback()
        return jsonify({"error": "Give a reason."}), 400

    adv.status         = status
    adv.status_reason  = reason or None
    adv.reviewed_at    = datetime.now(timezone.utc)
    adv.reviewed_by_id = g.user.id
    db.commit()
    return jsonify(_advertiser_json(adv, _names(db, [adv])))
