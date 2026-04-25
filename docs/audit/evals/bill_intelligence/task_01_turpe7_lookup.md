# Task 01 — Lookup TURPE 7 HPH valeur canonique

**Agent cible** : `bill-intelligence`
**Difficulté** : easy
**Sprint origin** : Bill / TURPE

## Prompt exact

> Quelle est la valeur TURPE 7 HPH (c_HPH) pour segment LU actuellement ? D'où vient-elle ?

## Golden output (PASS)

- [ ] Consulte YAML `tarifs_reglementaires.yaml` + ParameterStore
- [ ] Cite valeur exacte (0.0569 €/kWh selon V120 findings)
- [ ] Cite `valid_from`
- [ ] Distingue TURPE (€) vs CO₂ (kgCO₂)
- [ ] Source : délibération CRE

## Anti-patterns (FAIL)

- ❌ Hardcode la valeur sans cite
- ❌ Confond avec TURPE 6
- ❌ Réponse vague "c'est dans le YAML"

## Rationale

Lookup basique mais teste discipline SoT + source.
