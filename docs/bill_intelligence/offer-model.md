# OFFER MODEL — PROMEOS Bill Intelligence

**Date**: 2026-02-13
**Status**: Placeholder (D6 — offres fournisseurs non implementees en POC)

---

## 1. Objectif

Le module Offres modelise les contrats et grilles tarifaires des fournisseurs d'energie.
Il est necessaire pour atteindre le **shadow billing L2+** (recalcul par composante).

---

## 2. Structure cible (non implementee)

### OfferTemplate

| Champ | Type | Description |
|-------|------|-------------|
| offer_id | str | Identifiant unique |
| supplier | str | Nom fournisseur |
| energy_type | Enum | elec / gaz |
| offer_name | str | Nom commercial |
| effective_from | date | Debut de validite |
| effective_to | date | Fin de validite |
| pricing_model | Enum | fixe / indexe / spot |
| components | List[OfferComponent] | Grille tarifaire |

### OfferComponent

| Champ | Type | Description |
|-------|------|-------------|
| component_type | ComponentType | Type (abonnement, conso_hp...) |
| unit_price | float | Prix unitaire EUR |
| unit | str | Unite (EUR/kWh, EUR/kVA/mois...) |
| conditions_json | str | Conditions d'application (puissance, horaire...) |

---

## 3. Integration prevue

```
Invoice parsed
  → Match OfferTemplate by (supplier, contract_ref, period)
  → For each InvoiceComponent:
      → Find matching OfferComponent
      → Recalculate: qty * offer_unit_price → shadow_amount
      → Compare with invoice amount → anomaly si ecart
  → Shadow level → L2_COMPONENT
```

---

## 4. Sources de donnees

| Source | Format | Statut |
|--------|--------|--------|
| CRE (Commission de Regulation de l'Energie) | PDF/HTML | Disponible via referentiel |
| Grilles TURPE (Enedis) | PDF | A ingerer dans KB |
| Grilles ATRD (GRDF) | PDF | A ingerer dans KB |
| Offres commerciales | CSV/JSON | Saisie manuelle ou import |

---

## 5. Fichier source

```
app/bill_intelligence/offers/__init__.py  # Placeholder, NOT_IMPLEMENTED
```

Ce module sera implemente quand les documents tarifs seront ingeres dans la KB
et que les grilles TURPE/ATRD seront disponibles comme RuleCards avec citations.
