# Exemples API PROMEOS

> Requetes/reponses realistes alignees sur les donnees de demo.
> Tous les exemples utilisent des champs reels des schemas Pydantic.

---

## 1. Liste des sites

### Request

```
GET /api/patrimoine/sites?portefeuille_id=1&limit=3
Authorization: Bearer <token>
X-Request-Id: req-a1b2c3d4
```

### Response `200 OK`

```
X-Request-Id: req-a1b2c3d4
X-Response-Time: 42ms
```

```json
{
  "total": 12,
  "sites": [
    {
      "id": 1,
      "nom": "Hypermarche Paris #01",
      "type": "commerce",
      "adresse": "87 Avenue de la Republique",
      "code_postal": "75001",
      "ville": "Paris",
      "region": "IDF",
      "surface_m2": 7500,
      "nombre_employes": 142,
      "siret": "55400867154321",
      "naf_code": "4711F",
      "actif": true,
      "portefeuille_id": 1,
      "data_source": "demo",
      "created_at": "2025-09-15T10:30:00",
      "updated_at": "2025-11-20T14:12:00"
    },
    {
      "id": 2,
      "nom": "Hypermarche Lyon #02",
      "type": "commerce",
      "adresse": "33 Rue Victor Hugo",
      "code_postal": "69001",
      "ville": "Lyon",
      "region": "ARA",
      "surface_m2": 5200,
      "nombre_employes": 98,
      "siret": "55400867178432",
      "naf_code": "4711F",
      "actif": true,
      "portefeuille_id": 1,
      "data_source": "demo",
      "created_at": "2025-09-15T10:30:01",
      "updated_at": "2025-11-20T14:12:01"
    },
    {
      "id": 3,
      "nom": "Hypermarche Marseille #03",
      "type": "commerce",
      "adresse": "156 Boulevard Gambetta",
      "code_postal": "13001",
      "ville": "Marseille",
      "region": "PACA",
      "surface_m2": 9800,
      "nombre_employes": 175,
      "siret": "55400867192187",
      "naf_code": "4711F",
      "actif": true,
      "portefeuille_id": 1,
      "data_source": "demo",
      "created_at": "2025-09-15T10:30:02",
      "updated_at": "2025-11-20T14:12:02"
    }
  ]
}
```

---

## 2. Creer un compteur

### Request

```
POST /api/compteurs
Authorization: Bearer <token>
X-Request-Id: req-e5f6g7h8
Content-Type: application/json
```

```json
{
  "site_id": 1,
  "type": "electricite",
  "numero_serie": "DEMO-E-0001",
  "puissance_souscrite_kw": 250.0
}
```

### Response `200 OK`

```json
{
  "id": 1,
  "site_id": 1,
  "type": "electricite",
  "numero_serie": "DEMO-E-0001",
  "puissance_souscrite_kw": 250.0
}
```

---

## 3. Consommations d'un compteur

### Request

```
GET /api/consommations?compteur_id=1&limit=3
Authorization: Bearer <token>
X-Request-Id: req-i9j0k1l2
```

### Response `200 OK`

```json
[
  {
    "id": 412,
    "compteur_id": 1,
    "timestamp": "2025-12-18T14:00:00",
    "valeur": 38.72,
    "cout_euro": 5.81
  },
  {
    "id": 411,
    "compteur_id": 1,
    "timestamp": "2025-12-18T13:00:00",
    "valeur": 36.15,
    "cout_euro": 5.42
  },
  {
    "id": 410,
    "compteur_id": 1,
    "timestamp": "2025-12-18T12:00:00",
    "valeur": 41.03,
    "cout_euro": 6.15
  }
]
```

---

## 4. Conformites reglementaires -- synthese

### Request

```
GET /api/compliance/summary?org_id=1
Authorization: Bearer <token>
X-Request-Id: req-m3n4o5p6
```

### Response `200 OK`

```
X-Request-Id: req-m3n4o5p6
X-Response-Time: 87ms
```

```json
{
  "total_sites": 36,
  "sites_ok": 14,
  "sites_nok": 9,
  "sites_unknown": 8,
  "pct_ok": 38.9,
  "findings_by_regulation": {
    "bacs": { "ok": 12, "nok": 8, "unknown": 4, "out_of_scope": 12 },
    "decret_tertiaire_operat": { "ok": 10, "nok": 8, "unknown": 6, "out_of_scope": 12 },
    "aper": { "ok": 4, "nok": 0, "unknown": 6, "out_of_scope": 26 }
  },
  "top_actions": [
    "Installer un systeme GTB classe A ou B",
    "Completer les donnees energetiques annuelles",
    "Soumettre la declaration sur OPERAT"
  ]
}
```

---

## 5. Findings compliance -- detail d'un finding

### Request

```
GET /api/compliance/findings/42
Authorization: Bearer <token>
X-Request-Id: req-q7r8s9t0
```

### Response `200 OK`

