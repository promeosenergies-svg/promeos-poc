# PROMEOS - Navigation Copy Spec V3.4 DIAMANT

## Objectif

Labels de navigation "enterprise-grade", lisibles par DG, DAF, directeur immobilier et energy manager. Orientation valeur, pas technique.

## Principes

1. **Capitalisation** : 1re lettre majuscule, reste minuscule. Ex: "Plan d'actions", "Veille".
2. **Accents** : toujours corrects, jamais de sequences unicode echappees dans le code source.
3. **Pluriel** : utiliser le pluriel quand le contexte est multi-objets (Consommations, Imports, Connexions).
4. **Pas de "&"** dans les menus. Remplacer par un mot unique ou reformuler.
5. **Longueur** : 1-2 mots dans le menu lateral, version longue possible en H1.
6. **Langue** : francais, professionnel, sans jargon technique inutile.
7. **Coherence** : le label Sidebar, le Breadcrumb et le H1 doivent se correspondre.
8. **Sous-titres** : chaque page a un sous-titre descriptif sous le H1 (1 ligne, style `text-sm text-gray-500`).

## Sections de navigation

| Section | Usage |
|---------|-------|
| **Pilotage** | Vue d'ensemble, decisions, synthese |
| **Execution** | Actions concretes, conformite |
| **Analyse** | Donnees, diagnostics, couts |
| **Administration** | Configuration, import, referentiels |

## Dictionnaire des termes V3.4

| Label menu | H1 page | Sous-titre | Route canonique | Aliases |
|-----------|---------|------------|-----------------|---------|
| Tableau de bord | Tableau de bord | Synthese 2 minutes : conformite, pertes, actions | `/` | `/dashboard` |
| Vue executive | Vue executive | KPIs portefeuille & priorites multi-sites | `/cockpit` | `/synthese`, `/executive` |
| Conformite | Conformite reglementaire | - | `/conformite` | `/compliance` |
| Plan d'actions | Plan d'actions | - | `/actions` | `/plan-action`, `/plan-actions` |
| Patrimoine | Patrimoine | - | `/patrimoine` | - |
| Consommations | Consommations | - | `/consommations` | `/conso` |
| Diagnostic | Diagnostic | Detection automatique : horaires, talon, pointes, derives | `/diagnostic-conso` | `/anomalies`, `/diagnostic` |
| Facturation | Facturation | Shadow billing, TURPE/ATRD/ATRT, ecarts & anomalies | `/bill-intel` | `/factures`, `/facturation` |
| Achats energie | Achats energie | Simuler & arbitrer vos strategies d'achat | `/achat-energie` | `/achats`, `/purchase` |
| Performance | Performance | KPIs, puissance, qualite de donnees & alertes | `/monitoring` | `/performance` |
| Imports | Imports | Fichiers, CSV, historiques & controles | `/import` | `/imports` |
| Connexions | Connexions | Sources : Enedis, GRDF, fournisseurs, GTB, IoT | `/connectors` | `/connexions` |
| Segmentation | Segmentation | - | `/segmentation` | - |
| Veille | Veille | Reglementaire & marche : alertes et syntheses | `/watchers` | `/veille` |
| Referentiels | Referentiels | Regles, grilles, modeles & dictionnaires | `/kb` | `/referentiels` |

## Changelog V3.3 → V3.4

| Ancien (V3.3) | Nouveau (V3.4) | Raison |
|---------------|----------------|--------|
| Synthese | Vue executive | Plus clair pour C-level |
| Plan d'action | Plan d'actions | Pluriel coherent (multi-actions) |
| Detection d'anomalies | Diagnostic | Plus court, plus pro |
| Import | Imports | Pluriel coherent |
| Sources de donnees | Connexions | Plus court, orientation integration |
| Veille reglementaire | Veille | Plus court, scope elargi (marche + reglementaire) |

## Aliases ajoutes en V3.4

| Alias | Redirige vers |
|-------|---------------|
| `/plan-actions` | `/actions` |
| `/diagnostic` | `/diagnostic-conso` |
| `/purchase` | `/achat-energie` |
| `/executive` | `/cockpit` |
| `/dashboard` | `/` |
| `/conso` | `/consommations` |
| `/imports` | `/import` |
| `/connexions` | `/connectors` |
| `/veille` | `/watchers` |

## Exemples menu vs H1

- Menu: **Facturation** / H1: **Facturation** (court = long)
- Menu: **Vue executive** / H1: **Vue executive** (renomme depuis Synthese)
- Menu: **Imports** / H1: **Imports** (pluriel coherent)
- Menu: **Conformite** / H1: **Conformite reglementaire** (menu court, H1 complet)
- Menu: **Diagnostic** / H1: **Diagnostic** (simplifie depuis Detection d'anomalies)

## Anti-patterns a eviter

- "Factures & ecarts" -> trop long, "&" interdit -> **Facturation**
- "Performance & suivi" -> trop long -> **Performance**
- "Regles & referentiels" -> trop long -> **Referentiels**
- "Importer des fichiers" -> verbe dans le menu -> **Imports**
- "Connecter des sources" -> verbe dans le menu -> **Connexions**
- "Achat Energie" -> singulier + majuscule superflue -> **Achats energie**
- Sequences `\u00e9` dans le code -> utiliser le caractere accentue directement
- "Sources de donnees" -> trop long -> **Connexions**
- "Veille reglementaire" -> trop long, scope restreint -> **Veille**
