# HELIOS — Paramètres détaillés des 5 sites seed

## Paris Bureaux

| Paramètre | Valeur |
|---|---|
| Surface | 3,500 m² |
| NAF | 70.10Z → BUREAU_STANDARD |
| Zone climatique | H1a (DJU ~2,400) |
| Vecteurs | Élec + Gaz |
| Baseload élec | 22% (~85 kW) |
| Puissance souscrite | ~200 kVA |
| Conso annuelle élec | ~550 MWh (~157 kWh/m²) |
| Conso annuelle gaz | ~180 MWh chauffage |
| DT applicable | Oui (>1,000m²) |
| BACS applicable | Selon puissance CVC (~150 kW → non en 2025, oui en 2027) |
| APER applicable | Selon parking (hypothèse: parking sous-sol 800m² → non) |
| Contrat seed | Cadre EDF Entreprises, Fixe Horosaisonnier, 24 mois |

## Lyon Bureaux

| Paramètre | Valeur |
|---|---|
| Surface | 1,200 m² |
| NAF | 69.10Z → BUREAU_STANDARD |
| Zone climatique | H1b (DJU ~2,750) |
| Vecteurs | Élec uniquement |
| Conso annuelle | ~185 MWh (~154 kWh/m²) |
| DT applicable | Oui |
| BACS applicable | Non (<290kW) |
| APER applicable | Non |
| Contrat | Cadre ENGIE Pro, Fixe 12 mois |

## Marseille École

| Paramètre | Valeur |
|---|---|
| Surface | 2,800 m² |
| NAF | 85.31Z → ENSEIGNEMENT |
| Zone climatique | H2d (DJU ~1,500) |
| Vecteurs | Élec + Gaz |
| Conso annuelle élec | ~280 MWh (~100 kWh/m²) |
| Spécificité | Vacances scolaires = 30% baseload |
| DT applicable | Oui |
| BACS applicable | À vérifier |
| APER applicable | Oui (parking école ~1,800m²) |
| Contrat | Cadre TotalEnergies, Indexé TRVE |

## Nice Hôtel

| Paramètre | Valeur |
|---|---|
| Surface | 4,000 m² |
| NAF | 55.10Z → HOTEL_HEBERGEMENT |
| Zone climatique | H3 (DJU ~1,200) |
| Vecteurs | Élec + Gaz |
| Conso annuelle élec | ~800 MWh (~200 kWh/m²) |
| Spécificité | 24/7, pic été (clim), baseload 38% |
| DT applicable | Oui |
| BACS applicable | Oui (gros CVC ~350kW) |
| APER applicable | Oui (parking hôtel ~2,000m²) |
| Contrat | Cadre Alpiq, Indexé EPEX Spot |

## Toulouse Entrepôt

| Paramètre | Valeur |
|---|---|
| Surface | 6,000 m² |
| NAF | 52.10B → LOGISTIQUE_SEC |
| Zone climatique | H2c (DJU ~1,800) |
| Vecteurs | Élec uniquement |
| Conso annuelle | ~240 MWh (~40 kWh/m²) |
| Spécificité | Éclairage dominant, faible thermosensibilité |
| DT applicable | Oui |
| BACS applicable | Non (entrepôt sec) |
| APER applicable | Oui (grande toiture 5,000m²) |
| Contrat | Cadre OHM Énergie, Fixe 12 mois |

## Anomalies injectées dans le seed

| Site | Anomalie | Type | Mois |
|---|---|---|---|
| Paris | Accise mal appliquée (24.50 au lieu de 25.79) | BILL_004 | Mois 8 |
| Lyon | Doublon facturation (même PRM, même mois) | BILL_006 | Mois 14 |
| Nice | Puissance souscrite ≠ Enedis | BILL_002 | Mois 3 |
| Marseille | TURPE 6 après 01/08/2025 | BILL_008 | Mois 20 |
| Toulouse | Surconsommation +18% vs baseline | CONSO_001 | Mois 11 |
