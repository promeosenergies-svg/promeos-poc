# Audit TURPE 7 dates réglementaires — Phase D-2 hotfix Tier 1 P0.1

**Date** : 2026-05-07
**Source** : `regulatory-expert` agent SDK (Pilier 6 ADR-016 audit deep multi-agents)
**Périmètre** : correction commit Phase D-1 (`2726c77b`) qui cite "JO 14/05/2025 = date application TURPE 7"

## Verdict cardinal

**Le YAML PROMEOS `tarifs_reglementaires.yaml` est factuellement faux** sur 2 dates :

| Champ | Avant (Phase D-1) | Correct | Confidence |
| --- | --- | --- | --- |
| `turpe_6.valid_to` | `2025-07-31` | **`2025-01-31`** | high |
| `turpe.valid_from` (TURPE 7) | `2025-08-01` | **`2025-02-01`** | high |
| Commentaire source | "JO 14/05/2025, en vigueur 1/08/2025" | "publié CRE 20/03/2025, mouvement tarifaire exceptionnel 1/02/2025" | high |

## Contexte réglementaire

CRE a annoncé en décembre 2024 un **mouvement tarifaire exceptionnel** au **1er février 2025** (au lieu du calendrier annuel habituel du 1er août). Source : communiqué CRE du 12/12/2024 + délibérations CRE 2025-77 (HTB/RTE) et 2025-78 (HTA-BT/Enedis) du 13/03/2025, publiées sur cre.fr le 20/03/2025.

Le **1er août 2025** a fait l'objet d'un communiqué CRE confirmant le **maintien stable** des grilles TURPE 7 — pas de mouvement tarifaire complémentaire.

## Impact

- **Shadow billing** : factures clients calculées avec césure `2025-08-01` au lieu de `2025-02-01` → recalcul rétroactif requis pour la période 2025-02 à 2025-07 (TURPE 7 appliqué dès février).
- **Audit juridique pilote externe** : assertion temporelle réglementaire invalide.

## Actions correctrices Phase D-2.1

Fichier : `backend/config/tarifs_reglementaires.yaml`

```yaml
turpe_6:
  source: "CRE délibération n°2021-13 — TURPE 6 HTA-BT (transition close 31/01/2025 par mouvement tarifaire exceptionnel TURPE 7)"
  valid_from: "2021-08-01"
  valid_to: "2025-01-31"  # CORRIGÉ Phase D-2 (était 2025-07-31)

turpe:
  source: "CRE délibération n°2025-78 du 13/03/2025 (publiée CRE 20/03/2025) — TURPE 7 HTA-BT, mouvement tarifaire exceptionnel 1er février 2025 (communiqué CRE 12/12/2024). NOR Légifrance à figer Phase D-3."
  valid_from: "2025-02-01"  # CORRIGÉ Phase D-2 (était 2025-08-01)
  valid_to: null
```

## Référence à figer Phase D-3

- **NOR Légifrance** : non récupéré (Légifrance.gouv.fr retourne 403 systématique sur WebFetch — escalade humaine consultation directe nécessaire)
- **Date publication JO exacte** : probablement entre 14/03 et fin mars 2025 (publication CRE = 20/03/2025), mention "JO 14/05/2025" du commit Phase D-1 vraisemblablement erronée — confidence: medium-low.

## Sources cardinales

- CRE.fr — page délibération TURPE 7 HTA-BT : https://www.cre.fr/documents/deliberations/tarif-dutilisation-des-reseaux-publics-de-distribution-delectricite-turpe-7-hta-bt-1.html
- CRE.fr — recherche TURPE 7 mouvement exceptionnel 1er février 2025 : https://www.cre.fr/recherche?q=mouvement+tarifaire+TURPE+7+1er+fevrier+2025
- CRE.fr — communiqué TRVE 1er août 2025 (maintien grilles stables) : https://www.cre.fr/recherche?q=TURPE+7+evolution+1er+aout+2025+ajustement

**Confidence verdict global** : high (consensus CRE multi-sources + cohérence calendrier SENTINEL-REG `agent_veille_reglementaire.md`).
