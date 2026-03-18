# Sprint 21 — Fondations Flex (spec exécutable)

**Date :** 2026-03-18
**Scope :** Fondation uniquement — aucun pilotage réel, aucun nouveau menu principal
**Prérequis :** Sprints 0-20 mergés, audit flex-current-vision validé

---

## 1. DÉCISION

Sprint 21 pose les **fondations data** de la brique flex sans créer de logique de dispatch ni de navigation dédiée. Les objets flex s'intègrent dans les vues patrimoine et conformité existantes.

**Ce qu'on fait :**
- Modèle FlexAsset + lien BACS
- Fenêtres tarifaires autorisées saisonnalisées (pas de hardcode HC)
- TURPE 7 grille de référence
- Structure NEBCO (signal, pas de valorisation)
- Enrichissement flex_mini existant

**Ce qu'on ne fait PAS :**
- Pas de dispatch/pilotage/commande
- Pas de menu "Flexibilité" dans la navigation principale
- Pas de hardcode "11h-17h HC"
- Pas de logique ACC
- Pas de financement CEE garanti

---

## 2. CORRECTIONS DE L'AUDIT

| Point audit v1 | Erreur/simplification | Correction v2 |
|---|---|---|
| "HC 11h-17h" hardcodé | Les fenêtres HC solaires varient par distributeur, saison, segment client | Modèle `TariffWindow` avec saison, type_jour, segment, source officielle |
| "Auto-conso solaire obligatoire" (APER) | APER impose l'installation d'ombrières/PV, pas l'autoconsommation | 2 temps : (a) obligation solarisation, (b) opportunité autoconso/ACC/stockage |
| CEE P6 = "financement projets" | Les CEE sont un levier potentiel, pas un financement garanti | CEE = éligibilité/financement potentiel, jamais garanti. TRI > 3 ans requis |
| NEBCO seuil "100 kW ?" | Non confirmé dans les sources CRE disponibles | Seuil = "à confirmer via délibération CRE 2025-199". Ne pas hardcoder |
| TURPE 7 "spread HP/HC élargi" | Simplifié. Les barèmes TURPE 7 sont structurés par segment (C1-C5, BTINF, etc.) | Intégrer la grille CRE complète par segment, pas un spread unique |
| "Météo démo = baseline non fiabilisé" | Correct mais l'impact est surestimé pour Sprint 21 | Météo réelle = P1 (Sprint 22), pas bloquant pour les fondations |
| Flex scoring "non défendable" | Le flex_mini existant est un scoring heuristique acceptable pour le POC | Enrichir flex_mini avec FlexAsset quand dispo, ne pas le jeter |

---

## 3. SCOPE SPRINT 21

### A. FlexAsset — inventaire assets pilotables

**Objectif :** Permettre d'inventorier les leviers de flexibilité par site/bâtiment.

**Modèle :** `FlexAsset`

| Champ | Type | Obligatoire | Description |
|-------|------|-------------|-------------|
| id | int PK | oui | |
| site_id | FK sites | oui | Site de rattachement |
| batiment_id | FK batiments | non | Bâtiment si applicable |
| bacs_cvc_system_id | FK bacs_cvc_systems | non | Lien CVC si applicable |
| asset_type | enum | oui | `hvac`, `irve`, `cold_storage`, `thermal_storage`, `battery`, `pv`, `lighting`, `process`, `other` |
| label | str(300) | oui | Nom descriptif |
| power_kw | float | non | Puissance nominale |
| energy_kwh | float | non | Capacité de stockage si applicable |
| is_controllable | bool | oui | Pilotable oui/non |
| control_method | str(50) | non | `gtb`, `api`, `manual`, `scheduled`, `unknown` |
| gtb_class | str(1) | non | Classe EN 15232 (A/B/C/D) si lié BACS |
| data_source | str(50) | non | `declaratif`, `inspection`, `import`, `bacs_sync` |
| confidence | str(20) | non | `high`, `medium`, `low`, `unverified` |
| status | str(20) | oui | `active`, `inactive`, `decommissioned` |
| notes | text | non | |
| created_at | datetime | auto | |
| updated_at | datetime | auto | |

