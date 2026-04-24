# Task 04 — XSS via dangerouslySetInnerHTML

**Agent cible** : `security-auditor`
**Difficulté** : medium
**Sprint origin** : Frontend / XSS

## Prompt exact

> Code React : `<div dangerouslySetInnerHTML={{ __html: site.description }} />` avec `site.description` venant de API. Audit.

## Golden output (PASS)

- [ ] Détecte XSS stored P0 High/Critical
- [ ] CWE-79
- [ ] Vecteur : input non-sanitized rendu HTML
- [ ] Remediation : `DOMPurify.sanitize(html)` OU suppression du pattern
- [ ] Délègue à `implementer` pour fix

## Anti-patterns (FAIL)

- ❌ "safe si l'API sanitize en amont" sans preuve
- ❌ Medium (sous-estimation)
- ❌ Pas de DOMPurify suggéré

## Rationale

Anti-pattern frontend dangereux. Test rigueur sur périmètre React.
