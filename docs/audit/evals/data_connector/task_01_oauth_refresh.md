# Task 01 — OAuth2 refresh DataConnect Enedis

**Agent cible** : `data-connector`
**Difficulté** : easy
**Sprint origin** : Enedis / OAuth

## Prompt exact

> Le token DataConnect Enedis expire dans 2 min. Implémente le refresh automatique sans fuite secret.

## Golden output (PASS)

- [ ] Pattern refresh-before-expire (buffer 5 min)
- [ ] `client_id` / `client_secret` via env vars (jamais code)
- [ ] Retry exponentiel si refresh fail
- [ ] Skill `@promeos-enedis/SKILL.md`
- [ ] Délègue à `security-auditor` pour review secrets

## Anti-patterns (FAIL)

- ❌ Hardcode client_secret
- ❌ Refresh on-401 (pattern fragile)
- ❌ Retry infini

## Rationale

Plumbing OAuth standard mais critique. Fuite secret = incident majeur.
