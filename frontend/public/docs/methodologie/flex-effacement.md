# Méthodologie — Flex Intelligence (Effacement comme revenu)

> Référence accessible depuis le SolPageFooter de `/flex`.
> Dernière révision : 2026-04-27 (Sprint 1.10 — couverture nav 100%).

## Objet

PROMEOS Sol évalue le potentiel d'effacement de votre patrimoine sans engagement. Le moteur **Flex Intelligence** inventorie les actifs pilotables (CVC, batterie, photovoltaïque, process), calcule un **Flex Score** sur 4 dimensions et chiffre les revenus potentiels via les mécanismes RTE de marché capacité (NEBCO, AOFD).

**Différenciation marché clé** : PROMEOS Sol n'est **pas aggregateur**. Vos données restent chez vous, vous choisissez librement votre dispositif (auto-effacement, contrat aggregateur, ou combinaison). Vs Voltalis / GreenFlex / Smart Energie / Veolia Effacement / EDF Effacement (qui contractualisent l'agrégation).

## Promesse §4.6 doctrine

« Effacement comme revenu — éligibilité NEBCO (mécanisme effacement RTE), Flex Score, bridge aggregateurs. PROMEOS industrialise l'audit flex sans contrainte : pas d'engagement aggregateur, neutralité, données chez le client. »

## Vocabulaire — explications FR

| Acronyme | Sens |
|---------|------|
| **NEBCO** | Notification Effacement Bloc Courte Durée — mécanisme effacement RTE court terme |
| **AOFD** | Appels d'Offres Effacement Diffus — RTE, contrats long terme |
| **GTB** | Gestion Technique du Bâtiment — système contrôle CVC/éclairage/etc. |
| **Capacité RTE** | Mécanisme de capacité : revenu pour disponibilité d'effacement |
| **Aggregateur** | Tiers qui contractualise et revend l'effacement de plusieurs sites |

## Sources réglementaires

| Référentiel | Périmètre |
|-------------|-----------|
| **RTE Règles Mécanisme Capacité** | Cadre marché capacité 2024-2026 |
| **Règles NEBCO** (RTE) | Bloc effacement courte durée — appel jour J |
| **AOFD Diffus** (RTE) | Appels d'offres long terme effacement |
| **EN 15232** | Classes A/B/C/D efficacité GTB (norme bâtiments) |
| **ISO 50001 §6.6** | Surveillance assets pilotables |

## Inventaire FlexAsset

```python
class FlexAsset:
    site_id: int
    asset_type: HVAC | IRVE | COLD_STORAGE | THERMAL_STORAGE
                | BATTERY | PV | LIGHTING | PROCESS | OTHER
    power_kw: float            # Puissance nominale
    energy_kwh: float | None   # Capacité stockage si applicable
    is_controllable: bool      # Contrôle distant possible ?
    control_method: GTB | API | MANUAL | SCHEDULED
    gtb_class: 'A' | 'B' | 'C' | 'D'   # Classe EN 15232
    confidence: high | medium | low | unverified
```

Sources d'inventaire (`data_source`) : déclaratif site, inspection terrain, import CSV, sync BACS automatique. La **confidence** (haute/moyenne/faible/non vérifié) qualifie chaque actif.

## Flex Score (4 dimensions)

```python
flex_score = mean([
    technical_readiness_score,   # Maturité tech (assets contrôlables, GTB classe A/B)
    data_confidence_score,       # Qualité données (couverture, fraîcheur, complétude)
    economic_relevance_score,    # Impact € potentiel vs effort (kWh/an × prix marché)
    regulatory_alignment_score,  # Aligné NEBCO/AOFD/Tempo (status enum)
])
```

| Score | Verdict |
|-------|---------|
| **≥ 60/100** | Potentiel actionnable — passage en revenu NEBCO/AOFD envisageable |
| **30-60** | Intermédiaire — leviers identifiables pour passer le cap |
| **< 30** | Limité — instrumentation prioritaire (GTB / métrologie) |

## Algorithme priorisation

### 1. Filtrage assets contrôlables

```python
controllable_assets = [a for a in assets if a.is_controllable]
total_kw = sum(a.power_kw for a in controllable_assets)
```

