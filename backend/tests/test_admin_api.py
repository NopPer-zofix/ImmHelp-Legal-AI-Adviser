"""Auth, ownership, admin dashboard, bans and advertisers, on a throwaway SQLite DB.
OpenAI and the Chroma path are faked, as in test_chat_flow.py.

    python tests/test_admin_api.py
"""
import os
import sqlite3
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

_db = os.path.join(tempfile.mkdtemp(prefix="admin_"), "test.db")

# An "old" database from before this change: no role/ban/consent columns, no chat titles.
# init_db() must add them without losing rows.
with sqlite3.connect(_db) as conn:
    conn.executescript("""
        CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR UNIQUE NOT NULL,
                            password VARCHAR NOT NULL, username VARCHAR NOT NULL);
        CREATE TABLE chats (id INTEGER PRIMARY KEY, user_id INTEGER NOT NULL REFERENCES users(id));
        INSERT INTO users (email, password, username) VALUES ('old@user.cy', 'x', 'Old User');
    """)

os.environ["DATABASE_URL"] = "sqlite:///" + _db.replace("\\", "/")
os.environ["OPENAI_API_KEY"] = "sk-test"
os.environ["JWT_SECRET"] = "test-secret"


def _reply(text):
    return types.SimpleNamespace(choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=text))])


class _Completions:
    @staticmethod
    def create(model, messages, **kw):
        if messages[0]["content"].startswith("You are a ROUTER"):
            return _reply("VISA")
        return _reply("A short answer.")


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.embeddings = types.SimpleNamespace(
            create=lambda model, input: types.SimpleNamespace(data=[types.SimpleNamespace(embedding=[0.1] * 8)]))
        self.chat = types.SimpleNamespace(completions=_Completions())


import openai
openai.OpenAI = FakeOpenAI

import chromadb
_tmp = tempfile.mkdtemp(prefix="chroma_admin_")
_real = chromadb.PersistentClient
chromadb.PersistentClient = lambda path=None, **kw: _real(path=_tmp, **kw)

import server
from models import SessionLocal, User

fails = []


def check(name, cond):
    print(("  ok   " if cond else "  FAIL ") + name)
    if not cond:
        fails.append(name)


def client(token=None):
    c = server.app.test_client()
    if token:
        c.environ_base["HTTP_AUTHORIZATION"] = "Bearer " + token
    return c


anon = client()

# ---------------------------------------------------------------- migration
print("-- old database gets the new columns --")
server.init_db()
with SessionLocal() as db:
    old = db.query(User).filter(User.email == "old@user.cy").first()
    check("existing user kept", old is not None)
    check("existing user is a regular user", old.role == "user" and old.is_banned is False)
server.init_db()
check("running init_db twice is fine", True)

# ---------------------------------------------------------------- auth
print("-- registration and login --")
r = anon.post("/users", json={"email": "ann@x.cy", "password": "pw", "username": "Ann",
                              "consent": {"version": "2026-09-18"}})
ann = r.get_json()
check("register returns 201 with token and role", r.status_code == 201 and ann.get("token") and ann["role"] == "user")
with SessionLocal() as db:
    check("consent version stored", db.get(User, ann["id"]).consent_version == "2026-09-18")

r = anon.post("/login", json={"email": "ann@x.cy", "password": "pw"})
check("login returns a token", r.status_code == 200 and r.get_json().get("token"))

check("no token → 401", anon.post("/chats", json={}).status_code == 401)
check("bad token → 401", client("nonsense").get(f"/chats/{ann['id']}").status_code == 401)

A = client(ann["token"])
bob = anon.post("/users", json={"email": "bob@x.cy", "password": "pw", "username": "Bob"}).get_json()
B = client(bob["token"])

print("-- chats belong to their owner --")
cid = A.post("/chats", json={"user_id": bob["id"]}).get_json()
check("chat is created for the caller, not the body's user_id", cid["user_id"] == ann["id"])
cid = cid["id"]
check("owner can ask", A.post("/ask", json={"chat_id": cid, "question": "What documents do I need for a student visa?"}).status_code == 200)
A.post("/ask", json={"chat_id": cid, "question": "what documents do I need for a student visa"})
check("another user can't ask in it", B.post("/ask", json={"chat_id": cid, "question": "What documents do I need?"}).status_code == 404)
check("another user can't read it", B.get(f"/messages/{cid}").status_code == 404)
check("another user can't list Ann's chats", B.get(f"/chats/{ann['id']}").status_code == 404)

r = A.patch(f"/chats/{cid}", json={"title": "  Student   visa  "})
check("rename works and tidies spaces", r.status_code == 200 and r.get_json()["title"] == "Student visa")
check("title comes back in the list", A.get(f"/chats/{ann['id']}").get_json()[0]["title"] == "Student visa")
check("another user can't rename it", B.patch(f"/chats/{cid}", json={"title": "x"}).status_code == 404)

