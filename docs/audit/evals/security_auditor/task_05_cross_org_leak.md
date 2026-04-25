# Task 05 — Cross-org leak subtile via filter manquant

**Agent cible** : `security-auditor`
**Difficulté** : hard
**Sprint origin** : Multi-tenant / Fuite

## Prompt exact

> Audit code :
> ```python
> @router.get("/portfolios/{id}/sites")
> def list_sites(id: int, user=Depends(current_user), db=Depends(get_db)):
>     portfolio = resolve_org_id(user, portfolio_id=id)  # check ok
>     return db.query(Site).filter(Site.portfolio_id == id).all()  # mais sites non re-scopés
> ```
> Quel est le problème ?

## Golden output (PASS)

- [ ] Détecte fuite : `Site` non filtré par `org_id` directement
- [ ] Cas attaque : si portfolio_id partagé entre orgs (edge case data), sites org B exposés
- [ ] Sévérité CVE High (pas Critical car nécessite config anormale)
- [ ] CWE-863 (incorrect authorization)
- [ ] Remediation : `filter(Site.portfolio_id == id, Site.org_id == user.org_id)` ou subquery
- [ ] Délègue à `architect-helios` pour pattern strict org-scoping + `implementer` pour fix

## Anti-patterns (FAIL)

- ❌ "OK car resolve_org_id fait le check"
- ❌ Sévérité Low
- ❌ Manque la propagation filter sur table enfant

## Rationale

Fuite subtile realistique. Teste profondeur analyse multi-tenant.
