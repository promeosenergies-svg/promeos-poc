---
name: energy-autoconsommation
description: "Autoconsommation collective ACC, PPA, production décentralisée France : clés de répartition, périmètre élargi, TURPE ACC, garanties d'origine GO, ombrières PV parkings APER, toitures solaires, stockage couplé, taux autoconsommation, AO CRE, S21/S22, LCOE, surplus injection. Utiliser ce skill pour autoconsommation, PV B2B, ACC, PPA corporate, garanties d'origine, ombrières parking, dimensionnement PV, ou production énergie décentralisée."
---

# Autoconsommation & Production Décentralisée France

## Proactive triggers

- Toiture > 500m² sans évaluation PV → "Cette toiture est éligible APER. Évaluer le potentiel PV."
- Parking > 1500m² sans ombrières → "Obligation APER: ombrières PV sur 50% du parking. Sanctions: 40,000€/an + 200€/place."
- Taux autoconsommation < 50% → "Taux d'autoconsommation faible. Évaluer le stockage ou le pilotage de charge."

## Autoconsommation individuelle (ACI)

Producteur = consommateur, même PRM. Pas de TURPE sur la part autoconsommée.
Surplus : injection gratuite (≤36kVA sans contrat), vente OA EDF (guichet ≤500kWc), vente marché.
KPIs : taux autoconsommation = conso_locale / production_totale, taux autoproduction = conso_locale / conso_totale.

## Autoconsommation collective (ACC)

Producteur(s) ≠ consommateurs, multi-PRM, au sein d'un périmètre géographique.
**PMO** (Personne Morale Organisatrice) obligatoire : gère clés de répartition, convention avec Enedis.
Linky requis (tous participants). Comptage 30min pour allocation.

### Périmètre géographique

| Puissance installée | Rayon max | Cadre |
|---|---|---|
| ≤3 MW | 2 km | Standard |
| 3-10 MW | 10 km | Arrêté 21/02/2025 (élargi) |
| 5-10 MW | 20 km (expérimental) | Cas par cas, demande DGEC |

### Clés de répartition

- **Statique** : coefficients fixes (ex: 30% participant A, 70% participant B). Simple, peu optimal.
- **Dynamique** : prorata consommation réelle au pas 30min. Maximise l'autoconsommation, requiert données temps réel.
- **Au prorata puissance souscrite** : variante statique proportionnelle.

### TURPE en ACC

Part soutirage : réduite sur la part autoconsommée (exonération composante variable du TURPE).
Composante fixe TURPE : maintenue intégralement (gestion, comptage).
Composante injection (S21/S22) : producteur paie le TURPE injection.
⚠️ Le bénéfice TURPE ACC dépend du ratio autoconsommation : au-dessus de 30%, gain significatif.

### Tarifs injection surplus (S21/S22)

| Tranche | S21 (vente totale) | S22 (surplus) |
|---|---|---|
| ≤3 kWc | ~0.1276 €/kWh | ~0.1276 €/kWh |
| 3-9 kWc | ~0.1087 €/kWh | ~0.0761 €/kWh |
| 9-36 kWc | ~0.1087 €/kWh | ~0.0761 €/kWh |
| 36-100 kWc | ~0.1087 €/kWh | ~0.0761 €/kWh |
| 100-500 kWc | Guichet OA EDF | ~0.0560 €/kWh |

Tarifs OA révisés trimestriellement (CRE). Valeurs indicatives 2025.

## PPA (Power Purchase Agreement)

| Type | Durée | Avantage | Complexité |
|---|---|---|---|
| Physique on-site | 15-25 ans | Pas de TURPE, contrôle total | Investissement lourd ou tiers |
| Physique off-site | 10-20 ans | Volume garanti, prix fixe | Contrat + injection réseau |
| Virtuel (VPPA) | 10-15 ans | CfD financier, pas de flux physique | Comptabilité IFRS complexe |
| Sleeved | 5-15 ans | Fournisseur intermédiaire, simple | Marge fournisseur |

**GO** (Garanties d'Origine) : 1 certificat = 1 MWh renouvelable. Registre Powernext.
Prix GO 2025 : ~0.5-2 €/MWh (solaire) à ~1-4 €/MWh (éolien).
CSRD : les PPA avec GO sont valorisables dans le reporting scope 2 (market-based).

## Dimensionnement PV B2B

### Rendement régional

| Ville | Zone | Productible (kWh/kWc/an) | Orientation optimale |
|---|---|---|---|
| Paris | H1a | ~1000 | Sud, 30° |
| Lyon | H1b | ~1100 | Sud, 30° |
| Bordeaux | H2b | ~1200 | Sud, 30° |
| Marseille | H2d | ~1350 | Sud, 25° |
| Nice | H3 | ~1400 | Sud, 25° |

### Règle de pouce

- 1 kWc ≈ 6-7 m² de panneaux
- 500m² toiture → ~75 kWc → 75-105 MWh/an selon zone
- Autoconsommation cible : 70-90% (avec stockage possible >85%)
- LCOE PV toiture 2025 : ~50-80 €/MWh (compétitif vs marché)

### ROI estimé

| Configuration | ROI | TRI |
|---|---|---|
| ACI sans stockage | 6-10 ans | 8-15% |
| ACI + stockage | 8-14 ans | 5-10% |
| ACC sans stockage | 5-9 ans | 10-18% |
| Tiers investisseur | 0€ CAPEX, économie 10-20% | N/A |

## Stockage couplé PV

Batteries Li-ion : gain autoconsommation +15-30%. CAPEX ~150-250 €/kWh.
Dimensionnement : ratio stockage/PV typique 0.5-1.0 kWh/kWc.
Applications : peak shaving (CMDPS), arbitrage HP/HC, secours, participation FCR.
Cumul revenus : autoconsommation + FCR + peak shaving = stacking possible.

## APER (Accélération Production Énergies Renouvelables)

**Parkings** ≥1,500m² → 50% ombrières PV. Calendrier :
- Nouveaux : immédiat.
- Existants 1,500-10,000m² : 01/07/2028.
- Existants >10,000m² : 01/07/2026.
Sanctions : 40,000€/an + 200€/place non équipée.

**Toitures** ≥500m² → 50% végétalisée ou PV (neuf et rénovations lourdes).

### Dispositifs de soutien

- OA EDF guichet ouvert : ≤500kWc, prix garanti 20 ans.
- >500kWc : AO CRE (périodes PPE), complément de rémunération.
- CEE : certaines installations PV éligibles (BAT-EQ-127 ombrières).
- Prime à l'investissement (résidentiel principalement).

## AO CRE — calendrier PPE

Appels d'offres périodiques pour installations >500kWc :
- AO toitures/ombrières : 2-3 périodes/an, prix plafond ~90-110 €/MWh.
- AO sol : trimestriel, prix plafond ~60-80 €/MWh.
- AO innovation : stockage + PV, agrégation.

## Règles PROMEOS

- Calcul autoconsommation = backend-only
- Taux autoconsommation ≥ 0% et ≤ 100%
- Production PV seed : profil solaire réaliste par zone climatique (H1/H2/H3)
- ACC : neutralisé en DEMO_MODE (scope_context)
