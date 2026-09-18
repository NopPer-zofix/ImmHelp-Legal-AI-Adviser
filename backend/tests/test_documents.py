"""Document catalogue, .txt ingestion, scan skipping and the download endpoint.
Only OpenAI and the Chroma path are faked."""
import os
import sys
import tempfile
import types
from urllib.parse import quote

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(ROOT)
sys.path.insert(0, ROOT)

_db = os.path.join(tempfile.mkdtemp(prefix="docs_"), "test.db")
os.environ["DATABASE_URL"] = "sqlite:///" + _db.replace("\\", "/")
os.environ.setdefault("OPENAI_API_KEY", "sk-test")

calls = {"router": [], "answer": []}
ROUTER_REPLY = {"value": "TRANSPORT"}


class _Completions:
    @staticmethod
    def create(model, messages, **kw):
        if messages[0]["content"].startswith("You are a ROUTER"):
            calls["router"].append(messages)
            return _reply(ROUTER_REPLY["value"])
        calls["answer"].append(messages)
        return _reply("ANSWER")


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
_tmp = tempfile.mkdtemp(prefix="chroma_docs_")
_real = chromadb.PersistentClient
chromadb.PersistentClient = lambda path=None, **kw: _real(path=_tmp, **kw)

import server

server.init_db()
app = server.app.test_client()

fails = []


def check(name, cond, detail=""):
    print(("  ok   " if cond else "  FAIL ") + name + (f"  <- {detail}" if not cond else ""))
    if not cond:
        fails.append(name)


def sources():
    metas = server.collection.get(include=["metadatas"])["metadatas"]
    return {os.path.basename(m["source"]) for m in metas}


indexed = sources()

print("\n-- .txt is ingested --")
check("website_info.txt indexed", "website_info.txt" in indexed)
check("it is tagged transport", any(
    m["topic"] == "transport" for m in server.collection.get(include=["metadatas"])["metadatas"]
    if os.path.basename(m["source"]) == "website_info.txt"))

print("\n-- catalogue is not treated as content --")
check("catalog.json not indexed", "catalog.json" not in indexed)

print("\n-- scanned PDFs are skipped, not indexed as junk --")
for scan in ("TOM 101.pdf", "TOM 153E.pdf", "TOM7D.pdf", "ΤΟΜ9Γ.pdf",
             "Appointment-arrangiment.pdf"):
    check(f"{scan} skipped", scan not in indexed)

print("\n-- readable PDFs still ingested --")
for good in ("TOM7DEN.pdf", "DoRT_MOT_Test.pdf", "Visa-Application.pdf"):
    check(f"{good} indexed", good in indexed)

print("\n-- manifests --")
tm = server.TOPIC_MANIFESTS["TRANSPORT"]
vm = server.TOPIC_MANIFESTS["VISA"]
check("transport manifest built", len(tm) > 200, f"{len(tm)} chars")
check("visa manifest built", len(vm) > 200, f"{len(vm)} chars")
check("names the 7D form", "TOM 7D" in tm)
check("carries a link", "/documents/transport/TOM7DEN.pdf" in tm)
check("catalogue comment keys excluded", "_comment" not in tm and "_scanned" not in tm)
check("scanned-but-catalogued forms are still offered",
      "TOM 9Γ" in tm and "TOM 153E" in tm and "TOM 101" in tm)
check("a scan offered for download is not in the index",
      quote("TOM 101.pdf") in tm and "TOM 101.pdf" not in indexed)

# Behaviour, not data: a null title must never be offered, whatever the real
# catalogues happen to contain today.
_probe = tempfile.mkdtemp()
os.makedirs(os.path.join(_probe, "visa"), exist_ok=True)
open(os.path.join(_probe, "visa", "named.pdf"), "wb").close()
open(os.path.join(_probe, "visa", "unnamed.pdf"), "wb").close()
with open(os.path.join(_probe, "visa", "catalog.json"), "w", encoding="utf-8") as f:
    f.write('{"_note": "c", "named.pdf": {"title": "A named form", "description": "d"},'
            ' "unnamed.pdf": {"title": null, "description": null}}')
