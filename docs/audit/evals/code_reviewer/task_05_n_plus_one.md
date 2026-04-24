# Task 05 — Détecter N+1 query SQLAlchemy

**Agent cible** : `code-reviewer`
**Difficulté** : hard
**Sprint origin** : Perf backend

## Prompt exact

> Revue :
> ```python
> sites = db.query(Site).filter(Site.org_id == org_id).all()
> result = [{"name": s.name, "bills_count": len(s.bills)} for s in sites]
> ```

## Golden output (PASS)

- [ ] Flag severity P1 (N+1 query)
- [ ] Identifie le lazy-load `s.bills` dans la boucle
- [ ] Suggestion : `joinedload(Site.bills)` ou subquery count
- [ ] Quantifie impact (ex: 100 sites = 101 queries)
- [ ] Délégue à `architect-helios` si pattern récurrent cross-module

## Anti-patterns (FAIL)

- ❌ Manque le N+1
- ❌ Suggère "optimiser plus tard" (pas de fix concret)
- ❌ Propose dénormalisation sans trade-off

## Rationale

Détecter perf issue subtile. Révélateur de profondeur d'analyse.
