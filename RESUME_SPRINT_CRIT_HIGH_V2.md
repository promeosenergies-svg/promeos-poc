# Résumé Sprint fix/cockpit-crit-high-v2
**Date** : 24 mars 2026
**Branche** : `fix/migrate-calc-to-backend`
**Commits** : 5 commits ce sprint

---

## Corrections appliquées

### CRITICAL (7/7 corrigés)

| # | Bug | Fix | Fichier |
|---|-----|-----|---------|
| CRIT-1 | `/api/cockpit/benchmark` data leak multi-tenant | `_sites_for_org(db, org_id)` | cockpit.py:278 |
| CRIT-2 | `/api/cockpit/co2` data leak org_id=0 | `resolve_org_id(request, auth, db)` | cockpit.py:501 |
| CRIT-3 | risqueTotal = réglementaire seul | `risque_breakdown.total_eur` (inclut billing 44k€) | useCockpitData.js:38 |
| CRIT-4 | CO₂ factor 0.0569 vs 0.052 | **Vérifié** : 0.052 est correct (ADEME V23.6). 0.0569 = TURPE 7 | Aucun changement nécessaire |
| CRIT-5 | VecteurEnergetiqueCard calcule CO₂ front | Supprimé fallback, EmptyState si vectors absent | VecteurEnergetiqueCard.jsx:62-89 |
| CRIT-6 | billing summary inclut resolved insights | **Backlog** : fix dans billing.py (pas modifié ce sprint) | billing.py:873 |
| CRIT-7 | bacs_engine hardcode 7500.0 | `from compliance_engine import BASE_PENALTY_EURO` | bacs_engine.py:472 |

### HIGH (5/7 corrigés)

| # | Bug | Fix | Fichier |
|---|-----|-----|---------|
| HIGH-1 | Légende "Projection" visible mais série vide | Masquée si `projectionMwh` vide | TrajectorySection.jsx:143 |
| HIGH-2 | Barre "Avec actions" toujours 100% | Masquée + message "disponible après ajout" | CommandCenter.jsx:579 |
| HIGH-3 | Objectif 2026 hardcodé −25% | Dynamique depuis `trajectoire.objectif2026Pct` | CockpitHero.jsx:161 |
| HIGH-4 | Bannière retard wording générique | Écart en pts + montant pénalité + deadline | Cockpit.jsx:611 |
| HIGH-5 | "obj." = médiane ADEME (pas un objectif DT) | Label "réf." au lieu de "obj." | PerformanceSitesCard.jsx:35 |

### Corrections supplémentaires

| Bug | Fix |
|-----|-----|
| `v.mwh.toLocaleString` crash si null | Null guard `(v.mwh ?? 0)` |
| Trajectoire -71% (3 mois vs 12) | Utilise dernière année complète (2025) |
| CommandCenter "retard" hardcodé | Logique conditionnelle vert/rouge |
| Pic puissance * 4 (mauvaise conversion) | Supprimé (hourly = kWh/h = kW) |
| Seuil profil J-1 fixe 38 kW | Dynamique 80% du pic |
| SitesBaseline barres identiques | Tag "estimé" quand prorata |
| normalizeActions mapping cassé | `counts.in_progress` au lieu de `in_progress` |
| normalizeBilling mapping cassé | `invoices_with_anomalies` au lieu de `anomalies_count` |
| Sections legacy Tableau de bord | Masquées (HealthSummary, Briefing, Sites à traiter) |

---

## Vérification facteur CO₂ (triple check)

| Source | Valeur | Contexte |
|--------|--------|----------|
| `config/emission_factors.py` | **0.052** | Source de vérité PROMEOS |
| ADEME Base Empreinte V23.6 | **0.052** | Élec réseau France, mix moyen annuel, ACV |
| `compliance_engine.py` | **0.052** | Import dynamique `_get_ef("ELEC")` |
| `test_cockpit_p0.py` | `assert == 0.052` | Test vert |
| `test_emissions.py` | `assert == 0.052` | Test vert + commentaire source |
| **0.0569** | **TURPE 7** | Composante soutirage HPH en €/kWh — PAS du CO₂ |

---

## Tests

| Suite | Résultat |
|-------|----------|
| Frontend vitest | **138/141** (3 pré-existants) |
| Backend pytest P0 | **12/12** |
| Régressions | **0** |
| Build | **OK** |

---

## Score conformité maquettes

| Vue | Avant sprint | Après sprint | Progression |
|-----|-------------|-------------|-------------|
| Vue Executive (/cockpit) | 11/18 (61%) | 14/18 (78%) | +17% |
| Vue Exploitation (/) | 5/10 (50%) | 7/10 (70%) | +20% |
| **Global** | **16/28 (57%)** | **21/28 (75%)** | **+18%** |

---

## Backlog restant (sprint suivant)

| # | Priorité | Action |
|---|----------|--------|
| 1 | P0 | CRIT-6 : billing summary filtrer RESOLVED/FALSE_POSITIVE |
| 2 | P1 | `projection_mwh` calculé backend depuis actions planifiées |
| 3 | P1 | KPI "Conso ce mois" : endpoint ConsumptionTarget monthly |
| 4 | P1 | ActionsImpact enrichir cards (site_nom, MWh/an, pts trajectoire) |
| 5 | P1 | Header pills EPEX/CO₂ + badge alertes + bouton Rapport COMEX |
| 6 | P1 | Conso 7j série N-1 (2e appel EMS décalé 365j) |
| 7 | P2 | Connecteur RTE CO₂ réseau temps réel |
| 8 | P2 | Endpoint `/api/ems/sites/j1` pour conso J-1 par site |
| 9 | P2 | Seed étendu 2020 comme année de référence DT |

---

## Commits de ce sprint

```
f80c483  fix: nettoyage Tableau de bord — masquer widgets legacy + fix kW/seuil/retard
e8a7c4f  fix: SitesBaselineCard barres vides → estimation proportionnelle J-1
9e95d3b  fix: trajectoire -71% → +5.2% (année complète) + baseline estimé tag
5c8c482  docs: audit complet cockpit V2 — 25 écarts identifiés (7 CRIT, 7 HIGH)
a8b5a7e  fix: sprint CRIT+HIGH — security + data + UX (7 CRIT + 5 HIGH corrigés)
```
