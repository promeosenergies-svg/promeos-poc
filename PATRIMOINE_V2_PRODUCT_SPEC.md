# PROMEOS — Patrimoine V2 : Spécification Produit

> Date : 2026-03-15
> Statut : Proposition validée, prête pour sprint
> Périmètre : UX / structure métier / parcours — pas de refactor technique profond

---

## 1. Verdict produit

Le module Patrimoine expose le modèle de données au lieu du métier. Le wizard 7 étapes reproduit la hiérarchie technique (Org → Entité Juridique → Portefeuille → Site → Bâtiment → Compteur) alors que l'utilisateur pense « j'ai un site à ajouter ». Le Portefeuille est un concept sans réalité métier pour 80% des utilisateurs. L'import propose 4 modes dont la différence est floue.

**Ce qui change maintenant :**
- Le site devient l'objet d'entrée unique
- La hiérarchie juridique est auto-générée ou reportée
- Le Portefeuille devient un regroupement facultatif
- L'import passe de 4 à 2 modes (auto-détectés)

---

## 2. Faits (acquis dans le POC)

- Modèle de données complet B2B France : SIREN, SIRET, NAF, décret tertiaire, BACS, OPERAT, PRM/PCE
- `provision_site()` auto-crée 1 bâtiment + obligations → « 1 site = 1 bâtiment » existe côté backend
- Soft-delete unifié et cohérent (lot correctif livré, 1255 tests OK)
- Pipeline d'import staging robuste (QA, corrections, activation)
- DeliveryPoint séparé du Compteur (PRM/PCE clean)
- Geocoding BAN intégré, classification NAF automatique
- Compliance scoring composite automatique à la création
- Filtres URL-synced, vue table + carte, drawer site 4 onglets, KPIs patrimoine

---

## 3. Hypothèses

| # | Hypothèse | Confiance |
|---|-----------|-----------|
| H1 | 70-80% des premiers usages = 1 org, 1-5 sites, parcours simple | Haute |
| H2 | L'utilisateur pense « site » pas « entité juridique » | Haute |
| H3 | « Portefeuille » est incompris (confusion financière) | Moyenne |
| H4 | Les energy managers experts acceptent un mode avancé séparé | Haute |
| H5 | Express + Complet couvrent 95% des besoins ; Assisté et Demo = marginaux | Moyenne |
| H6 | Le SIREN est rarement connu au moment de la création rapide | Moyenne |
| H7 | Le cas multi-SIREN concerne <15% des utilisateurs au démarrage | Haute |
| H8 | Un site sans compteur a de la valeur (conformité, obligations, cartographie) | Haute |

---

## 4. Décisions produit

| # | Décision | Justification |
|---|----------|---------------|
| D1 | **Le Site est l'objet pivot d'entrée** | Unité mentale de l'utilisateur |
| D2 | **1 site = 1 bâtiment par défaut** (natif) | `provision_site()` le fait déjà |
| D3 | **Portefeuille → tag/regroupement facultatif**, retiré du flux de création | Zéro valeur en création |
| D4 | **Org + Entité Juridique auto-créées** si inexistantes | SIREN ne doit pas bloquer |
| D5 | **Création rapide = 1 formulaire, 1 étape, 5 champs** | Nom, type, adresse, ville, CP |
| D6 | **Import simplifié à 2 modes** : Express + Complet (auto-détecté) | Demo = bouton séparé. Assisté = roadmap. |
| D7 | **Compteurs ajoutables depuis la fiche site**, pas dans le wizard | Découplage création / enrichissement |
| D8 | **Enrichissement progressif** = barre complétude actionnable sur fiche site | Score existant, mais drill-down manquant |
| D9 | **SIREN/SIRET facultatif** à la création, requis pour conformité/OPERAT | Ne bloque pas l'onboarding |
| D10 | **Multi-entité = mode expert** via « Structure juridique » | Pas dans le parcours simple |

---

## 5. Modèle cible Patrimoine V2

### Architecture 3 couches

