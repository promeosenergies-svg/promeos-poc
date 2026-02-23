# Patrimoine Snapshot — Contrat API (V58)

**Endpoint** : `GET /api/patrimoine/sites/{site_id}/snapshot`
**Auth** : `X-Org-Id` header (ou JWT) requis

---

## SnapshotResponse

```json
{
  "site_id": 1,
  "nom": "Siège Social Paris",
  "type": "bureau",
  "actif": true,
  "surface_site_m2": 5000.0,
  "surface_sot_m2": 5000.0,
  "surface_tolerance_pct": 0.05,
  "nb_batiments": 2,
  "batiments": [
    {
      "id": 10,
      "nom": "Bâtiment A — Siège",
      "surface_m2": 3000.0,
      "annee_construction": 2005,
      "cvc_power_kw": 120.5,
      "usages": [
        { "id": 1, "type": "bureaux" }
      ]
    },
    {
      "id": 11,
      "nom": "Bâtiment B — Annexe",
      "surface_m2": 2000.0,
      "annee_construction": 2010,
      "cvc_power_kw": null,
      "usages": []
    }
  ],
  "nb_compteurs": 1,
  "compteurs": [
    {
      "id": 5,
      "type": "electrique",
      "numero_serie": "PRM12345678901",
      "delivery_point_id": 3,
      "delivery_code": "12345678901234",
      "energy_vector": "ELECTRICITY"
    }
  ],
  "nb_delivery_points": 1,
  "delivery_points": [
    {
      "id": 3,
      "code": "12345678901234",
      "energy_type": "ELEC",
      "status": "ACTIVE"
    }
  ],
  "nb_contracts": 1,
  "contracts": [
    {
      "id": 7,
      "energy_type": "elec",
      "supplier_name": "EDF",
      "start_date": "2023-01-01",
      "end_date": "2025-12-31",
      "auto_renew": false
    }
  ],
  "computed_at": "2026-02-23T14:00:00Z"
}
```

### Règles surface SoT (D1)

| Cas | surface_sot_m2 |
|-----|----------------|
| Bâtiments présents (deleted_at IS NULL) | `sum(b.surface_m2)` |
| Aucun bâtiment actif | `site.surface_m2` |
| Aucun bâtiment ET site.surface_m2 NULL | `null` |

### Filtrage strict

- Bâtiments : `deleted_at IS NULL` uniquement
- Compteurs : `actif = True AND deleted_at IS NULL` uniquement
- DeliveryPoints : `deleted_at IS NULL` uniquement
- Contrats : tous (pas de soft-delete sur `EnergyContract`)

---

## AnomaliesResponse

**Endpoint** : `GET /api/patrimoine/sites/{site_id}/anomalies`

```json
{
  "site_id": 1,
  "anomalies": [
    {
      "code": "SURFACE_MISMATCH",
      "severity": "MEDIUM",
      "title_fr": "Écart de surface détecté",
      "detail_fr": "Surface site : 5000 m² · ∑ bâtiments : 7500 m² · Écart : 50.0 % (tolérance : 5 %).",
      "evidence": {
        "surface_site_m2": 5000,
        "surface_batiments_sum_m2": 7500.0,
        "ecart_pct": 50.0
      },
      "cta": {
        "label": "Voir les bâtiments",
        "to": "/patrimoine"
      },
      "fix_hint_fr": "Mettez à jour la surface du site ou des bâtiments pour réduire l'écart."
    }
  ],
  "completude_score": 93,
  "nb_anomalies": 1,
  "computed_at": "2026-02-23T14:00:00Z"
}
```

### Codes P0

| Code | Sévérité | Pénalité | Condition |
|------|----------|----------|-----------|
| `ORPHANS_DETECTED` | CRITICAL | -30 | site.actif=False + enfants actifs |
| `CONTRACT_DATE_INVALID` | HIGH | -15 | start >= end |
| `CONTRACT_OVERLAP_SITE` | HIGH | -15 | chevauchement contrats même énergie |
| `SURFACE_MISSING` | HIGH | -15 | surface_sot_m2 nulle |
| `BUILDING_MISSING` | MEDIUM | -7 | 0 bâtiment |
| `METER_NO_DELIVERY_POINT` | MEDIUM | -7 | compteur sans DP |
| `SURFACE_MISMATCH` | MEDIUM | -7 | écart > 5 % |
| `BUILDING_USAGE_MISSING` | LOW | -3 | bâtiment sans usage |

### Score de complétude

```
score = max(0, 100 - Σ penalties)
```

Trié : CRITICAL → HIGH → MEDIUM → LOW (backend).

---

## ListOrgAnomaliesResponse

**Endpoint** : `GET /api/patrimoine/anomalies`

**Paramètres** :
- `page` (int, défaut=1)
- `page_size` (int, défaut=20, max=100)
- `min_score` (int optionnel, filtre sites avec score ≤ valeur)

```json
{
  "total": 5,
  "page": 1,
  "page_size": 20,
  "sites": [
    {
      "site_id": 3,
      "nom": "Entrepôt Lyon",
      "completude_score": 40,
      "nb_anomalies": 4,
      "top_severity": "CRITICAL",
      "anomalies": [...]
    }
  ]
}
```

Trié par `completude_score ASC` (les plus dégradés en premier).

---

## Nomenclature Compteur vs Meter (D3)

| Modèle | Table | Rôle | Exposé dans snapshot |
|--------|-------|------|---------------------|
| `Compteur` | `compteurs` | Entité patrimoine métier (CRUD, delivery_point FK, actif, soft-delete) | ✅ `compteurs[]` |
| `Meter` | `meter` | Entité analytics (lectures, profils, anomalies KB engine) | ❌ (hors périmètre snapshot) |

`Compteur.delivery_code` = property : retourne `delivery_point.code` ou fallback `meter_id` (legacy).
