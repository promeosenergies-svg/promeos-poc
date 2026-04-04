---
name: promeos-seed
description: "Données de démonstration PROMEOS : seed HELIOS (5 sites), MERIDIAN (3 sites), courbes de charge 730 jours, archétypes NAF, profils consommation. Utiliser ce skill dès qu'il est question de données de démo, seed, jeux de test, scénarios de démonstration, profils consommation par archétype, ou données HELIOS/MERIDIAN."
---

# PROMEOS Seed — Données de Démo

## Routing

| Contexte | Fichier |
|---|---|
| Paramètres détaillés HELIOS 5 sites, anomalies seed | `references/helios-detailed.md` |
| Tout le reste (profils, hiérarchie, idempotence) | Ce SKILL.md suffit |

## Proactive triggers

- Consommation kWh/m² hors range archétype → "La consommation seedée est hors du range attendu pour cet archétype."
- RNG ≠ 42 détecté → "Le seed doit utiliser RNG=42 pour la reproductibilité."
- Somme horaire ≠ total mensuel → "Incohérence: la somme des consommations horaires ne correspond pas au total mensuel."

## HELIOS (5 sites)

| Site | Ville | Surface | NAF | Archétype |
|---|---|---|---|---|
| Paris Bureaux | Paris | 3,500m² | 70.10Z | BUREAU_STANDARD |
| Lyon Bureaux | Lyon | 1,200m² | 69.10Z | BUREAU_STANDARD |
| Marseille École | Marseille | 2,800m² | 85.31Z | ENSEIGNEMENT |
| Nice Hôtel | Nice | 4,000m² | 55.10Z | HOTEL_HEBERGEMENT |
| Toulouse Entrepôt | Toulouse | 6,000m² | 52.10B | LOGISTIQUE_SEC |

MERIDIAN SAS: Levallois ~2,000m², Bordeaux ~1,500m², Gennevilliers ~3,000m².

## Paramètres

RNG=42, 730 jours, résolution horaire, ref_year=2020, timezone Europe/Paris.

## Profils consommation

BUREAU: baseload 20-25%, pointe 8h-19h lun-ven, +30% hiver, kWh/m²=120-180, HP/HC ~70/30.
ENSEIGNEMENT: vacances=30% baseload, pointe 7h-18h scolaire, quasi-nul été, kWh/m²=80-130.
HOTEL: 24/7, pic été (clim), baseload 35-40%, kWh/m²=150-250, HP/HC ~65/35.
LOGISTIQUE: éclairage dominant, 6h-22h, kWh/m²=30-70, HP/HC ~80/20.

## Hiérarchie data model

Organisation → EntiteJuridique → Portefeuille → Site → Bâtiment/Compteur/DeliveryPoint.

## Règles

- RNG=42 toujours (reproductibilité)
- Valeurs réalistes par archétype
- Cohérence: somme horaire = total mensuel facturé
- Anomalies seed documentées et vérifiables
- Consommation ≥ 0
- Idempotence: `seed:{org_id}:{site_id}:{year}:{month}`

Fichier: `backend/services/demo_seed/orchestrator.py`
