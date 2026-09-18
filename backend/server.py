from flask import Flask, request, jsonify, g, send_from_directory
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.exceptions import NotFound
from urllib.parse import quote
import chromadb
import json
import os
import re
import sys
import unicodedata
import uuid
from datetime import datetime, timezone

import compaction

# engine, SessionLocal and Base are re-exported for the tests and scripts that use server.*
from models import (engine, SessionLocal, Base, User, Chat, Message, ChatState,
                    get_db, close_db, init_db)
from auth import login_required, user_payload, banned_response, is_self_or_admin
from admin_api import admin_bp

load_dotenv()

# Windows consoles are usually cp125x/cp1251: a Greek document name in a log line
# would otherwise raise UnicodeEncodeError and take startup down with it.
for _stream in (sys.stdout, sys.stderr):
    try:
        _stream.reconfigure(errors="replace")
    except (AttributeError, ValueError):
        pass

app = Flask(__name__)
app.teardown_appcontext(close_db)
app.register_blueprint(admin_bp)

# OpenAI
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Persistent ChromaDB
chroma_client = chromadb.PersistentClient(path="./chroma_db")
collection = chroma_client.get_or_create_collection(name="knowledge")


# -----------------------------
# EMBEDDINGS
# -----------------------------
def create_embedding(text):
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding


# -----------------------------
# PDF READING
# -----------------------------
def read_pdf(file_path):
    reader = PdfReader(file_path)
    text = ""
    for page in reader.pages:
        text += (page.extract_text() or "") + "\n"
    return text


def read_document(file_path):
    if file_path.lower().endswith(".pdf"):
        return read_pdf(file_path)

    with open(file_path, "r", encoding="utf-8") as f:
        return f.read()


# -----------------------------
# TEXT CHUNKING
# -----------------------------
def chunk_text(text, chunk_size=1000):
    chunks = []
    for i in range(0, len(text), chunk_size):
        chunks.append(text[i:i + chunk_size])
    return chunks


# -----------------------------
# INGEST PDFs
# -----------------------------
def ingest_document(file_path, topic):
    # Already indexed - checked once per file, not once per chunk
    existing = collection.get(where={"source": file_path})
    if len(existing["ids"]) > 0:
        return

    text = read_document(file_path)

    # Scanned forms have no text layer. Indexing them adds empty or single-character
    # chunks that pollute retrieval, so skip them - they stay downloadable via the
    # catalogue, they are just not searchable until someone OCRs them.
    if len(text.strip()) < MIN_INGEST_CHARS:
        print(f"Skipping [{topic}]: {file_path} - only {len(text.strip())} chars of text. "
              f"Still downloadable; OCR it to make it searchable.")
        return

    print(f"Ingesting [{topic}]: {file_path}")
    chunks = chunk_text(text)

    for chunk in chunks:
        embedding = create_embedding(chunk)
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())],
            metadatas=[{"source": file_path, "topic": topic}]
        )
    print("Done")


def purge_untagged_chunks():
    """Drop chunks indexed before topics existed - they carry no `topic` metadata
    and stale paths, so a topic-filtered query would never return them."""
    existing = collection.get(include=["metadatas"])
    stale = [
        chunk_id
        for chunk_id, meta in zip(existing["ids"], existing["metadatas"])
        if not (meta or {}).get("topic")
    ]
    if stale:
        print(f"Removing {len(stale)} untagged chunks from a previous index...")
        collection.delete(ids=stale)


# -----------------------------
# PROMPTS
# -----------------------------
# The old single system_prompt.txt is superseded by these: shared rules live in
# system_prompt_base.txt, everything topic-specific in the per-topic files.
_BASE_DIR = os.path.dirname(__file__)


