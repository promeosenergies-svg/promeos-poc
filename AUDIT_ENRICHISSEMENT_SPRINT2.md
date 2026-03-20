# Audit enrichissement site — Sprint 2 Patrimoine

> Date : 2026-03-15
> Objectif : Identifier comment enrichir un site après quick-create, et où simplifier
> Statut : Cadrage terminé, prêt à coder

---

## FAITS

### Gap principal

**Le gap est 100% frontend.** Tous les endpoints backend existent. Aucun formulaire d'édition/enrichissement de site n'existe côté UI.

### État actuel des composants

| Composant | Fichier | Cliquable | Permet d'enrichir |
|-----------|---------|-----------|-------------------|
| SiteCompletude (drawer Résumé) | `Patrimoine.jsx:1871-1913` | Non (display-only) | Non — texte + badges |
| MetricPill (Surface, Compteurs) | `Patrimoine.jsx:2074-2081` | Non | Non |
| SiteMetersTab (onglet Compteurs) | `Patrimoine.jsx:1627-1827` | Partiel | Sous-compteurs uniquement |
| Actions tab | `Patrimoine.jsx:2025-2050` | Oui | Non — navigation seulement |
| Site360 page | `Site360.jsx:109-386` | Limité | Lecture seule |

### Parcours actuels pour enrichir un site

| Action | Parcours actuel | Friction |
|--------|----------------|----------|
| Modifier SIRET | Impossible depuis l'UI | Bloquant |
| Modifier surface | Impossible depuis l'UI | Bloquant |
| Ajouter compteur principal | Aucun chemin clair | Bloquant |
| Ajouter contrat | Aucun CTA visible | Bloquant |
| Ajouter PDL | Auto seulement (via compteur) | Indirect |
| Ajouter sous-compteur | Drawer > Compteurs > expand > + | OK (4 clics) |

### API backend prêtes (zéro changement nécessaire)

| Action | Endpoint | Méthode | Prêt |
|--------|----------|---------|------|
| Modifier SIRET/surface/adresse | `/api/patrimoine/sites/{id}` | PATCH | Oui |
| Ajouter compteur | `/api/compteurs` | POST | Oui |
| Ajouter contrat | `/api/patrimoine/contracts` | POST | Oui |
| Créer bâtiment | `/api/patrimoine/crud/batiments` | POST | Oui |
| Modifier compteur (auto-crée DP) | `/api/patrimoine/compteurs/{id}` | PATCH | Oui |
| Ajouter sous-compteur | `/api/patrimoine/meters/{id}/sub-meters` | POST | Oui |

---

## HYPOTHÈSES

| # | Hypothèse | Confiance |
|---|-----------|-----------|
| H1 | L'utilisateur veut enrichir depuis le drawer, pas naviguer ailleurs | Haute |
| H2 | Rendre les lignes de complétude cliquables = impact maximal | Haute |
| H3 | 3 mini-formulaires suffisent : éditer site, ajouter compteur, ajouter contrat | Haute |
| H4 | L'ajout de DP n'a pas besoin d'UI — auto-créé via compteur | Haute |
| H5 | Le SIRET suffit pour l'association société au niveau POC | Moyenne |

---

## DÉCISIONS RECOMMANDÉES

| # | Décision | Justification |
|---|----------|---------------|
| D1 | Rendre SiteCompletude cliquable — chaque action ouvre un mini-formulaire inline | Impact max, effort min, backend prêt |
| D2 | 3 mini-formulaires : EditSiteFields, AddCompteur, AddContrat | Couvre les 5 actions de complétude |
| D3 | Tout reste dans le drawer — pas de page dédiée | Cohérent, pas de navigation |
| D4 | L'ajout PDL reste automatique via meter_id | Pas besoin d'UI dédiée |
| D5 | CTA "Ajouter un compteur" dans l'onglet Compteurs | Chemin direct pour utilisateurs avancés |

---

## FICHIERS À MODIFIER

### À modifier

| Fichier | Modification | Effort |
|---------|-------------|--------|
| `Patrimoine.jsx` — SiteCompletude | Lignes cliquables (onClick → formulaire) | S |
| `Patrimoine.jsx` — SiteDrawerContent | État formulaire actif + rendu conditionnel | S |
| `Patrimoine.jsx` — SiteMetersTab | CTA "Ajouter un compteur" en haut | S |
| **Nouveau** `DrawerEditSite.jsx` | SIRET, surface, adresse, GPS → PATCH site | M |
| **Nouveau** `DrawerAddCompteur.jsx` | Type, PRM/PCE optionnel → POST compteur | M |
| **Nouveau** `DrawerAddContrat.jsx` | Fournisseur, type, dates → POST contrat | M |

### À ne pas toucher

| Fichier | Raison |
|---------|--------|
| `QuickCreateSite.jsx` | Sprint 1 — protéger |
| `SiteCreationWizard.jsx` | Wizard avancé hors scope |
| `Site360.jsx` | Page séparée hors scope |
| Tous les endpoints backend | Déjà prêts |

---

## RISQUES

| # | Risque | Sévérité | Mitigation |
|---|--------|----------|-----------|
| R1 | Drawer trop chargé avec formulaires inline | Moyenne | Formulaires remplacent le contenu (pas en plus) |
| R2 | Utilisateur ne comprend pas que les lignes sont cliquables | Faible | Curseur pointer + icône "+" |
| R3 | Score complétude pas rafraîchi après enrichissement | Moyenne | Recharger SiteCompletude après action |
| R4 | SIRET invalide au PATCH | Faible | Validation front 14 chiffres |

---

## PLAN DE PATCH SPRINT 2

| Step | Patch | Fichier(s) | Effort | Impact |
|------|-------|-----------|--------|--------|
| **S2-1** | Complétude cliquable + formulaire édition site | `Patrimoine.jsx`, `DrawerEditSite.jsx` | M | Débloque SIRET + surface + GPS |
| **S2-2** | Formulaire ajout compteur depuis drawer | `DrawerAddCompteur.jsx`, `Patrimoine.jsx` | M | Débloque PDL (auto via meter_id) |
| **S2-3** | Formulaire ajout contrat depuis drawer | `DrawerAddContrat.jsx`, `Patrimoine.jsx` | M | Débloque action contrat |
| **S2-4** | CTA "Ajouter compteur" dans onglet Compteurs | `Patrimoine.jsx` SiteMetersTab | S | Chemin alternatif |
| **S2-5** | Validation + tests + commit | Tests + build | S | Stabilisation |

### Point d'attaque recommandé

**S2-1** : rendre SiteCompletude cliquable + créer DrawerEditSite.jsx.

Ratio impact/effort le plus fort : 1 composant nouveau + quelques lignes dans SiteCompletude = 3 actions de complétude débloquées (SIRET, surface, GPS).
