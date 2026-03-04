"""
PROMEOS KB Module
Knowledge Base management with FTS5 search and apply engine
"""

from .models import KBDatabase, get_kb_db

__all__ = ["KBDatabase", "get_kb_db"]
