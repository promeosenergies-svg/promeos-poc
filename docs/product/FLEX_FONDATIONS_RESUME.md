# Résumé — Audit Flex + Spec Sprint 21

**Date :** 2026-03-18
**Branche :** `audit/flex-current-vision`
**Commits :** `114e08c` (audit v1) + `efcba5a` (spec v2 corrigée)

---

## 1. Verdict

**PROMEOS est structurellement prêt à 70-80% pour la flexibilité.** Le socle existant (EMS, signature, schedule, REFLEX_SOLAR, BACS, monitoring, action center) couvre la majorité des prérequis. Les 8 gaps identifiés sont comblables en 3 sprints fondation sans refonte.

---

## 2. Existant validé

| Composant | Maturité | Utilité flex |
|-----------|----------|-------------|
| EMS Timeseries (15min/h/j) | Complet | Courbes de charge = base de tout scoring |
| Signature énergétique | Complet | Baseline thermique défendable |
| Schedule detection | Complet | Horaires d'exploitation = fenêtres de flex |
| HP/HC + TOU | Complet | Grilles tarifaires = signal d'optimisation |
| REFLEX_SOLAR (6 blocs DR) | Complet | Demand response déjà modélisé |
| BACS/GTB (EN 15232) | Complet | Classe GTB → potentiel pilotage |
| APER/PV (PVGIS) | Complet | Estimation production solaire |
| Monitoring (KPI, alertes) | Complet | Détection anomalies = déclencheurs flex |
| Flex Mini (heuristique) | Partiel | Scoring HVAC/IRVE/Froid acceptable POC |
| Action center + recommandations | Complet | Prescriptif → action flex |

---

## 3. Corrections réglementaires appliquées

| Erreur audit v1 | Correction v2 |
|-----------------|---------------|
| HC 11h-17h hardcodé | Fenêtres `HC_SOLAIRE` saisonnalisées dans TariffCalendar |
| APER = auto-conso obligatoire | APER = solarisation obligatoire + opportunités séparées |
| CEE P6 = financement | CEE = éligibilité potentielle + caveat TRI > 3 ans |
| NEBCO seuil = 100 kW | Non confirmé CRE — ne pas hardcoder |
| TURPE 7 spread élargi | Grille CRE par segment (C5/C4/C3/HTA) |

---

## 4. Réglementation mars 2026

| Réglementation | Statut | Échéance clé |
|----------------|--------|-------------|
| NEBCO (ex-NEBEF) | En vigueur 01/09/2025 | Flex bidirectionnelle active |
| TURPE 7 | En vigueur 01/08/2025 | MAJ annuelles, tarif stockage 08/2026 |
| HC solaires | Phase 1 active 11/2025 | Phase 2 : 12/2026-10/2027 |
| BACS >290kW | En vigueur | 01/01/2025 (passé) |
| BACS 70-290kW | Reporté | 01/01/2030 |
| APER parking >10 000 m² | En vigueur | **01/07/2026** (imminent) |
| CEE P6 | En vigueur 01/01/2026 | 1 050 TWhc/an, TRI > 3 ans |
| Mécanisme capacité | Transition | Nouveau méca hiver 2026-27 |

---

## 5. Scope Sprint 21 (fondation uniquement)

| Action | Effort | Impact |
|--------|--------|--------|
| FlexAsset model + CRUD + lien BACS | M | Inventaire assets pilotables |
| TariffWindow saisonnalisé (HC_NUIT, HC_SOLAIRE, HP) | S | Plus de hardcode HC |
| TURPE 7 grille CRE (C5/C4/C3) | M | Barèmes à jour |
| NebcoSignal structure | S | Prêt pour valorisation future |
| flex_mini enrichi (FlexAsset > heuristique) | S | Scoring plus fiable |
| APER 2 temps (solarisation + opportunités) | S | Logique correcte |
| CEE P6 éligibilité + caveat | S | Pas de faux engagement |

**Ce qu'on ne fait PAS :**
- Pas de dispatch/pilotage
- Pas de menu "Flexibilité"
- Pas de logique ACC
- Pas de météo réelle (Sprint 22)

---

## 6. Livrables créés

| Fichier | Contenu |
|---------|---------|
| [docs/audits/general/flex-current-vision-audit.md](docs/audits/general/flex-current-vision-audit.md) | Audit complet technique + réglementaire |
| [docs/backlog/flex-sprint-21-spec.md](docs/backlog/flex-sprint-21-spec.md) | Spec exécutable Sprint 21 |
| [docs/decisions/adr/ADR-flex-foundation-v2.md](docs/decisions/adr/ADR-flex-foundation-v2.md) | Décisions architecture |
| [docs/data-dictionary/flex-foundation-v2.md](docs/data-dictionary/flex-foundation-v2.md) | Modèles + enums + relations |

---

## 7. Séquencement recommandé

| Sprint | Focus | Prérequis |
|--------|-------|-----------|
| **21** | FlexAsset + TariffWindow + TURPE 7 + NEBCO structure | Aucun |
| **22** | Météo réelle (Open-Meteo) + DJU/DJC + FlexBaseline | Sprint 21 |
| **23** | FlexPotential calculé + NEBCO valorisation + portfolio flex | Sprint 22 |
