"""Entry point for gunicorn in Docker: `gunicorn wsgi:app`.

`python server.py` still works for local development; it calls init_db() itself.
"""
from models import init_db

# Create tables and add new columns before the app starts taking requests
init_db()

from server import app  # noqa: E402  (importing server also indexes new documents)
