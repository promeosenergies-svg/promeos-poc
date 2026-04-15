# Audit ciblé — Flux de création Patrimoine (Sprint 1)

> Date : 2026-03-15
> Objectif : Identifier les points exacts à modifier pour un quick-create centré sur le site
> Statut : Cadrage terminé, prêt à coder

---

## FAITS

### 1. Point d'entrée actuel

| Élément | Fichier | Ligne | Détail |
|---------|---------|-------|--------|
| CTA principal | `pages/Patrimoine.jsx` | 686-689 | `"Nouveau site"` → ouvre `QuickCreateSite` |
| State quick-create | `pages/Patrimoine.jsx` | 170 | `showQuickCreate` state |
| State wizard ancien | `pages/Patrimoine.jsx` | 169 | `showSiteWizard` state — **orphelin, aucun CTA n'y pointe** |
| Render quick-create | `pages/Patrimoine.jsx` | 1575-1580 | `<QuickCreateSite onSuccess={() => window.location.reload()} />` |
| Render wizard ancien | `pages/Patrimoine.jsx` | 1581-1586 | `<SiteCreationWizard />` — monté mais inaccessible |
| Empty state | `pages/Patrimoine.jsx` | 698-711 | Propose uniquement « Importer » — pas de création rapide |

### 2. Deux chemins de création coexistent

| Chemin | Endpoint | PF requis | Auto-provision | Auto-org | Anti-doublons |
|--------|----------|-----------|----------------|----------|---------------|
| **QuickCreateSite** | `POST /api/sites/quick-create` | Non (auto) | Oui | Oui | Oui (nom+CP) |
| **SiteCreationWizard** | `POST /patrimoine/crud/sites` | **Oui (bloquant)** | **Non** | Non | Non |
| **createSite ancien** | `POST /api/sites` | Non (auto) | Oui | Non (400) | Non |

Point critique : le CRUD endpoint (`patrimoine/crud/sites`) ne provisionne ni bâtiment ni obligations.

### 3. Chaîne de dépendances

```
Organisation (obligatoire en DB)
  └─ EntiteJuridique (FK org_id NOT NULL, SIREN NOT NULL unique)
       └─ Portefeuille (FK entite_juridique_id NOT NULL)
            └─ Site (FK portefeuille_id — requis par schema CRUD, auto-résolu par quick-create)
                 ├─ Bâtiment (auto-créé par provision_site)
                 └─ Compteur (ajout séparé)
```

### 4. Validations bloquantes par endpoint

| Validation | quick-create | patrimoine/crud/sites | Problème |
|------------|-------------|----------------------|----------|
| `nom` vide | Bloque (légitime) | Bloque (légitime) | Aucun |
| `type` absent | Défaut `bureau` | **Bloque** | Excessif |
| `portefeuille_id` absent | Auto-résolu | **Bloque** | Excessif |
| SIREN 9 chiffres | Non requis | **Bloque** (wizard étape 2) | Bloque l'onboarding |

### 5. Comportement « 1 site = 1 bâtiment »

| Chemin | Bâtiment auto-créé | Mécanisme | Fichier |
|--------|-------------------|-----------|---------|
| quick-create | Oui | `provision_site()` → `create_batiment_for_site()` | `onboarding_service.py:82-93` |
| patrimoine/crud/sites | **Non** | Aucun appel à `provision_site()` | `patrimoine_crud.py:415-434` |

Auto-génération bâtiment :
- nom = "Batiment principal"
- surface = site.surface_m2 ou 1000 m²
- cvc_power_kw = estimation W/m² par usage

### 6. Portefeuille imposé à tort

| Fichier | Ligne | Contrainte |
|---------|-------|-----------|
| `schemas/patrimoine_crud.py` | 90 | `portefeuille_id: int` requis, pas de default |
| `SiteCreationWizard.jsx` | 40 | Étape 3 obligatoire dans le wizard |
| `SiteCreationWizard.jsx` | 772 | `canProceed` bloque si pas de PF |
| `SiteCreationWizard.jsx` | 834-841 | Crée PF avant le site |

Le quick-create contourne en auto-résolvant/créant le PF.

### 7. Fichiers impliqués

#### Backend

| Fichier | Rôle | État |
|---------|------|------|
| `routes/sites.py` | Endpoint quick-create | Créé (commit 72b159a) |
| `routes/patrimoine_crud.py` | CRUD sites (wizard) | Inchangé |
| `services/onboarding_service.py` | `provision_site`, `create_site_from_data`, `create_organisation_full` | Inchangé, réutilisé |
| `schemas/patrimoine_crud.py` | Schema SiteCreate | Inchangé |

