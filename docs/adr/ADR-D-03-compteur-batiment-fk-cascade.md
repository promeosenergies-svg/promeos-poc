# ADR-D-03 — `Compteur.batiment_id` FK ajout cascade analytics

**Statut** : ✅ ACCEPTED — implémenté Phase D-4 Tier 1 (commit `2268e90d`)
**Date** : 2026-05-08
**Sprint** : Phase D-4 Tier 1 candidat
**Décideurs** : à figer post-revue (architect-helios + ems-expert)

## Contexte

Audit écarts matrice v1 (`AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`) révèle :

- Matrice §4.6.A#12 `batiment_id` FK Compteur→Batiment annoncée "À vérifier"
- **Verdict audit : ABSENT du repo**
- Sans cette FK, agrégation conso par bâtiment impossible

Différenciateur PROMEOS : BACS classe + APER zoning nécessitent agrégation par bâtiment, pas par site.

## Options

### Option A — FK directe `Compteur.batiment_id` nullable

- **Pour** : analytics par bâtiment direct, perf query, alignement matrice v1
- **Contre** : migration colonne + risque baseline tests

### Option B — Cascade indirecte via Site.batiments + Compteur.site_id

- **Pour** : pas de migration
- **Contre** : agrégation par bâtiment impossible (Compteur lie Site, pas Batiment)

### Option C — Table de jointure `compteur_batiment_links`

- **Pour** : N:N possible (cas multi-bâtiments)
- **Contre** : surcomplexité — Pilier 7 ADR-016 anti-pattern (table de jointure pour 1:N)

## Décision (à figer Phase D-4 Tier 1)

**Recommandation cardinal** : Option A (FK directe nullable).

Justification :
1. Différenciateur PROMEOS BACS + APER analytique par bâtiment
2. Cohérent doctrine Pilier 1 (SoT runtime explicite)
3. Migration Alembic légère (1 colonne + index)

## Conséquences

- Migration Alembic 17e (`Compteur.batiment_id` Integer FK nullable + index)
- Nullable car cas legacy : compteurs existants sans rattachement bâtiment
- Wizard onboarding doit proposer rattachement (non bloquant MVP)
- Cascade ondelete=SET NULL (Bâtiment supprimé n'efface pas Compteur)

## Effort estimé

**3-4h** : migration + cascade + tests + wizard onboarding (option).

## Liens

- [`AUDIT_ECARTS_MATRICE_V1_2026_05_07.md`](../audits/AUDIT_ECARTS_MATRICE_V1_2026_05_07.md) §3 P0-MATV1-010
- Matrice v1 : §4.6.A#12
- ADR-D-01 (dualité Compteur/Meter — Pilier 8 ADR-016)
