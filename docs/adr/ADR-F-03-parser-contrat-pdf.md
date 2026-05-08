# ADR-F-03 — Parser contrat PDF (extraction métadonnées + bridge Fournisseur Phase F1)

**Statut** : 🟢 ACCEPTED — Phase F3 cardinal post-F2 (commit `d60cac8c` sur `claude/refonte-sol2`)
**Date** : 2026-05-08
**Sprint** : Phase F3 (P0-3 Vision Consolidée v1.3, ~3 h granulaires)
**Décideurs** : architect-helios + bill-intelligence + regulatory-expert
**Lié** : ADR-F-01 (Fournisseur entité) · ADR-F-02 (parser PDF facture)

## Contexte

Vision Consolidée v1.3 P0-3 : "Parser contrat" — finaliser le 3e fix repo pour passer 48 % → 78 % livré.

État actuel cardinal :
- ✅ `EnergyContract` modèle complet (~30 colonnes : supplier_name, dates, prix, indexation, etc.)
- ✅ Fournisseur entité Phase F1 + Bridge SIREN Phase F2
- ✅ Parser PDF facture (`pdf_parser.py`)
- ❌ **GAP Phase F3** : aucun parser pour PDF de **contrats** (signés)
- ❌ Onboarding contrat = saisie manuelle 30+ champs → friction utilisateur cardinal

## Décision

**Service `contract_pdf_parser`** + **endpoint `/api/contracts/import-pdf`** + **bridge Fournisseur** (réutilise F2 resolver).

### Décisions granulaires

| ID | Décision | Choix retenu |
|---|---|---|
| **D1** | Persistance auto vs review | **Review obligatoire** — endpoint retourne dict champs extraits + `confidence`, frontend affiche pré-remplissage à valider avant CREATE EnergyContract |
| **D2** | Champs cardinaux extraits | **8 champs** : supplier_name, fournisseur_id (résolu), reference_fournisseur, date_signature, start_date, end_date, price_ref_eur_per_kwh, fixed_fee_eur_per_month |
| **D3** | Réutilisation parser facture | **Oui** : `extract_text_with_fitz` + `extract_siren_from_pdf_text` réutilisés ; nouveaux regex contrat-spécifiques |
| **D4** | Tests cardinaux | **8 tests** T-CONTRACT-01→08 |

## Implémentation (~3 h granulaires)

1. **F3.1** — Service `services/contract_pdf_parser.py` : extraction 8 champs cardinaux (~1 h)
2. **F3.2** — Endpoint `POST /api/contracts/parse-pdf` (preview, pas de persistance) (~30 min)
3. **F3.3** — Tests cardinaux T-CONTRACT-01→08 (~1 h)
4. **F3.4** — Audit code-reviewer + /simplify + qa-guardian + commit (~30 min)

## Conséquences

**Positives** :
- Onboarding contrat : pré-remplissage automatique 8 champs → friction divisée par 4
- Bridge Fournisseur F1 actionnable (résolution SIREN du contrat)
- Vision v1.3 3/3 P0 livrés

**Négatives** :
- Pas de persistance auto (review humain) — Phase F4 ou F5 si confiance suffisante atteinte
- Templates initiaux limités (générique + EDF/Engie) — extension par lot si besoin client

## Tests cardinaux (8)

| ID | Description |
|---|---|
| T-CONTRACT-01 | Extraction supplier_name + SIREN depuis PDF contrat |
| T-CONTRACT-02 | Extraction date_signature format DD/MM/YYYY |
| T-CONTRACT-03 | Extraction start_date + end_date contrat |
| T-CONTRACT-04 | Extraction price_ref EUR/kWh (élec) |
| T-CONTRACT-05 | Extraction fixed_fee abonnement EUR/mois |
| T-CONTRACT-06 | Extraction reference_fournisseur (n° contrat) |
| T-CONTRACT-07 | Bridge Fournisseur Phase F1 — fournisseur_id résolu via SIREN |
| T-CONTRACT-08 | Confidence score : >= 0.5 si 4+ champs trouvés |

## Liens

- ADR-F-01 (Fournisseur entité) · ADR-F-02 (parser PDF facture)
- `app/bill_intelligence/parsers/pdf_parser.py` (réutilisation `extract_text_with_fitz` + `extract_siren_from_pdf_text`)
- `services/fournisseur_resolver_service.py` (réutilisation `resolve_fournisseur_from_siren`)
- `models/billing_models.py:40` (EnergyContract cible)
- Vision Consolidée v1.3 §"3 fixes P0 repo"
