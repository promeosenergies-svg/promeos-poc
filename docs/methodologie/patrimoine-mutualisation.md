# Méthodologie — Mutualisation Décret Tertiaire (Patrimoine)

> Référence accessible depuis le SolPageFooter de `/patrimoine`.
> Dernière révision : 2026-04-26 (Sprint 1.4bis).

## Objet

La **mutualisation Décret Tertiaire** est le différenciateur §4.1 de la doctrine PROMEOS Sol. Elle calcule l'économie potentielle (€/an) lorsque les efforts de réduction conso sont consolidés à l'échelle du portefeuille — les sites en avance compensent les sites en dérive vis-à-vis des jalons -40 % / -50 % / -60 %.

## Base légale

- [Décret n°2019-771](https://www.legifrance.gouv.fr/loda/id/JORFTEXT000038812251/) — Article 3 du Décret tertiaire (`L111-10-3` du code de la construction et de l'habitation)
- L'article autorise la mutualisation des objectifs entre sites d'une même entité juridique sur le périmètre tertiaire assujetti.

## Calcul

### 1. Trajectoire par site
Pour chaque site avec EFA déclarée :

```
objectif_kwh_2030 = reference_year_kwh × (1 - 0.40)
ecart_kwh = consommation_actuelle - objectif_kwh_2030
```

- `ecart > 0` → site en déficit
- `ecart < 0` → site en surplus (peut compenser un autre site)

### 2. Mutualisation portefeuille

```
ecart_total_kwh = Σ ecart_kwh sur tous les sites
conforme_mutualise = ecart_total_kwh ≤ 0
```

Si `conforme_mutualise == True`, l'effet de portefeuille rend le patrimoine conforme — aucune pénalité par site.

### 3. Économie chiffrée

```
penalite_sans_mutualisation = nb_sites_deficit × 7 500 €
penalite_avec_mutualisation = (max(0, ecart_total_kwh) / objectif_total) × penalty_factor
economie_mutualisation_eur = penalite_sans_mutualisation - penalite_avec_mutualisation
```

## Hypothèses

- Les sites doivent appartenir à la même **entité juridique** (limite légale du Décret 2019-771).
- Les déclarations OPERAT N-1 doivent être complètes pour les sites mis en mutualisation.
- L'économie estimée suppose la pénalité forfaitaire 7 500 €/site (Article 7 Décret 2019-771).

## Provenance

- `Patrimoine PROMEOS` — registre Org → EJ → Pf → Site
- `compute_mutualisation()` — service backend canonique

Niveau de confiance affiché : **haute** dès que la simulation produit une économie >0 €/an, sinon moyenne.

## Référence interne

- `backend/services/tertiaire_mutualisation_service.py` — service SoT
- `backend/services/narrative/narrative_generator.py:_build_patrimoine`
- `models/tertiaire.py` — TertiaireEfa, TertiaireEfaConsumption

## Différenciation marché

À ce jour aucun concurrent référencé (Advizeo, Deepki, Citron, Energisme, Trinergy) ne propose une simulation chiffrée de mutualisation portefeuille en €/an. Cette feature est unique dans le marché B2B multisite français.

## Versioning

Modifications du modèle (ajout d'un facteur correctif, changement de jalon) donnent lieu à un commit explicite et une mise à jour de cette page. La règle Article 3 Décret 2019-771 reste invariante.
