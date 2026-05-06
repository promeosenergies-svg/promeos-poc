"""PROMEOS Phase 7.6 — Pre-commit hooks systémiques (ADR-016 Pilier 5).

3 hooks cardinaux empêchent récidive angles morts Phase C audit transversal Phase 5.7 :
- check_alembic_no_drop : anti-DROP autogenerate Alembic
- check_sqlite_pragma_fk : anti-PRAGMA foreign_keys=OFF SQLite
- check_math_consistency : anti-erreur-arithmétique formules YAML/ADR
"""
