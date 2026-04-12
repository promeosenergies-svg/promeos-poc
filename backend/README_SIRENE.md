# Module Referentiel Sirene — PROMEOS

## Objectif

Brique de reference Sirene isolee permettant :
1. Stocker localement le stock mensuel INSEE (unites legales + etablissements + doublons)
2. Rechercher des entreprises par nom, SIREN, SIRET, CP ou commune
3. Creer des clients PROMEOS (Organisation + Entite juridique + Sites) depuis les donnees Sirene
4. Tracer chaque creation avec source, date et payload brut

## Architecture

```
backend/
  models/sirene.py          — 5 modeles SQLAlchemy (tables sirene_*)
  services/sirene_import.py — Import full/delta/doublons (CSV INSEE)
  routes/sirene.py          — 8 endpoints API
  schemas/sirene.py         — Schemas Pydantic requete/reponse
  tests/test_sirene.py      — 27 tests (mapping, import, API, onboarding)
  database/migrations.py    — Migration idempotente (create tables)

frontend/
  src/services/api/sirene.js        — Client API
  src/pages/SireneOnboardingPage.jsx — Flow 3 etapes (recherche → selection → confirmation)
  src/__tests__/sirene_onboarding.test.js — 9 tests structure
```

## Tables creees

| Table | Contenu |
|-------|---------|
| `sirene_unites_legales` | Stock mensuel UL (SIREN, denomination, NAF, etat, etc.) |
| `sirene_etablissements` | Stock mensuel etablissements (SIRET, adresse, siege, etc.) |
| `sirene_doublons` | Paires SIREN/SIREN doublon (INSEE) |
| `sirene_sync_runs` | Journal d'imports (stats, erreurs, correlation_id) |
| `customer_creation_traces` | Trace onboarding (source, objets crees, user) |

## Endpoints API

| Methode | Path | Role |
|---------|------|------|
| GET | `/api/reference/sirene/search?q=...` | Recherche full-text |
| GET | `/api/reference/sirene/unites-legales/{siren}` | Detail UL |
| GET | `/api/reference/sirene/unites-legales/{siren}/etablissements` | Etablissements d'une UL |
| GET | `/api/reference/sirene/etablissements/{siret}` | Detail etablissement |
| POST | `/api/admin/sirene/import-full` | Import full (admin) |
| POST | `/api/admin/sirene/import-delta` | Import delta (admin) |
| GET | `/api/admin/sirene/sync-runs` | Historique imports |
| POST | `/api/onboarding/from-sirene` | Creer client depuis Sirene |

## Commandes Import

### Via CLI
```bash
cd backend

# Import full stock mensuel
python -m services.sirene_import --type full \
  --ul /chemin/stockUniteLegale_utf8.csv \
  --etab /chemin/stockEtablissement_utf8.csv \
  --snapshot-date 2026-03-31

# Import delta (seuls les enregistrements recents)
python -m services.sirene_import --type delta \
  --ul /chemin/stockUniteLegale_utf8.csv \
  --etab /chemin/stockEtablissement_utf8.csv

# Import doublons
python -m services.sirene_import --type doublons \
  --file /chemin/stockDoublons_utf8.csv
```

### Via API (admin)
```bash
curl -X POST http://localhost:8001/api/admin/sirene/import-full \
  -H "Content-Type: application/json" \
  -d '{"ul_path": "/chemin/stockUniteLegale.csv", "etab_path": "/chemin/stockEtablissement.csv"}'
```

## Source des fichiers

Telecharger depuis [data.gouv.fr](https://www.data.gouv.fr/datasets/base-sirene-des-entreprises-et-de-leurs-etablissements-siren-siret) :
- `stockUniteLegale_utf8.csv` (~900 MB ZIP)
- `stockEtablissement_utf8.csv` (~2.6 GB ZIP)
- `stockDoublons_utf8.csv` (~110 MB ZIP)

Fichiers publies le 1er de chaque mois.

## Regles metier

### Ce que Sirene CREE
- 1 Organisation (conteneur PROMEOS)
- 1 Entite juridique (signataire, avec SIREN unique)
- 1 Portefeuille "Principal"
- N Sites (1 par etablissement selectionne)

### Ce que Sirene NE CREE JAMAIS
- Batiment
- Compteur
- DeliveryPoint
- Contrat
- Facture
- Obligation reglementaire

### Anti-doublons
1. **SIREN** : si deja present dans `entites_juridiques` → 409 CONFLICT (bloquant)
2. **SIRET** : si deja present dans `sites.siret` �� warning (non bloquant)
3. **Doublons INSEE** : si un doublon SIREN existe dans PROMEOS → warning
4. **Nom similaire** : si une organisation similaire existe → warning

## Tests

```bash
# Backend (27 tests)
cd backend && python -m pytest tests/test_sirene.py -v

# Frontend (9 tests)
cd frontend && npx vitest run src/__tests__/sirene_onboarding.test.js
```

## Risques connus

1. **Volumes** : l'import full d'un stock complet (35M etablissements) prend du temps en SQLite. Recommander PostgreSQL en production.
2. **Recherche full-text** : utilise ILIKE (ok pour <1M lignes). Pour volumes plus importants, migrer vers FTS5 (SQLite) ou pg_trgm (PostgreSQL).
3. **NAF 2025** : le code `activite_principale_naf25` est stocke mais pas encore utilise dans la classification PROMEOS.
4. **Telecharement auto** : pas de telechargement automatique depuis data.gouv.fr (fichiers >2 GB).

## Limites volontaires

- Pas de creation de batiment/compteur depuis Sirene (regle metier)
- Pas d'enrichissement automatique du patrimoine existant (choix utilisateur explicite)
- Pas de synchronisation bidirectionnelle Sirene ↔ PROMEOS
- Pas de telechargement automatique des fichiers INSEE

## Rollback

Pour supprimer le module Sirene :
1. Retirer `_create_sirene_tables(engine)` de `database/migrations.py`
2. Retirer l'import dans `models/__init__.py`
3. Retirer `app.include_router(sirene_router)` de `main.py`
4. Les tables `sirene_*` et `customer_creation_traces` peuvent etre droppees manuellement
5. Aucun impact sur les tables metier existantes
