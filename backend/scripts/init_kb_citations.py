"""Initialize KB citations + rule_cards schema in production KB."""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.kb.models import get_kb_db
from app.kb.citations import init_citations_schema

db = get_kb_db()
init_citations_schema(db.conn)
print("KB citations schema initialized OK")

# Verify tables
cursor = db.conn.cursor()
for table in ["kb_citations", "kb_rule_cards", "kb_rule_card_citations"]:
    cursor.execute(f"SELECT COUNT(*) FROM {table}")
    count = cursor.fetchone()[0]
    print(f"  {table}: {count} rows")