**Règles :**
- Si `bacs_cvc_system_id` est renseigné, `gtb_class` est dérivé automatiquement du CVC
- `is_controllable` = false par défaut, passage à true nécessite une source
- Aucun FlexAsset ne peut avoir `confidence = high` sans `data_source` renseigné

### B. TariffWindow — fenêtres tarifaires saisonnalisées

**Objectif :** Remplacer tout hardcode HC/HP par un modèle de fenêtres autorisées.

**Enrichissement de `TariffCalendar` :**

Le champ `ruleset_json` existant supporte déjà des fenêtres JSON. On standardise le format :

```json
{
  "version": "TURPE7-C5-2025",
  "segment": "C5",
  "effective_from": "2025-08-01",
  "seasons": [
    {
      "id": "hiver",
      "months": [11, 12, 1, 2, 3],
      "windows": [
        {"period": "HC_NUIT", "start": "23:00", "end": "07:00", "day_types": ["all"]},
        {"period": "HP", "start": "07:00", "end": "23:00", "day_types": ["all"]}
      ]
    },
    {
      "id": "ete",
      "months": [4, 5, 6, 7, 8, 9, 10],
      "windows": [
        {"period": "HC_NUIT", "start": "23:00", "end": "07:00", "day_types": ["all"]},
        {"period": "HC_SOLAIRE", "start": "11:00", "end": "17:00", "day_types": ["weekday"]},
        {"period": "HP", "start": "07:00", "end": "11:00", "day_types": ["weekday"]},
        {"period": "HP", "start": "17:00", "end": "23:00", "day_types": ["weekday"]}
      ]
    }
  ],
  "source": "CRE délibération 2025-78",
  "notes": "HC solaires = phase réforme Enedis, applicable selon calendrier distributeur"
}
```

**Règles :**
- Jamais de hardcode "11h-17h" — toujours référence à une TariffCalendar versionnée
- Les fenêtres HC solaires dépendent du distributeur et du calendrier de migration Enedis
- `HC_SOLAIRE` est un type de période distinct de `HC_NUIT`
- Le modèle doit supporter N saisons avec N fenêtres chacune

### C. TURPE 7 grille de référence

**Objectif :** Intégrer les barèmes TURPE 7 CRE dans TariffCalendar.

**Action :** Créer un seed `gen_tariff_turpe7.py` qui insère les grilles CRE :
- TURPE 7 BT ≤ 36 kVA (C5)
- TURPE 7 BT > 36 kVA (C4)
- TURPE 7 HTA (C3/C2)

**Source :** Délibération CRE 2025-78 (Légifrance JORFTEXT000051587195)

**Règles :**
- Chaque grille est une TariffCalendar avec `source = "CRE"`, `version = "TURPE7"`
- `effective_from = "2025-08-01"`
- Les barèmes annuels (08/2026, 08/2027, 08/2028) sont préparés comme versions futures

### D. NebcoSignal — structure marché

**Objectif :** Préparer la structure pour la valorisation flex sur marché wholesale.

**Modèle :** `NebcoSignal`

| Champ | Type | Description |
|-------|------|-------------|
| id | int PK | |
| date | date | Date du signal |
| bloc_type | str(50) | `effacement`, `consommation`, `mixte` |
| direction | str(10) | `up` (réduction), `down` (augmentation) |
| price_eur_mwh | float | Prix du bloc |
| volume_mw | float | Volume |
| source | str(50) | `rte`, `epex_spot`, `manual`, `simulation` |
| notes | text | |
| created_at | datetime | auto |

**Règles :**
- Aucune valorisation calculée dans Sprint 21 — structure uniquement
- Le seuil de participation NEBCO n'est pas hardcodé (non confirmé CRE)
- `direction = "down"` (consommation augmentée) est nouveau NEBCO vs ancien NEBEF

### E. Enrichissement flex_mini existant

**Objectif :** Quand des FlexAsset existent, enrichir le scoring existant.

