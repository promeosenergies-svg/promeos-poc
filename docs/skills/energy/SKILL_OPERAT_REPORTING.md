---
name: promeos-operat-reporting
description: >
  Expert plateforme OPERAT et reporting Décret Tertiaire.
  Déclaration annuelle, exports preuves, jalons,
  trajectoires, correction DJU, dossier opposable.
version: 1.0.0
tags: [operat, reporting, dt, declaration, preuves, jalons]
---

# OPERAT & Reporting Décret Tertiaire — Expert PROMEOS

## 1. Plateforme OPERAT

### Qu'est-ce que c'est ?
- Observatoire de la Performance Énergétique de la Rénovation
  et des Actions du Tertiaire
- Gérée par l'ADEME
- URL : https://operat.ademe.fr
- 600M+ m² déclarés (2022), 25 300 bâtiments

### Qui déclare ?
- Le propriétaire du bâtiment (ou le preneur à bail si délégation)
- Obligation annuelle avant le 30 septembre N+1
- Pour tous bâtiments tertiaires >= 1 000 m²

### Données à déclarer
| Donnée | Fréquence | Source |
|--------|-----------|--------|
| Surface SHON RT | 1 fois | Acte notarial / plans |
| Activité principale (code OPERAT) | Annuel | Gestionnaire |
| Consommation élec (kWh) | Annuel | Factures / Enedis |
| Consommation gaz (kWh) | Annuel | Factures / GRDF |
| Consommation autres fluides | Annuel | Factures |
| Année référence | 1 fois | Choix déclarant |
| Modulation surface (si partielle) | Si applicable | Gestionnaire |

## 2. Calcul de la Trajectoire

### Formule de base
```
IPE (Intensité en Énergie Finale) = Σ conso (kWhEF) / Surface (m²)
Objectif N = IPE_référence × (1 - réduction_jalon)
```

### Correction DJU (si demandée)
```
IPE_corrigé = IPE_mesuré × (DJU_référence / DJU_année)
```
- DJU méthode COSTIC (préférée PROMEOS)
- Correction possible si écart DJU > 10% vs référence
- À documenter dans le dossier OPERAT

### Jalons officiels à déclarer
| Jalon | Réduction | Statut |
|-------|-----------|--------|
| 2030 | -40% | OFFICIEL — à afficher |
| 2040 | -50% | OFFICIEL — à afficher |
| 2050 | -60% | OFFICIEL — à afficher |

> **ATTENTION** : Le "jalon 2026 (-25%)" n'a JAMAIS été un objectif
> réglementaire inscrit dans le Décret n°2019-771. C'est une cible
> indicative utilisée par certains acteurs de l'industrie.
> Ne jamais l'afficher comme obligation légale dans PROMEOS.

## 3. Modulations Réglementaires

### Modulation surface (Art. R131-25)
Si le bâtiment est multi-locataire ou multi-usage :
- Surface par usage = base du calcul
- Chaque usage a son propre objectif

### Modulation contraintes techniques
- Bâtiment classé monument historique — objectif réduit
- Projet de rénovation en cours — report documenté
- TRI > 10 ans — action non requise si justifié

### Valeur ajoutée PROMEOS
Générer automatiquement le dossier OPERAT avec :
- Export CSV conforme au format ADEME
- Calcul IPE par usage
- Justificatifs DJU annexés
- Attestation conformité PDF signée

## 4. Preuves et Dossier Opposable

### Pièces à conserver (10 ans)
- Factures énergétiques (électricité, gaz, autres)
- Contrats de fourniture
- Relevés Enedis / GRDF
- Calculs DJU et sources météo
- Plans de bâtiment (surface SHON RT)
- Actions réalisées (travaux, contrats, formations)

### Structure dossier PROMEOS
```
dossier_operat_SITE_ANNEE/
├── 01_declaration_operat.csv
├── 02_consommations_factures.pdf
├── 03_releves_enedis.json
├── 04_calcul_dju_costic.xlsx
├── 05_trajectoire_projections.pdf
├── 06_actions_realisees.md
└── 07_attestation_conformite.pdf
```

## 5. Sanctions et Risques

### Pénalités réglementaires (Code de la construction, Art. L174-25)
| Niveau | Déclencheur | Sanction |
|--------|-------------|---------|
| Mise en demeure | Non-déclaration > 6 mois | Avertissement préfet |
| Amende personne physique | Non-conformité persistante | 1 500 € |
| Amende personne morale | Non-conformité persistante | 7 500 € |
| Publication | Liste des contrevenants | Image publique |

### Dans le code PROMEOS
```python
# Source unique : backend/config/emission_factors.py
BASE_PENALTY_EURO = 7_500          # Personne morale — Art. L174-25
A_RISQUE_PENALTY_RATIO = 0.5      # 50% — scoring interne PROMEOS
A_RISQUE_PENALTY_EURO = 3_750     # ⚠️ Valeur interne, PAS réglementaire
# Pénalité personne physique : 1 500 € (non modélisée, hors scope B2B)
```

## 6. API OPERAT (si disponible)

ADEME travaille sur une API REST pour OPERAT.
En attendant : import CSV via interface web.
PROMEOS : générer le CSV au bon format automatiquement.

Format attendu : colonnes ADEME v3.2
- `identifiant_operat` (code unique bâtiment)
- `annee_consommation`
- `type_energie` (ELECTRICITE, GAZ_NATUREL, etc.)
- `consommation_kwh`
- `surface_utile_m2`
- `activite_principale` (code OPERAT)
