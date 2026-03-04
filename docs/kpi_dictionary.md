# PROMEOS POC — KPI Dictionary (Source de verite)

> Version: V113.1 | Date: 2026-03-04

## Conventions globales

- **Arrondi**: `Math.round()` (arrondi au plus proche) sauf indication contraire
- **Monnaie**: Toujours `€` (symbole), jamais `EUR` (texte). Format grands montants: `XX k€` (espace avant k)
- **Energie**: kWh pour valeurs < 10 000, MWh pour valeurs >= 10 000
- **Pourcentage**: `XX%` sans decimale sauf precision requise (ex: couverture 83.5%)
- **CO2**: Facteur ADEME France 2024 = 0.052 kg CO2e/kWh (electricite)
- **Periode**: Toujours relative au scope selectionne (org + sites + date range)

---

## 1. Conformite (%)

| Champ | Valeur |
|-------|--------|
| **Definition** | Pourcentage de sites conformes au Decret Tertiaire |
| **Formule** | `Math.round(conformes / total * 100)` |
| **Unite** | % |
| **Agregation** | Count sites with `statut_conformite === 'conforme'` / total sites |
| **Perimetre** | Scope org (tous sites actifs) |
| **Source backend** | `/api/sites` → field `statut_conformite` |
| **Source frontend** | `dashboardEssentials.js` → `computeConformite()` |
| **Seuils** | Vert >= 80%, Amber 50-80%, Rouge < 50% |

---

## 2. Couverture donnees (%)

| Champ | Valeur |
|-------|--------|
| **Definition** | Pourcentage de sites avec des donnees de consommation |
| **Formule** | `Math.round(sitesWithConso / total * 100)` |
| **Unite** | % |
| **Agregation** | Count sites where `conso_kwh_an > 0` / total sites |
| **Perimetre** | Scope org |
| **Source backend** | `/api/sites` → field `conso_kwh_an` |
| **Seuils** | `suspicious: 30%, warn: 50%, opportunity: 80%` |

---

## 3. Risque financier (k€)

| Champ | Valeur |
|-------|--------|
| **Definition** | Somme des risques financiers estimes par site |
| **Formule** | `Math.round(sum(risque_eur) / 1000)` |
| **Unite** | k€ (format: `XX k€` avec espace) |
| **Agregation** | Somme sur tous les sites du scope |
| **Perimetre** | Scope org |
| **Source backend** | `/api/cockpit` → `risque_financier_euro` |
| **Seuils** | `warn: 10 k€, crit: 50 k€` |

---

## 4. Maturite / Readiness Score (%)

| Champ | Valeur |
|-------|--------|
| **Definition** | Score composite de maturite energetique |
| **Formule** | `couverture * 0.3 + conformite * 0.4 + actionsScore * 0.3` |
| **Unite** | % |
| **Poids** | data: 30%, conformite: 40%, actions: 30% |
| **actionsScore** | 55% si non-conformes > 0, sinon 80% |
| **Perimetre** | Scope org |
| **Source** | Calcul frontend (`dashboardEssentials.js`) |
| **Seuils** | `crit: 40%, warn: 70%` |

---

## 5. Consommation totale (kWh / MWh)

| Champ | Valeur |
|-------|--------|
| **Definition** | Consommation energetique totale sur la periode |
| **Formule** | Somme des `value_kwh` des readings sur la periode selectionnee |
| **Unite** | kWh (< 10 000), MWh (>= 10 000) |
| **Sources prioritaires** | 1. `hphc.total_kwh` 2. `tunnel.total_kwh` 3. `progression.ytd_actual_kwh` |
| **Perimetre** | Scope site(s) + date range |
| **Source backend** | `/ems/hphc`, `/ems/tunnel`, `/ems/timeseries` |

---

## 6. Cout unitaire (EUR/MWh)

| Champ | Valeur |
|-------|--------|
| **Definition** | Prix moyen de l'energie sur la periode |
| **Formule** | `Math.round((totalEur / totalKwh) * 1000 * 100) / 100` |
| **Unite** | EUR/MWh (2 decimales) |
| **Validation** | Valeurs > 500 EUR/MWh suspectes (erreur de donnees) |
| **Source** | Calcul frontend a partir de `hphc.total_cost_eur` / `total_kwh` |

---

## 7. CO2e (kg)

| Champ | Valeur |
|-------|--------|
| **Definition** | Impact carbone de la consommation |
| **Formule** | `totalKwh * 0.052` |
| **Unite** | kg CO2e |
| **Facteur** | 0.052 kg CO2e/kWh (ADEME France 2024, electricite) |
| **Source** | Calcul frontend |

---

## 8. Pic Puissance P95 (kW)

| Champ | Valeur |
|-------|--------|
| **Definition** | 95eme percentile de la puissance appelee |
| **Formule** | `Math.max(...tunnel.envelope.*.p95)` |
| **Unite** | kW |
| **Source backend** | `/ems/tunnel` → `envelope[].p95` |

---

## 9. Load Factor (%)

| Champ | Valeur |
|-------|--------|
| **Definition** | Facteur de charge = utilisation effective vs capacite |
| **Formule** | `E_total / (Pmax * hours) * 100` |
| **Unite** | % |
| **Seuils** | `ok: >= 85%, warn: 50-85%, crit: < 50%` |
| **Source backend** | `/api/monitoring/kpis` |

---

## 10. Data Quality Coverage (%)

| Champ | Valeur |
|-------|--------|
| **Definition** | Completude des donnees de consommation (12 mois glissants) |
| **Formule** | `months_covered / 12 * 100` |
| **Unite** | % |
| **Seuils** | `green: >= 80%, amber: 50-80%, red: < 50%` |
| **Source backend** | `/api/data-quality/completeness` → `overall_coverage_pct` |

---

## 11. Priority Score (Copilot)

| Champ | Valeur |
|-------|--------|
| **Definition** | Score de priorite des actions copilot (plus haut = plus urgent) |
| **Formule** | `(6 - priority) * 20 + min(savings_eur / 100, 50)` |
| **Unite** | Score (0-100+) |
| **Source backend** | `copilot_engine.py` → `priority_score` |

---

## Lineage (source → affichage)

```
Backend DB → SQLAlchemy Model → Route/Service → JSON Response
    → Frontend api.js → ScopeContext filter → Page Component → KPI Display
```
