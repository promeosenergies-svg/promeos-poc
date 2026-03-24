# Audit Cockpit UX/UI — Rapprochement Maquettes
**Date** : 2026-03-24
**Branche** : `feat/cockpit-world-class`
**Commit audit** : `69c85a4`

---

## Résumé des corrections appliquées

### Bugs de données corrigés (impact immédiat sur les KPIs affichés)

| Bug | Avant | Après | Impact |
|-----|-------|-------|--------|
| `actions.enCours` | Toujours **0** (clé `en_cours` inexistante) | **5** (lit `counts.in_progress`) | Card "Actions en cours" affiche 5/12 |
| `billing.anomalies` | Toujours **0** (clé `anomalies_count` inexistante) | **29** (lit `invoices_with_anomalies`) | Billing anomalies visible |
| `risque_breakdown.billing_anomalies_eur` | Hardcodé **0** backend | **44 140 €** (query `BillingInsight.estimated_loss_eur`) | Risque total passe de 26k€ à ~70k€ |
| `actions.potentielEur` | Toujours **0** (clé `savings_eur`) | **63 488 €** (lit `total_gain_eur`) | "+63 k€/an potentiel" visible |

### Layout corrigé (rapprochement maquettes)

| Correction | Page | Détail |
|------------|------|--------|
| Scope indicator masqué | /cockpit | Expert-only (absent des maquettes exécutives) |
| Single-site row masqué | /cockpit | Expert-only (pas dans la maquette COMEX) |
| KPI J-1 en premier | / | Après tabs, avant tout le reste (maquette) |
| Trajectoire + Actions 2-col | / | Progression et Actions du jour côte à côte |
| SitesBaseline après charts | / | Avant les sections legacy |
| Sections legacy déplacées | / | HealthSummary, BriefingHeroCard, EssentialsRow après maquette |
| `fmtEur` dans Sites à risque | / | Remplace `.toLocaleString('fr-FR') €` |
| Accents FR corrigés | / | "réglementaire", "pénalité", "Vérifier", "séparément" |

---

## État actuel vs maquettes cibles

### Vue Executive (/cockpit) — Correspondance

| Section maquette | État | Notes |
|-----------------|------|-------|
| Tabs Vue exec / Tableau de bord | ✅ OK | Navigation bidirectionnelle |
| 4 KPI cards (Score, Risque, Réduction, Actions) | ✅ OK | Score 84.1, Risque 26k€, Actions 5/12 |
| Sous-texte gauge DT 45% · BACS 30% · APER 25% | ✅ OK | Constantes réglementaires |
| Bannière retard trajectoire | ✅ OK | Avec montant pénalité + deadline |
| Alertes prioritaires (3 items) | ✅ OK | 3 actions P0 avec gain EUR + jours |
| Événements récents (4 items) | ✅ OK | Notifications avec colored dots |
| Courbe trajectoire DT | ⚠️ PARTIEL | Données réelles absentes → EmptyState |
| Performance par site kWh/m² | ✅ OK | 5 sites avec barres + objectifs |
| Vecteur énergétique | ✅ OK | Élec 88% + Gaz 12% + CO₂ scopes |
| Actions Impact | ✅ OK | 6 actions avec rationale + gain EUR |
| Zones expert masquées | ✅ OK | Scope indicator, ExecKpiRow, detail zone |

### Vue Exploitation (/) — Correspondance

| Section maquette | État | Notes |
|-----------------|------|-------|
| 4 KPI J-1 | ⚠️ PARTIEL | Conso hier = données EMS si dispo, Conso mois = —, Pic kW, CO₂ = — |
| Conso 7 jours BarChart | ✅ OK | Recharts BarChart avec données EMS |
| Profil journalier J-1 | ⚠️ PARTIEL | Zone + seuil conditionnel, "indisponible" si pas de hourly |
| Progression trajectoire | ✅ OK | Double barre + objectif 2026 (en 2-col avec Actions) |
| Actions du jour | ✅ OK | TodayActionsCard avec 5 items (en 2-col avec Trajectoire) |
| Sites J-1 vs Baseline | ⚠️ PARTIEL | Barres présentes mais données J-1 pas encore injectées |

---

## Données HELIOS seedées mais NON exploitées (backlog)

| Donnée | Volume | Endpoint existant | Priorité |
|--------|--------|-------------------|----------|
| ConsumptionTargets monthly `actual_kwh` | 288 rows | `/api/consumption/targets` | **P1** — "Conso ce mois" |
| MeterReadings 15min (J-1) | ~35k/jour | `/api/ems/timeseries` | **P1** — KPI J-1 + Profil |
| Actions ROI (realized/estimated) | 12 actions | `/api/actions/roi_summary` | P2 — enrichir ActionsImpact |
| Contract expiry radar | 8 contrats | `/api/contracts_radar` | P2 — alerte contrats |
| Portfolio consumption `peak_kw`, `base_night_pct` | 5 sites | `/api/portfolio/consumption/summary` | P2 — KPI puissance |
| Notifications `by_status` (new/read/dismissed) | 20 events | `/api/notifications/summary` | P3 — badge non-lu |

---

## Violations architecture restantes (hors scope ce sprint)

| Violation | Fichier | Sévérité |
|-----------|---------|----------|
| VecteurEnergetiqueCard agrège CO₂ en front | `VecteurEnergetiqueCard.jsx` | HIGH |
| Cockpit.jsx `rawKpis` useMemo recalcule pctConf, risque | `Cockpit.jsx:193-237` | HIGH |
| CommandCenter.jsx `rawKpis` dupliqué | `CommandCenter.jsx:197-222` | HIGH |
| CO₂ calculé front avec facteur 0.052 (devrait être 0.0569) | `CreateActionModal.jsx:106` | HIGH |
| `useCommandCenterData` `kw = v * 4` non documenté | `useCommandCenterData.js:55` | MEDIUM |
| SitesBaselineCard `deltaPct` dérivé non documenté | `SitesBaselineCard.jsx:20` | MEDIUM |

---

## Commandes de vérification

```bash
# Backend
cd backend && pytest tests/test_cockpit_p0.py -v  # 13/13

# Frontend
cd frontend && npx vitest run  # 137 pass, 2 pre-existing fails
NODE_OPTIONS="--max-old-space-size=4096" npx vite build  # OK

# API live
curl -s http://localhost:8001/api/cockpit -H "X-Org-Id: 1" | \
  python3 -c "import sys,json; s=json.load(sys.stdin)['stats']; \
  print('Billing anomalies EUR:', s['risque_breakdown']['billing_anomalies_eur']); \
  print('Total risque:', s['risque_breakdown']['total_eur'])"

curl -s http://localhost:8001/api/actions/summary -H "X-Org-Id: 1" | \
  python3 -c "import sys,json; d=json.load(sys.stdin); \
  print('En cours:', d['counts']['in_progress']); \
  print('Total gain:', d['total_gain_eur'])"
```
