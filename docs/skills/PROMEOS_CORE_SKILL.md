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

## Regle d'or absolue — ZERO calcul metier en frontend

Toute logique de calcul appartient au backend. Le frontend est affichage uniquement.

### Calculs INTERDITS en frontend :
- CO2 : `* 0.052` ou `* 0.227`
- Penalites DT : `* 7500` ou `* 3750`
- Prix fallback : `* 0.068`
- Reduction % : `1 - x/y * 100`
- IPE : surface x intensite
- Score conformite : ponderation quelconque

## Valeurs canoniques

| Constante | Valeur | Source |
|-----------|--------|--------|
| CO2 electricite | 0.052 kgCO2/kWh | ADEME Base Empreinte V23.6 |
| CO2 gaz | 0.227 kgCO2/kWh | ADEME Base Empreinte V23.6 |
| Coef. energie primaire elec | 1.9 | Janvier 2026 |
| Prix fallback elec | 0.068 EUR/kWh | DEFAULT_PRICE_ELEC_EUR_KWH |
| Accise elec entreprises | 25.79 EUR/MWh | CRE 2025 |
| OID benchmark bureaux | 146 kWhEF/m2/an | OPERAT 2022 |

CRITIQUE : 0.0569 = tarif TURPE 7 HPH reseau (EUR/kWh), PAS un facteur CO2.

## Jalons Decret Tertiaire (Decret n2019-771)

- 2030 : -40% vs annee ref (2020) — is_official: true
- 2040 : -50% vs annee ref — is_official: true
- 2050 : -60% vs annee ref — is_official: true
- Jalon 2026 (-25%) : SUPPRIME des API responses

## Scoring conformite — Poids canoniques

```python
SCORING_PROFILE = {
    "DT": 0.39,    # regime AUDIT applicable
    "BACS": 0.28,
    "APER": 0.17,
    "AUDIT": 0.16,
}
# Sans AUDIT : DT 45% / BACS 30% / APER 25%
# Source unique : regops/scoring.py -> RegAssessment.compliance_score
```

## Sources de verite — une seule par domaine

- Consommation : `consumption_unified_service.py`
- Conformite scoring : `regops/scoring.py`
- Facteurs emission : `emission_factors.py`
- NAF -> archetype : `utils/naf_resolver.py` -> `resolve_naf_code()`
- Pricing contrat : `resolve_pricing(annexe)` -> source: cadre ou override
- Tarifs reglementes : `tarifs_reglementaires.yaml`

## Architecture hierarchique

Organisation -> EntiteJuridique -> Portefeuille -> Site -> Batiment -> Compteur -> DeliveryPoint

## Regles API

```python
# Erreur standardisee obligatoire
{
    "error": "RESOURCE_NOT_FOUND",
    "message": "Site introuvable",
    "hint": "Verifiez l'identifiant site_id",
    "correlation_id": "uuid-ici"
}
# Datetime : datetime.now(UTC) — jamais utcnow() (deprecie)
# Idempotence : cle format kb-reco:{site_id}:{code}
```

## Navigation PROMEOS

- Simple mode : <= 11 entrees
- Expert mode : <= 19 entrees (11 + 8 sub)
- CommandPalette Ctrl+K : toutes pages cachees
- Zero ecran mort, zero lien orphelin

## Dataset demo

HELIOS SAS (5 sites) : Paris 3500m2, Lyon 1200m2, Marseille 2800m2, Nice 4000m2, Toulouse 6000m2
MERIDIAN SAS (3 sites) : Levallois, Bordeaux, Gennevilliers
Seed : 730j data horaire, RNG=42, ref_year=2020

## Pattern commit obligatoire

```
fix(p0): Phase N — description
feat(module): description fonctionnelle
```

## Checklist QA avant merge

- [ ] Zero calcul metier frontend (grep source-guard)
- [ ] Valeurs canoniques CO2/prix/jalons inchangees
- [ ] Tests FE >= 3 783, BE >= 843, zero regression
- [ ] Tous etats UI : loading/empty/error/partial
- [ ] datetime.now(UTC) partout
- [ ] Unites coherentes tous ecrans
