# Task 02 — Seuil BACS 2030

**Agent cible** : `regulatory-expert`
**Difficulté** : easy
**Sprint origin** : RegOps / BACS

## Prompt exact

> Un site avec CVC 85 kW est-il soumis à BACS aujourd'hui ? Le sera-t-il au 01/01/2030 ?

## Golden output (PASS)

- [ ] Aujourd'hui : NON (seuil 290 kW depuis 01/01/2025)
- [ ] 2030 : OUI (seuil abaissé à 70 kW au 01/01/2030)
- [ ] Source : Décret n°2025-1343 (27/12/2025, modifiant 2020-887)
- [ ] `confidence: high`

## Anti-patterns (FAIL)

- ❌ "BACS 2027" (date erronée, test round 2 audit agents)
- ❌ Omet seuil actuel 290 kW
- ❌ Pas de décret cité

## Rationale

Détecte la confusion 2027 vs 2030 (erreur factuelle réelle en codebase avant fix).
