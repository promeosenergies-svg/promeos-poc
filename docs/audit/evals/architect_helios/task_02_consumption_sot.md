# Task 02 — SoT consommation unifiée

**Agent cible** : `architect-helios`
**Difficulté** : easy
**Sprint origin** : EMS / SoT

## Prompt exact

> Une nouvelle feature veut calculer la conso totale d'un portefeuille. Quelle SoT utiliser et pourquoi ?

## Contexte fourni

- Skill : `@.claude/skills/helios_architecture/SKILL.md`

## Golden output (PASS = tous cochés)

- [ ] Cite `backend/services/consumption_unified_service.py` comme SoT
- [ ] Rappelle org-scoping obligatoire via `resolve_org_id`
- [ ] Refuse nouvelle aggrégation custom
- [ ] Délégue implémentation à `implementer`

## Anti-patterns (FAIL si présent)

- ❌ Autorise `session.query(Conso).sum()` custom
- ❌ Oublie org-scoping
- ❌ Écrit le code directement

## Rationale

Respect strict des SoT critiques. Erreur ici = fragmentation conso.
