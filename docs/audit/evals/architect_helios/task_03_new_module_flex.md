# Task 03 — ADR nouveau module Flex scoring NEBCO

**Agent cible** : `architect-helios`
**Difficulté** : medium
**Sprint origin** : Flex / Pilotage

## Prompt exact

> Produis un ADR pour un nouveau module "Flex NEBCO scoring" qui évalue l'éligibilité d'un site au dispositif NEBCO en combinant : archétype NAF, puissance pilotable, usage (CVC/froid/IRVE), historique CDC. Où placer dans l'archi HELIOS ?

## Contexte fourni

- Skill : `@.claude/skills/helios_architecture/SKILL.md`
- Memory : `memory/project_flexibilite_strategie_produit.md`
- Pillars existants : EMS (`backend/ems/`), Bill, Achat

## Golden output (PASS = tous cochés)

- [ ] ADR format complet
- [ ] Place dans pillar **Flex** (owner `ems-expert` temp jusqu'à agent dédié)
- [ ] Réutilise `naf_resolver` + `consumption_unified_service`
- [ ] Expose endpoint org-scopé
- [ ] Délègue à `ems-expert` pour logique + `implementer` pour code
- [ ] **Refuse** de coder

## Anti-patterns (FAIL si présent)

- ❌ Nouveau pillar "NEBCO" parallèle (fragmentation)
- ❌ Ignore pillar Flex existant
- ❌ Calcul dans le frontend

## Rationale

Teste la capacité à placer une feature dans l'archi existante sans créer de nouveau silo.
