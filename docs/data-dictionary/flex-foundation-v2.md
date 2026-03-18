# Data Dictionary — Flex Foundation V2

**Date :** 2026-03-18
**Scope :** Sprint 21 — fondations uniquement

---

## Nouveaux modèles

### FlexAsset

| Champ | Type | PK/FK | Nullable | Default | Description |
|-------|------|-------|----------|---------|-------------|
| id | Integer | PK | non | auto | Identifiant unique |
| site_id | Integer | FK sites.id | non | — | Site de rattachement |
| batiment_id | Integer | FK batiments.id | oui | null | Bâtiment si applicable |
| bacs_cvc_system_id | Integer | FK bacs_cvc_systems.id | oui | null | Lien CVC BACS si applicable |
| asset_type | Enum | — | non | — | hvac, irve, cold_storage, thermal_storage, battery, pv, lighting, process, other |
| label | String(300) | — | non | — | Nom descriptif de l'asset |
| power_kw | Float | — | oui | null | Puissance nominale en kW |
| energy_kwh | Float | — | oui | null | Capacité stockage en kWh (batterie, thermique) |
| is_controllable | Boolean | — | non | false | Asset pilotable oui/non |
| control_method | String(50) | — | oui | null | gtb, api, manual, scheduled, unknown |
| gtb_class | String(1) | — | oui | null | Classe EN 15232 (A/B/C/D), dérivé de BACS si lié |
| data_source | String(50) | — | oui | null | declaratif, inspection, import, bacs_sync |
| confidence | String(20) | — | oui | unverified | high, medium, low, unverified |
| status | String(20) | — | non | active | active, inactive, decommissioned |
| notes | Text | — | oui | null | Notes libres |
| created_at | DateTime | — | non | now() | Date de création |
| updated_at | DateTime | — | non | now() | Dernière modification |

**Contraintes :**
- `confidence = "high"` interdit si `data_source` est null
- `gtb_class` auto-dérivé de `BacsCvcSystem.system_class` si `bacs_cvc_system_id` est renseigné
- `site_id` doit référencer un site actif (not deleted)

### NebcoSignal

| Champ | Type | PK/FK | Nullable | Default | Description |
|-------|------|-------|----------|---------|-------------|
| id | Integer | PK | non | auto | Identifiant unique |
| date | Date | — | non | — | Date du signal |
| bloc_type | String(50) | — | non | — | effacement, consommation, mixte |
| direction | String(10) | — | non | — | up (réduction conso), down (augmentation conso) |
| price_eur_mwh | Float | — | oui | null | Prix du bloc en EUR/MWh |
| volume_mw | Float | — | oui | null | Volume en MW |
| source | String(50) | — | oui | manual | rte, epex_spot, manual, simulation |
| notes | Text | — | oui | null | |
| created_at | DateTime | — | non | now() | |

**Note :** `direction = "down"` est spécifique à NEBCO (vs NEBEF qui ne supportait que "up").

---

## Modèles enrichis

### TariffCalendar.ruleset_json — format saisonnalisé

**Format standardisé des fenêtres :**

```json
{
  "version": "string (ex: TURPE7-C5-2025)",
  "segment": "string (ex: C5, C4, C3, HTA)",
  "effective_from": "YYYY-MM-DD",
  "seasons": [
    {
      "id": "string (ex: hiver, ete, mi_saison)",
      "months": [1, 2, 3, ...],
      "windows": [
        {
          "period": "string (HC_NUIT | HC_SOLAIRE | HP | POINTE | SUPER_POINTE)",
          "start": "HH:MM",
          "end": "HH:MM",
          "day_types": ["weekday", "weekend", "holiday", "all"],
          "price_component_eur_kwh": 0.00 (optionnel)
        }
      ]
    }
  ],
  "source": "string (CRE, Enedis, manual)",
  "notes": "string"
}
```

**Types de période :**

| Période | Description |
|---------|-------------|
| HC_NUIT | Heures creuses nocturnes (typiquement 23h-7h) |
| HC_SOLAIRE | Heures creuses solaires (réforme 2025-2027, typiquement journée été) |
| HP | Heures pleines standard |
| POINTE | Pointe hiver (TURPE HTA/HTB) |
| SUPER_POINTE | Super-pointe (si applicable) |

**Règle :** Les fenêtres HC_SOLAIRE ne sont PAS universelles. Elles dépendent du calendrier de migration Enedis et du segment client.

---

## Enums ajoutés

### FlexAssetType

| Valeur | Description |
|--------|-------------|
| hvac | Système CVC (chauffage, clim, ventilation) |
| irve | Borne de recharge véhicule électrique |
| cold_storage | Stockage froid (chambre froide, process froid) |
| thermal_storage | Stockage thermique (ballon ECS, inertie bâtiment) |
| battery | Batterie stationnaire |
| pv | Production photovoltaïque |
| lighting | Éclairage pilotable |
| process | Process industriel flexible |
| other | Autre asset pilotable |

### ControlMethod

| Valeur | Description |
|--------|-------------|
| gtb | Pilotage via GTB/GTC |
| api | Pilotage via API (cloud, IoT) |
| manual | Pilotage manuel (consigne opérateur) |
| scheduled | Pilotage programmé (horloge, timer) |
| unknown | Méthode non identifiée |

### NebcoDirection

| Valeur | Description |
|--------|-------------|
| up | Réduction de consommation (effacement classique NEBEF) |
| down | Augmentation de consommation (nouveau NEBCO) |

---

## Relations clés

```
Site ──1:N──► FlexAsset
BacsCvcSystem ──0:1──► FlexAsset (enrichissement optionnel)
FlexAsset.gtb_class ◄── dérivé de BacsCvcSystem.system_class
TariffCalendar ──contient──► seasons[].windows[] (fenêtres saisonnalisées)
NebcoSignal (standalone, pas de FK — données marché)
```

---

## Corrections par rapport à v1

| v1 | v2 | Raison |
|----|-----|--------|
| `HC: 11h-17h` hardcodé | `HC_SOLAIRE` dans TariffCalendar saisonnalisé | Fenêtres variables par distributeur/segment |
| `APER = auto-conso obligatoire` | `APER = solarisation obligatoire + opportunités séparées` | Loi impose l'installation, pas le mode de consommation |
| `CEE = financement` | `CEE = éligibilité potentielle + caveat` | Volume et valorisation non garantis |
| `NEBCO seuil = 100 kW` | `NEBCO seuil = non confirmé` | Pas de source CRE officielle trouvée |
| `TURPE 7 spread élargi` | `TURPE 7 grille CRE par segment` | Barèmes structurés par segment, pas un spread unique |
