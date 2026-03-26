# Market Data -- Architecture

## Tables

| Table | Usage | Source de verite |
|-------|-------|-----------------|
| `mkt_prices` | Prix marche (spot, forward, capacite) | OUI |
| `regulated_tariffs` | Tarifs reglementes versionnes (TURPE, CSPE, VNU, CEE, CTA, TVA) | OUI |
| `price_signals` | Signaux prix calcules pour les clients | OUI |
| `price_decompositions` | Decomposition prix complet par site | OUI |
| `market_data_fetch_logs` | Logs de fetch connecteurs | OUI |
| ~~`market_prices`~~ | ~~Legacy Step 17~~ | DEPRECATED |

## Referentiels YAML

| Fichier | Usage |
|---------|-------|
| `referentials/market_tariffs_2026.yaml` | Tarifs pour la decomposition prix (CSPE, TURPE, VNU, Capacite, CEE, CTA, TVA) |
| `config/tarifs_reglementaires.yaml` | Referentiel CRE brut pour Bill Intelligence (shadow billing) |

Les deux fichiers coexistent car ils servent des modules differents.
Les valeurs TURPE doivent etre identiques entre les deux.

## Connecteurs

| Connecteur | Source | Auth | Statut |
|-----------|--------|------|--------|
| `entsoe_connector.py` | ENTSO-E Transparency | Token email | Pret |
| RTE Wholesale | data.rte-france.com | OAuth2 | Prevu |
| EEX DataSource | EEX Group | Payant (85 EUR/mois FR) | Prevu |
| Pilott | Sirenergies | Freemium | Prevu |

## Prix de reference -- Cascade

```
get_reference_price(db, site_id):
  1. Prix contractuel du site (EnergyContract.price_ref_eur_per_kwh)
  2. Moyenne spot 30j depuis mkt_prices (EPEX Spot FR)
  3. SiteTariffProfile du site
  4. Fallback 0.068 EUR/kWh (68 EUR/MWh)
```

## Enums cles (market_models.py)

- `MarketDataSource`: ENTSOE, RTE_WHOLESALE, EEX, EPEX_SPOT, PILOTT, MANUAL, COMPUTED
- `MarketType`: SPOT_DAY_AHEAD, SPOT_INTRADAY, FORWARD_MONTH/QUARTER/YEAR/WEEK, CAPACITY, BALANCING
- `PriceZone`: FR, DE_LU, BE, ES, IT_NORTH, NL, GB, CH
- `TariffType`: TURPE, CSPE, CAPACITY, CEE, CTA, TVA, VNU, ATRD
- `TariffComponent`: 22 composantes (TURPE HPH/HCH/HPB/HCB/Fixe/Comptage, CSPE C5/C4/C2, VNU seuils, etc.)
- `Resolution`: PT15M, PT30M, PT60M, P1D, P1W, P1M, P3M, P1Y

## TURPE 7 dans market_tariffs_2026.yaml

6 composantes HTA CU poste (depuis 1er aout 2025, CRE n.2025-78):

| Composante | Valeur | Unite |
|-----------|--------|-------|
| TURPE_SOUTIRAGE_HPH | 63.70 | EUR/MWh |
| TURPE_SOUTIRAGE_HCH | 44.40 | EUR/MWh |
| TURPE_SOUTIRAGE_HPB | 14.30 | EUR/MWh |
| TURPE_SOUTIRAGE_HCB | 10.40 | EUR/MWh |
| TURPE_PART_FIXE | 9.84 | EUR/kW/an |
| TURPE_COMPTAGE | 312.12 | EUR/an |