def load_prompt(filename):
    path = os.path.join(_BASE_DIR, filename)
    try:
        with open(path, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        print(f"Warning: {filename} not found at {path}. Proceeding without it.")
        return ""


# Shared rules, prepended to whichever topic prompt the router picks
SYSTEM_PROMPT = load_prompt("system_prompt_base.txt")

# Router: reads the question and replies with topic labels only
ORCHESTRATOR_PROMPT = load_prompt("sys_prompt_orchestrator.txt")

# GENERAL deliberately has no specialist prompt - it runs on the base prompt alone
TOPIC_PROMPTS = {
    "VISA":        load_prompt("system_prompt_visa.txt"),
    "TRANSPORT":   load_prompt("system_prompt_transport.txt"),
    "REAL_ESTATE": load_prompt("system_prompt_realestate.txt"),
    "GENERAL":     "",
}

# Topic label -> documents/<folder>, which is also the `topic` tag on each chunk
TOPIC_FOLDERS = {
    "VISA":        "visa",
    "TRANSPORT":   "transport",
    "REAL_ESTATE": "real_estate",
    "GENERAL":     "general",
}

OUT_OF_SCOPE_ANSWER = (
    "Your request is not clear, I am an AI which is trained for immigration help answers. "
    "Please use me accordingly."
)

NO_CONTEXT_NOTE = (
    "No reference documents matched this question. Answer from general knowledge within the "
    "rules above, and tell the user which details they must confirm with the competent authority."
)


# -----------------------------
# ROUTER
# -----------------------------
def classify_topic(question, history_messages, prior_topics=""):
    """Ask the router which topic prompt should handle this question.
    Returns a list of labels, or ["OUT_OF_SCOPE"]. Falls back to GENERAL.

    All the router needs is what topic the chat is currently on. The previous turn's
    labels say that in ~10 tokens; the recent user turns say it in ~120. Re-sending
    the assistant answers costs ~700 tokens each and adds almost no routing signal.
    """
    if not ORCHESTRATOR_PROMPT:
        return ["GENERAL"]

    if prior_topics:
        hint = [{"role": "user",
                 "content": f"[the previous turn in this chat was routed: {prior_topics}]"}]
    else:
        hint = [m for m in history_messages if m.get("role") == "user"][-3:]

    try:
        response = client.chat.completions.create(
            model="gpt-4.1-mini",
            temperature=0,
            max_tokens=16,
            messages=(
                [{"role": "system", "content": ORCHESTRATOR_PROMPT}]
                + hint
                + [{"role": "user", "content": question}]
            )
        )
        raw = response.choices[0].message.content or ""
    except Exception as e:
        print(f"Router call failed ({e}); falling back to GENERAL.")
        return ["GENERAL"]

    # Strip stray punctuation the model may append to a label
    labels = [re.sub(r"[^A-Z_]", "", part.upper()) for part in raw.split(",")]
    labels = [l for l in labels if l in TOPIC_PROMPTS or l == "OUT_OF_SCOPE"]

    if not labels:
        print(f"Router returned an unusable label ({raw!r}); falling back to GENERAL.")
        return ["GENERAL"]
    if "OUT_OF_SCOPE" in labels:
        return ["OUT_OF_SCOPE"]
    return labels[:2]


# -----------------------------
# LOAD PDFs ON STARTUP
# -----------------------------
DOCUMENTS_PATH = "./documents"

INGEST_EXTENSIONS = (".pdf", ".txt", ".md")

MIN_INGEST_CHARS = 200

CATALOG_FILENAME = "catalog.json"

PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")


def document_url(folder, filename):
    return f"{PUBLIC_BASE_URL}/documents/{folder}/{quote(filename)}"


def resolve_filename(folder, filename):
    folder_path = os.path.join(DOCUMENTS_PATH, folder)

    if os.path.isfile(os.path.join(folder_path, filename)):
        return filename

    target = unicodedata.normalize("NFC", filename)

    try:
        for real in os.listdir(folder_path):
            if unicodedata.normalize("NFC", real) == target:
                return real
    except FileNotFoundError:
        pass

    return None


def load_catalog(folder):
    path = os.path.join(DOCUMENTS_PATH, folder, CATALOG_FILENAME)

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}
    except (json.JSONDecodeError, UnicodeDecodeError) as e:
        print(f"Warning: {path} is not valid JSON ({e}). No downloads offered for {folder}.")
        return {}


def build_manifest(folder):
   
    entries = []

    for filename, meta in sorted(load_catalog(folder).items()):
        if filename.startswith("_"):
            continue

        title = (meta or {}).get("title")
        if not title:
            print(f"Note: {folder}/{filename} has no title in {CATALOG_FILENAME}; "
                  f"not offered for download.")
            continue

        real_name = resolve_filename(folder, filename)
        if real_name is None:
            print(f"Warning: {folder}/{CATALOG_FILENAME} lists {filename}, "
                  f"which does not exist on disk.")
            continue

        description = (meta or {}).get("description", "")
        entries.append(f"- {title}"
                       + (f" - {description}" if description else "")
                       + f"\n  Link: {document_url(folder, real_name)}")

    if not entries:
        return ""

    return ("DOWNLOADABLE DOCUMENTS available for this topic.\n"
            "When one of these is the form or reference the user actually needs, give its "
            "title and its link, copied exactly as written here. Offer only what is relevant "
            "to the question - do not list them all. Never invent a link, never offer a "
            "document that is not on this list, and never claim to know the contents of a "
            "document beyond the description given here.\n\n"
            + "\n".join(entries))


