# Task 01 — Détecter duplication constante canonique

**Agent cible** : `code-reviewer`
**Difficulté** : easy
**Sprint origin** : Source-guards

## Prompt exact

> Revue ce diff : `+ const CO2_FACTOR = 0.052;` ajouté dans `frontend/src/utils/helpers.js`.

## Golden output (PASS)

- [ ] Flag severity P0 (duplication SoT)
- [ ] Format JSON `{finding, severity, file, line, evidence, suggestion}`
- [ ] Cite SoT canonique `backend/config/emission_factors.py` (ou `EmissionFactorsContext` frontend)
- [ ] Suggestion : import du hook / endpoint

## Anti-patterns (FAIL)

- ❌ Laisse passer
- ❌ Flag P2 (sévérité trop basse)
- ❌ Ne cite pas la SoT

## Rationale

Cas le plus fréquent. Si laissé passer, dette se multiplie.
