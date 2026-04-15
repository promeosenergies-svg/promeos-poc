# BRIEF V1.3 — Usages Énergétiques Premium

**Date** : 2026-03-14
**Statut V1.2** : Crédible, structurée, démontrable
**Objectif V1.3** : Granularité zone/compteur, export preuve, multi-sites

---

## 1. Zones fonctionnelles (priorité haute)

### Ce qui est prêt
- Modèle `Usage` avec `batiment_id`, `type`, `surface_m2`, `pct_of_total`
- Lien `Meter.usage_id` → permet de rattacher un sous-compteur à un usage

### Ce qui manque
- **Zone physique** : un usage peut couvrir plusieurs zones (ex: CVC couvre tout un bâtiment, éclairage couvre un étage). Le modèle actuel n'a pas de notion de "zone" (étage, aile, local technique).
- **Plan de comptage visuel** : la V1.2 affiche un arbre texte. Il faudrait un schéma interactif (synoptique simplifié) montrant compteur principal → sous-compteurs → usages → zones.

### Sprint suivant
- Ajouter un modèle `Zone` (optionnel) avec `batiment_id`, `etage`, `surface_m2`, `type_zone`
- Lier `Usage.zone_id` (nullable, migration non-breaking)
- Enrichir le plan de comptage avec un mode visuel (SVG ou canvas simplifié)

---

## 2. Couverture de comptage (priorité haute)

### Ce qui est prêt
- Couverture calculée par compteur principal : `sub_kwh / principal_kwh × 100`
- Readiness pénalise si couverture < 50%
- Affichage par compteur dans le plan de comptage

### Ce qui manque
- **Couverture globale site** : moyenne pondérée par kWh de chaque compteur principal (pas une simple moyenne)
- **Couverture par vecteur** : distinguer élec vs gaz vs chaleur
- **Alerte couverture dégradée** : si un sous-compteur perd ses readings, la couverture baisse mais personne n'est alerté
- **Historique couverture** : évolution de la couverture dans le temps

### Sprint suivant
- Ajouter `global_coverage_pct` pondéré dans `get_metering_plan`
- Ventiler par vecteur énergétique
- Ajouter un insight automatique `type=couverture_degradee` si coverage < seuil

---

## 3. Usage ↔ Zone ↔ Point de mesure (priorité moyenne)

### Ce qui est prêt
- `Meter → Usage` (via `usage_id`)
- `Usage → Batiment` (via `batiment_id`)
- Groupement par `TypeUsage` dans top UES, coût, compliance

### Ce qui manque
- **Traçabilité inverse** : depuis un usage, lister tous les points de mesure qui contribuent
- **Multi-source par usage** : un usage peut avoir un sous-compteur ET un complément estimé
- **Confidence score** : si 80% mesuré + 20% estimé, afficher le niveau de confiance

### Sprint suivant
- Endpoint `GET /api/usages/{usage_id}/sources` retournant la liste des Meters + leur contribution
- Ajouter un champ `confidence_pct` calculé dans les baselines

---

## 4. Export preuve sérieux (priorité haute)

### Ce qui est prêt
- Bouton "Exporter / Imprimer" qui appelle `window.print()`
- Données complètes en JSON via l'API

### Ce qui manque
- **Export PDF structuré** : dossier preuve avec header site, période, baselines, écarts, conformité, plan de comptage — format opposable pour audit BACS ou Décret Tertiaire
- **Export CSV/Excel** : données brutes pour les energy managers
- **Horodatage + signature** : preuve que les données ont été générées à date T

### Sprint suivant
- Endpoint `GET /api/usages/{site_id}/export?format=pdf` utilisant weasyprint ou reportlab
- Endpoint `GET /api/usages/{site_id}/export?format=csv`
- Inclure un hash SHA256 des données dans le PDF pour l'intégrité

---

## 5. Lecture multi-sites / portefeuille (priorité moyenne)

### Ce qui est prêt
- `ScopeContext` gère org/site
- Chaque endpoint est paramétré par `site_id`
- La page affiche correctement "Sélectionnez un site" si aucun site choisi

### Ce qui manque
- **Vue portfolio usages** : voir les top usages agrégés sur tous les sites d'une org
- **Benchmark inter-sites** : comparer l'IPE d'un usage entre sites (ex: éclairage Lyon vs Paris)
- **Heatmap usages × sites** : matrice visuelle des usages par site avec code couleur performance

### Sprint suivant
- Endpoint `GET /api/usages/portfolio/{org_id}` agrégeant les top UES multi-sites
- Composant `UsagesPortfolioView` avec mode "comparaison" et "agrégation"
- Intégration dans le cockpit portfolio existant

---

## Ordre de priorité recommandé

| # | Chantier | Effort | Impact démo | Impact métier |
|---|----------|--------|-------------|---------------|
| 1 | Export preuve PDF/CSV | 2-3j | Fort | Critique (audit) |
| 2 | Couverture globale pondérée + par vecteur | 1j | Fort | Fort |
| 3 | Zones fonctionnelles (modèle + lien) | 2j | Moyen | Fort |
| 4 | Usage ↔ sources + confidence | 1-2j | Moyen | Moyen |
| 5 | Vue portfolio multi-sites | 2-3j | Fort | Moyen |

---

## Ce qui est déjà premium (acquis V1.2)

- Readiness score 0-100 avec recommandations
- Plan de comptage hiérarchique avec couverture %
- Baselines avant/après avec tendances et résumé exécutif
- Coût par usage ventilé et normalisé
- Conformité dédupliquée (BACS + DT + ISO)
- Liens cross-briques (facture, contrat, achat, conformité, diagnostic)
- Source de données explicite (Mesuré / Estimé / Baseline)
- 5 587 tests frontend sans régression
