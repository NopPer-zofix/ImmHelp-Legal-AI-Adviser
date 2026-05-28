from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
import chromadb
import os
import uuid

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import declarative_base
from sqlalchemy import Column, Integer, String, ForeignKey, DateTime
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


# -----------------------------
# MODELS
# -----------------------------
class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    email    = Column(String, unique=True, nullable=False)
    password = Column(String, nullable=False)
    username = Column(String, nullable=False)


class Chat(Base):
    __tablename__ = "chats"

    id      = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)


class Message(Base):
    __tablename__ = "messages"

    id         = Column(Integer, primary_key=True)
    user_id    = Column(Integer, ForeignKey("users.id"), nullable=False)
    chat_id    = Column(Integer, ForeignKey("chats.id"), nullable=False)
    message    = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


app = Flask(__name__)

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
        text += page.extract_text() + "\n"
    return text


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
def ingest_pdf(file_path):
    print(f"Ingesting: {file_path}")
    text   = read_pdf(file_path)
    chunks = chunk_text(text)

    for chunk in chunks:
        existing = collection.get(where={"source": file_path})
        if len(existing["ids"]) > 0:
            return

        embedding = create_embedding(chunk)
        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())],
            metadatas=[{"source": file_path}]
        )
    print("Done")


# -----------------------------
# LOAD PDFs ON STARTUP
# -----------------------------
DOCUMENTS_PATH = "./documents"

for filename in os.listdir(DOCUMENTS_PATH):
    if filename.endswith(".pdf"):
        ingest_pdf(os.path.join(DOCUMENTS_PATH, filename))


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({"status": "ok"})


# -----------------------------
# USER ENDPOINTS
# -----------------------------
@app.route("/users", methods=["POST"])
def create_user():
    db   = SessionLocal()
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

    user = User(email=email, password=password, username=username)
    db.add(user)
    db.commit()
    db.refresh(user)

    return jsonify({
        "id":       user.id,
        "email":    user.email,
        "username": user.username
    }), 201


@app.route("/users/<int:user_id>", methods=["GET"])
def get_user(user_id):
    db   = SessionLocal()
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        return jsonify({"error": "user not found"}), 404

    return jsonify({
        "id":       user.id,
        "email":    user.email,
        "username": user.username
    })


# -----------------------------
# CHAT ENDPOINTS
# -----------------------------
@app.route("/chats", methods=["POST"])
def create_chat():
    db   = SessionLocal()
    data = request.get_json()

    if not data:
        return jsonify({"error": "invalid request"}), 400

    user_id = data.get("user_id")

    if not user_id:
        return jsonify({"error": "user_id is required"}), 400

    if not db.query(User).filter(User.id == user_id).first():
        return jsonify({"error": "user not found"}), 404

    chat = Chat(user_id=user_id)
    db.add(chat)
    db.commit()
    db.refresh(chat)

    return jsonify({
        "id":      chat.id,
        "user_id": chat.user_id
    }), 201


@app.route("/chats/<int:user_id>", methods=["GET"])
def get_user_chats(user_id):
    db = SessionLocal()

    if not db.query(User).filter(User.id == user_id).first():
        return jsonify({"error": "user not found"}), 404

    chats = db.query(Chat).filter(Chat.user_id == user_id).all()

    return jsonify([{
        "id":      c.id,
        "user_id": c.user_id
    } for c in chats])


# -----------------------------
# MESSAGE ENDPOINTS
# -----------------------------
@app.route("/messages/<int:chat_id>", methods=["GET"])
def get_chat_messages(chat_id):
    db = SessionLocal()

    if not db.query(Chat).filter(Chat.id == chat_id).first():
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


# -----------------------------
# RAG ENDPOINT
# -----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    db   = SessionLocal()
    data = request.get_json()

    if not data:
        return jsonify({"error": "invalid request"}), 400

    question = data.get("question")
    user_id  = data.get("user_id")
    chat_id  = data.get("chat_id")

    if not question:
        return jsonify({"error": "question required"}), 400

    # Validate user
    if not db.query(User).filter(User.id == user_id).first():
        return jsonify({"error": "user not found"}), 404

    # Validate chat
    if not db.query(Chat).filter(Chat.id == chat_id).first():
        return jsonify({"error": "chat not found"}), 404

    # Save message to PostgreSQL
    db.add(Message(user_id=user_id, chat_id=chat_id, message=question))
    db.commit()

    # -----------------------------------
    # VECTOR SEARCH
    # -----------------------------------
    question_embedding = create_embedding(question)

    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=5
    )

    context = "\n\n".join(results["documents"][0])

    # -----------------------------------
    # GPT RESPONSE
    # -----------------------------------
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": f"Answer using the provided context.\n\nContext:\n{context}"
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    answer = response.choices[0].message.content

    # Save assistant reply to DB
    db.add(Message(user_id=user_id, chat_id=chat_id, message=f"[assistant] {answer}"))
    db.commit()

    return jsonify({"answer": answer})


if __name__ == "__main__":
    Base.metadata.create_all(bind=engine)
    app.run(debug=True)