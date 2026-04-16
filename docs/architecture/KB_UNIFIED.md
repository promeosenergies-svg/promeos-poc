# KB Architecture Decision

**Date** : 2026-04-16
**Décision** : Option A — Unifier sur `app/kb/` (FTS5 engine)
**Auteur** : Claude Code + Amine

## Raison

Basé sur le bilan Phase 0 (audit 16/04/2026) :

- **System 1** (`routes/kb_usages.py`) : 1067 lignes, 6 tables SQLAlchemy dans promeos.db,
  13 endpoints, stable en production. **Pas d'org-scoping** (P0 sécurité).
- **System 2** (`app/kb/`) : 8 modules, SQLite+FTS5 dans kb.db, apply engine déterministe,
  draft/validated lifecycle. Plus extensible.

System 2 (`app/kb/`) est retenu car :
1. Apply engine déterministe (scope + logic.when) — prêt pour injection agents
2. FTS5 full-text search natif
3. Lifecycle draft → validated → deprecated
4. Schéma extensible (tags_json, scope_json, logic_json)

System 1 (`kb_usages.py`) reste en place pour les archetypes/anomaly_rules/recommendations
(tables SQLAlchemy dans promeos.db). Pas de migration destructive.

## Impact

| Fichier | Action |
|---------|--------|
| `backend/data/kb/taxonomy.yaml` | CRÉER — taxonomie canonique |
| `backend/scripts/kb_ingest_constants.py` | CRÉER — ingestion 11 constantes dans kb.db |
| `backend/scripts/kb_export_skills.py` | CRÉER — sync kb.db → .claude/skills/ |
| `backend/routes/kb_usages.py` | MODIFIER — ajouter org-scoping |
| `backend/ai_layer/agents/*.py` | MODIFIER — injection contexte KB |
| `backend/models/annotation.py` | CRÉER — table annotations |
| `backend/models/annotator_profile.py` | CRÉER — profils annotateurs |

## Tests baseline

- Backend : `python -m pytest tests/ -v` (état avant modification)
- KB spécifiques : à créer dans cette branche
