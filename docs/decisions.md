# Decisions d'architecture — Referentiel Tarifs & Taxes

## D1 — Stdlib uniquement (zero dep externe pour fetch/parse)

**Contexte** : Le referentiel telecharge et parse du HTML gouvernemental.

**Decision** : Utiliser uniquement `urllib.request`, `html.parser`, `re`, `json`, `sqlite3` de la stdlib Python. Pas de `requests`, `beautifulsoup4`, `lxml`, `feedparser`.

**Raison** :
- Reduit la surface d'attaque (pas de dep transitives)
- Simplifie le deploiement et le CI
- Les pages ciblees sont du HTML simple (pas de JS rendering)
- `yaml` est la seule dep ajoutee (deja presente pour RegOps)

---

## D2 — Snapshot immutable par source/date

**Contexte** : On doit tracer exactement quelle version d'un texte reglementaire a ete utilisee pour un calcul.

**Decision** : Chaque fetch cree un dossier `snapshots/{source_id}/{YYYY-MM-DD}/` contenant 3 fichiers immutables : `raw.html`, `extracted.md`, `metadata.json`.

**Raison** :
- Immutabilite = audit trail fiable
- Un re-fetch le meme jour ecrase le snapshot du jour (idempotent)
- Le hash SHA-256 dans metadata.json permet la detection de changements entre snapshots

---

## D3 — YAML watchlist + validation CLI

**Contexte** : La liste des sources doit etre maintenable par un humain et validable par la CI.

**Decision** : Un seul fichier YAML (`sources_watchlist_24m.yaml`) avec schema JSON + CLI `validate`.

**Raison** :
- YAML = lisible, commentable, diffable dans Git
- Le CLI `validate` verifie : unicite ids, format, HTTPS, whitelist domaines, enums
- Pas besoin de JSON Schema runtime (jsonschema) — validation custom en Python

---

## D4 — Whitelist de 4 domaines

**Contexte** : On ne doit fetcher que des sources gouvernementales officielles.

**Decision** : Les 4 domaines autorises sont : `cre.fr`, `legifrance.gouv.fr`, `bofip.impots.gouv.fr`, `impots.gouv.fr`.

**Raison** :
- Securite : empeche l'ajout accidentel de sources non-officielles
- Conformite : toutes les sources sont publiques et gouvernementales
- Sous-domaines acceptes (ex: `www.cre.fr` match `cre.fr`)

---

## D5 — Manifeste JSON + index SQLite

**Contexte** : Le bill intelligence doit interroger rapidement les sources applicables pour un calcul.

**Decision** : Deux formats d'index :
- `sources_manifest.json` — manifeste complet (portable, lisible)
- `sources_index.sqlite` — base SQLite pour requetes SQL (tags, authority, date)

**Raison** :
- Le JSON est suffisant pour le service.py (chargement en memoire)
- Le SQLite offre des requetes avancees pour le futur (dashboard, reporting)
- Les deux sont generes par la meme commande `build-manifest`

---

## D6 — Rate limiting 1.5s + retry backoff

**Contexte** : Les sites gouvernementaux ne doivent pas etre surcharges.

**Decision** : 1.5s entre requetes au meme domaine. 3 retries avec backoff exponentiel (2s, 4s, 8s). Timeout 30s.

**Raison** :
- Respect des sites publics
- Robustesse face aux erreurs reseau transitoires
- Le fetch complet (~30 sources) prend ~2 minutes avec rate limiting

---

## D7 — Baseline flag pour sources hors fenetre

**Contexte** : Certaines deliberations (ATRD7 2024, ATRT8 2024) ont ete publiees avant la fenetre 24 mois mais restent la reference en vigueur.

**Decision** : Le champ `baseline: true` dans le YAML exempte la source du filtre `--since`.

**Raison** :
- Un tarif publie en janvier 2024 reste applicable jusqu'a sa prochaine evolution
- Sans baseline, ces sources seraient filtrees par la fenetre et manqueraient au referentiel

---

## D8 — Extraction CRE specifique

**Contexte** : Les pages CRE contiennent des metadonnees structurees (numero deliberation, dates, type document) qui ne sont pas dans le HTML standard.

**Decision** : Un extracteur dedie (`extract_cre_metadata.py`) avec regex sur le HTML CRE.

**Raison** :
- Les deliberations CRE ont un format semi-structure reconnaissable
- Le numero de deliberation (ex: 2025-018) est essentiel pour la tracabilite
- Les dates en francais (16 janvier 2025) sont normalisees en ISO 8601

---

## D9 — Service layer pour integration bill intelligence

**Contexte** : Le moteur de facturation doit savoir quelles sources reglementaires s'appliquent a un calcul.

**Decision** : `service.py` expose `get_sources_for_calc(tags)` et `build_calc_trace(calc_id, tags, amount)`.

**Raison** :
- Le matching se fait par tags (ex: ["turpe6", "hta", "distribution"])
- La trace inclut la reference `source_id@sha256[:12]` pour audit
- Le format est pret pour integration dans les futures factures detaillees