purge_untagged_chunks()

# Each sub-folder is a topic; its name becomes the `topic` tag on every chunk inside
for label, folder in TOPIC_FOLDERS.items():
    folder_path = os.path.join(DOCUMENTS_PATH, folder)

    if not os.path.isdir(folder_path):
        print(f"Warning: {folder_path} is missing, nothing ingested for {label}.")
        continue

    for filename in sorted(os.listdir(folder_path)):
        if filename == CATALOG_FILENAME:
            continue
        if filename.lower().endswith(INGEST_EXTENSIONS):
            ingest_document(os.path.join(folder_path, filename), folder)



TOPIC_MANIFESTS = {label: build_manifest(folder) for label, folder in TOPIC_FOLDERS.items()}


# -----------------------------
# DOCUMENT DOWNLOADS
# -----------------------------
@app.route("/documents/<topic>/<path:filename>", methods=["GET"])
def get_document(topic, filename):
   
    if topic not in TOPIC_FOLDERS.values():
        return jsonify({"error": "unknown topic"}), 404

    real_name = resolve_filename(topic, filename)
    if real_name is None:
        return jsonify({"error": "document not found"}), 404

    try:
        return send_from_directory(
            os.path.join(DOCUMENTS_PATH, topic), real_name, as_attachment=True
        )
    except NotFound:
        return jsonify({"error": "document not found"}), 404


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok"})


def own_chat(db, chat_id):
    """The chat if it belongs to the logged-in user (admins may read any), else None."""
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if chat and is_self_or_admin(chat.user_id):
        return chat
    return None


# -----------------------------
# USER ENDPOINTS
# -----------------------------
@app.route("/users", methods=["POST"])
def create_user():
    db   = get_db()
    data = request.get_json()

    if not data:
        return jsonify({"error": "invalid request"}), 400

    email    = data.get("email")
    password = data.get("password")
    username = data.get("username")

    if not all([email, password, username]):
        return jsonify({"error": "email, password and username are required"}), 400

    if db.query(User).filter(User.email == email).first():
        return jsonify({"error": "email already registered"}), 409

    user = User(email=email, password=generate_password_hash(password), username=username)

    # The frontend sends the version of the registration notice the user accepted
    consent = data.get("consent")
    if isinstance(consent, dict) and consent.get("version"):
        user.consent_version     = str(consent["version"])[:40]
        user.consent_accepted_at = datetime.now(timezone.utc)

    db.add(user)
    db.commit()
    db.refresh(user)

    # Registering also logs the user in
    return jsonify(user_payload(user)), 201


@app.route("/users/<int:user_id>", methods=["GET"])
@login_required
def get_user(user_id):
    db   = get_db()
    user = db.query(User).filter(User.id == user_id).first()

    if not user or not is_self_or_admin(user_id):
        return jsonify({"error": "user not found"}), 404

    return jsonify({
        "id":       user.id,
        "email":    user.email,
        "username": user.username,
        "role":     user.role
    })


# -----------------------------
# LOGIN ENDPOINT
# -----------------------------
@app.route("/login", methods=["POST"])
def login():
    db   = get_db()
    data = request.get_json()

    if not data:
        return jsonify({"error": "invalid request"}), 400

    email    = data.get("email")
    password = data.get("password")

    if not all([email, password]):
        return jsonify({"error": "email and password are required"}), 400

    user = db.query(User).filter(User.email == email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "invalid email or password"}), 401

    if user.is_banned:
        return banned_response()

    return jsonify(user_payload(user))


# -----------------------------
# CHAT ENDPOINTS
# -----------------------------
@app.route("/chats", methods=["POST"])
@login_required
def create_chat():
    db = get_db()

    # The chat always belongs to the caller; a user_id in the body is ignored
    user_id = g.user.id

    chat = Chat(user_id=user_id)
    db.add(chat)
    db.commit()
    db.refresh(chat)

    return jsonify({
        "id":      chat.id,
        "user_id": chat.user_id
    }), 201


@app.route("/chats/<int:user_id>", methods=["GET"])
@login_required
def get_user_chats(user_id):
    db = get_db()

    if not is_self_or_admin(user_id) or not db.query(User).filter(User.id == user_id).first():
        return jsonify({"error": "user not found"}), 404

    chats = db.query(Chat).filter(Chat.user_id == user_id).order_by(Chat.id).all()

    return jsonify([{
        "id":      c.id,
        "user_id": c.user_id,
        "title":   c.title
    } for c in chats])


