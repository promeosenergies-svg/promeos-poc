# Task 01 — Deadline OPERAT N+1

**Agent cible** : `regulatory-expert`
**Difficulté** : easy
**Sprint origin** : RegOps / Décret Tertiaire

## Prompt exact

> Quelle est la deadline officielle de dépôt des données de consommation N-1 sur la plateforme OPERAT ? Cite la source légale exacte.

## Contexte fourni

- Fichier : `backend/config/tarifs_reglementaires.yaml`
- Skill : `@.claude/skills/regulatory_calendar/SKILL.md`
- Memory : `memory/reference_regulatory_landscape_2026_2050.md`

## Golden output (PASS = tous cochés)

- [ ] Date citée : **30 septembre** de l'année N+1 (dépôt conso N-1)
- [ ] Source : **Décret n°2019-771** (Décret Tertiaire)
- [ ] Mentionne plateforme OPERAT (ADEME)
- [ ] `confidence: high` sur cette donnée
- [ ] Format sortie structuré `{finding, source, date_of_truth, confidence}`

## Anti-patterns (FAIL si présent)

- ❌ "30 juin" (ancienne version avant 2022)
- ❌ "avant fin d'année" (vague)
- ❌ Absence de référence décret
- ❌ `confidence: low` sur une donnée cardinale

## Rationale

Question factuelle basique testant la mémoire réglementaire et la discipline "zéro chiffre sans source". Si l'agent échoue ici, toute cascade downstream (scoring conformité, alertes) sera fausse.
