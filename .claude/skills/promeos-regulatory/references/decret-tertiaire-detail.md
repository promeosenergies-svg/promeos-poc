# Décret Tertiaire — Référence détaillée

## Textes de référence

- Décret n°2019-771 du 26/07/2019 (JORF 28/07/2019)
- Arrêté du 10/04/2020 (méthode de calcul)
- Arrêté Valeurs Absolues VI (septembre 2025)
- Plateforme OPERAT: https://operat.ademe.fr

## Champ d'application (Art. R174-22 CCH)

Bâtiments ou parties de bâtiments à usage tertiaire dont la surface ≥ 1,000 m².
Applicable que le bâtiment soit en propriété ou en location.
Applicable aux secteurs public ET privé.

## Jalons de réduction (Art. R174-23 CCH)

| Année | Réduction relative vs référence | is_official PROMEOS |
|---|---|---|
| 2030 | -40% | true |
| 2040 | -50% | true |
| 2050 | -60% | true |

⚠️ Le jalon intermédiaire 2026 (-25%) n'est PAS un jalon officiel du décret.
Il n'apparaît PAS dans les réponses API PROMEOS.

## Année de référence

- Choix entre 2010 et 2020 (Art. R174-23 CCH, alinéa 2)
- L'assujetti choisit l'année la plus favorable
- Si données manquantes: utiliser la moyenne des 3 premières années disponibles
- PROMEOS seed: 2020 par défaut (première année OPERAT pleine post-COVID)

## Méthode de calcul (correction climatique)

```
# Étape 1: Correction climatique de la référence
conso_ref_corrigée = conso_ref_brute × (DJU_normale_zone / DJU_année_ref)

# Étape 2: Correction climatique de l'année courante  
conso_courante_corrigée = conso_courante_brute × (DJU_normale_zone / DJU_année_courante)

# Étape 3: Calcul de l'objectif
objectif_2030 = conso_ref_corrigée × (1 - 0.40)
objectif_2040 = conso_ref_corrigée × (1 - 0.50)
objectif_2050 = conso_ref_corrigée × (1 - 0.60)

# Étape 4: Évaluation du statut
écart = (conso_courante_corrigée - objectif_année) / conso_ref_corrigée × 100
CONFORME si écart ≤ 0%
EN_ALERTE si 0% < écart < 10%
NON_CONFORME si écart ≥ 10%
```

## Valeurs absolues (arrêté VA VI, sept 2025)

Alternative à la méthode relative. L'assujetti peut choisir la plus favorable.

| Catégorie OPERAT | Seuil VA 2030 (kWhEF/m²/an) |
|---|---|
| BUREAU_STANDARD | ~110 |
| ENSEIGNEMENT | ~90 |
| HOTEL_HEBERGEMENT | ~180 |
| LOGISTIQUE_SEC | ~60 |
| COMMERCE | ~160 |
| SANTE | ~200 |

## Modulation (Art. R174-24 CCH)

Motifs acceptés:
- Changement d'activité substantiel
- Contraintes techniques ou patrimoniales
- Conditions météorologiques exceptionnelles
- Coût manifestement disproportionné

Deadline premier dépôt: **30 septembre 2026**
Dossier à déposer sur OPERAT avec justificatifs.

## Sanctions (Art. R185-2 CCH)

- Publication sur OPERAT de la liste des bâtiments non conformes ("name and shame")
- Amende potentielle (montant en cours de définition)
- Premier bilan officiel: 2031

## Mapping NAF → Catégorie OPERAT

Fichier PROMEOS: `backend/utils/naf_resolver.py` → `resolve_naf_code()`

| NAF | Catégorie | Archétype seed |
|---|---|---|
| 70.10Z | BUREAU_STANDARD | Paris, Lyon |
| 69.10Z | BUREAU_STANDARD | Lyon |
| 85.31Z | ENSEIGNEMENT | Marseille |
| 55.10Z | HOTEL_HEBERGEMENT | Nice |
| 52.10B | LOGISTIQUE_SEC | Toulouse |
