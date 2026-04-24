# Task 04 — Calcul TURPE 7 HPH site C5 T1

**Agent cible** : `regulatory-expert`
**Difficulté** : medium
**Sprint origin** : Tarifs / TURPE

## Prompt exact

> Site C5 profil T1, 8 000 kWh en HPH mars 2026. Quelle composante variable TURPE 7 HPH appliquer ? Cite source + date d'effet.

## Golden output (PASS)

- [ ] Consulte YAML `tarifs_reglementaires.yaml` (SoT)
- [ ] Cite valeur TURPE 7 c_HPH appliquée pour segment C5 T1
- [ ] Cite `valid_from` + délibération CRE correspondante
- [ ] Distingue TURPE 7 HPH (€/kWh) du facteur CO₂ (kgCO₂/kWh)
- [ ] Délègue à `bill-intelligence` pour calcul facture complète

## Anti-patterns (FAIL)

- ❌ Confondre 0.0569 (TURPE HPH LU) avec 0.052 (CO₂)
- ❌ Inventer une valeur sans source
- ❌ Omettre le segment tarifaire (C5 T1 vs C4 etc.)

## Rationale

Détecte la confusion TURPE/CO₂ (anti-pattern historique PROMEOS).
