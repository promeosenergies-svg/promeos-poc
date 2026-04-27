# Méthodologie — Vue COMEX (cockpit Jean-Marc CFO)

> Référence accessible depuis le SolPageFooter de `/cockpit?angle=comex`.
> Dernière révision : 2026-04-26 (Sprint 1.4bis).

## Objet

La **vue COMEX** orchestre 3 KPIs CFO (Trajectoire 2030 / Exposition financière / Leviers économies) et un échéancier hebdomadaire en week-cards. Cette page consolide les sources sourcées RegOps + RegAssessment + estimation modélisée Bill-Intel. Le brief est exportable en CODIR.

## KPIs canoniques

### 1. Trajectoire 2030
Score pondéré identique à `/conformite` — voir [Méthodologie Conformité RegOps](./conformite-regops).

### 2. Exposition financière
Cumul provisions DT (7 500 €/site non-conforme + 3 750 €/site à risque). Source : Décret n°2019-771.

### 3. Leviers économies (estimés)
Heuristique modélisée : **~8 500 €/site en dérive** = 5 % de la facture annuelle moyenne ETI tertiaire (30 €/m²/an × 600 m² médian × 5 %).

Sprint 5 Bill-Intel remplacera cette estimation par les reclaims TURPE / accise / CTA réels + le simulateur achat post-ARENH.

## Provenance

- `RegOps` — moteur scoring conformité canonique
- `RegAssessment` — modèle d'évaluation par site
- `Estimation modélisée PROMEOS` — heuristique leviers (non sourcé, à remplacer S5)

Niveau de confiance affiché : **haute** dès qu'un score conformité est calculé sur ≥1 site, sinon moyenne.

## Référence interne

- `backend/services/narrative/narrative_generator.py:_build_cockpit_comex`
- `backend/services/kpi_service.py` — KpiService
- `backend/regops/` — moteur RegOps canonique

## Versioning

Modifications du modèle de calcul leviers ou des pondérations RegOps donnent lieu à un commit explicite et une mise à jour de cette page. Sprint 5 Bill-Intel = première substitution prévue.