tmp = A.post("/chats").get_json()["id"]
A.post("/ask", json={"chat_id": tmp, "question": "How do I renew my residence permit?"})
check("another user can't delete it", B.delete(f"/chats/{tmp}").status_code == 404)
check("owner deletes chat with its messages", A.delete(f"/chats/{tmp}").status_code == 200
      and A.get(f"/messages/{tmp}").status_code == 404)

# ---------------------------------------------------------------- admin
print("-- admin access --")
check("regular user gets 403 on admin routes", A.get("/admin/users").status_code == 403)

with SessionLocal() as db:
    db.get(User, bob["id"]).role = "admin"
    db.commit()
Admin = B   # role is read from the database on every request, so the old token now works as admin

s = Admin.get("/admin/stats").get_json()
# 2 questions left: the deleted chat took its question with it
check("stats count users and questions", s["users"] == 3 and s["messages_total"] == 2 and s["messages_7d"] == 2 and s["banned_users"] == 0)

top = Admin.get("/admin/top-questions?days=7").get_json()
check("top questions group case and punctuation", top[0]["count"] == 2 and "student visa" in top[0]["question"].lower())
check("assistant replies aren't counted", all(not q["question"].startswith("[assistant]") for q in top))

users = {u["email"]: u for u in Admin.get("/admin/users").get_json()}
check("users list includes activity", users["ann@x.cy"]["message_count"] == 2 and users["ann@x.cy"]["last_active_at"])

print("-- bans --")
check("admin can't ban self", Admin.post(f"/admin/users/{bob['id']}/ban", json={}).status_code == 400)
r = Admin.post(f"/admin/users/{ann['id']}/ban", json={"reason": "Spam"})
check("ban works", r.status_code == 200)
r = A.get(f"/chats/{ann['id']}")
check("banned user's token stops working at once", r.status_code == 403 and r.get_json()["code"] == "banned")
check("banned user can't log in", anon.post("/login", json={"email": "ann@x.cy", "password": "pw"}).status_code == 403)
check("reason is visible to admins", {u["email"]: u for u in Admin.get("/admin/users").get_json()}["ann@x.cy"]["banned_reason"] == "Spam")
Admin.post(f"/admin/users/{ann['id']}/unban")
check("unban restores access", A.get(f"/chats/{ann['id']}").status_code == 200)

# ---------------------------------------------------------------- advertisers
print("-- advertisers --")
base = {"company": "Seaside Homes", "reg_number": "HE 1", "website": "https://seaside.example",
        "category": "real_estate", "contact_name": "Nikos", "contact_email": "n@seaside.example",
        "topics": ["REAL_ESTATE"]}
check("regular user can't list advertisers", A.get("/admin/advertisers").status_code == 403)
check("bad website rejected", Admin.post("/admin/advertisers", json={**base, "website": "seaside"}).status_code == 400)
check("unknown topic rejected", Admin.post("/admin/advertisers", json={**base, "topics": ["FOOD"]}).status_code == 400)

r = Admin.post("/admin/advertisers", json=base)
adv = r.get_json()
check("created as pending with the creator's name", r.status_code == 201 and adv["status"] == "pending" and adv["created_by"] == "Bob")

aid = adv["id"]
all_checks = {"registration": True, "website": True, "licence": True}
r = Admin.post(f"/admin/advertisers/{aid}/status", json={"status": "approved", "checks": all_checks})
check("no approval without a licence number", r.status_code == 400 and "licence" in r.get_json()["error"])
Admin.patch(f"/admin/advertisers/{aid}", json={"licence_number": "EARC 1"})
r = Admin.post(f"/admin/advertisers/{aid}/status", json={"status": "approved", "checks": {"registration": True}})
check("no approval with checks missing", r.status_code == 400)
r = Admin.post(f"/admin/advertisers/{aid}/status", json={"status": "approved", "checks": all_checks})
check("approval with everything in place", r.status_code == 200 and r.get_json()["reviewed_by"] == "Bob")

r = Admin.patch(f"/admin/advertisers/{aid}", json={"notes": "Called them"})
check("editing notes keeps it approved", r.get_json()["status"] == "approved")
r = Admin.patch(f"/admin/advertisers/{aid}", json={"website": "https://new-seaside.example"})
check("editing the website sends it back to review", r.get_json()["status"] == "pending"
      and r.get_json()["sent_back_to_review"] and r.get_json()["checks"] == {})

check("reject needs a reason", Admin.post(f"/admin/advertisers/{aid}/status", json={"status": "rejected"}).status_code == 400)
r = Admin.post(f"/admin/advertisers/{aid}/status", json={"status": "rejected", "reason": "No licence"})
check("reject with reason", r.status_code == 200 and r.get_json()["status_reason"] == "No licence")
check("rejected can't jump to approved", Admin.post(f"/admin/advertisers/{aid}/status",
      json={"status": "approved", "checks": all_checks}).status_code == 400)
check("rejected can go back to review", Admin.post(f"/admin/advertisers/{aid}/status", json={"status": "pending"}).status_code == 200)

print()
print("ALL PASSED" if not fails else f"{len(fails)} FAILED: {fails}")
sys.exit(1 if fails else 0)
