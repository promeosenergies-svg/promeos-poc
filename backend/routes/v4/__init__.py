"""Routes V4 — endpoints `/api/v4/*` du Centre d'Action (Sprint M2-4).

Séparé des routers legacy (`routes/*.py`) : les routes V4 dépendent
systématiquement de `populate_org_context` + `require_v4_role` et passent
exclusivement par les repositories org-scopés `BaseRepositoryV4`.
"""
