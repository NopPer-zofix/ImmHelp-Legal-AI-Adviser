from flask import Flask, request, jsonify
from openai import OpenAI
import chromadb
from dotenv import load_dotenv
import os

load_dotenv()

app = Flask(__name__)

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Chroma setup
chroma_client = chromadb.Client()

collection = chroma_client.get_or_create_collection(
    name="documents"
)

# Add some example knowledge
collection.add(
    documents=[
        "Paris is the capital of France",
        "Python is a programming language",
        "ChromaDB is a vector database"
    ],
    ids=["1", "2", "3"]
)


@app.route("/ping", methods=["GET"])
def ping():
    return jsonify({
        "status": "ok"
    })


@app.route("/ask", methods=["POST"])
def ask():
    data = request.get_json()

    if not data or "question" not in data:
        return jsonify({
            "error": "question field required"
        }), 400

    question = data["question"]

    # Search relevant docs
    results = collection.query(
        query_texts=[question],
        n_results=2
    )

    context_docs = results["documents"][0]
    context = "\n".join(context_docs)

    # Ask ChatGPT
    response = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {
                "role": "system",
                "content": f"""
Use the following context to answer questions.

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
        "context": context_docs,
        "answer": answer
    })


if __name__ == "__main__":
    app.run(debug=True)