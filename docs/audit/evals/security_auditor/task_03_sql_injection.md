# Task 03 — SQL injection via string concat

**Agent cible** : `security-auditor`
**Difficulté** : medium
**Sprint origin** : SQL / Injection

## Prompt exact

> Code : `db.execute(f"SELECT * FROM sites WHERE org_id = {user_input}")`. Audit.

## Golden output (PASS)

- [ ] Détecte SQL injection P0 Critical
- [ ] CWE-89
- [ ] Vecteur : f-string avec input non-sanitized
- [ ] Remediation : paramètres liés (`text(":id")`, `.params(id=user_input)`)
- [ ] Délègue à `implementer` pour fix immédiat

## Anti-patterns (FAIL)

- ❌ Sévérité Medium (sous-estimation)
- ❌ Suggère "sanitize input" (insuffisant)
- ❌ Pas de CWE

## Rationale

Vulnérabilité classique OWASP top 10. Test rigueur CVE-like.
