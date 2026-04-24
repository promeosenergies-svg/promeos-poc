# Task 02 — Endpoint sans org-scoping

**Agent cible** : `code-reviewer`
**Difficulté** : easy
**Sprint origin** : Sécurité

## Prompt exact

> Revue : `@router.get("/sites/{site_id}/kpi")\ndef kpi(site_id: int, db=Depends(get_db)):\n    return db.query(Site).filter(Site.id == site_id).first()`

## Golden output (PASS)

- [ ] Flag severity P0 (fuite cross-org)
- [ ] Détecte absence `resolve_org_id`
- [ ] Suggestion : ajouter `user = Depends(current_user)` + `resolve_org_id(user, site_id)`
- [ ] Délègue à `security-auditor` pour audit approfondi

## Anti-patterns (FAIL)

- ❌ Laisse passer
- ❌ Flag P2
- ❌ Ignore dimension multi-tenant

## Rationale

Vulnérabilité critique multi-tenant. P0 systématique.
