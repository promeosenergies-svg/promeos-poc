# Ingestion Report: BACS_SEUILS

**Title:** Decret BACS - Seuils, dates, exemptions
**Content Hash:** 5d9e2650f3e05e93
**Ingested at:** 2026-02-11T19:35:48

## Pipeline Summary

| Step | Count |
|------|-------|
| Sections extracted | 23 |
| Chunks generated | 18 |
| YAML drafts created | 18 |

## Drafts by Type

- **knowledge**: 3
- **rule**: 15

## Drafts by Domain

- **reglementaire**: 14
- **usages**: 4

## Sections

1. **Décret BACS — seuils, dates, exemptions TRI** (level 1, 35 words)
2. **DÉCRET BACS — Synthèse Officielle** (level 1, 0 words)
3. **Seuils, Dates Applicables, Exemptions TRI, Inspections** (level 2, 0 words)
4. **1. CONTEXTE RÉGLEMENTAIRE OFFICIEL** (level 3, 108 words)
5. **2. CHAMP D’APPLICATION** (level 3, 47 words)
6. **3. SEUILS RÉGLEMENTAIRES ET ÉCHÉANCES Puissance CVC Bâtiments existants Bâtiments neufs Mise en conformité requise ≥ 290 kW Obligation depuis 22/07/2020 Obligation depuis 21/07/2021 2 1er janvier 2025 70–290 kW Obligation depuis 09/04/2023 Obligation depuis 08/04/2024 1er janvier 2027** (level 3, 66 words)
7. **4. EXEMPTIONS — CRITÈRE DU TEMPS DE RETOUR SUR INVESTISSEMENT (TRI)** (level 3, 0 words)
8. **Modification du seuil en 2023** (level 3, 30 words)
9. **Conditions d’exemption 3** (level 3, 152 words)
10. **5. EXIGENCES FONCTIONNELLES DU BACS** (level 3, 119 words)
11. **6. INSPECTIONS PÉRIODIQUES OBLIGATOIRES** (level 3, 19 words)
12. **Fréquence d’inspection Situation Délai Première inspection (après installation ou remplacement du BACS) 2 ans maximum après mise en service Inspections suivantes 5 ans maximum** (level 3, 0 words)
13. **Contenu obligatoire de l’inspection 8** (level 3, 72 words)
14. **Responsabilités & Délais de remise** (level 3, 37 words)
15. **7. OBLIGATIONS DE RELATION AU BACS POUR SYSTÈMES TECHNIQUES** (level 3, 0 words)
16. **Bâtiments existants** (level 3, 24 words)
17. **Obligation lors de remplacement d’équipement** (level 3, 38 words)
18. **8. MODALITÉS DE CONFORMITÉ & PREUVES REQUISES** (level 3, 94 words)
19. **9. SANCTIONS & MISE EN CONFORMITÉ** (level 3, 82 words)
20. **10. TAUX DE COUVERTURE DE L’OBLIGATION** (level 3, 66 words)
21. **11. INTÉGRATION AVEC AUTRES OBLIGATIONS** (level 3, 57 words)
22. **12. RÉFÉRENCES OFFICIELLES** (level 3, 81 words)
23. **SYNTHÈSE EXÉCUTIVE Aspect Détail Obligation principale Installation d’un BACS (GTB classe C min.) pour tous bâtiments tertiaires ≥ 70 kW Seuils clés 290 kW (échéance 01/01/2025) ; 70 kW (échéance 01/01/2027) Exemption TRI > 10 ans (déduction aides) — Justification exigée, conservée 10 ans Inspections Tous les 2 ans (post-installation) puis tous les 5 ans ; rapport obligatoire 1 mois ; conservation 10 ans Pas de plateforme déclarative Contrairement au Tertiaire (OPERAT) — Conformité via dossiers / preuves conservés Fonction clé Suivi horaire énergie, détection pertes efficacité, ajustement automatique, pilotage manuel Responsabilité Propriétaire des systèmes CVC ; formation exploitant obligatoire** (level 2, 258 words)

## Generated Drafts

| ID | Type | Domain | Confidence | Status |
|----|------|--------|------------|--------|
| BACS_SEUILS_0 | rule | reglementaire | low | draft |
| BACS_SEUILS_1 | rule | reglementaire | low | draft |
| BACS_SEUILS_2 | knowledge | reglementaire | low | draft |
| BACS_SEUILS_3 | rule | reglementaire | low | draft |
| BACS_SEUILS_4 | rule | reglementaire | low | draft |
| BACS_SEUILS_5 | rule | reglementaire | low | draft |
| BACS_SEUILS_6 | rule | usages | low | draft |
| BACS_SEUILS_7 | rule | reglementaire | low | draft |
| BACS_SEUILS_8 | rule | usages | low | draft |
| BACS_SEUILS_9 | knowledge | reglementaire | low | draft |
| BACS_SEUILS_10 | knowledge | reglementaire | low | draft |
| BACS_SEUILS_11 | rule | reglementaire | low | draft |
| BACS_SEUILS_12 | rule | reglementaire | low | draft |
| BACS_SEUILS_13 | rule | reglementaire | low | draft |
| BACS_SEUILS_14 | rule | reglementaire | low | draft |
| BACS_SEUILS_15 | rule | usages | low | draft |
| BACS_SEUILS_16 | rule | reglementaire | low | draft |
| BACS_SEUILS_17 | rule | usages | low | draft |

## Next Steps

1. Review drafts in `docs/kb/drafts/BACS_SEUILS/`
2. Upgrade confidence and refine tags/logic for each draft
3. Promote to validated: `python backend/scripts/kb_promote_item.py <file.yaml>`
4. Import to DB: `python backend/scripts/kb_seed_import.py --include-drafts`
5. Rebuild FTS index: `python backend/scripts/kb_build_index.py`