@app.route("/chats/<int:chat_id>", methods=["PATCH"])
@login_required
def rename_chat(chat_id):
    db   = get_db()
    data = request.get_json(silent=True) or {}
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == g.user.id).first()

    if not chat:
        return jsonify({"error": "chat not found"}), 404

    title = " ".join(str(data.get("title", "")).split())[:120]
    if not title:
        return jsonify({"error": "title is required"}), 400

    chat.title = title
    db.commit()
    return jsonify({"id": chat.id, "user_id": chat.user_id, "title": chat.title})


@app.route("/chats/<int:chat_id>", methods=["DELETE"])
@login_required
def delete_chat(chat_id):
    db   = get_db()
    chat = db.query(Chat).filter(Chat.id == chat_id, Chat.user_id == g.user.id).first()

    if not chat:
        return jsonify({"error": "chat not found"}), 404

    # Children first: messages and chat_state reference the chat
    db.query(Message).filter(Message.chat_id == chat_id).delete()
    db.query(ChatState).filter(ChatState.chat_id == chat_id).delete()
    db.delete(chat)
    db.commit()
    return jsonify({"deleted": chat_id})


# -----------------------------
# MESSAGE ENDPOINTS
# -----------------------------
@app.route("/messages/<int:chat_id>", methods=["GET"])
@login_required
def get_chat_messages(chat_id):
    db = get_db()

    if not own_chat(db, chat_id):
        return jsonify({"error": "chat not found"}), 404

    messages = (
        db.query(Message)
        .filter(Message.chat_id == chat_id)
        .order_by(Message.created_at)
        .all()
    )

    return jsonify([{
        "id":         m.id,
        "user_id":    m.user_id,
        "chat_id":    m.chat_id,
        "message":    m.message,
        "created_at": m.created_at.isoformat()
    } for m in messages])


@app.route("/messages", methods=["POST"])
@login_required
def create_message():
    db   = get_db()
    data = request.get_json()

    if not data:
        return jsonify({"error": "invalid request"}), 400

    user_id = g.user.id
    chat_id = data.get("chat_id")
    message = data.get("message")
    role    = data.get("role", "assistant")

    if not all([chat_id, message]):
        return jsonify({"error": "chat_id and message are required"}), 400

    if role not in ("user", "assistant"):
        return jsonify({"error": "role must be 'user' or 'assistant'"}), 400

    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat or chat.user_id != user_id:
        return jsonify({"error": "chat not found"}), 404

    # Prefix assistant messages consistently with the existing convention
    content = f"[assistant] {message}" if role == "assistant" else message
    m = Message(user_id=user_id, chat_id=chat_id, message=content)
    db.add(m)
    db.commit()
    db.refresh(m)

    return jsonify({
        "id":         m.id,
        "user_id":    m.user_id,
        "chat_id":    m.chat_id,
        "message":    m.message,
        "created_at": m.created_at.isoformat()
    }), 201


# -----------------------------
# CHAT HISTORY
# -----------------------------
ASSISTANT_PREFIX = "[assistant] "


def load_history(db, chat_id, after_id, before_id):
    """Rebuild the conversation from Postgres as (ids, messages), oldest first.

    Role is recovered from the stored "[assistant] " prefix, which is how rows have
    always been written. Returns ids in parallel so compaction can turn a position in
    the list back into a watermark.
    """
    rows = (
        db.query(Message)
        .filter(Message.chat_id == chat_id,
                Message.id > after_id,
                Message.id < before_id)
        .order_by(Message.id)
        .all()
    )

    ids, messages = [], []
    for row in rows:
        if row.message.startswith(ASSISTANT_PREFIX):
            messages.append({"role": "assistant",
                             "content": row.message[len(ASSISTANT_PREFIX):]})
        else:
            messages.append({"role": "user", "content": row.message})
        ids.append(row.id)

    return ids, messages


def get_chat_state(db, chat_id):
    state = db.query(ChatState).filter(ChatState.chat_id == chat_id).first()

    if not state:
        state = ChatState(chat_id=chat_id, profile="",
                          compacted_through_id=0, last_topics="")
        db.add(state)
        db.commit()
        db.refresh(state)

    return state


