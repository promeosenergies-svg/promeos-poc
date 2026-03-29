# Bilan — Usage Knowledge Base (NAF → Archétypes Énergétiques)

**Date** : 2026-03-29
**Commit** : `45ad2cb` sur `main`
**GitHub** : `promeosenergies-svg/promeos-poc`

---

## Résumé

Livraison d'une **base de connaissances usages énergétiques** complète, permettant à PROMEOS de contextualiser automatiquement chaque site client à partir de son code NAF, sans configuration manuelle.

---

## Livrables commités

| Fichier | Chemin | Contenu |
|---------|--------|---------|
| **archetypes_energy_v1.json** | `docs/base_documentaire/naf_archetype_mapping/` | 15 archétypes énergétiques complets |
| **naf_to_archetype_v1.json** | `docs/base_documentaire/naf_archetype_mapping/` | 732 codes NAF Rev2 → archétype |
| **manifest.json** | `docs/base_documentaire/naf_archetype_mapping/` | Métadonnées, provenance, intégrité |
| **FEAT_USAGE_KNOWLEDGE_BASE.md** | `docs/` | Spec d'implémentation 4 phases |

---

## Les 15 archétypes

| Code | Titre | kWh/m²/an (moy.) | Seuil nuit | Seuil WE |
|------|-------|:-----------------:|:----------:|:--------:|
| BUREAU_STANDARD | Bureaux Tertiaires | 180 | 0.20 | 0.25 |
| COMMERCE_ALIMENTAIRE | Commerce Alimentaire | 600 | 0.75 | 1.10 |
| COMMERCE_NON_ALIMENTAIRE | Commerce Non-Alimentaire | 220 | 0.15 | 0.30 |
| RESTAURATION_SERVICE | Restauration | 350 | 0.15 | 1.30 |
| HOTEL_HEBERGEMENT | Hôtels & Hébergement | 250 | 0.65 | 1.40 |
| LOGISTIQUE_FROID | Entrepôt Frigorifique | 180 | 0.85 | 0.95 |
| LOGISTIQUE_SEC | Entrepôt & Logistique | 50 | 0.15 | 0.30 |
| HOPITAL_STANDARD | Établissement de Santé | 340 | 0.85 | 1.00 |
| INDUSTRIE_LEGERE | Industrie & Manufacturing | 140 | 0.45 | 0.55 |
| ENSEIGNEMENT | Enseignement & Formation | 130 | 0.12 | 0.20 |
| ADMINISTRATION | Administration Publique | 170 | 0.18 | 0.22 |
| DATA_CENTER_IT | Data Center & Hébergement IT | 1000 | 0.98 | 1.05 |
| SPORT_LOISIRS | Sport, Culture & Loisirs | 250 | 0.30 | 1.40 |
| COPROPRIETE_LOGEMENT | Copropriété & Logement Social | 50 | 0.65 | 1.15 |
| AUTRE_TERTIAIRE | Autre / Non classifié | 175 | 0.25 | 0.30 |

---

## Couverture NAF

| Métrique | Valeur |
|----------|--------|
| Codes NAF Rev2 mappés | **732** (100% des sous-classes INSEE) |
| Confidence HIGH | 355 codes (48.5%) |
| Confidence MEDIUM | 256 codes (35.0%) |
| Confidence LOW | 121 codes (16.5%) |

### Répartition par archétype

| Archétype | Nb codes | % |
|-----------|:--------:|:-:|
| INDUSTRIE_LEGERE | 284 | 38.8% |
| BUREAU_STANDARD | 131 | 17.9% |
| AUTRE_TERTIAIRE | 110 | 15.0% |
| LOGISTIQUE_SEC | 69 | 9.4% |
| COMMERCE_NON_ALIMENTAIRE | 50 | 6.8% |
| HOPITAL_STANDARD | 20 | 2.7% |
| ENSEIGNEMENT | 15 | 2.0% |
| COMMERCE_ALIMENTAIRE | 13 | 1.8% |
| ADMINISTRATION | 11 | 1.5% |
| SPORT_LOISIRS | 11 | 1.5% |
| RESTAURATION_SERVICE | 7 | 1.0% |
| COPROPRIETE_LOGEMENT | 5 | 0.7% |
| HOTEL_HEBERGEMENT | 4 | 0.5% |
| LOGISTIQUE_FROID | 1 | 0.1% |
| DATA_CENTER_IT | 1 | 0.1% |

---

## Contenu de chaque archétype

Pour chacun des 15 archétypes, le JSON fournit :

1. **Benchmarks kWh/m²/an** : min, max, avg, P10, P50, P90 (sources ADEME, OID, ELMAS)
2. **Répartition des usages** : HVAC, éclairage, froid, IT, ECS, process... avec fourchettes %
3. **Signature temporelle** : heures actives, jours actifs, ratio nuit/jour, ratio weekend, pics matin/après-midi, saisonnalité
4. **Seuils d'anomalie contextualisés** : 8 seuils par archétype (base nuit, weekend, puissance pointe, saisonnalité, ratio m², gaz été)
5. **Leviers d'action** : 3-5 leviers prioritaires par archétype
6. **Métadonnées** : applicabilité DT/BACS, puissance CVC typique, clusters ELMAS, sections NAF

---

## Sources documentaires

| Source | Utilisation |
|--------|------------|
| INSEE NAF Rev2 (732 sous-classes) | Classification activités |
| ADEME Base Empreinte V23.6 | Benchmarks énergétiques tertiaire |
| ELMAS — Mines Paris (55 730 clients, 18 clusters) | Profils de charge, clusters |
| OID 2022 (25 300 bâtiments, 70M m²) | Benchmarks bureaux/tertiaire |
| AREC IDF | Benchmarks santé |
| Enertech | Benchmarks logistique, commerce |
| Uptime Institute | Benchmarks data centers (PUE) |
| CRE | Données marché énergie France |

---

## Seed HELIOS (démo)

Les 5 sites de la démo HELIOS sont recalés sur des archétypes réalistes :

| Site | NAF | Archétype |
|------|-----|-----------|
| Paris Bureaux 3500m² | 70.10Z | BUREAU_STANDARD |
| Lyon Bureaux 1200m² | 69.10Z | BUREAU_STANDARD |
| Marseille École 2800m² | 85.31Z | ENSEIGNEMENT |
| Nice Hôtel 4000m² | 55.10Z | HOTEL_HEBERGEMENT |
| Toulouse Entrepôt 6000m² | 52.10B | LOGISTIQUE_SEC |

---

## Prochaines étapes (implémentation)

Le fichier `FEAT_USAGE_KNOWLEDGE_BASE.md` détaille 4 phases :

| Phase | Description | Effort |
|-------|-------------|--------|
| **Phase 1** | Seed KB (tables + script idempotent) | 1j |
| **Phase 2** | Auto-affectation archétype (service + API) | 1j |
| **Phase 3** | Hooks patrimoine + Intake Wizard | 0.5j |
| **Phase 4** | Exploitation transversale (6 modules) | 2-3j |

**Flux cible** : SIRET → NAF (API Sirene) → archétype (KB) → profil d'usage → diagnostic contextualisé → actions personnalisées.

---

## Valeur produit

- **Zéro configuration** : l'archétype est assigné automatiquement dès la saisie du SIRET
- **Anomalies contextualisées** : un bureau qui consomme 20% la nuit est anormal ; un commerce alimentaire à 75% est normal
- **Benchmarks sectoriels** : chaque site est comparé à ses pairs (même archétype)
- **Actions pertinentes** : les recommandations sont filtrées par type d'activité
- **Conformité DT** : détection automatique de changement d'activité
