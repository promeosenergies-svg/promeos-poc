# PROMEOS — Règles Réglementaires

> Source de vérité : `backend/regops/config/regs.yaml` + `backend/rules/*.yaml`

## 1. Décret Tertiaire / OPERAT

### Assujettissement
- **Seuil** : surface tertiaire assujettie ≥ 1 000 m²
- **Source** : Art. R. 174-22 du Code de la construction
- **Implémentation** : `tertiaire_service.py` → `qualify_efa()`

### Trajectoire de réduction
| Échéance | Objectif | Implémenté |
|----------|----------|-----------|
| 2030 | −40% vs référence | ✅ Rule `DT_TRAJECTORY_2030` |
| 2040 | −50% vs référence | ✅ Rule `DT_TRAJECTORY_2040` |
| 2050 | −60% vs référence | ❌ Non implémenté |

### Obligations
| Rule ID | Condition | Sévérité | Action requise |
|---------|-----------|----------|----------------|
| `DT_SCOPE` | `tertiaire_area_m2 >= 1000` | HIGH | Qualifier le site |
| `DT_OPERAT` | Déclaration OPERAT soumise | CRITICAL | Déclarer conso sur OPERAT |
| `DT_ENERGY_DATA` | Données conso annuelles | MEDIUM | Collecter données |

### Pénalités
| Infraction | Montant | Source |
|-----------|---------|--------|
| Non-déclaration OPERAT | 7 500 € | Art. R. 185-2 |
| Non-affichage trajectoire | 1 500 € | Art. R. 185-2 |

### Formule risque site
```
Si NON_CONFORME : 7 500 €
Si A_RISQUE     : 3 750 €
Si CONFORME     : 0 €
```

---

## 2. Décret BACS / GTB-GTC

### Assujettissement par Puissance Utile (Putile)
| Seuil | Obligation | Échéance |
|-------|-----------|----------|
| CVC > 290 kW | GTB classe A ou B obligatoire | 01/01/2025 |
| 70 < CVC ≤ 290 kW | GTB classe A ou B obligatoire | 01/01/2030 |
| CVC ≤ 70 kW | Non concerné | — |

### Calcul Putile
```
Par canal (chauffage / climatisation) :
  - Architecture CASCADE ou RESEAU → SUM(unité.kw)
  - Architecture INDEPENDANT → MAX(unité.kw)

Putile_final = MAX(Putile_chauffage, Putile_climatisation)
```
**Source** : `bacs_engine.py` → `compute_putile()`

### Obligations
| Rule ID | Condition | Sévérité |
|---------|-----------|----------|
| `BACS_HIGH_DEADLINE` | CVC > 290 kW + pas d'attestation | CRITICAL |
| `BACS_LOW_DEADLINE` | 70 < CVC ≤ 290 kW + pas d'attestation | HIGH |
| `BACS_ATTESTATION` | Attestation valide requise | HIGH |
| `BACS_DEROGATION` | Dérogation possible (TRI > 10 ans) | LOW |

### Exigences R.175-3 (10 fonctionnalités GTB)
1. Suivi et enregistrement continu
2. Pas de temps horaire
3. Logique par zone fonctionnelle
4. Conservation mensuelle 5 ans
5. Valeurs de référence
6. Détection pertes d'efficacité
7. Interopérabilité (BACnet/KNX/OPC)
8. Arrêt manuel possible
9. Gestion autonome
10. Propriété/accessibilité des données

### Pénalité
| Infraction | Montant |
|-----------|---------|
| Non-conformité BACS | 7 500 € |

### Preuves requises (4)
- Attestation BACS
- Consignes exploitation
- Formation personnel
- Rapport d'inspection

---

## 3. Loi APER (Solarisation)

### Seuils
| Type | Surface seuil | Échéance | Obligation |
|------|--------------|----------|------------|
| Parking extérieur ≥ 10 000 m² | 10 000 m² | 01/07/2026 | Ombrières PV |
| Parking extérieur ≥ 1 500 m² | 1 500 m² | 01/07/2028 | Ombrières PV |
| Toiture neuve/rénovée | 500 m² | 01/01/2028 | PV ou végétalisation |

### Rules
| Rule ID | Condition | Sévérité |
|---------|-----------|----------|
| `APER_PARKING` | `parking_m2 >= 1500 AND outdoor` | HIGH |
| `APER_TOITURE` | `roof_m2 >= 500` | MEDIUM |
| `APER_PARKING_TYPE` | Vérification parking extérieur | LOW |

### Estimation PV
- Placeholder dans `aper_service.py`
- PVGIS non branché (P1 gap)
- Benchmark ADEME disponible dans les données de seed

---

## 4. CEE (Certificats d'Économie d'Énergie)

- **Statut** : mécanisme de financement, hors score conformité
- **Modèle** : `cee_models.py` — CeeDossier, CeeEvidence, CeeStep
- **Workflow** : instruction → validation → délivrance
- **Gap** : pas intégré dans le calcul ROI des actions (P1)

---

## 5. Score Conformité Composite

### Formule
```
score = Σ(score_fw × weight_fw) − penalty_critiques
```

### Poids
| Framework | Poids | Source |
|-----------|-------|--------|
| Décret Tertiaire / OPERAT | 0.45 | `regs.yaml` |
| BACS | 0.30 | `regs.yaml` |
| APER | 0.25 | `regs.yaml` |
| **Total** | **1.00** | |

### Pénalité findings critiques
- Par finding critique : −5 pts
- Maximum : −20 pts
- Source : `regs.yaml > scoring > critical_penalty`

### Score par statut
| Statut | Score |
|--------|-------|
| COMPLIANT / CONFORME | 100 |
| DEROGATION | 80 |
| AT_RISK / A_RISQUE / EN_COURS | 50 |
| NON_COMPLIANT / NON_CONFORME | 0 |
| UNKNOWN | 50 |

---

## 6. Versionning des règles

- Fichiers YAML versionnés : `decret_tertiaire_operat_v1.yaml`, `decret_bacs_v1.yaml`, `loi_aper_v1.yaml`
- `engine_version` stocké sur `RegAssessment` et `ComplianceRunBatch`
- Champ `framework` explicite sur `RegAssessment` (V101+)
- `_detect_framework_legacy()` conservé en fallback