```json
{
  "id": 42,
  "site_id": 3,
  "site_nom": "Hypermarche Marseille #03",
  "regulation": "bacs",
  "rule_id": "BACS_HIGH_DEADLINE",
  "status": "NOK",
  "severity": "critical",
  "deadline": "2025-01-01",
  "evidence": "CVC > 290 kW, echeance 01/01/2025 — attestation BACS manquante",
  "actions": [
    "Installer un systeme GTB classe A ou B",
    "Obtenir attestation BACS"
  ],
  "insight_status": "open",
  "owner": null,
  "notes": null,
  "run_batch_id": 1,
  "inputs": { "cvc_power_kw": 312.5, "tertiaire_area_m2": 9800 },
  "params": { "threshold_kw": 290, "deadline": "2025-01-01" },
  "evidence_refs": {},
  "engine_version": "demo_seed_v1",
  "created_at": "2025-11-20T14:15:00",
  "updated_at": "2025-11-20T14:15:00"
}
```

---

## 6. Compteurs d'un site

### Request

```
GET /api/compteurs?site_id=2
Authorization: Bearer <token>
X-Request-Id: req-u1v2w3x4
```

### Response `200 OK`

```json
[
  {
    "id": 3,
    "site_id": 2,
    "type": "electricite",
    "numero_serie": "DEMO-E-0002",
    "puissance_souscrite_kw": 180.0,
    "created_at": "2025-09-15T10:30:01"
  },
  {
    "id": 4,
    "site_id": 2,
    "type": "gaz",
    "numero_serie": "DEMO-G-0002",
    "puissance_souscrite_kw": null,
    "created_at": "2025-09-15T10:30:01"
  }
]
```

---

## 7. Alertes monitoring actives

### Request

```
GET /api/monitoring/alerts?site_id=1&status=open&limit=3
Authorization: Bearer <token>
X-Request-Id: req-y5z6a7b8
```

### Response `200 OK`

```
X-Request-Id: req-y5z6a7b8
X-Response-Time: 35ms
```

```json
[
  {
    "id": 17,
    "alert_type": "high_night_base",
    "severity": "warning",
    "site_id": 1,
    "meter_id": 1,
    "explanation": "Consommation nocturne elevee : 42% de la conso totale.",
    "recommended_action": "Verifier les equipements fonctionnant la nuit (CVC, eclairage, process).",
    "estimated_impact_kwh": 18500,
    "estimated_impact_eur": 2775,
    "evidence": { "night_ratio": 0.42, "threshold": 0.35 },
    "kb_link": {},
    "status": "open",
    "acknowledged_at": null,
    "resolved_at": null,
    "resolution_note": null,
    "snapshot_id": 1,
    "created_at": "2025-12-01T08:00:00"
  },
  {
    "id": 18,
    "alert_type": "power_risk",
    "severity": "critical",
    "site_id": 1,
    "meter_id": 1,
    "explanation": "Risque de depassement de puissance souscrite (score 85/100).",
    "recommended_action": "Evaluer un ajustement de la puissance souscrite ou un effacement de pointe.",
    "estimated_impact_kwh": null,
    "estimated_impact_eur": 4250,
    "evidence": { "risk_score": 85 },
    "kb_link": {},
    "status": "open",
    "acknowledged_at": null,
    "resolved_at": null,
    "resolution_note": null,
    "snapshot_id": 1,
    "created_at": "2025-12-01T08:00:01"
  },
  {
    "id": 19,
    "alert_type": "off_hours_consumption",
    "severity": "warning",
    "site_id": 1,
    "meter_id": 1,
    "explanation": "Consommation hors horaires elevee : 45% du total.",
    "recommended_action": "Programmer l'extinction des equipements en dehors des heures d'ouverture.",
    "estimated_impact_kwh": 12400,
    "estimated_impact_eur": 1860,
    "evidence": { "off_hours_ratio": 0.45, "off_hours_kwh": 24800 },
    "kb_link": {},
    "status": "open",
    "acknowledged_at": null,
    "resolved_at": null,
    "resolution_note": null,
    "snapshot_id": 1,
    "created_at": "2025-12-01T08:00:02"
  }
]
```

---

## 8. Factures d'une periode

### Request

```
GET /api/billing/invoices?site_id=1&status=validated
Authorization: Bearer <token>
X-Request-Id: req-c9d0e1f2
```

### Response `200 OK`

```
X-Request-Id: req-c9d0e1f2
X-Response-Time: 28ms
```

```json
{
  "invoices": [
    {
      "id": 1,
      "site_id": 1,
      "invoice_number": "INV-0001-202512",
      "period_start": "2025-12-01",
      "period_end": "2025-12-31",
      "total_eur": 18742.50,
      "energy_kwh": 125000.0,
      "status": "validated",
      "source": "demo_seed"
    },
    {
      "id": 5,
      "site_id": 1,
      "invoice_number": "INV-0001-202511",
      "period_start": "2025-11-01",
      "period_end": "2025-11-30",
      "total_eur": 16890.30,
      "energy_kwh": 112000.0,
      "status": "validated",
      "source": "demo_seed"
    }
  ],
  "count": 2
}
```

---

## 9. Creer une facture avec lignes

### Request