_saved_path = server.DOCUMENTS_PATH
server.DOCUMENTS_PATH = _probe
_probe_manifest = server.build_manifest("visa")
server.DOCUMENTS_PATH = _saved_path
check("null-title entry is excluded", "unnamed.pdf" not in _probe_manifest)
check("titled entry is included", "A named form" in _probe_manifest)
check("comment key excluded", "_note" not in _probe_manifest)
check("visa manifest names MEDU2", "MEDU2" in vm)
check("greek filename is url-encoded",
      quote("ΤΟΜ_46ΒEN.pdf") in tm)
check("general has no manifest", server.TOPIC_MANIFESTS["GENERAL"] == "")

print("\n-- greek filenames resolve across unicode normalisation --")
check("every catalogued visa file resolves on disk",
      all(server.resolve_filename("visa", k) is not None
          for k in server.load_catalog("visa") if not k.startswith("_")))
check("every catalogued transport file resolves on disk",
      all(server.resolve_filename("transport", k) is not None
          for k in server.load_catalog("transport") if not k.startswith("_")))
check("precomposed name finds the decomposed file",
      server.resolve_filename(
          "visa", "Έντυπο-μετα"
                  "γραφής-MEDU2.doc") is not None)
check("release agreement is offered", "Release agreement" in vm)
check("transfer form is offered", "transfer" in vm.lower())
check("a genuinely missing file still resolves to None",
      server.resolve_filename("visa", "definitely-not-here.pdf") is None)

print("\n-- download endpoint --")
r = app.get("/documents/transport/TOM7DEN.pdf")
check("serves a real file", r.status_code == 200, str(r.status_code))
check("served as an attachment", "attachment" in r.headers.get("Content-Disposition", ""))
check("body is a PDF", r.data[:4] == b"%PDF", str(r.data[:8]))

r = app.get("/documents/transport/" + quote("ΤΟΜ_46ΒEN.pdf"))
check("serves a greek-named file", r.status_code == 200, str(r.status_code))

check("unknown topic rejected", app.get("/documents/nope/x.pdf").status_code == 404)
check("missing file 404s", app.get("/documents/transport/nothere.pdf").status_code == 404)
check("catalogue itself is reachable but harmless",
      app.get("/documents/transport/catalog.json").status_code in (200, 404))

print("\n-- path traversal --")
for attack in ("../../server.py", "..%2f..%2fserver.py", "....//server.py",
               "..\\..\\server.py"):
    r = app.get("/documents/transport/" + attack)
    leaked = r.status_code == 200 and b"Flask" in r.data
    check(f"blocked: {attack}", not leaked, f"status {r.status_code}")

print("\n-- manifest reaches the answer prompt --")
r = app.post("/users", json={"email": "d@e.f", "password": "pw", "username": "doctester"})
app.environ_base["HTTP_AUTHORIZATION"] = "Bearer " + r.get_json()["token"]
uid = r.get_json()["id"]
cid = app.post("/chats", json={"user_id": uid}).get_json()["id"]

calls["answer"].clear()
app.post("/ask", json={"user_id": uid, "chat_id": cid,
                       "question": "How do I apply for a Cyprus driving licence?"})
system_msg = calls["answer"][-1][0]["content"]
check("system prompt carries the manifest", "DOWNLOADABLE DOCUMENTS" in system_msg)
check("manifest sits in the system message, not the context",
      "TOM 7D" in system_msg)
check("transport rules still present", "drives on the LEFT" in system_msg)

ROUTER_REPLY["value"] = "VISA"
calls["answer"].clear()
app.post("/ask", json={"user_id": uid, "chat_id": cid,
                       "question": "What do I need for a student permit application?"})
visa_system = calls["answer"][-1][0]["content"]
check("visa turn gets the visa manifest", "MEDU2" in visa_system)
check("visa turn does NOT get transport forms", "TOM 7D" not in visa_system)

print("\n" + ("ALL PASSED" if not fails else f"{len(fails)} FAILED: {fails}"))
sys.exit(1 if fails else 0)
