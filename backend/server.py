from flask import Flask, request, jsonify
from openai import OpenAI
from dotenv import load_dotenv
from pypdf import PdfReader
import chromadb
import os
import uuid

load_dotenv()

app = Flask(__name__)

# OpenAI
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY")
)

# Persistent ChromaDB
chroma_client = chromadb.PersistentClient(
    path="./chroma_db"
)

collection = chroma_client.get_or_create_collection(
    name="knowledge"
)


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
        chunk = text[i:i + chunk_size]
        chunks.append(chunk)

    return chunks


# -----------------------------
# INGEST PDFs
# -----------------------------
def ingest_pdf(file_path):

    print(f"Ingesting: {file_path}")

    text = read_pdf(file_path)

    chunks = chunk_text(text)

    for chunk in chunks:
        embedding = create_embedding(chunk)

        existing = collection.get(
            where={"source": file_path}
        )

        if len(existing["ids"]) > 0:
            return

        collection.add(
            documents=[chunk],
            embeddings=[embedding],
            ids=[str(uuid.uuid4())],
            metadatas=[{
                "source": file_path
            }]
        )

    print("Done")


# -----------------------------
# LOAD PDFs ON STARTUP
# -----------------------------
DOCUMENTS_PATH = "./documents"

for filename in os.listdir(DOCUMENTS_PATH):
    if filename.endswith(".pdf"):
        ingest_pdf(
            os.path.join(DOCUMENTS_PATH, filename)
        )


# -----------------------------
# HEALTH CHECK
# -----------------------------
@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok"
    })


# -----------------------------
# RAG ENDPOINT
# -----------------------------
@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()

    if not data or "question" not in data:
        return jsonify({
            "error": "question field required"
        }), 400

    question = data["question"]

    # Create embedding for question
    question_embedding = create_embedding(question)

    # Search vector DB
    results = collection.query(
        query_embeddings=[question_embedding],
        n_results=5
    )

    documents = results["documents"][0]

    context = "\n\n".join(documents)

    # Ask GPT
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
Answer the user's question using the context below.

Context:
{context}
"""
            },
            {
                "role": "user",
                "content": question
            }
        ]
    )

    answer = response.choices[0].message.content

    return jsonify({
        "question": question,
        "answer": answer,
        "sources": results["metadatas"][0]
    })


if __name__ == "__main__":
    app.run(debug=True)