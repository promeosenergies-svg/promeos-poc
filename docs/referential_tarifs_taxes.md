# Brique 2 — Referentiel Tarifs & Taxes (elec + gaz)

## Objectif

Constituer un referentiel de sources reglementaires officielles pour les tarifs d'acheminement (TURPE, ATRD, ATRT, ATS) et les taxes energie (CTA, accises, TVA) sur une fenetre glissante de 24 mois.

Ce referentiel permet :
- La **tracabilite** des calculs de facturation (bill intelligence)
- La **detection de changements** reglementaires (hash SHA-256 par snapshot)
- L'**audit** des sources utilisees dans chaque calcul

## Architecture

```
backend/
  app/referential/
    sources_watchlist_24m.yaml    # 30 sources officielles
    schemas/
      sources_watchlist.schema.json
    snapshots/                    # raw.html + extracted.md + metadata.json par source/date
      {source_id}/{YYYY-MM-DD}/
    indices/
      sources_manifest.json       # manifeste global
      sources_index.sqlite        # index SQL pour requetes rapides
    service.py                    # API pour bill intelligence
  scripts/referential/
    cli.py                        # CLI: validate / fetch / build-manifest / report
    fetch_sources.py              # fetcher HTTP avec retries + rate-limiting
    normalize_text.py             # HTML -> Markdown (stdlib uniquement)
    extract_cre_metadata.py       # extraction metadata CRE (deliberation, dates)
```

## Sources couvertes (30)

| Regulation | Energie | Autorite | Nb sources |
|-----------|---------|----------|-----------|
| TURPE 6 | Electricite | CRE | 4 |
| TURPE 7 | Electricite | CRE + Legifrance | 6 |
| ATRD 7 | Gaz | CRE + Legifrance | 4 |
| ATRT 8 | Gaz | CRE + Legifrance | 4 |
| ATS 3 | Gaz | CRE + Legifrance | 4 |
| CTA | Multi | CRE + Legifrance | 2 |
| Accises (CIBS) | Elec + Gaz | Legifrance + BOFiP + impots.gouv | 4 |
| TVA | Multi | BOFiP | 1 |

### Domaines autorises

- `cre.fr` — Commission de Regulation de l'Energie
- `legifrance.gouv.fr` — Journal Officiel (JORF)
- `bofip.impots.gouv.fr` — Bulletin Officiel des Finances Publiques
- `impots.gouv.fr` — formulaires et attestations

## CLI — Usage

```bash
cd backend

# 1. Valider le YAML (structure, enums, domaines, unicite ids)
python scripts/referential/cli.py validate

# 2. Telecharger les sources (fenetre 24 mois)
python scripts/referential/cli.py fetch --since 2024-02-01 --until 2026-02-10

# 3. Mode dry-run (validation sans telechargement)
python scripts/referential/cli.py fetch --dry-run

# 4. Construire le manifeste + index SQLite
python scripts/referential/cli.py build-manifest

# 5. Rapport de synthese
python scripts/referential/cli.py report
```

## Pipeline de fetch

Pour chaque source :

1. **HTTP GET** avec User-Agent PROMEOS, retries (3x, backoff exponentiel), timeout 30s
2. **Rate limiting** : 1.5s entre requetes au meme domaine
3. **Normalisation** : HTML -> Markdown (suppression nav/scripts/styles)
4. **Hashing** : SHA-256 sur le raw HTML + SHA-256 sur le Markdown normalise
5. **Extraction CRE** : numero deliberation, dates, type document, energie, lien PDF
6. **Stockage** : `snapshots/{source_id}/{YYYY-MM-DD}/` avec 3 fichiers :
   - `raw.html` — contenu brut
   - `extracted.md` — texte normalise
   - `metadata.json` — metadonnees structurees

## Manifeste

Le manifeste (`indices/sources_manifest.json`) contient :

```json
{
  "generated_at": "2025-02-10T15:30:00Z",
  "window": {"start": "2024-02-01", "end": "2026-02-10"},
  "sources": {
    "cre_turpe6_hta_bt_2024_08": {
      "latest": {"date": "2025-02-10", "sha256_raw": "abc123..."},
      "history": [...],
      "has_content_changes": true,
      "authority": "CRE",
      "tags": ["turpe", "turpe6", "hta", "bt"]
    }
  },
  "stats": {
    "total_sources": 30,
    "total_snapshots": 30,
    "sources_with_changes": 0,
    "errors": 0
  }
}
```

## Integration Bill Intelligence

Le module `service.py` fournit :

```python
from app.referential.service import get_sources_for_calc, build_calc_trace

# Trouver les sources applicables pour un calcul TURPE
sources = get_sources_for_calc(tags=["turpe6", "hta", "distribution"])

# Construire la trace d'audit
trace = build_calc_trace(
    calc_id="facture_123_turpe",
    tags=["turpe6", "hta"],
    amount=1234.56,
    details={"puissance": 250, "option": "LU"}
)
# trace["sources_used"] = ["cre_turpe6_hta_bt_2024_08@abc123def456"]
```

## Tests

```bash
# 48 tests couvrant :
python -m pytest tests/test_watchlist_schema.py -v    # 17 tests — YAML, ids, domaines, enums
python -m pytest tests/test_manifest_build.py -v      # 11 tests — manifeste, SQLite, detection changements
python -m pytest tests/test_fetch_dry_run.py -v       # 20 tests — normalizer, CRE, dry-run, filtrage fenetre
```

## Securite

- **HTTPS obligatoire** — toutes les URLs
- **Whitelist domaines** — 4 domaines gouvernementaux uniquement
- **User-Agent identifie** — `PROMEOS-POC/1.0 (referentiel-tarifs; contact@promeos.fr)`
- **Rate limiting** — 1.5s entre requetes meme domaine
- **Pas de scraping agressif** — retries avec backoff exponentiel
- **Zero dependance externe** — stdlib Python uniquement (urllib, html.parser, re)