# -----------------------------
# RAG ENDPOINT
# -----------------------------
@app.route("/ask", methods=["POST"])
@login_required
def ask():
    db   = get_db()
    data = request.get_json()

    if not data:
        return jsonify({"error": "invalid request"}), 400

    question = data.get("question")
    user_id  = g.user.id          # from the token; a user_id in the body is ignored
    chat_id  = data.get("chat_id")
    history  = data.get("history", [])  # optional fallback; history is read from the DB

    if not question:
        return jsonify({"error": "question required"}), 400

    if len(question.strip()) < 10:
        return jsonify({"answer": "Your request is too short for me to properly answer it. Please describe your immigration or study-in-Cyprus question in more detail."})

    # Validate chat: it must exist and belong to the caller
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    if not chat or chat.user_id != user_id:
        return jsonify({"error": "chat not found"}), 404

    # Save message to PostgreSQL
    user_message = Message(user_id=user_id, chat_id=chat_id, message=question)
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    # -----------------------------------
    # HISTORY
    # -----------------------------------
    # Authoritative history comes from Postgres, not the request body: one source of
    # truth, and it gives compaction somewhere to keep its state.
    state = get_chat_state(db, chat_id)
    history_ids, history_messages = load_history(
        db, chat_id,
        after_id=state.compacted_through_id,
        before_id=user_message.id
    )

    # Clients that pass their own history still work on a chat with no stored rows
    if not history_messages and history:
        valid_roles = {"user", "assistant"}
        history_messages = [
            {"role": m["role"], "content": m["content"]}
            for m in history
            if isinstance(m, dict)
            and m.get("role") in valid_roles
            and isinstance(m.get("content"), str)
        ]
        history_ids = []

    # -----------------------------------
    # COMPACTION
    # -----------------------------------
    # Only once the chat crosses the high-water mark. The dropped turns stay in
    # Postgres for /messages; the watermark just stops them being re-sent every turn.
    if history_ids and compaction.needs_compaction(history_messages):
        dropped, kept = compaction.split_for_compaction(history_messages)

        if dropped:
            state.profile = compaction.extract_profile(client, dropped, state.profile)
            state.compacted_through_id = history_ids[len(dropped) - 1]
            db.commit()
            history_messages = kept
            print(f"Compacted chat {chat_id}: folded {len(dropped)} messages into the "
                  f"profile, watermark now {state.compacted_through_id}")

    # -----------------------------------
    # ROUTE THE QUESTION
    # -----------------------------------
    topics = classify_topic(question, history_messages, state.last_topics)

    if topics == ["OUT_OF_SCOPE"]:
        # last_topics is deliberately left alone - a refusal should not become the
        # anchor that the next follow-up gets routed against
        db.add(Message(
            user_id=user_id,
            chat_id=chat_id,
            message=f"[assistant] {OUT_OF_SCOPE_ANSWER}"
        ))
        db.commit()
        return jsonify({"answer": OUT_OF_SCOPE_ANSWER, "topics": topics})

    state.last_topics = ",".join(topics)
    db.commit()

    # -----------------------------------
    # VECTOR SEARCH, LIMITED TO THE ROUTED TOPICS
    # -----------------------------------
    question_embedding = create_embedding(question)

    # "general" is always searched alongside the routed folders as a fallback
    folders = sorted({TOPIC_FOLDERS[t] for t in topics} | {"general"})

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=5,
        where={"topic": {"$in": folders}}
    )

    documents = results["documents"][0] if results["documents"] else []
    context   = "\n\n".join(documents)

    # -----------------------------------
    # BUILD MESSAGES: base + topic prompt(s) + context + history
    # -----------------------------------
    context_block = (
        f"Answer using the provided context.\n\nContext:\n{context}"
        if context else NO_CONTEXT_NOTE
    )

    system_prompt = "\n\n".join(filter(None,
        [SYSTEM_PROMPT]
        + [TOPIC_PROMPTS.get(t, "") for t in topics]
        + [TOPIC_MANIFESTS.get(t, "") for t in topics]
    ))

    # Cache-friendly order: [system][profile][history][context][question].
    # The context changes every turn, so it goes last - keeping it in the system
    # message would put the whole history downstream of a varying block.
    messages = compaction.build_messages(
        system_prompt, state.profile, history_messages, context_block, question
    )

    # -----------------------------------
    # GPT RESPONSE
    # -----------------------------------
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=messages
    )

    answer = response.choices[0].message.content

    # Save assistant reply to DB
    db.add(Message(user_id=user_id, chat_id=chat_id, message=f"[assistant] {answer}"))
    db.commit()

    return jsonify({"answer": answer, "topics": topics})


if __name__ == "__main__":
    init_db()   # creates tables and adds any new columns to existing ones
    app.run(debug=os.getenv("FLASK_DEBUG") == "1")