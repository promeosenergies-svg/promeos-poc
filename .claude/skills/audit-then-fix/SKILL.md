---
name: audit-then-fix
description: Use whenever modifying code in HELIOS / Promeos repo. Enforces the doctrine "audit AVANT fix" — read fully, diagnose in writing, plan, then fix, then test, then verify source-guards. Triggers on any task involving code modification, bug fix, refactor, feature addition, or response to user reports of broken behavior.
---

# Audit Then Fix — Méthodo doctrinale Promeos

Skill socle. Référencée par `decret-tertiaire`, `bill-intelligence-fr`, `cee-p6`, et toute Skill régulatoire future.

## Principe directeur

Aucune modification de code sans audit préalable écrit. La doctrine 12 principes l'impose, le sprint nav l'a validé sur 14 itérations consécutives. Le coût d'un audit raté est inférieur au coût d'une régression sur 6 027 tests.

## Workflow obligatoire — 6 phases

### Phase 0 — STOP gate read-only

Avant toute édition :

- Lire intégralement les fichiers cibles (pas de skim, pas de grep partiel)
- Lire les tests associés (`backend/tests/test_<module>*.py`, `tests/source_guards/test_*_source_guards.py` correspondants)
- Lire les constantes doctrinales si module régulatoire (`backend/doctrine/constants.py`, `backend/config/tarifs_reglementaires.yaml`)
- Identifier le périmètre exact : fichiers touchés, fichiers protégés à éviter, source-guards qui couvrent la zone

**Sortie attendue** : récap écrit "voici ce que j'ai lu, voici ce que je comprends de l'état actuel". Pas de modification autorisée tant que ce récap n'est pas produit.

### Phase 1 — Audit structuré

Format imposé :

- ✅ Constats validés (ce qui marche bien, à préserver)
- ⚠️ Constats à risque (ce qui marche mais fragile, dépendances cachées)
- ❌ Constats bloquants (ce qui est cassé, incohérent, ou viole la doctrine)

Chaque constat est sourcé : `fichier:ligne` ou `test:nom_test`. Pas de constat flou.

### Phase 2 — Plan P0/P1/P2

- **P0** : bloquants pilote, sécurité, valeurs fausses, navigation morte, crash
- **P1** : crédibilité B2B, calculs, unités, cohérence cross-écran, messages d'erreur
- **P2** : best-in-world, guiding, automation, premium UX

Chaque action du plan inclut : fichier(s) à toucher, logique à ajouter, tests à créer/modifier, source-guards à vérifier ou ajouter.

### Phase 3 — Implémentation atomique

Une action P0/P1/P2 = un commit. Format imposé :

```
fix(module-pN): Phase X.Y — description courte FR/EN

Détails techniques EN.

Refs: #issue, doctrine principle Y
```

Règles de modification :

- Constantes régulatoires : flux exclusif via `backend/doctrine/constants.py`. Jamais en dur.
- Tarifs : flux exclusif via `backend/config/tarifs_reglementaires.yaml`.
- Nomenclature : "Marché de gros" jamais "Post-ARENH" ; "NEBCO" jamais "NEBEF".
- Fichiers protégés (validation explicite avant édition) : `backend/database/migrations.py`, `backend/doctrine/constants.py`, `backend/config/tarifs_reglementaires.yaml`, `backend/services/consumption_unified_service.py`, source-guards.

### Phase 4 — Tests & QA

Avant de considérer une action terminée :

- `pytest -x -q` doit être vert (~6 027 tests, plancher de non-régression)
- `pytest backend/tests/ -k source_guards -x -q` doit être vert (46 tests SG)
- `pytest tests/doctrine/ -x -q` doit être vert (9 tests)
- Si modification frontend : Vitest vert + build clean
- Si modification UX visible : audit Playwright screenshots si la zone est sous SDK CX/UX/UI agent

Tests obligatoires à créer/modifier selon contexte :

- Module régulatoire touché → test source-guard ajouté ou étendu
- Nouveau KPI → test unitaire formule + test cohérence cross-écran
- Nouvelle constante → test présence dans `backend/doctrine/constants.py`

### Phase 5 — DoD checklist

Conditions exactes pour fermer une action :

- [ ] Audit Phase 0+1 produit en écrit
- [ ] Plan P0/P1/P2 explicite
- [ ] Commit(s) atomique(s) au format doctrinal
- [ ] `pytest -x -q` vert
- [ ] Source-guards verts (46 tests)
- [ ] Doctrine verte (9 tests)
- [ ] Build frontend clean si applicable
- [ ] MCP code-review + simplify exécutés sur le diff
- [ ] Aucun fichier protégé modifié sans validation explicite tracée
- [ ] Nomenclature respectée (Marché de gros / NEBCO)
- [ ] Constantes régulatoires routées via doctrine/constants.py

## MCP obligatoires (sur tout diff)

- **Context7** : vérification doc à jour pour libs externes touchées
- **code-review** : audit du diff avant commit
- **simplify** : challenge de la complexité ajoutée

Ne pas commit si l'un des trois remonte un blocage non résolu.

## Triggers spécifiques où cette Skill DOIT s'activer

- Demande de fix bug
- Demande de refacto
- Demande d'ajout feature
- Demande de modification module régulatoire
- Réponse à un rapport utilisateur "X ne marche pas"
- Toute édition dans `backend/regops/`, `backend/services/billing_*`, `backend/doctrine/`

## Triggers où cette Skill peut être allégée

- Documentation pure (`docs/`, `README.md`) sans impact code
- Fichiers de config dev local (`.env.example`, `.gitignore`)
- Tests purs sans modification du code testé (et même là, audit Phase 0 reste recommandé)

## Anti-patterns interdits

- "Je vois le bug, je fix direct" sans audit écrit → refusé
- "Les tests passent, je commit" sans MCP code-review → refusé
- "C'est une petite modif" sur un fichier protégé sans validation → refusé
- Constante régulatoire en dur dans un service → refusé, route obligatoire via doctrine
- Multiple changements logiques dans 1 commit → refusé, splitter

## Référence croisée

- `docs/dev/conventions.md` — stack, paths canoniques, modèles Claude Code par défaut
- Doctrine 12 principes — règle d'or "tout est lié, audit avant fix"
- Issue #270 — TODO labels unités frontend (à intégrer si refacto FE en cours)
