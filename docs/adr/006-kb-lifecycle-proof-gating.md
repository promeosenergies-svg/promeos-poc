# ADR-006: KB Document Lifecycle & Proof Gating

**Date**: 2026-02-20
**Statut**: Accepted
**Auteurs**: Equipe PROMEOS

---

## Contexte

PROMEOS V33-V37 a construit le moteur de leviers (leverEngine), les actions CTA, les contrats OPERAT/factures/achat, et la Data Activation. Les leviers portent deja `proofHint` (conformite) et `proofLinks` (facturation), mais aucune UI ne permet de deposer ou gerer les preuves documentaires.

Le backend KB existe (FTS5, items, docs, chunks, citations) avec un 3-state lifecycle sur `kb_items` (draft/validated/deprecated). Cependant `kb_docs` n'a pas de colonne status, pas d'endpoint d'upload client, et aucun lien entre le cockpit et la Memobox.

---

## Probleme

Comment permettre aux utilisateurs de deposer des preuves documentaires depuis le cockpit, gerer leur cycle de vie (brouillon a decisionnel), et garantir que seuls les documents valides alimentent le moteur deterministe — sans casser le lifecycle existant des kb_items?

---

## Options envisagees

### Option A: Lifecycle unifie kb_items + kb_docs (meme table, meme status)

- (+) Un seul modele de lifecycle
- (-) kb_items a un CHECK constraint 3-state, migration destructive
- (-) Regression potentielle sur le moteur d'evaluation existant
- (-) Semantique differente (items = regles, docs = preuves)

### Option B: Lifecycle 4-state sur kb_docs uniquement (choisi)

- (+) Zero regression sur kb_items (3-state inchange)
- (+) Migration additive idempotente (ALTER TABLE ADD COLUMN)
- (+) Semantique claire: docs = preuves avec cycle validationnel
- (+) Gating deterministe simple (function pure)
- (-) Deux modeles de lifecycle a connaitre

### Option C: Workflow externe (n-state machine, table separee)

- (+) Flexible, extensible
- (-) Sur-ingenierie pour V1 (4 etats suffisent)
- (-) Complexite operationnelle

---

## Decision

**Option B** — Lifecycle 4-etats sur `kb_docs` uniquement.

### Etats du cycle de vie

```
draft → review → validated → decisional
                           ↘ deprecated
                  ↗ draft (retour si probleme)
```

| Etat | Description | Alimente le moteur |
|------|-------------|-------------------|
| draft | Brouillon, document en preparation | Non |
| review | En cours de revue / validation | Non |
| validated | Valide par un responsable | Oui |
| decisional | Document decisionnel (engagement) | Oui |
| deprecated | Obsolete, remplace | Non |

### Transitions autorisees

```python
DOC_TRANSITION_RULES = {
    "draft": {"review"},
    "review": {"validated", "draft"},
    "validated": {"decisional", "deprecated"},
    "decisional": {"deprecated"},
    "deprecated": set(),
}
```

### Gating deterministe

```python
def kb_doc_allows_deterministic(doc_status: str) -> bool:
    return doc_status in ("validated", "decisional")
```

Seuls les documents `validated` ou `decisional` alimentent les regles d'evaluation deterministes du moteur KB.

### Upload client

Nouvel endpoint `POST /api/kb/upload` (multipart/form-data, max 10 Mo). Reutilise le pipeline `ingest_document()` existant avec dedup SHA256.

### Proof deep-link

`buildProofLink(lever)` dans `proofLinkModel.js` (modele pur, sans React ni API) construit une URL `/kb?context=proof&domain=X&lever=Y&hint=Z` permettant un depot de preuve en 1 clic depuis le cockpit.

---

## Consequences

### Positives

- Les utilisateurs peuvent deposer des preuves depuis le cockpit (CTA "Deposer" sur chaque levier)
- Le cycle de vie garantit que seuls les documents valides sont utilises
- La Memobox (/kb) offre une vue unifiee items + documents avec filtres
- Zero regression sur kb_items et le moteur d'evaluation existant
- Migration additive et idempotente

### Negatives

- Deux modeles de lifecycle coexistent (kb_items 3-state, kb_docs 4-state)
- Pas de workflow multi-utilisateurs en V1 (ajout futur)
- Pas de versioning de documents en V1

### Fichiers impactes

| Fichier | Modification |
|---------|-------------|
| `backend/app/kb/models.py` | +status/domain/used_by_modules colonnes, +index |
| `backend/app/kb/store.py` | +update_doc_status(), +get_docs_filtered() |
| `backend/app/kb/doc_ingest.py` | +kb_doc_allows_deterministic(), status dans doc_record |
| `backend/app/kb/router.py` | +POST /upload, +POST /docs/{id}/status, GET /docs filtres |
| `backend/tests/test_kb_memobox.py` | 15+ tests lifecycle, gating, dedup |
| `frontend/src/models/proofLinkModel.js` | buildProofLink, hasProofData, DOC_STATUS_LABELS |
| `frontend/src/services/api.js` | +uploadKBDoc, +changeKBDocStatus, +getKBDocs |
| `frontend/src/pages/cockpit/ImpactDecisionPanel.jsx` | +micro-bloc preuve + CTA |
| `frontend/src/pages/KBExplorerPage.jsx` | Memobox rename + upload + docs tab + lifecycle |
| `frontend/src/layout/NavRegistry.js` | Label "Memobox" + keywords |
| `frontend/src/pages/__tests__/memoboxV38.test.js` | 35+ tests + source guards |
