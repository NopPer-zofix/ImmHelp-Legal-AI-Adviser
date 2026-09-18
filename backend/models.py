"""Database engine, session handling and all SQLAlchemy models.

Moved out of server.py so auth.py and admin_api.py can use the models without
importing server (which ingests PDFs on import).
"""
import os

from dotenv import load_dotenv
from flask import g
from sqlalchemy import (Boolean, Column, DateTime, ForeignKey, Integer, String, Text,
                        create_engine, inspect, text)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.sql import func

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base = declarative_base()


def get_db():
    """One session per request, closed in close_db() when the request ends.

    The routes used to call SessionLocal() and never close it, which leaks a
    Postgres connection per request.
    """
    if "db" not in g:
        g.db = SessionLocal()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# -----------------------------
# MODELS
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    email    = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    username = Column(String, nullable=False)

    # "user" or "admin". Promote someone with: python make_admin.py you@example.com
    role          = Column(String(20), nullable=False, default="user", server_default="user")
    is_banned     = Column(Boolean, nullable=False, default=False, server_default=text("false"))
    banned_reason = Column(String, nullable=True)
    banned_at     = Column(DateTime(timezone=True), nullable=True)
    created_at    = Column(DateTime(timezone=True), server_default=func.now())

    # Registration notice the user accepted (see the frontend's src/lib/consent.js)
    consent_version     = Column(String(40), nullable=True)
    consent_accepted_at = Column(DateTime(timezone=True), nullable=True)


class Chat(Base):
    __tablename__ = "chats"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title   = Column(String(120), nullable=True)   # set when the user renames the chat


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id    = Column(Integer, ForeignKey("chats.id"), nullable=False)
    message    = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class ChatState(Base):
    """Per-chat state that is not itself a message.

    `compacted_through_id` is a watermark, not a delete: every message stays in the
    messages table for /messages, but anything at or below the watermark has been
    folded into `profile` and is no longer re-sent to the model on each turn.
    """
    __tablename__ = "chat_state"

    chat_id              = Column(Integer, ForeignKey("chats.id"), primary_key=True)
    profile              = Column(String, nullable=False, default="")
    compacted_through_id = Column(Integer, nullable=False, default=0)
    last_topics          = Column(String, nullable=False, default="")
    updated_at           = Column(DateTime(timezone=True), server_default=func.now(),
                                  onupdate=func.now())


class Advertiser(Base):
    """A company that may run ads. Managed by admins in the frontend's /admin/ads page."""
    __tablename__ = "advertisers"

    id             = Column(Integer, primary_key=True)
    company        = Column(String, nullable=False)
    reg_number     = Column(String, nullable=False)
    website        = Column(String, nullable=False)
    category       = Column(String(40), nullable=False)
    licence_number = Column(String, nullable=False, default="")
    contact_name   = Column(String, nullable=False)
    contact_email  = Column(String, nullable=False)
    contact_phone  = Column(String, nullable=False, default="")
    topics         = Column(String, nullable=False, default="")    # "VISA,REAL_ESTATE"
    notes          = Column(Text, nullable=False, default="")

    # pending | approved | rejected | suspended
    status         = Column(String(20), nullable=False, default="pending")
    status_reason  = Column(String, nullable=True)
    checks         = Column(Text, nullable=False, default="{}")    # JSON: {"registration": true, ...}

    created_at     = Column(DateTime(timezone=True), server_default=func.now())
    created_by_id  = Column(Integer, ForeignKey("users.id"), nullable=True)
    reviewed_at    = Column(DateTime(timezone=True), nullable=True)
    reviewed_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)


# -----------------------------
# SCHEMA SETUP
# -----------------------------
# create_all() makes missing tables but never changes existing ones, so columns
# added after a table was first created are added here. Safe to run on every start.
_ADDED_COLUMNS = {
    "users": {
        "role":                {"postgresql": "VARCHAR(20) NOT NULL DEFAULT 'user'",
                                "sqlite":     "VARCHAR(20) NOT NULL DEFAULT 'user'"},
        "is_banned":           {"postgresql": "BOOLEAN NOT NULL DEFAULT FALSE",
                                "sqlite":     "BOOLEAN NOT NULL DEFAULT 0"},
        "banned_reason":       {"postgresql": "VARCHAR", "sqlite": "VARCHAR"},
        "banned_at":           {"postgresql": "TIMESTAMPTZ", "sqlite": "DATETIME"},
        # Existing users get the migration time as their join date
        "created_at":          {"postgresql": "TIMESTAMPTZ DEFAULT now()", "sqlite": "DATETIME"},
        "consent_version":     {"postgresql": "VARCHAR(40)", "sqlite": "VARCHAR(40)"},
        "consent_accepted_at": {"postgresql": "TIMESTAMPTZ", "sqlite": "DATETIME"},
    },
    "chats": {
        "title": {"postgresql": "VARCHAR(120)", "sqlite": "VARCHAR(120)"},
    },
}


def init_db():
    Base.metadata.create_all(bind=engine)

    dialect = engine.dialect.name
    inspector = inspect(engine)
    with engine.begin() as conn:
        for table, columns in _ADDED_COLUMNS.items():
            existing = {c["name"] for c in inspector.get_columns(table)}
            for name, ddl in columns.items():
                if name not in existing:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl.get(dialect, ddl['postgresql'])}"))
                    print(f"Database: added {table}.{name}")
