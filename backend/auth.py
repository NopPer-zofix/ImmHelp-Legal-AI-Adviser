"""Token authentication and role checks.

/login and /users return a signed token (JWT). The frontend sends it back as
`Authorization: Bearer <token>`, and every protected route looks the caller up
from it. The user id in a request body or URL is never trusted on its own.
"""
import os
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps

import jwt
from flask import g, jsonify, request

from models import User, get_db

TOKEN_LIFETIME = timedelta(days=7)

JWT_SECRET = os.getenv("JWT_SECRET")
if not JWT_SECRET:
    # Works for local development, but every restart logs everyone out.
    JWT_SECRET = secrets.token_hex(32)
    print("Warning: JWT_SECRET is not set in .env, so logins won't survive a server restart.")

BANNED_MESSAGE = "This account has been suspended. Contact support if you think this is a mistake."


def issue_token(user):
    now = datetime.now(timezone.utc)
    payload = {"sub": str(user.id), "role": user.role, "iat": now, "exp": now + TOKEN_LIFETIME}
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def user_payload(user):
    """What /login and /users return: the public profile plus a fresh token."""
    return {
        "id":       user.id,
        "email":    user.email,
        "username": user.username,
        "role":     user.role,
        "token":    issue_token(user),
    }


def banned_response():
    return jsonify({"error": BANNED_MESSAGE, "code": "banned"}), 403


def _user_from_token():
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    try:
        payload = jwt.decode(header[7:], JWT_SECRET, algorithms=["HS256"])
    except jwt.PyJWTError:
        return None
    # Always re-read the user: a ban or a role change applies on the next request
    return get_db().get(User, int(payload["sub"]))


def login_required(view):
    @wraps(view)
    def wrapper(*args, **kwargs):
        user = _user_from_token()
        if user is None:
            return jsonify({"error": "Your session has expired. Log in again.", "code": "unauthorized"}), 401
        if user.is_banned:
            return banned_response()
        g.user = user
        return view(*args, **kwargs)
    return wrapper


def admin_required(view):
    @login_required
    @wraps(view)
    def wrapper(*args, **kwargs):
        if g.user.role != "admin":
            return jsonify({"error": "Admin access required.", "code": "forbidden"}), 403
        return view(*args, **kwargs)
    return wrapper


def is_self_or_admin(user_id):
    return g.user.id == user_id or g.user.role == "admin"
