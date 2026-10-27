"""Print the PostgreSQL schema for ImmHelp (tables, columns, keys, indexes).

Structure only: nothing is read from or written to a database and no rows are exported.
Run from the backend folder:

    python db/export_schema.py > db/schema.sql
"""
import os
import sys

# Only needed so models.py can be imported; no connection is made.
os.environ.setdefault("DATABASE_URL", "postgresql://user@localhost/immhelp")
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy.dialects import postgresql  # noqa: E402
from sqlalchemy.schema import CreateIndex, CreateTable  # noqa: E402

import models  # noqa: E402

dialect = postgresql.dialect()

print("-- ImmHelp PostgreSQL schema (structure only, generated from models.py)")
print("-- Regenerate with: python db/export_schema.py > db/schema.sql")
print()
for table in models.Base.metadata.sorted_tables:
    print(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
    print()
    for index in sorted(table.indexes, key=lambda i: i.name or ""):
        print(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
    if table.indexes:
        print()
