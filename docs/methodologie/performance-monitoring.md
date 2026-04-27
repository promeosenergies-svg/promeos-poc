# Méthodologie — Monitoring Performance Électrique

> Référence accessible depuis le SolPageFooter de `/monitoring`.
> Dernière révision : 2026-04-27 (Sprint 1.7).

## Objet

Le **moteur Monitoring** de PROMEOS Sol pilote en continu la performance électrique de chaque site : puissance souscrite, charge réseau, qualité des relevés, profils horaires. Il détecte automatiquement les dérives et émet des alertes priorisées par impact économique. Conforme ISO 50001 (système de management de l'énergie) et COSTIC (méthodologie audit énergétique tertiaire FR).

## Promesse §4.2 doctrine

« Performance et diagnostics — pilotage temps réel, KPIs électriques, qualité données, alertes automatiques. Conforme ISO 50001 + COSTIC. »

## Sources réglementaires & référentielles

| Référentiel | Périmètre |
|------------|-----------|
| **ISO 50001:2018** | Système de management de l'énergie — base contractuelle Audit SMÉ |
| **COSTIC** | Méthodologie audit énergétique tertiaire (réseau bureaux d'études FR) |
| **Décret Tertiaire** | Obligations de réduction conso 2030/2040/2050 — supports monitoring |
| **CRE délibération TURPE 7** | Grille acheminement référence calcul puissance souscrite optimale |

## Mécanismes audités

### 1. Score de qualité données (`data_quality_score`, 0-100)

Calculé sur trois axes :

```
score = w_completeness × completeness_pct
      + w_consistency × consistency_pct
      + w_regularity × regularity_pct
```

| Axe | Mesure |
|-----|--------|
| **Complétude** | % d'index relevés présents sur la période (CDC 30 min ou journalier) |
| **Cohérence** | % de relevés sans valeur aberrante (ramp-rate, pic anormal, valeur nulle) |
| **Régularité** | Écart-type des intervalles de relevé |

Seuils :
- **≥ 80** : pilotage fiable, KPIs exploitables sans réserve
- **50-80** : zone de vigilance, vérifier la collecte télérelevé
- **< 50** : qualité dégradée, recommandation de réinstrumentation

### 2. Puissance souscrite vs Pmax

```
ratio_puissance = Pmax_observé / Puissance_souscrite
```

| Ratio | Signal |
|-------|--------|
| < 0,7 | **Surtarification** — puissance trop élevée, possibilité de baisse |
| 0,7-0,95 | Optimum |
| 0,95-1,0 | Zone tampon, surveiller les pics |
| ≥ 1,0 | **Dépassement** — pénalités CSPE/TURPE déclenchées |

### 3. Hors-horaires (`offhours_kwh`)

Consommation observée sur les plages 22h-6h en semaine + WE complet, ramenée en € via prix de référence contrat. Utile pour détecter :
- Ventilation/CTA tournant 24/7
- Eau chaude sanitaire mal programmée
- Veilles informatique non coupées

### 4. Profils jour-type

Comparaison `weekday_profile_kw[]` (moyenne semaine ouvrée) vs `weekend_profile_kw[]` (WE) sur 24 créneaux horaires. Ratio anormal (`weekend_ratio > 0,7`) = process tournant en non-occupation.

## Algorithme alertes

### Génération

Pour chaque site et chaque mécanisme audité, le moteur compare la valeur observée à un seuil :

```python
if observed > threshold:
    alert = MonitoringAlert(
        alert_type=mechanism,
        severity=compute_severity(deviation_pct),
        evidence_json={"measured": x, "threshold": y, "deviation_pct": z},
        explanation=...,
        recommended_action=...,
        estimated_impact_eur=compute_impact(deviation, price_ref),
    )
```

### Sévérité

| Sévérité | Critère |
|----------|---------|
| `INFO` | Écart < 10 % du seuil — informationnel |
| `WARNING` | 10-30 % d'écart — à programmer |
| `HIGH` | 30-50 % d'écart — action prioritaire |
| `CRITICAL` | ≥ 50 % d'écart **OU** dépassement puissance souscrite **OU** impact > 1 000 € |

### Workflow

```
OPEN  →  ACK  →  RESOLVED
```

- `OPEN` : alerte active, non traitée
- `ACK` : prise en charge (action programmée ou en cours)
- `RESOLVED` : correction validée, KPI revenu en zone normale

## KPIs hero §5

### 1. Confiance données
Moyenne `MonitoringSnapshot.data_quality_score` sur les derniers snapshots de chaque site du scope (org + scope filtré ScopeContext).

### 2. Alertes actives
`COUNT(MonitoringAlert WHERE status=OPEN)` sur le scope. Décomposé en `dont N critiques` si applicable.

### 3. Impact dérives
`Σ MonitoringAlert.estimated_impact_eur WHERE status=OPEN`. Cumul des pertes économiques estimées sur les alertes ouvertes — cible de récupération via correction.

## Provenance

| Confiance | Critère |
|-----------|---------|
| **Haute** | Score qualité moyen ≥ 80 + couverture EMS ≥ 80 % du scope |
| **Moyenne** | Score qualité 50-80, ou scope partiel |
| **Faible** | Score qualité < 50 — fiabilité dégradée signalée explicitement |

## Référence interne

- `backend/services/electric_monitoring/` — moteur monitoring
- `backend/models/energy_models.py:MonitoringSnapshot` + `MonitoringAlert`
- `backend/services/narrative/narrative_generator.py:_build_monitoring`
- `frontend/src/pages/MonitoringPage.jsx`

## Différenciation marché

Les concurrents (Advizeo, Deepki, Citron, Energisme) proposent généralement des dashboards de visualisation. PROMEOS Sol va plus loin : **détection automatique d'alertes** typées par mécanisme, **chiffrage € de l'impact** par alerte, **workflow lifecycle** OPEN/ACK/RESOLVED, et **liaison KB** vers les recommandations actionnables. Cette industrialisation est unique dans le marché B2B FR.

## Versioning

Mises à jour seuils (CRE TURPE, COSTIC, déductions ISO 50001) → publication via `engine_version` versionné dans MonitoringSnapshot. Modifications algorithme alertes → commit explicite + révision de cette page.
