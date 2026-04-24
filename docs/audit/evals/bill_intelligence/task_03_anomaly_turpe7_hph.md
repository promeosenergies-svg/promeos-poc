# Task 03 — Détection anomalie TURPE 7 HPH sur facture C5

**Agent cible** : `bill-intelligence`
**Difficulté** : medium
**Sprint origin** : Bill / Shadow billing

## Prompt exact

> Voici la ligne TURPE HPH d'une facture C5 (profil T1) de mars 2026 : `5000 kWh × 0.0612 €/kWh = 306.00 €`. Est-ce cohérent avec la grille TURPE 7 en vigueur ? Retourne ton output au format JSON anomalies.

## Contexte fourni

- Fichier SoT : `backend/config/tarifs_reglementaires.yaml` (section `turpe_7`)
- Service : `backend/services/billing_engine/catalog.py` (legacy, divergence possible)
- Skill : `@.claude/skills/tariff_constants/SKILL.md` (Phase 3B, placeholder possible)
- Memory : `memory/reference_turpe7_hphc.md`

## Golden output (PASS = tous cochés)

- [ ] Format JSON respecté : `{line_item, computed_value, reference_value, variance_pct, confidence, anomaly_type, recommandation}`
- [ ] Détecte l'écart : valeur facturée `0.0612` ≠ valeur TURPE 7 attendue pour C5 T1 HPH
- [ ] Cite `valid_from` de la grille appliquée
- [ ] `anomaly_type` correctement classé (`wrong_rate` ou `wrong_period`)
- [ ] Délégation vers `regulatory-expert` si divergence SoT YAML vs catalog.py détectée

## Anti-patterns (FAIL si présent)

- ❌ Confondre TURPE HPH avec facteur CO₂ (0.0569 vs 0.052)
- ❌ Hardcoder un tarif dans la réponse (doit citer ParameterStore)
- ❌ Accepter sans vérifier la SoT
- ❌ Réponse vague "il faudrait vérifier la grille"

## Rationale

Cas d'usage central `bill-intelligence` : détecter une anomalie sur ligne TURPE d'une facture réelle. Test combine : lecture SoT, calcul, format JSON, délégation cross-agent.
