# Ingestion Report: ARRETE_ACC_2025

**Title:** Arrete 21 fevrier 2025 - ACC 5MW/10MW
**Content Hash:** 85251488188d8aa2
**Ingested at:** 2026-02-11T19:35:46

## Pipeline Summary

| Step | Count |
|------|-------|
| Sections extracted | 22 |
| Chunks generated | 15 |
| YAML drafts created | 15 |

## Drafts by Type

- **checklist**: 1
- **knowledge**: 7
- **rule**: 7

## Drafts by Domain

- **acc**: 1
- **facturation**: 1
- **reglementaire**: 5
- **usages**: 8

## Sections

1. **Arrêté 21 février 2025 — ACC (5MW/10MW, rayon, modalités)** (level 1, 25 words)
2. **Arrêté du 21 février 2025 — Autoconsommation Collective (ACC)** (level 1, 0 words)
3. **Résumé officiel des seuils, périmètres et modalités** (level 2, 39 words)
4. **1. Augmentation des seuils de puissance cumulée** (level 2, 0 words)
5. **1.1 Seuil standard — Métropole continentale** (level 3, 108 words)
6. **1.2 Dérogation pour les collectivités territoriales — 10 MW** (level 3, 199 words)
7. **2. Critères de proximité géographique et périmètres d’application** (level 2, 0 words)
8. **2.1 Règle générale — Rayon de 2 km** (level 3, 72 words)
9. **2.2 Dérogations de périmètre — Typologies et procédures** (level 3, 86 words)
10. **2.3 Dérogation pour Services d’Incendie et de Secours (SIS) — Innovation du 2 mai 2025** (level 3, 75 words)
11. **2.4 Dérogation EPCI — Périmètre dérogatoire illimité** (level 3, 73 words)
12. **3. Modalités d’implémentation et rôles des acteurs** (level 2, 0 words)
13. **3.1 Gestionnaire de Réseau — Responsabilités d’Enedis** (level 3, 139 words)
14. **3.2 Personne Morale Organisatrice (PMO)** (level 3, 88 words)
15. **3.3 Procédure de demande de dérogation** (level 3, 79 words)
16. **4. Contexte réglementaire et mesures connexes** (level 2, 0 words)
17. **4.1 Exonération d’accise (1er mars 2025)** (level 3, 54 words)
18. **4.2 Cadre legal global Texte Date Objet Loi PACTE 2019 Création ACC en France Arrêté 21/11/2019 2019 Critères base: 3MW, 2km Arrêté 14/10/2020 2020 Dérogation 20km générale Arrêté 19/09/2023 2023 Dérogations zones rurales/semi-urbaines (10-20km) Arrêté 21/02/2025 2025 Seuils 5MW/10MW + dérogation EPCI Arrêté complémentaire 2/05/2025 Dérogation SIS 20km auto** (level 3, 0 words)
19. **5. Métriques et impact opérationnel** (level 2, 0 words)
20. **5.1 Adoption sur le terrain** (level 3, 52 words)
21. **5.2 Cas d’usage exemplaires** (level 3, 34 words)
22. **Conclusion** (level 2, 583 words)

## Generated Drafts

| ID | Type | Domain | Confidence | Status |
|----|------|--------|------------|--------|
| ARRETE_ACC_2025_0 | rule | usages | low | draft |
| ARRETE_ACC_2025_1 | knowledge | usages | low | draft |
| ARRETE_ACC_2025_2 | knowledge | usages | low | draft |
| ARRETE_ACC_2025_3 | rule | reglementaire | low | draft |
| ARRETE_ACC_2025_4 | rule | usages | low | draft |
| ARRETE_ACC_2025_5 | checklist | reglementaire | low | draft |
| ARRETE_ACC_2025_6 | knowledge | acc | low | draft |
| ARRETE_ACC_2025_7 | knowledge | reglementaire | low | draft |
| ARRETE_ACC_2025_8 | rule | usages | low | draft |
| ARRETE_ACC_2025_9 | rule | usages | low | draft |
| ARRETE_ACC_2025_10 | knowledge | reglementaire | low | draft |
| ARRETE_ACC_2025_11 | rule | usages | low | draft |
| ARRETE_ACC_2025_12 | knowledge | reglementaire | low | draft |
| ARRETE_ACC_2025_13 | knowledge | facturation | low | draft |
| ARRETE_ACC_2025_14 | rule | usages | low | draft |

## Next Steps

1. Review drafts in `docs/kb/drafts/ARRETE_ACC_2025/`
2. Upgrade confidence and refine tags/logic for each draft
3. Promote to validated: `python backend/scripts/kb_promote_item.py <file.yaml>`
4. Import to DB: `python backend/scripts/kb_seed_import.py --include-drafts`
5. Rebuild FTS index: `python backend/scripts/kb_build_index.py`