#### Frontend

| Fichier | Rôle | État |
|---------|------|------|
| `components/QuickCreateSite.jsx` | Modal création rapide 1 écran | Créé (commit 72b159a) |
| `components/SiteCreationWizard.jsx` | Wizard 7 étapes | Inchangé — **orphelin** |
| `pages/Patrimoine.jsx` | Page principale | Modifié — CTA pointe vers QuickCreate |
| `services/api.js` | `quickCreateSite()` | Ajouté |

---

## HYPOTHÈSES

| # | Hypothèse | Impact |
|---|-----------|--------|
| H1 | Le wizard 7 étapes n'est plus accessible via aucun chemin UI | Peut rester en code mort, à confirmer |
| H2 | L'empty state devrait proposer « Nouveau site » en plus d'« Importer » | Premier contact limité à l'import |
| H3 | Le SIREN "000000000" auto-créé posera problème si 2 quick-create sans org | Contrainte UNIQUE(siren) sur entites_juridiques bloquera |
| H4 | `window.location.reload()` est brutal mais fonctionnel pour le POC | Refresh ciblé = optimisation future |

---

## DÉCISIONS RECOMMANDÉES

| # | Décision | Justification |
|---|----------|---------------|
| D1 | Garder quick-create comme chemin principal | Fonctionnel, testé, committé |
| D2 | Rebrancher le wizard via lien « Création avancée » | Ne pas perdre le cas multi-entités |
| D3 | Ajouter « Nouveau site » dans l'empty state | Premier contact = création immédiate |
| D4 | Ne PAS toucher au CRUD endpoint ni au schema | Risque de régression, gain nul |
| D5 | Gérer le SIREN "000000000" dupliqué | Réutiliser org+EJ existante au lieu de recréer |

---

## FICHIERS À MODIFIER

### À modifier (Sprint 1 restant)

| Fichier | Modification | Effort | Risque |
|---------|-------------|--------|--------|
| `routes/sites.py` L79-102 | Fix SIREN dupliqué — réutiliser org/EJ existante | S | Faible |
| `pages/Patrimoine.jsx` L698-711 | Ajouter CTA « Nouveau site » dans l'empty state | S | Nul |
| `components/QuickCreateSite.jsx` | Ajouter lien « Création avancée » | S | Nul |
| `pages/Patrimoine.jsx` | Brancher lien vers `setShowSiteWizard(true)` | S | Nul |

### À NE PAS toucher

| Fichier | Raison |
|---------|--------|
| `SiteCreationWizard.jsx` | Fonctionne, ne rien casser |
| `schemas/patrimoine_crud.py` | Ne pas changer le schema CRUD |
| `services/onboarding_service.py` | Stable, réutilisé tel quel |
| `routes/patrimoine_crud.py` | Le wizard l'utilise |

---

## RISQUES

| # | Risque | Sévérité | Mitigation |
|---|--------|----------|-----------|
| R1 | SIREN "000000000" dupliqué → crash IntegrityError si 2 quick-create sans org existante | **Haute** | Vérifier EJ existante avant create_organisation_full() |
| R2 | Wizard orphelin → confusion développeur futur | Faible | Ajouter lien « Création avancée » |
| R3 | Empty state ne propose pas la création rapide | Moyenne | Ajouter CTA |
| R4 | `window.location.reload()` lent sur gros patrimoine | Faible | Acceptable POC |

---

## PLAN DE PATCH SPRINT 1

Le gros du travail est déjà fait (commit `72b159a`). Il reste 4 micro-patchs :

| # | Patch | Fichier(s) | Effort | Priorité |
|---|-------|-----------|--------|----------|
| **P1** | Fix SIREN "000000000" dupliqué — réutiliser org+EJ existante | `routes/sites.py` L79-102 | S | **Bloquant** |
| **P2** | Ajouter « Nouveau site » dans l'empty state | `pages/Patrimoine.jsx` L698-711 | S | Important |
| **P3** | Ajouter lien « Création avancée » dans QuickCreateSite | `QuickCreateSite.jsx` + `Patrimoine.jsx` | S | Confort |
| **P4** | Renommages UI si wizard rebranché | `SiteCreationWizard.jsx` L38-40, 89, 112, 644 | S | Cosmétique |

**Ordre recommandé :** P1 → P2 → P3 → P4

**Point d'entrée le plus simple :** Le quick-create est déjà le chemin principal. Le seul bug latent est P1 (SIREN dupliqué). C'est le premier patch à coder.