```
POST /api/billing/invoices
Authorization: Bearer <token>
X-Request-Id: req-g3h4i5j6
Content-Type: application/json
```

```json
{
  "site_id": 2,
  "contract_id": 2,
  "invoice_number": "INV-0002-202601",
  "period_start": "2026-01-01",
  "period_end": "2026-01-31",
  "issue_date": "2026-02-12",
  "total_eur": 14580.75,
  "energy_kwh": 98000.0,
  "lines": [
    {
      "line_type": "energy",
      "label": "Fourniture electricite",
      "qty": 98000.0,
      "unit": "kWh",
      "unit_price": 0.1185,
      "amount_eur": 11613.00
    },
    {
      "line_type": "network",
      "label": "Acheminement (TURPE)",
      "amount_eur": 1568.00
    },
    {
      "line_type": "tax",
      "label": "Taxes et contributions",
      "amount_eur": 1249.75
    },
    {
      "line_type": "other",
      "label": "Abonnement mensuel",
      "amount_eur": 150.00
    }
  ]
}
```

### Response `200 OK`

```json
{
  "status": "created",
  "invoice_id": 16
}
```

---

## 10. KPIs monitoring d'un site

### Request

```
GET /api/monitoring/kpis?site_id=5
Authorization: Bearer <token>
X-Request-Id: req-k7l8m9n0
```

### Response `200 OK`

```json
{
  "snapshot_id": 5,
  "site_id": 5,
  "meter_id": 5,
  "period": "2025-09-20 - 2025-12-18",
  "kpis": {
    "total_kwh": 142500.0,
    "pmean_kw": 65.8,
    "pmax_kw": 185.3,
    "pbase_kw": 12.4,
    "p95_kw": 142.0,
    "night_ratio": 0.18,
    "weekend_ratio": 0.95,
    "off_hours_ratio": 0.32,
    "off_hours_kwh": 45600.0,
    "load_factor": 0.355,
    "puissance_souscrite_kva": 120
  },
  "data_quality_score": 96.5,
  "risk_power_score": 72.0,
  "data_quality_details": {
    "quality_score": 96.5,
    "completeness": 0.98,
    "gaps_count": 3
  },
  "risk_power_details": {
    "risk_score": 72,
    "overrun_hours": 14,
    "max_overrun_pct": 18.5
  },
  "climate": {
    "r_squared": 0.74,
    "base_load_kwh": 8.2,
    "heating_slope": 1.45,
    "cooling_slope": 0.82,
    "balance_point_heat": 15.0,
    "balance_point_cool": 22.0
  },
  "schedule": {
    "open_days": "0,1,2,3,4,5",
    "open_time": "09:00",
    "close_time": "20:00",
    "is_24_7": false,
    "timezone": null
  },
  "impact": {
    "price": {
      "eur_per_kwh": 0.15,
      "source": "contract"
    },
    "off_hours": {
      "kwh": 45600.0,
      "eur": 6840.0,
      "annualized_eur": 27360.0
    },
    "power_overrun": {
      "p95_kw": 142.0,
      "psub_kva": 120,
      "overrun_kw": 22.0,
      "eur": 1100.0
    }
  },
  "emissions": {
    "total_kwh": 142500.0,
    "kgco2e_per_kwh": 0.052,
    "total_kgco2e": 7410.0,
    "total_tco2e": 7.41,
    "source_label": "Facteur demo POC (base ADEME 2024)"
  },
  "engine_version": "demo_seed_v1",
  "created_at": "2025-12-18T08:00:00"
}
```

---

## 11. Anomalies de facturation (insights)

### Request

```
GET /api/billing/insights?severity=high&status=open
Authorization: Bearer <token>
X-Request-Id: req-o1p2q3r4
```

### Response `200 OK`

```json
{
  "insights": [
    {
      "id": 3,
      "site_id": 3,
      "invoice_id": 8,
      "type": "overcharge",
      "severity": "high",
      "message": "Surfacturation detectee sur la facture INV-0003-202510: ecart de 28%.",
      "estimated_loss_eur": 3842.50,
      "insight_status": "open",
      "owner": null,
      "notes": null
    }
  ],
  "count": 1
}
```

---

## 12. Alertes legacy (Alerte model)

### Request

```
GET /api/alertes?site_id=1&resolue=false&limit=2
Authorization: Bearer <token>
X-Request-Id: req-s5t6u7v8
```

### Response `200 OK`

```json
{
  "total": 4,
  "alertes": [
    {
      "id": 12,
      "site_id": 1,
      "severite": "critical",
      "titre": "Depassement de puissance souscrite",
      "description": "Puissance mesuree 285 kW, souscrite 250 kW.",
      "timestamp": "2025-12-17T14:35:00",
      "resolue": false,
      "date_resolution": null
    },
    {
      "id": 11,
      "site_id": 1,
      "severite": "warning",
      "titre": "Consommation nocturne anormale",
      "description": "Consommation nocturne 42% superieure a la moyenne.",
      "timestamp": "2025-12-15T03:12:00",
      "resolue": false,
      "date_resolution": null
    }
  ]
}
```