**Modification de `services/flex_mini.py` :**
- Si des FlexAsset sont trouvés pour le site, les utiliser en priorité sur les heuristiques
- Ajouter `source: "asset"` vs `source: "heuristic"` dans chaque levier
- Conserver le fallback heuristique si aucun asset n'est inventorié
- Ne pas casser le comportement existant

### F. APER — correction logique 2 temps

**Objectif :** Clarifier que APER = obligation de solarisation, pas d'autoconsommation.

**Modification `services/aper_service.py` :**
- Renommer dans les réponses API : `"obligation": "solarisation_ombriere"` (pas "autoconsommation")
- Ajouter un champ `opportunities` :
  ```json
  {
    "autoconsommation_individuelle": true,
    "acc_possible": false,
    "stockage_batterie": false,
    "revente_surplus": true
  }
  ```
- Ne pas implémenter la logique ACC — juste le flag de possibilité

### G. CEE P6 — éligibilité potentielle

**Objectif :** Exposer CEE comme levier potentiel, jamais garanti.

**Action :** Ajouter dans les réponses conformité/recommandation :
```json
{
  "cee_eligible": true,
  "cee_period": "P6 (2026-2030)",
  "cee_caveat": "Éligibilité potentielle — volume et valorisation à confirmer par opérateur CEE agréé",
  "cee_tri_min_years": 3
}
```

---

## 4. ENDPOINTS

| Méthode | Path | Description |
|---------|------|-------------|
| GET | /api/flex/assets?site_id= | Liste assets pilotables par site |
| POST | /api/flex/assets | Créer un asset |
| PATCH | /api/flex/assets/{id} | Modifier un asset |
| GET | /api/flex/assets/sync-from-bacs?site_id= | Synchro CVC → FlexAsset |
| GET | /api/tariffs/calendars | Liste TariffCalendar (TURPE 7, etc.) |
| GET | /api/tariffs/calendars/{id}/windows?date=&segment= | Fenêtres applicables à une date |

**Pas d'endpoint pilotage/dispatch/NEBCO valorisation dans ce sprint.**

---

## 5. TESTS & QA

### Tests à écrire

1. **FlexAsset CRUD** : création, lecture, modification, suppression logique
2. **FlexAsset ← BACS sync** : CVC system → FlexAsset avec gtb_class dérivé
3. **FlexAsset confidence** : `high` impossible sans `data_source`
4. **TariffWindow saisonnalisé** : HC_SOLAIRE uniquement en été, pas de hardcode
5. **TURPE 7 seed** : grilles CRE insérées correctement
6. **NebcoSignal CRUD** : structure créée, direction up/down supportée
7. **flex_mini enrichi** : source = "asset" quand FlexAsset existe, fallback "heuristic"
8. **APER 2 temps** : obligation = solarisation, opportunities séparées
9. **CEE caveat** : jamais `cee_guaranteed`, toujours `cee_eligible` + caveat
10. **Invariant chaîne** : FlexAsset.site_id existe dans patrimoine actif

### Régression à vérifier

- flex_mini existant retourne les mêmes résultats sans FlexAsset
- TOU schedule existant continue de fonctionner
- APER dashboard existant non cassé
- Conformité BACS inchangée
- Action center non impacté

---

## 6. DEFINITION OF DONE

- [ ] FlexAsset modèle + CRUD + migration Alembic
- [ ] Lien BacsCvcSystem → FlexAsset (sync endpoint)
- [ ] TariffCalendar enrichi avec format saisonnalisé (HC_NUIT, HC_SOLAIRE, HP)
- [ ] Seed TURPE 7 (C5, C4, C3/C2) avec source CRE
- [ ] NebcoSignal modèle (structure uniquement)
- [ ] flex_mini enrichi (FlexAsset > heuristique)
- [ ] APER corrigé (solarisation ≠ autoconsommation)
- [ ] CEE P6 = éligibilité potentielle + caveat
- [ ] 10+ tests fondations
- [ ] 0 régression sur la chaîne PROMEOS
- [ ] Aucun menu "Flexibilité" créé
- [ ] Aucun dispatch/pilotage codé
