"""Exercise the new routing machinery with a stubbed OpenAI client and a throwaway
Chroma path, so nothing hits the API and the real ./chroma_db is untouched."""
import os
import sys
import tempfile
import types

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

os.environ.setdefault("DATABASE_URL", "postgresql://u:p@localhost/none")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

ROUTER_REPLY = {"value": "VISA"}
chat_calls = []


class _FakeEmbeddings:
    def create(self, model, input):
        return types.SimpleNamespace(data=[types.SimpleNamespace(embedding=[0.1] * 8)])


class _FakeChat:
    class completions:
        @staticmethod
        def create(model, messages, **kw):
            chat_calls.append({"model": model, "messages": messages, "kw": kw})
            return types.SimpleNamespace(
                choices=[types.SimpleNamespace(
                    message=types.SimpleNamespace(content=ROUTER_REPLY["value"]))]
            )


class FakeOpenAI:
    def __init__(self, api_key=None):
        self.embeddings = _FakeEmbeddings()
        self.chat = _FakeChat()


import openai
openai.OpenAI = FakeOpenAI

import chromadb
_tmp = tempfile.mkdtemp(prefix="chroma_smoke_")
_real_client = chromadb.PersistentClient
chromadb.PersistentClient = lambda path=None, **kw: _real_client(path=_tmp, **kw)

import server

failures = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {detail}" if not cond and detail else ""))
    if not cond:
        failures.append(name)


print("\n-- prompts loaded --")
check("base prompt", len(server.SYSTEM_PROMPT) > 200, f"{len(server.SYSTEM_PROMPT)} chars")
check("orchestrator prompt", len(server.ORCHESTRATOR_PROMPT) > 200, f"{len(server.ORCHESTRATOR_PROMPT)} chars")
for label in ("VISA", "TRANSPORT", "REAL_ESTATE"):
    check(f"topic prompt {label}", len(server.TOPIC_PROMPTS[label]) > 200,
          f"{len(server.TOPIC_PROMPTS[label])} chars")
check("GENERAL has no topic prompt", server.TOPIC_PROMPTS["GENERAL"] == "")

print("\n-- ingestion tagged by folder --")
all_chunks = server.collection.get(include=["metadatas"])
topics = {}
for meta in all_chunks["metadatas"]:
    topics[meta.get("topic")] = topics.get(meta.get("topic"), 0) + 1
print("   chunks per topic:", topics)
check("visa chunks indexed", topics.get("visa", 0) > 0)
check("every chunk carries a topic", None not in topics)
check("sources point at documents/visa",
      all("visa" in m["source"] for m in all_chunks["metadatas"]))

print("\n-- topic-filtered retrieval --")
emb = server.create_embedding("test")
hit = server.collection.query(query_embeddings=[emb], n_results=5,
                              where={"topic": {"$in": ["visa", "general"]}})
miss = server.collection.query(query_embeddings=[emb], n_results=5,
                               where={"topic": {"$in": ["transport", "general"]}})
check("visa filter returns chunks", len(hit["documents"][0]) > 0)
check("transport filter returns nothing (no docs yet)", len(miss["documents"][0]) == 0)
check("empty result is handled, not crashed", ("\n\n".join(miss["documents"][0])) == "")

print("\n-- router output parsing --")
cases = [
    ("VISA", ["VISA"]),
    ("  visa \n", ["VISA"]),
    ("VISA.", ["VISA"]),
    ("VISA,REAL_ESTATE", ["VISA", "REAL_ESTATE"]),
    ("REAL_ESTATE, VISA", ["REAL_ESTATE", "VISA"]),
    ('"TRANSPORT"', ["TRANSPORT"]),
    ("OUT_OF_SCOPE", ["OUT_OF_SCOPE"]),
    ("VISA,TRANSPORT,REAL_ESTATE", ["VISA", "TRANSPORT"]),
    ("GENERAL", ["GENERAL"]),
    ("I think this is about visas", ["GENERAL"]),
    ("", ["GENERAL"]),
]
for reply, expected in cases:
    ROUTER_REPLY["value"] = reply
    got = server.classify_topic("some question", [])
    check(f"{reply!r} -> {expected}", got == expected, f"got {got}")

print("\n-- router call shape --")
chat_calls.clear()
ROUTER_REPLY["value"] = "VISA"
hist = []
for i in range(5):
    hist.append({"role": "user", "content": f"q{i}"})
    hist.append({"role": "assistant", "content": "a" * 3000})
server.classify_topic("q", hist)
call = chat_calls[-1]
check("temperature pinned to 0", call["kw"].get("temperature") == 0)
check("max_tokens capped", call["kw"].get("max_tokens") == 16)
check("orchestrator prompt is the system message",
      call["messages"][0]["content"] == server.ORCHESTRATOR_PROMPT)
check("router gets user turns only, capped at 3",
      len(call["messages"]) == 1 + 3 + 1, f"{len(call['messages'])} msgs")
check("no assistant answers sent to the router",
      all(m["role"] == "user" for m in call["messages"][1:]))

chat_calls.clear()
server.classify_topic("q", hist, "VISA")
call = chat_calls[-1]
check("prior-topic hint replaces history entirely", len(call["messages"]) == 1 + 1 + 1,
      f"{len(call['messages'])} msgs")
check("hint names the prior topic", "routed: VISA" in call["messages"][1]["content"])

print("\n-- router failure falls back --")
def boom(*a, **k):
    raise RuntimeError("api down")
_saved = server.client.chat.completions.create
server.client.chat.completions.create = boom
check("exception -> GENERAL", server.classify_topic("q", []) == ["GENERAL"])
server.client.chat.completions.create = _saved

print("\n-- system prompt assembly --")
for topics_in, must_contain in [
    (["VISA"], "Before arriving in Cyprus"),
    (["TRANSPORT"], "drives on the LEFT"),
    (["REAL_ESTATE"], "independent lawyer"),
]:
    parts = [server.SYSTEM_PROMPT] + [server.TOPIC_PROMPTS.get(t, "") for t in topics_in] + ["ctx"]
    content = "\n\n".join(filter(None, parts))
    check(f"{topics_in} prompt includes its topic rules", must_contain.lower() in content.lower())
    check(f"{topics_in} prompt includes base rules", "SHARED BASE PROMPT" in content)

combined = "\n\n".join(filter(None, [server.SYSTEM_PROMPT]
                              + [server.TOPIC_PROMPTS[t] for t in ["VISA", "REAL_ESTATE"]] + ["ctx"]))
check("two-label prompt carries both topics",
      "before arriving in cyprus" in combined.lower() and "independent lawyer" in combined.lower())

print("\n-- purge of untagged chunks --")
server.collection.add(documents=["legacy chunk"], embeddings=[[0.1] * 8],
                      ids=["legacy-1"], metadatas=[{"source": "./documents/old.pdf"}])
before = len(server.collection.get()["ids"])
server.purge_untagged_chunks()
after = server.collection.get()["ids"]
check("legacy chunk removed", "legacy-1" not in after, f"{before} -> {len(after)}")
check("tagged chunks survive", len(after) == before - 1)

print("\n" + ("ALL PASSED" if not failures else f"{len(failures)} FAILED: {failures}"))
sys.exit(1 if failures else 0)
