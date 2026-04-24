# Task 01 — Vérifier baseline BE

**Agent cible** : `test-engineer`
**Difficulté** : easy
**Sprint origin** : Baseline

## Prompt exact

> Quelle est la baseline BE actuelle sur `origin/main` ? Comment la vérifier ?

## Golden output (PASS)

- [ ] Commande : `cd backend && python -m pytest --collect-only | tail -1`
- [ ] Compare à seuil doctrine CLAUDE.md (BE ≥ 843)
- [ ] Délègue à `qa-guardian` pour verdict FINAL
- [ ] Cite source CLAUDE.md

## Anti-patterns (FAIL)

- ❌ Donne un nombre fixe sans vérification live
- ❌ Oublie `origin/main` comme référence

## Rationale

Basique, teste connaissance outillage + source doctrine.
