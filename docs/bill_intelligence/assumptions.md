# PROMEOS Brique 2 — Bill Intelligence — Assumptions & Decisions

## Audit repo (T0)

### Existant reutilise

| Composant | Fichier | Decision |
|-----------|---------|----------|
| KB store + FTS5 | `app/kb/models.py`, `app/kb/store.py` | **ETENDRE** : ajouter tables citations, rule_cards, doc manifest enrichi |
| KB router | `app/kb/router.py` | **ETENDRE** : ajouter endpoints ingest, extract-rule |
| KB indexer | `app/kb/indexer.py` | **REUTILISER** tel quel (FTS5 deja fonctionnel) |
| Referentiel tarifs | `app/referential/` | **REUTILISER** : snapshots sources CRE comme docs KB |
| Energy models | `models/energy_models.py` | **ETENDRE** : ajouter modeles facture |
| Enums | `models/enums.py` | **ETENDRE** : ajouter enums bill intelligence |
| main.py | `main.py` | **MODIFIER** : inclure bill_intelligence router |

### A creer (neuf)

| Composant | Chemin | Raison |
|-----------|--------|--------|
| Domain model facture | `app/bill_intelligence/domain.py` | Modele canonique Invoice/Line/Component |
| Parser demo | `app/bill_intelligence/parsers/` | Parsing factures demo + PDF |
| Audit rules | `app/bill_intelligence/rules/` | 20 regles V0 + RuleCards |
| Engine calcul | `app/bill_intelligence/engine.py` | Shadow billing L0-L3 |
| Reconciliation | `app/bill_intelligence/reconciliation.py` | Ecart facture vs shadow |
| Reports | `app/bill_intelligence/reports.py` | Export HTML/CSV |
| API routes | `app/bill_intelligence/router.py` | Endpoints bill intelligence |
| KB Citation | `app/kb/citations.py` | Modele Citation + operations |
| KB RuleCard | `app/kb/rule_cards.py` | Modele RuleCard + operations |
| Data raw KB | `data/kb/raw/` | Documents bruts (PDF/HTML) |
| Data normalized KB | `data/kb/normalized/` | Texte extrait structure |

## Stack decisions

### D1 — Architecture coherente avec l'existant
Le prompt demande `/packages/kb/` etc. mais le repo utilise `backend/app/` + `backend/routes/`.
**Decision** : adapter au pattern existant (`backend/app/bill_intelligence/`).

### D2 — SQLite unique pour KB
La KB utilise deja `data/kb.db` avec FTS5.
**Decision** : etendre ce meme fichier avec nouvelles tables (citations, rule_cards, doc_manifest_v2).

### D3 — Zero invention de valeurs
Aucun tarif/taxe/taux en dur dans le code.
Toute valeur chiffree vient d'un doc KB + Citation.
Si absent : `PARAM_MISSING` + `TODO`.

### D4 — Niveaux shadow billing
- **L0** : Read & Explain (parsing + affichage structure)
- **L1** : Partial Shadow (arithmetique, TVA, prorata, coherences)
- **L2** : Component Shadow (composantes si doc+data disponibles)
- **L3** : Full Shadow (optionnel, rare en POC)

### D5 — Fenetre 24 mois
Toute facture/regle : 2024-02-01 → 2026-02-10.
Hors fenetre : `out_of_scope_poc=true`.

### D6 — Offres fournisseurs : placeholder
Module `offers/` cree mais `NOT_IMPLEMENTED`.
Interfaces documentees pour integration future.

### D7 — Demo corpus anonymise
Factures demo avec noms/montants fictifs mais structures realistes.
Format: JSON canonique + PDF template.

### D8 — Citation obligatoire pour regle normative
Toute RuleCard normative DOIT avoir >= 1 Citation.
Si KB contradictoire : `status = NEEDS_REVIEW`.

## Risques identifies

| Risque | Mitigation |
|--------|------------|
| KB vide au demarrage | Seed avec docs referentiel existants + 3 docs demo |
| Faux positifs audit | Seuils conservateurs + flag `confidence` sur chaque regle |
| PDF parsing fragile | 1 template elec + 1 gaz seulement, fallback JSON demo |
| Perimetre creep | Chaque ticket a un AC clair, pas de scope creep |