```
┌─────────────────────────────────────────────────────┐
│  COUCHE JURIDIQUE (enrichissable, pas bloquante)    │
│                                                     │
│  Société (Organisation)                             │
│    └─ Entité juridique (SIREN)                      │
│         └─ Établissement (SIRET) ← lien au Site     │
│                                                     │
│  Regroupement (ex-Portefeuille) ← tag facultatif    │
│  Responsabilités : propriétaire, occupant,          │
│                    gestionnaire, exploitant          │
├─────────────────────────────────────────────────────┤
│  COUCHE PHYSIQUE (pivot, entrée utilisateur)        │
│                                                     │
│  Site ★ (objet pivot)                               │
│    ├─ Bâtiment (auto-créé, 1:1 défaut, N possible)  │
│    └─ Localisation (adresse, GPS, commune)           │
├─────────────────────────────────────────────────────┤
│  COUCHE ÉNERGÉTIQUE (ajout progressif)              │
│                                                     │
│  Point de livraison (PRM/PCE)                       │
│    └─ Compteur (appareil physique)                  │
│  Contrat énergie                                    │
│  Consommation                                       │
└─────────────────────────────────────────────────────┘
```

### Objets : obligatoire vs facultatif vs auto-généré

| Objet | À la création | Enrichissement | Auto-généré |
|-------|--------------|----------------|-------------|
| **Site** | ✅ Obligatoire (nom + usage) | Adresse, surface, SIRET, NAF | Type via NAF si connu |
| **Société** | Auto-créée si absente | Nom, SIREN, type_client | « Mon entreprise » par défaut |
| **Entité juridique** | Auto-créée (1:1 société) | SIREN, SIRET siège, NAF | Hérite nom société |
| **Bâtiment** | Auto-créé | Surface, année, CVC | Surface = site, CVC estimée |
| **Regroupement** | ❌ Facultatif | Nom, description | Aucun |
| **Point de livraison** | ❌ Facultatif | PRM/PCE 14 chiffres | Auto si compteur a meter_id |
| **Compteur** | ❌ Facultatif | Type, n° série, puissance | N° série auto-généré |
| **Contrat** | ❌ Facultatif | Fournisseur, dates, prix | Aucun |
| **Obligations** | Auto-créées | Type, échéance, statut | Depuis type site + CVC |

### Réponses structurantes

- **Le site EST l'objet pivot** → OUI
- **1 site = 1 bâtiment est natif** → OUI
- **Portefeuille est obligatoire** → NON (tag facultatif « Regroupement »)

---

## 6. Parcours cibles

### Parcours A — Création rapide

> PME, DAF, DG, démo client — **< 30 secondes**

| Étape | Action |
|-------|--------|
| 1 | Clic « + Nouveau site » (CTA principal) |
| 2 | Formulaire 1 écran : nom, usage, adresse, CP, ville |
| 3 | Clic « Créer » → site visible immédiatement |

**Auto-généré :** Société, Entité juridique, Regroupement, Bâtiment principal, Obligations, Compliance score.

**Valeur immédiate :** Site dans cockpit + cartographie + KPIs + obligations calculées.

**Section « Plus de détails » (pliée) :** Surface, SIRET, NAF, coordonnées GPS, surface tertiaire.

### Parcours B — Création avancée

> Energy manager, property manager — patrimoine multi-entités

| Étape | Action |
|-------|--------|
| 1 | Patrimoine > « Structure juridique » |
| 2 | Créer/sélectionner société (SIREN) |
| 3 | Créer/sélectionner entité juridique (SIREN obligatoire ici) |
| 4 | Créer site(s) rattaché(s) (formulaire complet) |
| 5 | Ajouter bâtiments depuis la fiche site |
| 6 | Ajouter compteurs / PDL depuis la fiche site |

### Parcours C — Import express

> Tout profil avec un fichier — **< 2 minutes**

| Étape | Action |
|-------|--------|
| 1 | Clic « Importer » |
| 2 | Drag & drop CSV/Excel |
| 3 | Aperçu automatique (colonnes détectées, 5 premières lignes) |
| 4 | Clic « Importer » → création directe |

**Seul champ requis dans le fichier :** nom.
**Si erreurs détectées :** bascule automatique vers Import complet.

### Parcours D — Import complet

> Energy manager, intégrateur — base structurée + QA

| Étape | Action |
|-------|--------|
| 1 | Upload fichier |
| 2 | Aperçu + score qualité (grade A/B/C/D) |
| 3 | Corrections (individuelles ou auto-fix) |
| 4 | Validation + activation |
| 5 | Résultat (comptage, erreurs résiduelles) |

**S'active automatiquement** quand l'import express détecte > 3 findings.

### Parcours E — Enrichissement progressif

> Tout profil, retour sur un site existant