### 2. Seuil viabilité NEBCO

Bloc d'effacement RTE viable : **100 kW minimum** (constante PROMEOS `_FLEX_SEUIL_KW_SIGNIFICATIF`). En-dessous → revenus marginaux, recommandation auto-effacement local ou agrégation cross-sites.

### 3. Estimation revenus

```
revenu_estime_eur_an ≈ potential_kwh_year × prix_effacement_moyen
prix_effacement_moyen ≈ 30 €/MWh (NEBCO 2025-2026, à raffiner avec signal RTE)
```

Estimation conservative — les prix réels NEBCO varient selon volatilité spot et tension réseau hivernale.

## KPIs hero §5

### 1. Potentiel pilotable
`Σ FlexAsset.power_kw WHERE is_controllable=true` sur le scope. Décomposé en `dont N actifs sur M total` pour visibilité maturité.

### 2. Score Flex moyen
`AVG(FlexAssessment.flex_score)` sur les sites évalués. Décomposé en `sur N sites` pour transparence couverture audit.

### 3. Énergie annuelle
`Σ FlexAssessment.potential_kwh_year` converti en MWh/an. Convertible en revenu marché capacité ou appels d'offres effacement (estimation modélisée).

## Provenance

| Confiance | Critère |
|-----------|---------|
| **Haute** | Au moins 1 FlexAsset OU FlexAssessment + sites_count > 0 |
| **Moyenne** | sites_count > 0 mais aucun audit (patrimoine non instrumenté) |
| **Faible** | Aucun site analysé |

## Workflow recommandé

1. **Inventaire** — déclarer ou importer les actifs pilotables (CVC, batterie, PV)
2. **Audit** — lancer FlexAssessment, obtenir Flex Score 4 dimensions
3. **Décision** :
   - Score ≥ 60 + ≥ 100 kW → **éligible NEBCO**, choisir auto-effacement OU aggregateur informé
   - Score < 60 → renforcer instrumentation (GTB, métrologie temps réel) avant monétisation
   - Score < 30 → audit énergétique préalable (cf. `/diagnostic-conso`)

## Référence interne

- `backend/models/flex_models.py:FlexAsset`, `FlexAssessment`, `NebcoSignal`
- `backend/services/flex_assessment_service.py`
- `backend/services/flex/flexibility_scoring_engine.py`
- `backend/services/flex/archetype_resolver.py`
- `backend/services/narrative/narrative_generator.py:_build_flex`
- `frontend/src/pages/FlexPage.jsx`

## Différenciation marché — wedge

Concurrents traditionnels (Voltalis, GreenFlex, Smart Energie, Veolia Effacement, EDF Effacement) **contractualisent l'agrégation** : ils prennent une commission sur chaque effacement, votre site devient client de leur plateforme et vos données partent chez eux.

PROMEOS Sol propose **l'inverse** :

- Vos **données restent chez vous** (BDD client, pas SaaS multi-tenant aggregateur)
- Aucune commission sur l'effacement
- Vous choisissez librement : auto-effacement (vous touchez 100 % du revenu marché capacité) OU contrat aggregateur informé (avec tableau comparatif PROMEOS)
- Cas hybride supporté : effacement local pour les pics + contrat aggregateur pour la base

C'est un **moat durable** : si la régulation ouvre l'effacement à tous (post-décret 2026 simplification), PROMEOS bénéficie ; si l'agrégation reste oligopolistique, PROMEOS reste l'outil de comparaison neutre.

## Phase actuelle (Sprint 1.10)

Le briefing éditorial Sol §5 expose les 3 KPIs hero (Potentiel pilotable / Score Flex / Énergie annuelle) à partir de `FlexAsset` + `FlexAssessment` déjà persistés. La page `/flex` est minimale (P0 = grammaire éditoriale Sol industrialisée, données réelles) — la cartographie complète UI (carpet plot puissance pilotable 24×7, simulateur revenus NEBCO, comparateur aggregateurs) suivra Sprint 2+.

## Versioning

Mises à jour seuils RTE (NEBCO, AOFD, capacité) → publication versionnée avec révision de cette page. Calibrage annuel des constantes de scoring sur baseline observée.
