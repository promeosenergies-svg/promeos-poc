# Méthodologie — Diagnostic Consommation

> Référence accessible depuis le SolPageFooter de `/diagnostic-conso`.
> Dernière révision : 2026-04-27 (Sprint 1.8).

## Objet

Le **moteur Diagnostic** de PROMEOS Sol identifie automatiquement les leviers d'économies d'énergie sur chaque site : consommation hors heures d'ouverture, talon excessif, pics de puissance, dérives saisonnières, trous de données. Chaque levier est chiffré en euros annuels récupérables et associé à un plan d'actions priorisé par effort/gain. Conforme ISO 50001 (norme management énergie) et COSTIC (méthode audit énergétique tertiaire FR).

## Promesse §4.2 doctrine (suite Monitoring)

« Diagnostics consommation — détection automatique des anomalies, chiffrage € des leviers d'économies, plan d'actions priorisées par effort/gain. Conforme ISO 50001 + COSTIC NF EN 16247-2. »

## 5 catégories d'anomalies détectées

| Type | Signal | Méthode |
|------|--------|---------|
| `hors_horaires` | Consommation > seuil pendant les plages 22h-6h sem. + WE | Profil agrégé sur la période, ratio kWh hors-horaires / kWh total |
| `base_load` | Talon nuit > 30 % du Pmax — process tournant en non-occupation | `pbase_night_kw / pmax_kw` issu de MonitoringSnapshot |
| `pointe` | Pics de puissance répétés > 95% Pmax sans corrélation occupation | Histogramme `peak_to_average` + détection clustering |
| `derive` | Augmentation tendancielle vs baseline DJU+occupation | CUSUM sur signature énergétique (régression DJU+occupation) |
| `data_gap` | Trou ≥ 24h dans les relevés sur la période | Différentiel attendu vs relevé, conformité Enedis SGE |

### Méthode CUSUM (Cumulative Sum) — détection de dérive

Pour chaque site, baseline mensuelle calculée par régression linéaire :

```
conso_attendue = β₀ + β₁ × DJU + β₂ × occupation
```

CUSUM cumule les écarts résiduels entre conso observée et conso attendue. Une dérive est détectée si le cumul franchit ±3σ pendant ≥ 4 semaines consécutives — seuil ISO 50001 §6.6.

### Sources réglementaires

| Référentiel | Périmètre |
|-------------|-----------|
| **ISO 50001:2018 §6.6** | Surveillance, mesure et analyse — base CUSUM |
| **COSTIC NF EN 16247-2** | Méthode audit énergétique bâtiments tertiaires |
| **DJU COSTIC** | Degrés-Jours Unifiés base 18 °C, normalisation climatique |
| **Décret Tertiaire** | Cible -40% conso 2030 — diagnostic = première étape |

## Sévérité

| Sévérité | Critère |
|----------|---------|
| `low` | Gain estimé < 200 €/an OU période < 30j |
| `medium` | 200 €/an ≤ gain < 1 000 €/an |
| `high` | 1 000 €/an ≤ gain < 5 000 €/an |
| `critical` | ≥ 5 000 €/an OU récurrence ≥ 3 mois consécutifs OU dépassement contractuel |

## Workflow

```
OPEN  →  ACK  →  RESOLVED  ou  FALSE_POSITIVE
```

- `OPEN` : levier détecté, non traité
- `ACK` : action programmée (intégrée plan d'actions)
- `RESOLVED` : correction implémentée et validée par retour à la baseline
- `FALSE_POSITIVE` : faux positif documenté (saisonnalité acceptée, process spécial)

## Recommandations actionables

Chaque insight porte un `recommended_actions_json` sérialisé :

```json
[
  {
    "title": "Programmer arrêt CTA hors occupation",
    "rationale": "Talon nuit 38% Pmax — économie estimée 1850 €/an",
    "expected_gain_kwh": 12000,
    "expected_gain_eur": 1850,
    "effort": "low",
    "priority": "high"
  }
]
```

Prêt à être basculé en `Action` (workflow CTA → plan d'actions) via `/actions/new`.

## KPIs hero §5

### 1. Leviers identifiés
`COUNT(ConsumptionInsight WHERE insight_status=OPEN)` — décomposé en `dont N prioritaires` si `severity=critical`.

### 2. Gisement annuel
`Σ ConsumptionInsight.estimated_loss_eur WHERE status=OPEN` — cumul des pertes estimées récupérables par actions correctives. Ne mesure pas une perte réalisée mais un potentiel.

### 3. Économies sécurisées YTD
`Σ ConsumptionInsight.estimated_loss_eur WHERE status=RESOLVED` depuis le 1er janvier — cumul des gains validés (action implémentée + retour à la baseline confirmé).

## Provenance

| Confiance | Critère |
|-----------|---------|
| **Haute** | Au moins 1 levier OPEN ou RESOLVED + sites_count > 0 (analyse réelle) |
| **Moyenne** | sites_count > 0 mais aucun levier détecté (patrimoine optimisé OU couverture EMS partielle) |
| **Faible** | Aucun site analysé |

## Référence interne

- `backend/services/consumption_diag/` — moteur diagnostic 5 catégories
- `backend/models/consumption_insight.py:ConsumptionInsight`
- `backend/services/narrative/narrative_generator.py:_build_diagnostic`
- `frontend/src/pages/ConsumptionDiagPage.jsx`

## Différenciation marché

À notre connaissance, les concurrents B2B FR (Advizeo, Deepki, Citron, Energisme, Trinergy) proposent des dashboards de consommation sans détection automatique chiffrée des leviers + workflow lifecycle + plan d'actions priorisé. PROMEOS Sol industrialise ce travail traditionnellement fait à la main par les BE énergie en mission ponctuelle (audit COSTIC) — le moteur tourne en continu, le rapport est toujours à jour, le suivi des actions est intégré.

## Versioning

Mises à jour seuils sévérité ou méthodologie CUSUM → publication versionnée avec révision de cette page. Recalibration annuelle des seuils baseline DJU à chaque clôture saison de chauffe.
