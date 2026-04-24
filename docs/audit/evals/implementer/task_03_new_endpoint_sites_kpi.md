# Task 03 — Nouvel endpoint `/api/sites/{id}/kpi`

**Agent cible** : `implementer`
**Difficulté** : medium
**Sprint origin** : EMS / API

## Prompt exact

> Implémente `GET /api/sites/{site_id}/kpi` qui retourne conso totale + CO₂ + score conformité pour un site. ADR déjà validé par architect-helios.

## Contexte fourni

- SoT conso : `consumption_unified_service.py`
- SoT CO₂ : `config/emission_factors.py:get_emission_factor`
- SoT scoring : `regops/scoring.py`

## Golden output (PASS)

- [ ] Endpoint avec `resolve_org_id(user, site_id)` org-scoping
- [ ] Utilise `consumption_unified_service` (pas de query custom)
- [ ] CO₂ via `get_emission_factor("ELEC")` (pas hardcode)
- [ ] Pydantic response model
- [ ] Commit message canonical
- [ ] Délégue à `test-engineer` + `code-reviewer`

## Anti-patterns (FAIL)

- ❌ Pas d'org-scoping (fuite cross-org)
- ❌ Hardcode 0.052
- ❌ Query SQL directe sans SoT

## Rationale

Cas d'usage récurrent : créer endpoint respectant 3 SoT + org-scoping.
