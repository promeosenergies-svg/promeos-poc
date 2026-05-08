# ADR-F-02 — Parser PDF facture bridge Fournisseur entité (Phase F1)

**Statut** : 🟢 ACCEPTED — Phase F2 cardinal post-Phase F1 (commit `f72dafea` sur `claude/refonte-sol2`)
**Date** : 2026-05-08
**Sprint** : Phase F2 (P0-2 Vision Consolidée v1.3, ~3-4 h granulaires)
**Décideurs** : architect-helios + bill-intelligence + regulatory-expert
**Lié** : ADR-F-01 (Fournisseur entité) · ADR-F-03 (parser contrat) · ADR-F-04 (hard-cut supplier_name)

## Contexte

Vision Consolidée v1.3 P0-2 : "Parser PDF facture" — passer 48 % → 78 % livré.

État actuel cardinal :
- ✅ `app/bill_intelligence/parsers/pdf_parser.py` existe (templates EDF/Engie + 50+ regex)
- ✅ `routes/billing.py:import_invoice_pdf` POST endpoint opérationnel
- ✅ `EnergyInvoice` modèle persiste résultat parsing
- ❌ **GAP cardinal Phase F2** : pas de bridge avec `Fournisseur` Phase F1
  - `supplier` reste chaîne libre dans `raw_json` après parsing
  - Aucun `fournisseur_id` résolu au moment de l'import
  - Réconciliation cross-factures par fournisseur impossible
  - Bridge eIDAS Compliance+ Vision v1.3 non actionnable (signataire_email)

## Décision

**Service `fournisseur_resolver_service`** + **wire `import_invoice_pdf`** + **extraction SIREN PDF**.

Pas de refonte du parser existant (acquis solide). Bridge minimaliste de l'existant vers l'entité Fournisseur Phase F1.

### Décisions granulaires

| ID | Décision | Choix retenu |
|---|---|---|
| **D1** | Persistance fournisseur_id sur EnergyInvoice ? | **Non Phase F2** — résolution mémoire + log dans `raw_json["fournisseur_id"]` (lookup fast cross-factures via JSON). Ajout colonne FK reporté Phase F3 si scoring fournisseur cross-portefeuille devient cardinal. |
| **D2** | Extraction SIREN du PDF | **Regex `\b\d{9}\b` + heuristique contexte** (ligne contenant supplier_name proche). Fallback : nom canonique mapping (cohérent backfill F1.7) |
| **D3** | Création Fournisseur privé sur unmapped | **Non Phase F2** — log warning + suggestion onboarding manuel. Anti-doublon SIREN canonique respecté |
| **D4** | Tests cardinaux | **8 tests** : extraction SIREN / mapping name canonique / fallback unmapped / IDOR / idempotence wire pdf_parser |

## Implémentation (3-4 h granulaires)

1. **F2.1** — Extension `pdf_parser.py` : extraction SIREN/SIRET (~30 min)
2. **F2.2** — Service `fournisseur_resolver_service.py` : 3 fonctions cardinal (~1 h)
3. **F2.3** — Wire `routes/billing.py:import_invoice_pdf` : resolve + persist raw_json (~30 min)
4. **F2.4** — Tests cardinaux T-PARSE-01→08 (~1 h)
5. **F2.5** — Audit code-reviewer + qa-guardian + commit (~30 min)

## Conséquences

**Positives** :
- Réconciliation invoices ↔ Fournisseur canonique par SIREN déterministe
- Statistiques fournisseur cross-factures déblocables (count invoices par fournisseur, total montant)
- Bridge eIDAS actionnable (signataire_email canonique disponible)
- Pattern Vision v1.3 P0-2 livré

**Négatives** :
- `raw_json["fournisseur_id"]` non indexable directement (JSON SQLite limite) — Phase F3 si performance dégradée

**Neutres** :
- Pas de migration Alembic (simplification cardinale)
- Tests parser PDF existants restent verts (extension non-breaking)

## Tests cardinaux (8)

| ID | Description |
|---|---|
| T-PARSE-01 | Extraction SIREN 9 chiffres depuis texte PDF |
| T-PARSE-02 | Extraction SIRET 14 chiffres → SIREN[0:9] |
| T-PARSE-03 | Mapping supplier_name "EDF" → Fournisseur canonique EDF |
| T-PARSE-04 | Mapping supplier_name variants (E.D.F. / EDF Entreprises) → même canonique |
| T-PARSE-05 | Unmapped supplier_name → None + log warning (pas de crash) |
| T-PARSE-06 | Resolver IDOR : voit canoniques + privés scope (pas privés autre tenant) |
| T-PARSE-07 | Wire `import_invoice_pdf` : `raw_json["fournisseur_id"]` set après parse |
| T-PARSE-08 | Idempotence : re-import même PDF = même fournisseur_id (déterministe) |

## Liens

- ADR-F-01 (Fournisseur entité Phase F1)
- `app/bill_intelligence/parsers/pdf_parser.py` (parser existant)
- `routes/billing.py:1369` (import_invoice_pdf endpoint)
- `services/fournisseur_service.py` (Phase F1)
- Vision Consolidée v1.3 §"3 fixes P0 repo"