| Étape | Action |
|-------|--------|
| 1 | Ouvrir la fiche site |
| 2 | Voir la barre de complétude (« 40% — Ajoutez un compteur pour voir vos consommations ») |
| 3 | Compléter section par section |
| 4 | Chaque ajout recalcule obligations + conformité + score |

**Sections :** Identité, Localisation, Bâtiments, Énergie, Juridique, Regroupement.

---

## 7. Libellés B2B France

### Renommages recommandés

| Actuel | Recommandé | Raison |
|--------|-----------|--------|
| Organisation | **Société** | Terme usuel B2B France |
| Portefeuille | **Regroupement** | Évite confusion financière |
| Type (de site) | **Usage** | Vocabulaire réglementaire (décret tertiaire) |
| Activation (import) | **Créer les sites** | Jargon technique → action claire |

### À conserver tel quel

Site, Bâtiment, Compteur, Point de livraison (PDL), Entité juridique, Contrat énergie.

### À éviter dans l'UI

Portfolio, Staging, Batch, PRM/PCE seul (toujours accompagner de « Point de livraison »).

---

## 8. Recommandations UX/UI

### Structure écran — Page Patrimoine V2

```
┌──────────────────────────────────────────────────────┐
│  [+ Nouveau site]  [Importer]     🔍 Recherche...   │
├──────────────────────────────────────────────────────┤
│  Filtres : Usage ▾  Statut ▾  Regroupement ▾        │
│  Presets : [Tous] [À risque] [Incomplets]            │
├──────────────────────────────────────────────────────┤
│  KPIs : Sites │ PDL │ Contrats │ Conformité │ Compl. │
├──────────────────────────────────────────────────────┤
│  [Tableau ◉] [Carte ○]                              │
│  Nom         Usage   Ville   Compl.   Conformité     │
│  Bureau Lyon Bureau  Lyon    ████ 85%  ✓ Conforme    │
│  Usine Dijon Usine   Dijon   ██░░ 45%  ⚠ À risque   │
└──────────────────────────────────────────────────────┘
```

### CTA principaux

| CTA | Position | Style |
|-----|----------|-------|
| **+ Nouveau site** | Header gauche | Primary (bleu plein) |
| **Importer** | Header, après Nouveau site | Secondary (outline) |
| **Structure juridique** | Sous-nav Patrimoine | Lien texte |

### Simple vs Expert

| Aspect | Simple (défaut) | Expert |
|--------|----------------|--------|
| Création site | 1 formulaire, 5 champs | Via « Structure juridique » |
| Hiérarchie | Transparente (auto-créée) | Visible et éditable |
| Bâtiments | Auto-créé, éditable | Multi-bâtiments explicite |
| Regroupement | Absent | Tag sur les sites |
| Import | Express (auto-fallback complet) | Complet avec QA |

### Auto-remplissage

| Champ | Source |
|-------|--------|
| Société | ScopeContext org courante |
| Entité juridique | Auto-créée = société |
| Usage | `classify_naf(naf_code)` si NAF fourni |
| Surface tertiaire | = surface_m2 si type tertiaire |
| Bâtiment | « Bâtiment principal », surface = site |
| CVC puissance | Estimation W/m² par usage |
| GPS | Geocoding BAN si adresse + CP |
| Obligations | Décret tertiaire + BACS selon type + surface + CVC |

### Gestion des erreurs

| Situation | Comportement |
|-----------|-------------|
| Nom vide | Bordure rouge inline |
| SIREN invalide | Validation live « 9 chiffres requis » |
| Doublon détecté | Toast warning + lien vers l'existant |
| Import : fichier invalide | Message + téléchargement template |
| Import : erreurs QA | Bascule auto vers mode complet |
| Champ manquant pour conformité | Badge « Incomplet » + suggestion |

---

## 9. Import — Repositionnement

### Avant : 4 modes explicites

| Mode | Verdict |
|------|---------|
| Express | ✅ Garder |
| Import complet | ✅ Garder, mais pas comme choix séparé |
| Assisté | ❌ Retirer — roadmap future |
| Demo | ❌ Sortir de l'import — bouton séparé |

### Après : 1 entrée, auto-détection

```
Clic "Importer" → Drag & drop → Analyse auto
    │                                │
    ├── 0 erreur, QA = A ─────── Import rapide (création directe)
    │
    └── Erreurs détectées ─────── Import avec vérification (preview + corrections)
```

