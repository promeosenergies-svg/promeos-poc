# Méthodologie — Centre d'actions

> Référence accessible depuis le SolPageFooter de `/anomalies`.
> Dernière révision : 2026-04-27 (Sprint 1.9).

## Objet

Le **Centre d'actions** est la page transverse de PROMEOS Sol qui agrège en un flux unique toutes les anomalies détectées par les 4 piliers du produit : Conformité, Performance, Facturation, Achat. Chaque anomalie remonte vers une `ActionItem` enrichie de son origine, sa priorité et son gain estimé. Le résultat : un seul plan d'actions priorisé pour le DAF / Energy Manager — vs un dashboard par brique chez les concurrents.

## Promesse §3 P11 doctrine

« Le bon endroit pour chaque brique » — chaque pilier détecte ses anomalies dans son contexte (Bill-Intel sur factures, Diagnostic sur conso, Monitoring sur perf, RegOps sur conformité), mais le pilote opérationnel a UNE liste consolidée à traiter. C'est la promesse différenciante PROMEOS Sol vs Advizeo / Deepki / Citron / Energisme (silos par module).

## Sources agrégées

| Pilier | Brique source | Modèle insight | Critère import → ActionItem |
|--------|---------------|----------------|------------------------------|
| **Conformité** | `compliance_score_service` | `RegFinding` | `severity ∈ {HIGH, CRITICAL}` |
| **Performance** | `electric_monitoring` | `MonitoringAlert` | `status = OPEN` |
| **Performance** | `consumption_diag` | `ConsumptionInsight` | `status = OPEN ∧ severity ≥ medium` |
| **Facturation** | `billing_engine` (shadow v4.2) | `BillingInsight` | `status = OPEN ∧ estimated_loss_eur > 0` |
| **Achat** | `purchase_engine` | (renouvellement contrat) | `end_date ≤ +90j` |

L'orchestrateur (`services/actions/sync.py`) déduplique chaque anomalie via la clé composite `(org_id, source_type, source_id, source_key)` pour éviter les doublons cross-rounds d'analyse.

## Modèle ActionItem

```python
class ActionItem(Base):
    org_id: int               # scope canonical
    site_id: int | None       # nullable pour actions org-level
    source_type: ActionSourceType  # compliance / consumption / billing / purchase
    source_id: str            # ID dans la brique source
    source_key: str           # clé dedup intra-source
    title: str                # titre humain
    rationale: str            # justification détaillée
    priority: int             # 1 (critique) à 5 (faible)
    severity: str             # low | medium | high | critical
    estimated_gain_eur: float # gain financier estimé €/an
    due_date: date | None     # échéance
    status: ActionStatus      # OPEN → IN_PROGRESS → DONE / BLOCKED / FALSE_POSITIVE
    owner: str                # responsable assigné
    notes: str                # commentaires opérateur
```

## Workflow lifecycle

```
OPEN  →  IN_PROGRESS  →  DONE
  │                          ↑
  └──→  BLOCKED  ──→  ─────────
  └──→  FALSE_POSITIVE
```

- **OPEN** : anomalie détectée, à traiter
- **IN_PROGRESS** : action programmée, exécution en cours
- **DONE** : action implémentée + gain validé
- **BLOCKED** : dépendance externe (budget, tiers) — déblocage requis
- **FALSE_POSITIVE** : faux positif documenté

Chaque transition génère un `ActionEvent` horodaté (`models/action_detail_models.py`) pour traçabilité audit.

## Priorisation

| Niveau | Critère |
|--------|---------|
| **Critique** | `priority ≤ 2` OU `severity = critical` OU `due_date ≤ today + 7j` |
| **Urgent** | `due_date ≤ today + 30j` |
| **Standard** | `due_date ≤ today + 90j` |
| **Backlog** | sans échéance OU `due_date > today + 90j` |

Le tri principal côté hero week-card DRIFT : `severity = critical` → max `estimated_gain_eur`.

## KPIs hero §5

### 1. Anomalies actives
`COUNT(ActionItem WHERE status=OPEN AND org_id=current)` — décomposé en `dont N critiques` (priorité 1-2 ou severity=critical).

### 2. Impact financier
`Σ ActionItem.estimated_gain_eur WHERE status=OPEN`. Cumul des gains récupérables par actions correctives. Décomposé en `dont N sous 30j` pour visibilité urgence.

### 3. Économies sécurisées
`Σ ActionItem.estimated_gain_eur WHERE status=DONE AND created_at >= 1er janvier`. Gains validés depuis le début de l'année — base solide pour audit ISO 50001 et reporting CSRD.

## Provenance

| Confiance | Critère |
|-----------|---------|
| **Haute** | Au moins 1 ActionItem OPEN ou DONE + sites_count > 0 (orchestration active) |
| **Moyenne** | sites_count > 0 mais aucune action (patrimoine sain OU peu d'instrumentation) |
| **Faible** | Aucun site analysé |

## Référence interne

- `backend/models/action_item.py:ActionItem`
- `backend/services/actions/sync.py` — orchestrateur cross-source
- `backend/services/narrative/narrative_generator.py:_build_anomalies`
- `frontend/src/pages/AnomaliesPage.jsx`

## Différenciation marché

À notre connaissance, aucun acteur B2B FR (Advizeo / Deepki / Citron / Energisme / Trinergy) ne propose une vue **unifiée et priorisée** des anomalies cross-modules avec workflow lifecycle complet et chiffrage € agrégé. Chez les concurrents, l'utilisateur doit consulter chaque dashboard séparément et construire mentalement son plan d'actions. PROMEOS Sol industrialise cette consolidation.

## Versioning

Mises à jour priorité (seuils, règles de mapping severity→priority) → publication versionnée avec révision de cette page. Modifications schema `ActionItem` → migration SQL + commit explicite.
