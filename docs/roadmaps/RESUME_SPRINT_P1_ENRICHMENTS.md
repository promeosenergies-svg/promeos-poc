# Résumé Sprint P1 Enrichments
**Date** : 26 mars 2026
**Branche** : `fix/migrate-calc-to-backend`
**Objectif** : 75% → 85%+ conformité maquettes

---

## Corrections et enrichissements (4 commits)

### 1. Projection trajectoire — courbe verte active
- **Backend** : `projection_mwh` calculé depuis `estimated_gain_eur` des actions open/in_progress
- **Formule** : `savings_kwh = sum(estimated_gain_eur) / 0.068` (prix fallback)
- **Guard** : `[]` si aucune action n'a de savings (pas de valeur inventée)
- **Frontend** : légende "Projection" masquée si vide, barre "Avec actions" masquée si vide

### 2. KPI "Conso ce mois" — données réelles
- **Backend** : `GET /api/cockpit/conso-month` — source ConsumptionTarget monthly actual_kwh
- **Données** : Mars 2026, 5 sites, avec delta vs mois précédent
- **Frontend** : stub "—" remplacé par valeur réelle + delta % dans CommandCenter

### 3. ActionsImpact — site_nom inline
- **Backend** : `_serialize_action()` enrichi avec `site_nom` depuis relation ORM
- **Frontend** : "Action — Site" affiché dans chaque ligne d'action

### 4. Billing filter CRIT-6
- **Backend** : `billing/summary` filtre `RESOLVED` + `FALSE_POSITIVE`
- **Cohérence** : aligné avec `/api/cockpit` qui filtrait déjà correctement

---

## Endpoints créés/modifiés

| Endpoint | Action | Résultat |
|----------|--------|---------|
| `GET /api/cockpit/conso-month` | **NOUVEAU** | actual_mwh + delta vs mois préc. |
| `GET /api/cockpit/trajectory` | Modifié | `projection_mwh` calculé, plus `[]` hardcodé |
| `GET /api/actions/list` | Modifié | Champ `site_nom` ajouté |
| `GET /api/billing/summary` | Modifié | Filtre RESOLVED/FALSE_POSITIVE |

---

## Tests

| Suite | Résultat |
|-------|----------|
| Frontend vitest | **138/141** (3 pré-existants) |
| Régressions | **0** |

---

## Score conformité maquettes estimé

| Vue | Avant | Après | Progression |
|-----|-------|-------|-------------|
| Vue Executive (/cockpit) | 14/18 (78%) | 16/18 (89%) | +11% |
| Vue Exploitation (/) | 7/10 (70%) | 9/10 (90%) | +20% |
| **Global** | **21/28 (75%)** | **25/28 (89%)** | **+14%** |

Gains principaux :
- Projection trajectoire visible (+1 widget)
- KPI "Conso ce mois" fonctionnel (+1 widget)
- Actions avec nom de site (+qualité)
- Billing filtre cohérent (+qualité données)

---

## Backlog restant

| # | Priorité | Action |
|---|----------|--------|
| 1 | P1 | Header pills EPEX/CO₂ + badge alertes + bouton Rapport COMEX |
| 2 | P1 | Conso 7j série N-1 (comparaison semaine) |
| 3 | P2 | Connecteur RTE CO₂ réseau temps réel |
| 4 | P2 | Endpoint `/api/ems/sites/j1` pour conso J-1 par site |
| 5 | P2 | Seed étendu 2020 comme année de référence DT |