**Demo** : bouton séparé dans l'empty state.
**Assisté** : retiré de l'UI.

---

## 10. Gap Analysis

| # | Sujet | Actuel | Cible V2 | Priorité |
|---|-------|--------|----------|----------|
| 1 | Création site | Wizard 7 étapes | Formulaire 1 étape, 5 champs | **P0** |
| 2 | Portefeuille | Obligatoire dans la chaîne | Tag facultatif « Regroupement » | **P0** |
| 3 | Auto-création hiérarchie | Manuelle étape par étape | Société + EJ + PF auto si absents | **P0** |
| 4 | Import : choix mode | 4 modes explicites | 1 entrée, auto-détection | **P1** |
| 5 | Fiche site | Drawer 4 onglets | Page complète, sections enrichissables | **P1** |
| 6 | Barre complétude | KPI global % | Drill-down par champ + suggestion action | **P1** |
| 7 | Détection doublons | Absente | Alerte nom+CP, SIRET à l'import | **P2** |
| 8 | Libellés | Organisation, Portefeuille, Type | Société, Regroupement, Usage | **P2** |
| 9 | Import Demo | Dans le wizard 4 modes | Bouton séparé empty state | **P2** |
| 10 | Structure juridique | Mélangée dans le wizard | Vue dédiée sous-nav | **P2** |
| 11 | Rôles | Non implémenté | Métadonnées sur fiche site | **P3** |

---

## 11. Roadmap 30 jours

### Semaine 1 — Création rapide + auto-hiérarchie

- **J1-J2** : Backend — endpoint `/api/sites/quick-create` avec auto-création Société + EJ + PF
- **J3-J4** : Frontend — formulaire 1-étape remplaçant le wizard 7 étapes
- **J5** : Détection doublons basique (nom + code_postal)

### Semaine 2 — Import simplifié + fiche site

- **J6-J7** : Frontend — import unifié (1 drag & drop, auto-détection express/complet)
- **J8-J9** : Frontend — sortir Demo du wizard import, bouton séparé
- **J10** : Frontend — fiche site enrichie avec sections pliables + indicateur complétude

### Semaine 3 — Enrichissement progressif + libellés

- **J11-J12** : Barre complétude actionnable avec suggestions concrètes
- **J13-J14** : Renommage UI (Organisation → Société, Portefeuille → Regroupement, Type → Usage)
- **J15** : Portefeuille rendu facultatif (auto-créé « Principal », transparent)

### Semaine 4 — Structure juridique + polish

- **J16-J17** : Vue « Structure juridique » (arborescence Société > Entités > Sites)
- **J18-J19** : Tests E2E sur les 5 parcours (A-E)
- **J20** : Polish UX (empty states, messages d'erreur, responsive)

---

## 12. Top 5 actions

| # | Action | Effort | Owner | Deadline | Impact |
|---|--------|--------|-------|----------|--------|
| 1 | Endpoint `/api/sites/quick-create` + formulaire 1-étape | M | Back + Front | S1 | Time-to-first-site : 3 min → 30 sec |
| 2 | Import unifié 1 entrée (auto-détection express/complet) | S | Frontend | S2 | Confusion import éliminée |
| 3 | Portefeuille transparent (auto « Principal », masqué en création) | S | Back + Front | S3 | 1 étape supprimée, friction 0 |
| 4 | Barre complétude actionnable sur fiche site | M | Front + Back | S3 | Enrichissement guidé, rétention |
| 5 | Renommage Organisation → Société, Portefeuille → Regroupement, Type → Usage | S | Frontend | S3 | Compréhension immédiate B2B France |

---

## Annexe : Lien aux briques actives

Le Patrimoine V2 reste la colonne vertébrale. Chaque simplification UX préserve les données nécessaires aux autres briques :

| Brique | Données requises du Patrimoine | Impacté par V2 ? |
|--------|-------------------------------|-------------------|
| **Conformité** | Site (type, surface, CVC), Obligations | Non — auto-générées |
| **Achat énergie** | PDL (PRM/PCE), Contrats, Sites | Non — enrichissement progressif |
| **Facturation / Shadow billing** | Compteurs, PDL, Contrats | Non — ajout depuis fiche site |
| **EMS / Pilotage** | Compteurs, Consommations | Non — découplé de la création |
| **Cockpit exécutif** | KPIs agrégés Sites | Non — même données, meilleur accès |
