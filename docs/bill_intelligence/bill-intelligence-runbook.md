# RUNBOOK — PROMEOS Bill Intelligence

**Date**: 2026-02-13
**Scope**: Operations quotidiennes du module Bill Intelligence

---

## 1. Architecture

```
app/bill_intelligence/
  domain.py           # Modele canonique (dataclasses + enums)
  engine.py            # Pipeline: parse → audit → shadow → report
  timeline.py          # Timeline 24 mois (gaps/overlaps)
  router.py            # FastAPI (13 endpoints /api/bill/*)
  parsers/
    json_parser.py     # Parse JSON → Invoice (+ ConceptAllocation)
    pdf_parser.py      # Parse PDF text → Invoice (templates)
  rules/
    audit_rules_v0.py  # 20 regles V0 (arithmetique + TVA + coherence)
  offers/
    __init__.py        # Placeholder offres fournisseurs
```

---

## 2. Endpoints API

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/bill/demo/invoices` | Lister les factures demo |
| GET | `/api/bill/demo/invoices/{filename}` | Parser une facture demo |
| POST | `/api/bill/import` | Importer une facture JSON |
| POST | `/api/bill/audit/{invoice_id}` | Auditer une facture |
| POST | `/api/bill/audit-all` | Auditer toutes les factures demo |
| GET | `/api/bill/report/{invoice_id}` | Rapport HTML d'audit |
| GET | `/api/bill/anomalies/csv` | Export CSV de toutes les anomalies |
| GET | `/api/bill/rules` | Lister les 20 regles V0 |
| GET | `/api/bill/coverage` | Dashboard couverture L0-L3 |
| GET | `/api/bill/timeline` | Timeline 24 mois |
| GET | `/api/bill/dashboard` | Dashboard coverage KPIs |
| GET | `/api/bill/pdf/templates` | Lister les templates PDF |
| POST | `/api/bill/pdf/parse` | Parser du texte PDF |

---

## 3. Pipeline d'audit

```
1. PARSE
   Input: JSON brut ou fichier
   Output: Invoice (dataclass) avec status=PARSED, shadow_level=L0
   Chaque composante reçoit un ConceptAllocation (concept_id + confidence)

2. AUDIT
   Input: Invoice parsee
   Output: Invoice avec anomalies[] et status=AUDITED
   Execute les 20 regles V0 sequentiellement
   Enrichit les anomalies avec citations KB (P5, si disponible)

3. SHADOW BILLING L1
   Input: Invoice auditee
   Output: ShadowResult (recalcul HT/TVA/TTC par composante)
   Recalcule: qty*unit_price, TVA par type, totaux
   Compare avec facture originale → delta_ht, delta_ttc, delta_percent

4. REPORT
   Input: Invoice + ShadowResult
   Output: AuditReport (JSON ou HTML)
   Inclut: anomalies, shadow, concept_allocations, KB evidence
```

---

## 4. Operations courantes

### Ajouter une facture demo

1. Creer un fichier JSON dans `backend/data/invoices/demo/`
2. Structure requise: voir `facture_elec_edf_2025_01.json` comme reference
3. Champs obligatoires: `invoice_id`, `energy_type`, `supplier`, `components[]`
4. Chaque composante: `component_type`, `label`, `amount_ht`

### Ajouter une regle d'audit

1. Ouvrir `rules/audit_rules_v0.py`
2. Creer la fonction `rule_rXX_name(invoice: Invoice) -> List[InvoiceAnomaly]`
3. L'ajouter a `ALL_RULES` avec son ID et description
4. Attribuer un `rule_card_id` a chaque anomalie generee

### Verifier la couverture

```bash
# Auditer toutes les factures demo
curl http://localhost:8000/api/bill/audit-all

# Dashboard couverture
curl http://localhost:8000/api/bill/coverage
```

---

## 5. Concept Allocation

Chaque ligne de facture est allouee a un concept (fourniture, acheminement, taxes...).
- Mapping direct `ComponentType → BillingConcept` : confidence 1.0
- Fallback regex sur label : confidence 0.70-0.90
- Non reconnu : concept=autre, confidence=0.50

Voir [billing-concepts.md](billing-concepts.md) pour la taxonomie complete.

---

## 6. Troubleshooting

| Symptome | Cause probable | Fix |
|----------|----------------|-----|
| `ShadowLevel = L0` | Facture sans composantes | Verifier le JSON |
| `why_not_higher = L2 necessite grilles TURPE` | Pas de docs tarifs dans KB | Ingerer les docs TURPE |
| `concept=autre, confidence=0.50` | Label non reconnu | Ajouter un pattern regex |
| `RULE_RXX_ERROR` | Exception dans une regle | Voir les logs, corriger la regle |
| KB evidence vide | KB non initialisee ou table manquante | Lancer `init_citations_schema()` |
