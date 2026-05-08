# ADR-D-04 — `Site.bacs_puissance_cvc_totale_kw` cascade Σ(Batiment.cvc_power_kw)

**Statut** : DRAFT (post-audit Phase 0 matrice v1)
**Date** : 2026-05-08
**Sprint** : Phase D-4 Tier 1 candidat
**Décideurs** : à figer post-revue (architect-helios + regulatory-expert)

## Contexte

Audit écarts matrice v1 (`AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`) révèle :

- Matrice §4.4.E#43 `bacs_puissance_cvc_totale_kw` typage flou (saisie vs agrégé)
- Matrice §4.4.E#42 `bacs_assujetti` calculé via `puissance_cvc_totale_kw ≥ 70 (BACS_THRESHOLD_KW_EXISTING)`
- `Batiment.cvc_power_kw` existe au niveau bâtiment, mais Site n'agrège pas

Sans agrégation Site, scoring BACS impossible automatiquement.

## Options

### Option A — Cascade `cascade_recompute_service` Σ(Batiment)

- **Pour** : single source of truth (Batiment), anti-divergence, doctrine Pilier 3 (cascade vivante)
- **Contre** : nécessite service `cascade_recompute_service` Phase C-1

### Option B — Saisie utilisateur directe `Site.bacs_puissance_cvc_totale_kw`

- **Pour** : flexibilité onboarding (Site sans bâtiments détaillés)
- **Contre** : double SoT possible — risque divergence Site vs Σ Batiment

### Option C — Hybride avec validation

- **Pour** : flexibilité + anti-divergence
- **Contre** : complexité (3 cas : tous bâtiments saisis / aucun / partiels)

## Décision (à figer Phase D-4 Tier 1)

**Recommandation cardinal** : Option A (cascade Σ Batiment) avec fallback C ciblé.

Justification :
1. Doctrine Pilier 3 (cascade vivante) — pattern existant Phase C-4 (cascade Org consentements)
2. Anti double SoT (Site agrégé recalculé automatiquement)
3. Traçabilité audit : modification Batiment.cvc_power_kw → recalcul Site → AuditLog

## Conséquences

- Service `cascade_recompute_service` Phase C-1 cible (pré-requis)
- Trigger SQLAlchemy event listener `Batiment.cvc_power_kw` → invalidation cache Site
- Migration Alembic léger (`Site.bacs_puissance_cvc_totale_kw` Float nullable)
- Tests cascade : modif Batiment → recalcul Site → recalcul `bacs_assujetti`

## Effort estimé

**2-3h** : cascade + tests + recalcul `bacs_assujetti` cohérent.

## Liens

- [`AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`](../audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md) §3 P0-MATV1-005
- Matrice v1 : §4.4.E#42-43 + §8.4 cascade recompute
- Cascade existante : Sprint C-4 Phase 4.5 Org consentements
