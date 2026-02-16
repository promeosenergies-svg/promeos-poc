# Module BACS Expert — Decret n°2020-887

## 1. Vue d'ensemble

Le module BACS (Building Automation and Control Systems) implemente la reglementation
francaise sur l'automatisation et le controle technique des batiments (GTB/GTC).

**Decret n°2020-887** du 20 juillet 2020: obligation d'installer des systemes
d'automatisation et de controle pour les batiments tertiaires non-residentiels.

## 2. Architecture

```
┌─────────────────────────────────────────┐
│ frontend/src/components/BacsWizard.jsx  │  UI: Wizard 4 etapes
│ frontend/src/components/BacsOpsPanel.jsx│  UI: Panel monitoring ops
├─────────────────────────────────────────┤
│ frontend/src/services/api.js            │  10 fonctions BACS
├─────────────────────────────────────────┤
│ backend/routes/bacs.py                  │  10 endpoints API
├─────────────────────────────────────────┤
│ backend/services/bacs_engine.py         │  Moteur deterministe v2
│ backend/services/bacs_ops_monitor.py    │  Service monitoring ops
│ backend/services/bacs_seed.py           │  Seed demo 10 sites
├─────────────────────────────────────────┤
│ backend/models/bacs_models.py           │  4 modeles SQLAlchemy
│ backend/models/enums.py                 │  4 enums BACS
├─────────────────────────────────────────┤
│ backend/regops/rules/bacs.py            │  Wrapper legacy (compatibilite)
└─────────────────────────────────────────┘
```

## 3. Modeles de donnees

| Modele | Table | Description |
|--------|-------|-------------|
| BacsAsset | bacs_assets | Actif BACS lie a un site (eligibilite, PC, renouvellement) |
| BacsCvcSystem | bacs_cvc_systems | Systeme CVC inventorie (type, architecture, unites kW) |
| BacsAssessment | bacs_assessments | Evaluation cachee (obligation, seuil, TRI, score) |
| BacsInspection | bacs_inspections | Inspection quinquennale (date, statut, rapport) |

## 4. Calcul Putile (Puissance Utile)

| Architecture | Methode | Formule |
|-------------|---------|---------|
| CASCADE | Somme | Putile = sum(kW de toutes les unites) |
| NETWORK | Somme | Putile = sum(kW de toutes les unites) |
| INDEPENDENT | Maximum | Putile = max(kW parmi les unites) |

**Putile final** = max(Putile_chauffage, Putile_climatisation)

La ventilation est ignoree pour le calcul du seuil.

### Exemple

```
Systeme 1: Chauffage, CASCADE, [PAC 150kW, PAC 100kW] → 250 kW
Systeme 2: Climatisation, INDEPENDENT, [Chiller 180kW, Chiller 120kW] → 180 kW
Putile = max(250, 180) = 250 kW → seuil 70 kW → echeance 2030
```

## 5. Calendrier reglementaire

| Condition | Seuil | Echeance | Trigger |
|-----------|-------|----------|---------|
| Putile > 290 kW (existant) | 290 kW | 01/01/2025 | THRESHOLD_290 |
| Putile > 70 kW (existant) | 70 kW | 01/01/2030 | THRESHOLD_70 |
| Putile <= 70 kW | — | — | OUT_OF_SCOPE |
| Construction neuve post 09/04/2023 | 0 | Date PC | NEW_CONSTRUCTION |
| Renouvellement CVC post 09/04/2023 | 70 kW | Date renouv. | RENEWAL |

## 6. Exemption TRI

**Formule:**
```
cout_net = cout_bacs * (1 - aides_pct / 100)
economies_annuelles = conso_kwh * gain_pct / 100 * prix_kwh
TRI = cout_net / economies_annuelles
```

Si **TRI > 10 ans**: exemption possible (article R. 175-7 du CCH).

**Limites POC**: le calcul TRI est best-effort. Si les donnees manquent,
`tri_years: null` et `exemption_possible: null`. Le DQ gate signale WARNING.

## 7. Inspections quinquennales

- Periodicite max: **5 ans**
- 1ere inspection: echeance de l'obligation
- Suivantes: derniere inspection + 5 ans
- Statut: SCHEDULED, COMPLETED, OVERDUE

## 8. Data Quality Gate

| Tier | Champs | Impact |
|------|--------|--------|
| CRITICAL | cvc_power_kw | BLOCKED si manquant |
| OPTIONAL | has_bacs_attestation, has_bacs_derogation | Ameliore la confiance |
| BACS-specific CRITICAL | is_tertiary, pc_date, cvc_inventory, cvc_architecture | Evalues par bacs_engine DQ |
| BACS-specific IMPORTANT | conso_2_ans_kwh, prix_kwh, cout_bacs_eur, aides_pct | WARNING si manquants |

## 9. API Reference

| Methode | Endpoint | Description |
|---------|----------|-------------|
| GET | /api/regops/bacs/site/{id} | Assessment complet + systemes + inspections + DQ |
| POST | /api/regops/bacs/recompute/{id} | Recalculer l'assessment |
| GET | /api/regops/bacs/score_explain/{id} | Putile trace + seuil + TRI |
| GET | /api/regops/bacs/data_quality/{id} | Gate DQ BACS specifique |
| POST | /api/regops/bacs/asset | Creer un BacsAsset |
| POST | /api/regops/bacs/asset/{id}/system | Ajouter un systeme CVC |
| PUT | /api/regops/bacs/system/{id} | Modifier un systeme CVC |
| DELETE | /api/regops/bacs/system/{id} | Supprimer un systeme CVC |
| GET | /api/regops/bacs/site/{id}/ops | Panel monitoring ops |
| POST | /api/regops/bacs/seed_demo | Seed 10 sites demo |

## 10. Wizard UI (4 phases)

1. **Eligibilite**: tertiaire, date PC, renouvellement, responsable
2. **Inventaire CVC**: systemes + unites kW + Putile preview bar
3. **Resultat**: verdict assujetti/non, echeance, TRI, score, findings
4. **Plan d'actions**: actions recommandees + export JSON

## 11. Monitoring Ops

- **KPIs**: delai conformite, countdown inspection, alertes CVC, gains baseline
- **Consommation mensuelle**: barres CSS (pas de lib chart)
- **Heatmap horaire**: grille 24x7 CSS avec couleurs Tailwind
- **Findings operationnels**: insights conso enrichis contexte BACS/GTB
- **Alertes CVC**: stub simulees (temperature drift, schedule mismatch, COP drop)

## 12. Decisions POC + TODO backlog

| Decision | Raison | TODO futur |
|----------|--------|-----------|
| Pas de lib chart | POC 2 fondateurs, zero deps | Recharts/D3 si besoin |
| Heatmap CSS grille | Suffisant pour demo | Lib specialisee si perf |
| TRI best-effort | Donnees souvent manquantes | Formulaire dedié + defaults KB |
| Alertes CVC stub | Pas de connecteur GTB reel | Connecteur Modbus/BACnet |
| Inspections manuelles | Pas de source externe | Import automatique rapports |
| Legacy wrapper | Compatibilite pipeline RegOps | Migrer vers bacs_engine natif |

## 13. Tests

| Fichier | Tests | Couverture |
|---------|-------|-----------|
| test_bacs_engine.py | 34 | Putile, obligation, TRI, inspection, full flow, legacy |
| test_bacs_api.py | 16 | GET/POST/PUT/DELETE, seed demo, DQ gate |
| test_bacs_ops.py | 7 | KPIs, consumption linkage, ops panel, API endpoint |
| **Total** | **57** | |
