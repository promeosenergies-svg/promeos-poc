---
name: promeos-billing-shadow
description: >
  Expert facturation énergie B2B et shadow billing.
  Structure facture élec/gaz, TURPE 7, accise, CTA,
  détection anomalies, audit facture automatisé.
version: 2.0.0
tags: [billing, shadow, facture, turpe, accise, cta, anomalie]
---

# Facturation & Shadow Billing -- Expert PROMEOS

## 1. Structure d'une Facture Électricité B2B (depuis 01/02/2026)

### Composantes (ordre facture)
```
FACTURE ÉLECTRICITÉ B2B
  Fourniture (prix fournisseur)
    HP : consommation x prix_HP (EUR/kWh)
    HC : consommation x prix_HC (EUR/kWh)
    Abonnement fourniture
  TURPE 7 (acheminement réseau -- CRE délib. 2025-78)
    Part fixe (abonnement puissance)
    Part variable HPH/HCH/HPB/HCB/Pointe (EUR/kWh)
    CMDPS si dépassement puissance
  Accise électricité (depuis 01/02/2026)
    T1 ménages : 30.85 EUR/MWh
    T2 PME/pro : 26.58 EUR/MWh
  CTA : 15% de la part fixe TURPE (depuis 01/02/2026)
  TVA : 5.5% sur abo+CTA, 20% sur conso+taxes
```

### Pondération HP/HC type
- HP : 62% de la consommation annuelle
- HC : 38% de la consommation annuelle

## 2. Structure d'une Facture Gaz B2B

### Composantes
```
FACTURE GAZ B2B
  Fourniture (molécule)
    Prix x volume (EUR/MWh PCS)
    Abonnement fourniture
  Acheminement (ATRD + ATRT)
    Transport (ATRT/GRTgaz)
    Distribution (ATRD/GRDF)
  Accise gaz : 16.39 EUR/MWh (10.73 accise + 5.66 ZNI)
  CTA gaz : % part fixe acheminement
  TVA : 5.5% abo+CTA, 20% conso+taxes
  Stockage : contribution stockage souterrain
```

## 3. Contrats PROMEOS -- Architecture V2

### ContratCadre (niveau entité juridique)
- Fournisseur, dates, grille tarifaire de base
- 30 fournisseurs CRE validés

### AnnexeSite (niveau site)
- PRM/PCE, puissance souscrite, option tarifaire
- Surcharges prix optionnelles (override cadre)
- Engagement volume, indexation

### Règle de pricing
```python
resolve_pricing(annexe) -> source: 'cadre' ou 'override'
# Source unique de vérité pour tout calcul financier
```

### 16 règles de cohérence R1-R16
- R13 : puissance souscrite compatible segment tarifaire
- R14 : dates contrat cohérentes (début < fin)
- R15 : option tarifaire compatible avec tension
- R16 : volume engagement réaliste vs historique

## 4. Shadow Billing PROMEOS

### Principe
Recalculer la facture fournisseur à partir des données Enedis
et comparer avec la facture réelle pour détecter les erreurs.

### 20 règles d'audit automatisées
| Règle | Type | Impact |
|-------|------|--------|
| A01 | Erreur TVA (taux ou base) | Moyen |
| A02 | Erreur accise catégorie (T1 vs T2) | Élevé |
| A03 | Erreur puissance souscrite vs contrat | Élevé |
| A04 | Dépassement CMDPS non facturé | Moyen |
| A05 | Période de facturation incorrecte | Moyen |
| A06 | Option tarifaire sous-optimale | Élevé |
| A07 | CTA taux incorrect (!=15% depuis 02/2026) | Élevé |
| A08 | TURPE 6 appliqué au lieu de TURPE 7 | Élevé |
| A09 | Indexation ARENH post-2025 (caduque) | Élevé |
| A10 | Doublon PRM + même période (BILL_006) | Critique |

### Décomposition shadow billing
```python
# Calcul côté backend uniquement
facture_shadow = {
    "fourniture": conso_hp * prix_hp + conso_hc * prix_hc,
    "turpe": calcul_turpe_7(conso, puissance, option),
    "accise": conso_mwh * accise_categorie,  # T1=30.85, T2=26.58
    "cta": part_fixe_turpe * 0.15,            # 15% depuis 02/2026
    "tva_reduite": (abo + cta) * 0.055,
    "tva_pleine": (fourniture + turpe + accise) * 0.20,
    "total_ttc": total_ht + tva_reduite + tva_pleine
}
ecart = facture_reelle_ttc - facture_shadow_ttc
```

## 5. Accises 2026 (valeurs officielles depuis 01/02/2026)

| Énergie | Catégorie | Tarif |
|---------|-----------|-------|
| Électricité | T1 ménages (<=250 MWh) | 30.85 EUR/MWh |
| Électricité | T2 PME/pro (250 MWh-1 GWh) | 26.58 EUR/MWh |
| Gaz naturel | Total (accise + ZNI) | **16.39 EUR/MWh** |

Source : EDF/Engie docs 02/2026, Légifrance

## 6. Règles de Calcul TURPE 7 (CRE délib. n°2025-78)

### Structure TURPE 7 BT/HTA (01/08/2025 au 31/07/2029)
- Composante Soutirage (CS) : fixe + variable
- Composante Injection (CI) : si production
- Composante de Gestion (CG) : abonnement comptage

### Tarifs HPH par segment
| Segment | HPH (EUR/kWh) |
|---------|---------------|
| HTA | **0.0442** |
| BT > 36 kVA (C4) | **0.0569** |

### CMDPS
- **12.65 EUR/kW** par heure de dépassement
- Calculé sur puissance quart-heure max vs souscrite

## 7. CTA -- Historique et valeur actuelle

| Période | Taux CTA |
|---------|----------|
| Avant 08/2021 | 27.04% |
| 08/2021 - 01/2026 | 21.93% |
| **Depuis 01/02/2026** | **15%** |

Source : Arrêté du 28 janvier 2026 (CNIEG officiel)
