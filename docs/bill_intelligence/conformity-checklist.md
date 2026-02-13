# CONFORMITY CHECKLIST — PROMEOS Bill Intelligence

**Date**: 2026-02-13
**Scope**: Regles d'audit V0 (20 regles arithmetiques + coherences)

---

## Principes

| # | Principe | Implementation |
|---|----------|----------------|
| P1 | Aucune valeur chiffree sans source | Taux TVA 5.5%/20% = constantes legislatives universelles |
| P2 | Chaque anomalie porte sa regle | `rule_card_id` sur chaque `InvoiceAnomaly` |
| P3 | Tolerance explicite | `TOLERANCE_EUR = 0.02` (arrondi centimes) |
| P4 | Shadow billing progressif | L0 → L1 → L2 → L3 (chaque niveau documente son `why_not_higher`) |
| P5 | Citation obligatoire pour regle normative | RuleCards sans citation KB → `NEEDS_REVIEW` |

---

## Checklist des 20 regles V0

| # | Regle | Type | Severite max | Formule | Source |
|---|-------|------|--------------|---------|--------|
| R01 | Somme composantes vs total HT | arithmetique | ERROR | `sum(comp.amount_ht) == invoice.total_ht` | Universel |
| R02 | TTC = HT + TVA | arithmetique | ERROR | `total_ht + total_tva == total_ttc` | Universel |
| R03 | TVA taux correct par composante | TVA | ERROR | Abonnement/CTA/TURPE gestion → 5.5%, reste → 20% | CGI art. 278-0 bis |
| R04 | TVA montant = base * taux | TVA | WARNING | `amount_ht * tva_rate / 100 == tva_amount` | Universel |
| R05 | Quantite * prix unitaire = montant | arithmetique | WARNING | `qty * unit_price == amount_ht` | Universel |
| R06 | Dates coherentes | coherence | ERROR | `period_start < period_end`, `due_date >= invoice_date` | Logique |
| R07 | Composantes obligatoires | structure | WARNING | Elec: accise + CTA. Gaz: accise + CTA | Legislation |
| R08 | Montant negatif suspect | coherence | WARNING | `amount_ht < 0` hors remise/regularisation | Logique |
| R09 | Composante opaque (type autre) | structure | INFO | `component_type == autre` | Logique |
| R10 | Doublon composante | coherence | WARNING | Meme (type, label) apparait 2 fois | Logique |
| R11 | Conso composantes vs conso globale | coherence | WARNING | `sum(conso_comps.qty) == conso_kwh` | Logique |
| R12 | Base accise vs conso | fiscalite | WARNING | `accise.qty == conso_kwh` | Legislation |
| R13 | Prix unitaire dans plage credible | coherence | WARNING | `0.01 <= unit_price <= 1.00 EUR/kWh` | Marche |
| R14 | Periode > 35 jours | coherence | INFO | Facture couvrant plus d'un mois | Logique |
| R15 | Facture sans composante | structure | CRITICAL | `len(components) == 0` | Logique |
| R16 | Total TTC = 0 | coherence | INFO | Avoir ou facture rectificative ? | Logique |
| R17 | PDL/PCE manquant | structure | INFO | Rattachement site impossible | Operationnel |
| R18 | Somme TVA vs total TVA | TVA | ERROR | `sum(comp.tva_amount) == total_tva` | Universel |
| R19 | Penalite/depassement | alerte | WARNING | Presence de penalite ou depassement | Operationnel |
| R20 | Montant total eleve | alerte | INFO | `total_ttc > 50000 EUR` | Seuil interne |

---

## Statuts de conformite

| Statut | Signification |
|--------|---------------|
| PASS | Aucune anomalie detectee pour cette regle |
| FAIL | Anomalie detectee (voir severite) |
| N/A | Regle non applicable (donnees manquantes) |

---

## Escalade par severite

| Severite | Action requise |
|----------|----------------|
| INFO | Signalement, pas d'action obligatoire |
| WARNING | Verification recommandee |
| ERROR | Correction requise avant validation |
| CRITICAL | Blocage : facture non exploitable sans correction |

---

## Couverture Shadow Billing

| Niveau | Regles couvertes | Prerequis |
|--------|------------------|-----------|
| L0 (Read) | Aucune | Parsing reussi |
| L1 (Partial) | R01-R20 | Composantes parsees |
| L2 (Component) | + grilles TURPE/ATRD | Docs tarifs dans KB |
| L3 (Full) | + recalcul complet | Offre fournisseur + contrat |
