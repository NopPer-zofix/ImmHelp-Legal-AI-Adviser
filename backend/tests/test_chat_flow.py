"""End-to-end: real Flask routes, real SQLAlchemy (SQLite), real compaction.
Only OpenAI and the Chroma path are faked."""
import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

_db = os.path.join(tempfile.mkdtemp(prefix="e2e_"), "test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _db.replace("\\", "/")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

calls = {"router": [], "answer": [], "profile": []}
ROUTER_REPLY = {"value": "VISA"}


class _Completions:
    @staticmethod
    def create(model, messages, **kw):
        import compaction as _c
        head = messages[0]["content"]
        if head.startswith("You are a ROUTER"):
            calls["router"].append(messages)
            return _reply(ROUTER_REPLY["value"])
        if head.startswith(_c.PROFILE_SYSTEM_PROMPT[:40]):
            calls["profile"].append(messages)
            return _reply("Ukrainian national, third-country; student track; not yet in Cyprus.")
        calls["answer"].append(messages)
        return _reply("ANSWER " + "word " * 700)      # ~750 tokens, like a real reply


def _reply(text):
    return types.SimpleNamespace(
        choices=[types.SimpleNamespace(message=types.SimpleNamespace(content=text))])


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.embeddings = types.SimpleNamespace(
            create=lambda model, input: types.SimpleNamespace(
                data=[types.SimpleNamespace(embedding=[0.1] * 8)]))
        self.chat = types.SimpleNamespace(completions=_Completions())


import openai
openai.OpenAI = FakeOpenAI

import chromadb
_tmp = tempfile.mkdtemp(prefix="chroma_e2e_")
_real = chromadb.PersistentClient
chromadb.PersistentClient = lambda path=None, **kw: _real(path=_tmp, **kw)

import server
import compaction

server.init_db()
app = server.app.test_client()

fails = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {detail}" if not cond else ""))
    if not cond:
        fails.append(name)


# ---------------------------------------------------------------- setup
r = app.post("/users", json={"email": "a@b.c", "password": "pw", "username": "tester"})
uid = r.get_json()["id"]
# Every route except /users, /login and /ping needs the token from registration
app.environ_base["HTTP_AUTHORIZATION"] = "Bearer " + r.get_json()["token"]
cid = app.post("/chats", json={"user_id": uid}).get_json()["id"]

QUESTIONS = [
    "What documents do I need for a student visa for Cyprus?",
    "How long does the student permit take to be issued?",
    "What about renewing it after the first year?",
    "Do I need health insurance for the application?",
    "Which bank account proof is accepted for funds?",
    "How early before expiry should I file the renewal?",
    "What happens if my permit lapses while I wait?",
    "Do I need an apostille on my degree certificate?",
    "What medical tests are required before arriving?",
    "Can I change university without losing my permit?",
    "What supporting documents does the transfer need?",
    "How much are the application fees in total?",
    "Does my sponsor need to sign anything official?",
    "What proof of address will they accept from me?",
]

print("\n-- multi-turn chat --")
for i, q in enumerate(QUESTIONS):
    resp = app.post("/ask", json={"user_id": uid, "chat_id": cid, "question": q})
    check(f"turn {i+1} answered", resp.status_code == 200 and "answer" in resp.get_json(),
          str(resp.get_json())[:120]) if i in (0, len(QUESTIONS) - 1) else None

print("\n-- history rebuilt from the DB, not the request body --")
second = calls["answer"][1]
roles = [m["role"] for m in second]
check("turn 2 saw turn 1 without any history being posted",
      any(m["role"] == "assistant" for m in second), str(roles))
check("assistant prefix stripped when rebuilding",
      all(not m["content"].startswith("[assistant] ") for m in second))

print("\n-- message order is cache-friendly --")
last = calls["answer"][-1]
check("system first", last[0]["role"] == "system")
check("profile block present and second",
      last[1]["role"] == "system" and last[1]["content"].startswith("Known about this user:"),
      last[1]["content"][:60])
check("context is the second-to-last message",
      last[-2]["role"] == "system" and "Context:" in last[-2]["content"])
check("question is last", last[-1]["role"] == "user" and last[-1]["content"] == QUESTIONS[-1])

print("\n-- compaction fired --")
db = server.SessionLocal()
state = db.query(server.ChatState).filter(server.ChatState.chat_id == cid).first()
check("compaction ran", len(calls["profile"]) >= 1, f"{len(calls['profile'])} extractions")
check("watermark advanced", state.compacted_through_id > 0, f"={state.compacted_through_id}")
check("profile stored", state.profile.startswith("Ukrainian"), state.profile[:60])
check("last_topics stored", state.last_topics == "VISA", state.last_topics)

print("\n-- nothing was deleted --")
stored = app.get(f"/messages/{cid}").get_json()
check("every turn still in the DB", len(stored) == len(QUESTIONS) * 2,
      f"{len(stored)} rows for {len(QUESTIONS)} turns")

print("\n-- prompt size stopped growing --")
sizes = [sum(compaction.estimate_tokens(m["content"]) for m in c) for c in calls["answer"]]
peak = max(sizes)
check("final prompt smaller than the peak", sizes[-1] < peak, f"peak {peak}, final {sizes[-1]}")
print(f"       per-turn tokens: {sizes[0]} -> peak {peak} -> {sizes[-1]}")

print("\n-- router input is small --")
router_sizes = [sum(compaction.estimate_tokens(m["content"]) for m in c) for c in calls["router"]]
orch = compaction.estimate_tokens(server.ORCHESTRATOR_PROMPT)
check("router sends little beyond its own prompt", max(router_sizes) - orch < 200,
      f"max {max(router_sizes)}, prompt {orch}")
check("router got the prior-topic hint, not the answers",
      any("previous turn in this chat was routed" in m["content"] for m in calls["router"][-1]))

print("\n-- out of scope --")
ROUTER_REPLY["value"] = "OUT_OF_SCOPE"
before_answers = len(calls["answer"])
resp = app.post("/ask", json={"user_id": uid, "chat_id": cid,
                              "question": "Write me a Python script that sorts a list"})
body = resp.get_json()
check("canned refusal returned", body["answer"] == server.OUT_OF_SCOPE_ANSWER)
check("no answer call made", len(calls["answer"]) == before_answers)
db.expire_all()
state = db.query(server.ChatState).filter(server.ChatState.chat_id == cid).first()
check("last_topics not overwritten by a refusal", state.last_topics == "VISA", state.last_topics)

print("\n-- follow-up after the refusal still routes to VISA --")
ROUTER_REPLY["value"] = "VISA"
app.post("/ask", json={"user_id": uid, "chat_id": cid, "question": "And what about the renewal fee?"})
check("prior-topic hint survived the refusal",
      any("routed: VISA" in m["content"] for m in calls["router"][-1]))

print("\n-- a fresh chat starts clean --")
cid2 = app.post("/chats", json={"user_id": uid}).get_json()["id"]
calls["answer"].clear()
app.post("/ask", json={"user_id": uid, "chat_id": cid2, "question": "How do I rent a flat in Limassol?"})
first = calls["answer"][-1]
check("no profile block on a new chat",
      not any(m["content"].startswith("Known about this user:") for m in first))
check("no history leaked from the other chat", len(first) == 3, f"{len(first)} messages")

print("\n" + ("ALL PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
