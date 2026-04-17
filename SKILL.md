---
name: promeos-core
description: >
  PROMEOS Energy OS — regles non-negociables pour tout developpement sur le codebase.
  Encode les valeurs canoniques energie, l'architecture backend-only, les patterns
  de test, et la philosophie produit B2B France post-ARENH.
version: 1.0.0
tags: [energy, saas, france, regulatory, fastapi, react, b2b]
---

# PROMEOS Core Engineering Skill

## Regle absolue — ZERO calcul metier en frontend

Le frontend est affichage uniquement. Tout calcul appartient au backend.

### Calculs INTERDITS cote frontend :
- CO2 : `* 0.052` ou `* 0.227`
- Penalites DT : `* 7500` ou `* 3750`
- Prix fallback : `* 0.068`
- Reduction % : `1 - x/y * 100` ou variantes
- IPE : surface x intensite
- Score conformite : toute ponderation

## Valeurs canoniques — Source de verite absolue

| Constante | Valeur | Source |
|-----------|--------|--------|
| CO2 electricite | 0.052 kgCO2/kWh | ADEME Base Empreinte V23.6 |
| CO2 gaz | 0.227 kgCO2/kWh | ADEME Base Empreinte V23.6 |
| Coef. energie primaire elec | 1.9 | Janvier 2026 |
| Prix fallback elec | 0.068 EUR/kWh | DEFAULT_PRICE_ELEC_EUR_KWH |
| Accise elec entreprises | 25.79 EUR/MWh | CRE 2025 |
| TICGN | 15.43 EUR/MWh | CRE 2025 |
| OID benchmark bureaux | 146 kWhEF/m2/an | OPERAT 2022 |
| Penalite DT base | 7 500 EUR | Decret n2019-771 |
| NEBCO seuil | 100 kW par pas de pilotage | RM-5-NEBCO-V01 |

CRITIQUE : 0.0569 = tarif TURPE 7 HPH reseau (EUR/kWh) — PAS un facteur CO2.

## Jalons Decret Tertiaire (Decret n2019-771)

| Jalon | Objectif | is_official |
|-------|----------|-------------|
| 2030 | -40% vs annee ref (2020) | true |
| 2040 | -50% vs annee ref | true |
| 2050 | -60% vs annee ref | true |

Jalon 2026 (-25%) : SUPPRIME de toutes les API responses.

## Scoring conformite — Poids canoniques

```python
# Regime avec AUDIT applicable (conso > 2.75 GWh)
SCORING_WITH_AUDIT = {"DT": 0.39, "BACS": 0.28, "APER": 0.17, "AUDIT": 0.16}

# Regime sans AUDIT
SCORING_DEFAULT = {"DT": 0.45, "BACS": 0.30, "APER": 0.25}

# Source unique : regops/scoring.py -> RegAssessment.compliance_score
```

### Conditions d'applicabilite par framework :
- DT : surface >= 1 000 m2
- BACS : puissance CVC > 290 kW (2025) ou > 70 kW (2030, report décret 2025-1343)
- APER : parking >= 1 500 m2 ou toiture >= 500 m2
- AUDIT ÉNERGÉTIQUE : conso > 2.75 GWh — deadline 11/10/2026 (loi 2025-391)
- SMÉ ISO 50001 : conso > 23.6 GWh — deadline 11/10/2027 (loi 2025-391)

## Sources de verite — une seule par domaine

| Domaine | Fichier source |
|---------|----------------|
| Consommation | consumption_unified_service.py |
| Conformite scoring | regops/scoring.py -> RegAssessment.compliance_score |
| Facteurs emission | emission_factors.py |
| NAF -> archetype | utils/naf_resolver.py -> resolve_naf_code() |
| Pricing contrat | resolve_pricing(annexe) -> source: cadre/override |
| Tarifs reglementes | tarifs_reglementaires.yaml |

## Architecture hierarchique

Organisation -> EntiteJuridique -> Portefeuille -> Site -> Batiment -> Compteur -> DeliveryPoint

## Regles API obligatoires

```python
# Format erreur standardise
{
    "error": "RESOURCE_NOT_FOUND",
    "message": "Site introuvable",
    "hint": "Verifiez l'identifiant site_id",
    "correlation_id": "uuid-ici"
}
# Datetime : datetime.now(UTC) — jamais utcnow() (deprecie, 32 occurrences a migrer)
# Idempotence : cle format kb-reco:{site_id}:{code}
# Org-scoping : obligatoire sur tous les endpoints (P0 production)
```

## Navigation PROMEOS

- Simple mode : <= 11 entrees de navigation
- Expert mode : <= 19 entrees (11 + 8 sub-entrees)
- CommandPalette Ctrl+K : acces toutes pages cachees
- Zero ecran mort — zero bouton sans destination coherente
- Etats UI obligatoires : loading / empty / error / partial data

## Dataset demo

### HELIOS SAS (5 sites) :
| Site | Surface | Type |
|------|---------|------|
| Paris Bureaux | 3 500 m2 | Tertiaire/Bureau |
| Lyon Bureaux | 1 200 m2 | Tertiaire/Bureau |
| Marseille Ecole | 2 800 m2 | Education |
| Nice Hotel | 4 000 m2 | Hotellerie |
| Toulouse Entrepot | 6 000 m2 | Logistique |

### MERIDIAN SAS (3 sites) : Levallois, Bordeaux, Gennevilliers
Seed : 730 jours de donnees horaires, RNG=42, ref_year=2020 (DT baseline)

## Pattern de developpement obligatoire

```
Phase 0 : audit read-only uniquement (grep, find, cat) — STOP, bilan avant modif
Phase N : fix atomique -> tests -> commit
Commit : fix(p0): Phase N — description / feat(module): description
```

## Checklist QA avant merge

- [ ] Zero calcul metier en frontend (pytest source-guard confirme)
- [ ] Valeurs canoniques CO2/prix/jalons inchangees
- [ ] Tests FE >= 3 783 pass, BE >= 843 pass, 0 failed
- [ ] Tous etats UI presents : loading / empty / error / partial
- [ ] datetime.now(UTC) partout — pas utcnow()
- [ ] Unites coherentes sur tous les ecrans (kWh/MWh, EUR/MWh, HT/TTC)
- [ ] Endpoints org-scopes valides
