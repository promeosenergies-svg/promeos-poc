# PROMEOS — Audit UX / Architecture / Logique Metier

**Date :** 2026-03-27
**Auditeur :** Claude Opus 4.6 (audit automatise)
**Perimetre :** Frontend React (src/), Backend FastAPI (backend/), Demo pack Groupe HELIOS

---

## Resume executif

PROMEOS est une application mature avec une architecture bien structuree et un design system coherent. Le projet a atteint un niveau de qualite notable apres 110+ sprints. Les forces principales sont : la separation claire des couches (models purs, hooks, composants display-only), un glossaire pedagogique riche (40+ termes), et une gestion robuste des etats (loading, error, empty). Les principaux axes d'amelioration concernent la taille excessive de certains fichiers (MonitoringPage : 3112 lignes), des accents manquants dans les labels conformite, et une incoherence sur l'objectif trajectoire DT entre les pages.

### Scores globaux

| Categorie | Score | Tendance |
|---|---|---|
| UX / UI | **74 / 100** | Bon design system, responsive partiel |
| Coherence fonctionnelle | **71 / 100** | Incoherence objectif DT, risque doublonne |
| Architecture & Structure | **68 / 100** | Fichiers massifs, 2 fichiers morts |
| Logique metier | **82 / 100** | Seuils reglementaires corrects, sources tracees |
| Vue end-user | **78 / 100** | Glossaire riche, parcours fluide |

**Score global : 74,6 / 100**

---

## 1. UX / UI (Score : 74/100)

### 1.1 Coherence visuelle

#### Points conformes

- **Design System centralise** : `src/ui/index.js` exporte 30+ composants standardises (Button, Card, Badge, Tabs, Modal, Drawer, etc.)
  - Fichier : `frontend/src/ui/index.js`

- **Color tokens semantiques** : `src/ui/colorTokens.js` definit des tokens pour KPI (conformite=blue, risque=amber, alertes=indigo), severity (critical=red, high=amber, medium=blue), et accent bars.
  - Fichier : `frontend/src/ui/colorTokens.js`

- **Tint system unifie** : `tint.module()` et `tint.severity()` evitent les couleurs en dur. Les composants cockpit (ModuleLaunchers, EssentialsRow) utilisent ce systeme.
  - Fichier : `frontend/src/ui/colorTokens.js`, lignes 168-195

- **Conventions documentees** : `src/ui/conventions.js` definit `LAYOUT`, `TYPO`, `LABELS_FR` comme reference executable.
  - Fichier : `frontend/src/ui/conventions.js`

- **Icones coherentes** : Utilisation exclusive de Lucide React sur toute l'application.

#### Avertissements

- **PageShell ne contraint pas le responsive** : Le composant `PageShell.jsx` utilise `px-6 py-6` mais ne definit aucun breakpoint. Les pages gerent individuellement leur responsive avec `grid-cols-1 md:grid-cols-3`, ce qui peut entrainer des incoherences.
  - Fichier : `frontend/src/ui/PageShell.jsx`, ligne 20
  - Recommandation : Ajouter des breakpoints standards dans PageShell ou dans conventions.js

- **Taille de police non-standard** : Plusieurs composants utilisent `text-[10px]` ou `text-[11px]` (tailles non-Tailwind) au lieu de `text-xs` (12px). Cela brise la grille typographique.
  - Fichiers : `CockpitHero.jsx` (lignes 91, 117, 120, 158), `EssentialsRow.jsx` (ligne 31), `ModuleLaunchers.jsx` (lignes 80, 82)
  - Recommandation : Standardiser sur `text-xs` minimum pour la lisibilite

- **Micro-textes potentiellement illisibles** : `text-[9px]` utilise dans `ActionsImpact.jsx` (ligne 30) et `AlertesPrioritaires.jsx` pour les badges source. Trop petit pour un usage professionnel.
  - Recommandation : Minimum 10px, idealement 11px pour les labels secondaires

#### Problemes

- **Contraste insuffisant sur certains sous-textes** : `text-gray-400` sur fond blanc (`bg-white`) donne un ratio de contraste d'environ 2.6:1, en dessous du minimum WCAG AA (4.5:1 pour le texte).
  - Fichiers : `CommandCenter.jsx` (ligne 91 "sub" text), `KpiJ1Card` (ligne 91)
  - Recommandation : Utiliser `text-gray-500` minimum pour les textes de sous-titres

### 1.2 Labels et textes en francais

#### Points conformes

- **Labels centralises** : `complianceLabels.fr.js` contient REG_LABELS, STATUT_LABELS, ACTION_STATUS_LABELS, WORKFLOW_LABELS — tout en francais.
  - Fichier : `frontend/src/domain/compliance/complianceLabels.fr.js`

- **LABELS_FR pour les etats communs** : "Chargement...", "Aucune donnee", "Erreur de chargement", "Reessayer" — correctement centralises.
  - Fichier : `frontend/src/ui/conventions.js`, lignes 28-40

- **Formats FR** : `fmtEur()`, `fmtKwh()`, `fmtDateFR()` utilisent systematiquement la locale `fr-FR`. Les montants utilisent k euros (24 k euros) et les dates "14 fev. 2026".
  - Fichier : `frontend/src/utils/format.js`

#### Problemes

- **Accents manquants dans STATUT_LABELS** : 4 labels sans accents, visibles par l'utilisateur final :
  - `evaluation_incomplete: 'Evaluation incomplete'` -> devrait etre `'Evaluation incomplete'` (le 'E' majuscule n'a pas d'accent mais "incomplete" devrait etre "incomplete")
  - `preparation_en_cours: 'Preparation en cours'` -> `'Preparation en cours'` (manque accent sur 'e')
  - `classe_a_verifier: 'Classe systeme a verifier'` -> `'Classe systeme a verifier'` (manque accents sur 'e' de systeme et verifier)
  - `preuves_non_tracables: 'Preuves non tracables'` -> `'Preuves non tracables'` (manque accent cedille)
  - Fichier : `frontend/src/domain/compliance/complianceLabels.fr.js`, lignes 33-36
  - **Impact** : Affichage sans accents dans l'interface conformite pour un produit francais professionnel

- **CONFORMITE_WARNINGS sans accents** : Les 5 avertissements de securite conformite sont tous sans accents :
  - "aucun depot ADEME/OPERAT reel" -> "reel"
  - "Consommation de reference absente" -> "reference"
  - "Trajectoire de reduction non validee" -> "reduction", "validee"
  - "preuves documentaires ne disposent pas d'un audit-trail" -> OK mais "conformite" sans accent ligne 61
  - Fichier : `frontend/src/domain/compliance/complianceLabels.fr.js`, lignes 52-62
  - Recommandation : Corriger tous les accents dans ce fichier critique

- **Commentaire anglais expose** : `CommandCenter.jsx` ligne 50 contient le commentaire code "EnergyCopilotPage - dead code" qui n'est pas visible utilisateur, OK. Mais le commentaire inline `// eslint-disable-line react-hooks/exhaustive-deps` apparait 74 fois dans les pages, suggerant une utilisation excessive de suppressions de lint.

### 1.3 Etats vides, loading, erreurs

#### Points conformes

- **EmptyState standardise** : 4 variantes (empty, partial, unconfigured, error) avec icones et couleurs adaptees.
  - Fichier : `frontend/src/ui/EmptyState.jsx`

- **ErrorState robuste** : Titre, message, bouton retry, zone debug optionnelle avec status/error_code/trace_id.
  - Fichier : `frontend/src/ui/ErrorState.jsx`

- **Skeleton loading** : 4 variantes (Skeleton, SkeletonCard, SkeletonKpi, SkeletonTable) utilisees systematiquement dans Cockpit, CommandCenter, CockpitHero.
  - Fichier : `frontend/src/ui/Skeleton.jsx`

- **ErrorBoundary global** : Capture les erreurs React avec context (page, orgId), logger structure, boutons "Reessayer" et "Retour a l'accueil".
  - Fichier : `frontend/src/components/ErrorBoundary.jsx`

- **CommandCenter** gere les 3 etats : loading (SkeletonCard grid), error (ErrorState avec onRetry), et data (contenu normal).
  - Fichier : `frontend/src/pages/CommandCenter.jsx`, lignes 322-340

- **Cockpit.jsx** gere le loading des sites (sitesLoading -> SkeletonCard + SkeletonTable).
  - Fichier : `frontend/src/pages/Cockpit.jsx`, lignes 447-459

#### Avertissements

- **Catch silencieux dans useCockpitData** : Chaque appel API est wrappe dans `.catch(() => null)` ce qui masque les erreurs individuelles. Si `/api/cockpit/trajectory` echoue, la trajectoire est simplement `null` sans indication a l'utilisateur.
  - Fichier : `frontend/src/hooks/useCockpitData.js`, lignes 151-173
  - Recommandation : Logger les erreurs (deja fait) ET exposer un etat partiel ("Trajectoire indisponible") dans l'UI

- **CockpitHero** : Passe `description` au lieu de `message` pour ErrorState. ErrorState attend `message` et `title`, pas `description`.
  - Fichier : `frontend/src/pages/cockpit/CockpitHero.jsx`, ligne 63 : `<ErrorState title="..." description="..." />`
  - Impact : Le message d'erreur ne s'affiche pas (prop ignoree)

### 1.4 Responsive / Mobile

#### Avertissements

- **Responsive basique** : Les grilles utilisent `grid-cols-1 md:grid-cols-3` ou `grid-cols-2 md:grid-cols-4` mais il n'y a pas de breakpoint `sm:` intermediaire. Sur tablette (768-1024px), la transition est abrupte.
  - Fichiers : Tous les fichiers cockpit/*, CommandCenter.jsx

- **Masquage d'elements sur mobile** : `hidden sm:flex` pour les trust signals du header (ligne 350, CommandCenter.jsx). Information perdue sur mobile.
  - Recommandation : Placer ces infos dans un menu ou tooltip accessible sur mobile

- **Textes tronques** : `truncate` et `line-clamp-2` utilises massivement. Sur petit ecran, des informations critiques pourraient etre coupees (noms de sites, labels d'actions).

### 1.5 Accessibilite

#### Points conformes

- **Attributs ARIA presents** : 113 occurrences d'attributs aria-* sur 59 fichiers. Les composants critiques (Modal, Drawer, Explain, EvidenceDrawer, Pagination, Tabs) ont des roles ARIA corrects.
- **focus-visible** : Utilise dans Button, CockpitHero, EssentialsRow, ModuleLaunchers pour la navigation clavier.
- **role="term"** et `aria-describedby` dans Explain.jsx pour les termes techniques.
- **role="tooltip"** dans les tooltips portalisees.

#### Problemes

- **Boutons interactifs sans aria-label** : Plusieurs `<div onClick={...}>` et `<button>` sans texte accessible dans les cartes cockpit (CockpitHero.jsx utilise bien `role="button" tabIndex={0}`, mais certaines cartes dans CommandCenter.jsx manquent de role).
  - Fichier : `CommandCenter.jsx`, les KpiJ1Card n'ont pas de role button
  - Recommandation : Ajouter `role="button"` et `aria-label` aux cartes cliquables

- **Pas de skip-link** : Aucun lien "Aller au contenu principal" n'est present pour la navigation clavier.
  - Recommandation : Ajouter un skip-link dans AppShell

---

## 2. Coherence fonctionnelle (Score : 71/100)

### 2.1 Coherence des donnees entre pages

#### Points conformes

- **Source unique pour les KPIs** : `useCockpitData.js` fetch `/api/cockpit`, `/api/cockpit/trajectory`, `/api/actions/summary`, `/api/billing/summary` en parallele. Les normaliseurs (`normalizeCockpitKpis`, `normalizeTrajectory`) sont des fonctions pures sans logique metier.
  - Fichier : `frontend/src/hooks/useCockpitData.js`

- **normalizeDashboardModel** dans CommandCenter.jsx empeche les contradictions (si 100% conforme, risque = 0).
  - Fichier : `frontend/src/pages/CommandCenter.jsx`, lignes 126-141

- **Constantes partagees** : `lib/constants.js` definit les seuils de risque, couverture, conformite, maturite comme source unique de verite. Utilise dans Cockpit, Patrimoine, dashboardEssentials.
  - Fichier : `frontend/src/lib/constants.js`

- **getRiskStatus()** et `getStatusBadgeProps()` utilises de maniere coherente entre Cockpit et CommandCenter.

#### Problemes

- **Incoherence objectif trajectoire DT** : Deux valeurs par defaut differentes pour le meme concept :
  - `useCockpitData.js` ligne 62 : `objectifPremierJalonPct: raw.objectif_2030_pct ?? -40.0` (correct : DT 2030 = -40%)
  - `useCockpitData.js` ligne 77 : `objectif2026Pct: raw.objectif_2026_pct ?? -25.0` (correct pour 2026)
  - `CommandCenter.jsx` ligne 538 : `objectif {trajectoire.objectifPremierJalonPct ?? -25}%` (FAUX : affiche -25% au lieu de -40%)
  - `CockpitHero.jsx` ligne 176 : `{trajectoire?.objectifPremierJalonPct ?? -40}%` (correct : -40%)
  - **Impact** : Le tableau de bord (/) affiche "objectif -25%" tandis que la vue executive (/cockpit) affiche "objectif -40%" pour la MEME donnee trajectoire.
  - Fichier : `CommandCenter.jsx`, lignes 538, 567, 578
  - Recommandation : Utiliser `trajectoire?.objectifPremierJalonPct ?? -40` partout, ou mieux, ne pas mettre de fallback et afficher "---" si la donnee est absente

- **Double fetch /api/cockpit** : Cockpit.jsx fait DEUX appels a `/api/cockpit` :
  - Via `useCockpitData()` (ligne 119) qui appelle `getCockpit()`
  - Via `fetch('/api/cockpit', ...)` directement (ligne 184) pour `conso_confidence`
  - Fichier : `frontend/src/pages/Cockpit.jsx`, lignes 119 et 184
  - Recommandation : Extraire `conso_confidence` de la reponse de `useCockpitData()` au lieu de refaire un appel

- **Risque financier calcule differemment** :
  - CommandCenter.jsx (ligne 199) : `scopedSites.reduce((sum, s) => sum + (s.risque_eur || 0), 0)` — somme brute depuis les sites
  - Cockpit.jsx (ligne 203-204) : `cockpitKpis?.risqueTotal ?? sites.reduce(...)` — privilegiant la valeur backend si disponible
  - **Impact** : Le risque peut differer entre / et /cockpit si le backend ajoute des risques non-site (billing, contrats)

### 2.2 Liens de navigation

#### Points conformes

- **Route registry centralise** : `services/routes.js` definit 15+ helpers (toConsoExplorer, toBillIntel, toActionNew, toConformite, etc.) avec documentation JSDoc complete.
  - Fichier : `frontend/src/services/routes.js`

- **CTA "Voir conformite"** -> `/conformite` : Correct dans dashboardEssentials.js (ligne 52), CockpitHero.jsx (ligne 86), priority1 (ligne 367).

- **CTA "Plan d'action"** -> `/actions` : Correct dans dashboardEssentials.js (ligne 64), topActions (Cockpit.jsx).

- **ModuleLaunchers** : Routes correctement mappees (cockpit -> /cockpit, operations -> /conformite, analyse -> /consommations/explorer, marche -> /billing, admin -> /import).
  - Fichier : `frontend/src/pages/cockpit/ModuleLaunchers.jsx`

#### Avertissements

- **toActionsList() pointe vers /anomalies** : La fonction `toActionsList()` dans routes.js retourne `/anomalies?tab=actions` au lieu de `/actions`. Le composant AnomaliesPage est un hub multi-onglets qui inclut les actions, mais c'est confusant pour la navigation directe.
  - Fichier : `frontend/src/services/routes.js`, ligne 132
  - Recommandation : Verifier que c'est bien intentionnel ou creer un alias `/actions` -> `/anomalies?tab=actions`

---

## 3. Architecture & Structure (Score : 68/100)

### 3.1 Organisation des fichiers

#### Points conformes

- **Separation claire des couches** :
  - `pages/` : Pages route-level (90+ fichiers)
  - `components/` : Composants reutilisables (60+ fichiers)
  - `ui/` : Design system (40+ fichiers avec index.js barrel)
  - `models/` : Logique metier pure, sans React (27 fichiers dont 8 fichiers de test)
  - `hooks/` : Custom hooks React (13 fichiers)
  - `services/` : Couche API et utilitaires (21 fichiers)
  - `contexts/` : Contexts React (5 fichiers)
  - `domain/` : Regles metier et labels (conformite, purchase)
  - `lib/` : Constantes et utilitaires bas-niveau
  - `layout/` : AppShell, Sidebar, NavRegistry

- **Models purs testables** : `dashboardEssentials.js`, `guidedModeModel.js`, `complianceProfileRules.js` sont des modules purs sans import React. Les fonctions exportees sont des transformations de donnees.
  - Fichier : `frontend/src/models/dashboardEssentials.js` — "No React imports - fully testable in isolation"

- **Hooks specialises** : `useCockpitData`, `useCockpitSignals`, `useCommandCenterData`, `useComplianceMeta` — chacun une responsabilite claire.

- **Lazy loading systematique** : `App.jsx` utilise `lazy()` + `Suspense` pour toutes les pages (30+ routes), avec un fallback SkeletonCard.
  - Fichier : `frontend/src/App.jsx`

- **API decoupee** : `services/api/` contient des modules par domaine (core.js, auth.js, billing.js, energy.js, patrimoine.js, actions.js, conformite.js, cockpit.js, purchase.js, market.js, admin.js).

#### Avertissements

- **Sous-dossiers cockpit/ et conformite-tabs/ dans pages/** : Pattern non-standard. Les sous-composants de Cockpit (14 fichiers dans `pages/cockpit/`) pourraient etre dans `components/cockpit/` puisqu'ils ne sont pas des pages routees.
  - Recommandation : Deplacer `pages/cockpit/*.jsx` vers `components/cockpit/` pour respecter la convention

- **Pas de barrel export pour les pages** : Contrairement a `ui/index.js`, les pages n'ont pas de fichier index, ce qui force les imports explicites partout. Acceptable pour les pages lazy-loaded.

### 3.2 Fichiers trop volumineux (> 500 lignes)

#### Problemes

**Frontend (> 500 lignes) — 28 fichiers concernes :**

| Fichier | Lignes | Severite |
|---|---|---|
| `MonitoringPage.jsx` | 3 112 | CRITIQUE |
| `Patrimoine.jsx` | 2 243 | CRITIQUE |
| `PurchasePage.jsx` | 2 024 | CRITIQUE |
| `PurchaseAssistantPage.jsx` | 1 823 | CRITIQUE |
| `Site360.jsx` | 1 619 | CRITIQUE |
| `ActionsPage.jsx` | 1 579 | CRITIQUE |
| `ActionDetailDrawer.jsx` | 1 327 | ELEVE |
| `BillIntelPage.jsx` | 1 246 | ELEVE |
| `ConsommationsUsages.jsx` | 1 240 | ELEVE |
| `UsagesDashboardPage.jsx` | 1 203 | ELEVE |
| `ConsumptionDiagPage.jsx` | 1 173 | ELEVE |
| `PatrimoineWizard.jsx` | 1 163 | ELEVE |
| `ObligationsTab.jsx` | 1 155 | ELEVE |
| `TertiaireEfaDetailPage.jsx` | 1 099 | ELEVE |
| `Cockpit.jsx` | 1 070 | ELEVE |
| `SiteCreationWizard.jsx` | 1 040 | ELEVE |
| `ConsumptionExplorerPage.jsx` | 979 | MOYEN |
| `ConsumptionPortfolioPage.jsx` | 978 | MOYEN |
| `NavRegistry.js` | 977 | MOYEN |
| `StickyFilterBar.jsx` | 910 | MOYEN |
| `KBExplorerPage.jsx` | 833 | MOYEN |
| `ConformitePage.jsx` | 828 | MOYEN |
| `BacsWizard.jsx` | 796 | MOYEN |
| `UpgradeWizard.jsx` | 760 | MOYEN |
| `SiteCompliancePage.jsx` | 730 | MOYEN |
| `AnomaliesPage.jsx` | 720 | MOYEN |
| `dashboardEssentials.js` | 715 | MOYEN |
| `CommandCenter.jsx` | 711 | MOYEN |
| `BillingPage.jsx` | 709 | MOYEN |

- Recommandation : Les fichiers > 1000 lignes doivent etre decomposes en sous-composants. MonitoringPage (3112 lignes) est le cas le plus critique.

**Backend (> 500 lignes, hors venv/tests) — principaux :**

| Fichier | Lignes |
|---|---|
| `routes/billing.py` | 1 863 |
| `database/migrations.py` | 1 621 |
| `services/patrimoine_service.py` | 1 429 |
| `routes/actions.py` | 1 317 |
| `routes/purchase.py` | 1 265 |
| `services/billing_engine/catalog.py` | 1 261 |
| `services/compliance_engine.py` | 1 249 |

### 3.3 Fichiers morts / orphelins

#### Problemes

- **Dashboard.jsx** : 20+ lignes, importe `getAlertes` et utilise l'ancien design. N'est PAS reference dans `App.jsx` (aucune route ne pointe vers ce composant). Import de `COMPLIANCE_SCORE_THRESHOLDS` avec alias `_COMPLIANCE_SCORE_THRESHOLDS` + eslint-disable no-unused-vars confirme qu'il est inactif.
  - Fichier : `frontend/src/pages/Dashboard.jsx`
  - Recommandation : Supprimer ou archiver

- **EnergyCopilotPage.jsx** : Commente dans App.jsx avec le commentaire "dead code, no active route (Sprint B P0-7)". Le fichier existe toujours.
  - Fichier : `frontend/src/pages/EnergyCopilotPage.jsx`
  - Recommandation : Supprimer le fichier

- **CompliancePage.jsx** : Un commentaire dans App.jsx dit "CompliancePage deprecated -- /compliance root redirects to /conformite (V92)". Le fichier peut etre residuel.
  - Recommandation : Verifier et supprimer si non utilise

### 3.4 eslint-disable proliferation

#### Avertissements

- **74 occurrences de `eslint-disable`** dans les fichiers pages. `ConsumptionExplorerPage.jsx` en contient 14 a lui seul. Cela suggere :
  - Des hooks useMemo avec des deps non listees (souvent `react-hooks/exhaustive-deps`)
  - Des imports inutilises
  - Recommandation : Revoir les depedances des hooks pour eliminer les suppressions

### 3.5 Imports circulaires potentiels

#### Points conformes

- **Models purs** : Les fichiers `models/*.js` n'importent AUCUN fichier de `../pages/`, `../components/`, ou `../hooks/`. Ils importent uniquement depuis `../utils/` et `../lib/`. Pas de risque de circularite.

- **Hooks** : Les hooks importent depuis `../services/api` et `../contexts/`, pas depuis les pages. Architecture correcte.

---

## 4. Logique metier (Score : 82/100)

### 4.1 Seuils reglementaires

#### Points conformes

- **Decret Tertiaire — seuil surface 1 000 m2** : Correctement implementer dans `compliance_rules.py` ligne 134 : `if area < 1000: status="OUT_OF_SCOPE"`. Coherent avec le label FR "Reduire la consommation energetique des batiments tertiaires > 1 000 m2" (`complianceLabels.fr.js` ligne 21).

- **Decret Tertiaire — objectif -40% 2030** : Correctement implemente dans `compliance_rules.py` ligne 157 : `if pct >= 40: status="OK"`. Coherent avec useCockpitData.js (defaut -40.0) et le glossaire ("Obligation reglementaire de reduire [...] de -40 % d'ici 2030").

- **BACS — seuil 290 kW** : Correctement implemente dans `compliance_rules.py` ligne 227 : `if cvc <= 290: status="OK"`. Le seuil 70 kW est aussi correct pour le scope initial (ligne 213-216).

- **APER — parking 1 500 m2** : Correctement implemente dans `aper_service.py` ligne 57 : `if parking_area >= 1500 and parking_type == "outdoor"`. Coherent avec le label FR "parkings > 1 500 m2" et le glossaire APER.

- **Accise electricite 2025** : Le glossaire definit correctement "Taux 2025 : 22,50 EUR/MWh" (`glossary.js` ligne 39).

- **TVA differentie** : Le glossaire mentionne correctement "5,5 % sur l'abonnement et la CTA, et 20 % sur la consommation et les taxes" (`glossary.js` ligne 56).

#### Avertissements

- **Objectif -50% 2040 en dur** : `compliance_rules.py` ligne 169 utilise `if pct >= 50` pour DT_TRAJECTORY_2040. Ce seuil est correct (decret n2019-771) mais code en dur au lieu d'etre dans le YAML.
  - Recommandation : Externaliser dans le pack YAML `decret_tertiaire_operat_v1.yaml`

### 4.2 Conventions de signe

#### Points conformes

- **Reduction = valeur negative** : `objectifPremierJalonPct` est defini a `-40.0` (negatif). La comparaison `reductionPctActuelle > objectifPremierJalonPct` est correcte car -15 > -40 signifie "moins de reduction que l'objectif", donc en retard.
  - Fichier : `CockpitHero.jsx`, lignes 73-75

- **Risque = valeur positive en euros** : Coherent dans toute l'application. `risque_eur > 0` = il y a un risque.

- **Format fmtEur** : Retourne "---" pour 0, ce qui evite l'affichage confusant "0 euros" pour un risque nul.
  - Fichier : `frontend/src/utils/format.js`, ligne 22

#### Problemes

- **Incoherence fallback objectif trajectoire** : Comme mentionne en section 2.1, CommandCenter.jsx utilise `-25` comme fallback alors que CockpitHero.jsx utilise `-40`. L'objectif 2030 est -40%, l'objectif 2026 est -25%. Le champ `objectifPremierJalonPct` devrait etre -40 (2030) dans tous les cas.

### 4.3 Sources de donnees tracees

#### Points conformes

- **Sources ADEME** : Facteurs CO2 documentes dans `glossary.js` ligne 309 : "facteur d'emission ADEME par vecteur energetique (electricite : 0,057 kgCO2e/kWh, gaz : 0,227 kgCO2e/kWh)". Source : "ADEME Base Carbone 2024".

- **Sources CRE** : TURPE 7 documente avec "CRE n2025-78" dans le glossaire. Le glossaire CRE definit correctement "Commission de Regulation de l'Energie".

- **Sources Legifrance** : Le label DT_TRAJECTORY_2030 reference "Art. L174-1 Code de la construction -- Objectif -40%" (`complianceLabels.fr.js` ligne 295).

- **Source RegAssessment tracee** : CockpitHero affiche "Source : Moteur conformite" et "Confiance : haute/moyenne/basse" sous chaque KPI (lignes 120, 159).

- **ARENH** : Le glossaire definit correctement "prix fixe (42 euros/MWh)" (`glossary.js` ligne 157).

---

## 5. Vue end-user / Comprehension (Score : 78/100)

### 5.1 Comprehension DG non-technique

#### Points conformes

- **Glossaire riche** : 40+ termes definis dans `glossary.js` avec `term` (label FR), `short` (1-2 phrases), et `long` (explication detaillee optionnelle). Couvre : TURPE, accise, CSPE, CTA, TVA, kWh, MWh, shadow billing, DT, BACS, APER, CRE, ARENH, et plus.
  - Fichier : `frontend/src/ui/glossary.js`

- **Composant Explain inline** : Souligne les termes techniques avec un trait pointille et affiche la definition au survol. Utilise un portail React pour eviter les problemes de z-index. Support clavier (tabIndex, onFocus/onBlur).
  - Fichier : `frontend/src/ui/Explain.jsx`

- **Evidence Drawer** : Systeme "Pourquoi ce chiffre ?" pour expliquer les KPIs. Bouton HelpCircle dans CockpitHero (4 KPIs). Source, methode de calcul, et confiance expliquees.
  - Fichier : `frontend/src/ui/EvidenceDrawer.jsx`

- **Briefing du jour** : BriefingHeroCard et TodayActionsCard dans CommandCenter donnent un resume actionnable. Maximum 5 actions, triees par priorite.

- **Vue executive vs Tableau de bord** : Onglets CockpitTabs separent la vue DG (/cockpit) du tableau operationnel (/). Bon pattern.

- **Bouton "Rapport COMEX"** : BoutonRapportCOMEX.jsx dans la vue executive — suggere un export PDF pour le comite de direction.

#### Avertissements

- **Termes techniques non expliques dans certaines pages** : Les composants cockpit n'utilisent pas systematiquement `<Explain>`. Par exemple :
  - "CVC" dans compliance_rules.py (rendu comme "CVC > 290 kW") n'est pas explique dans le front
  - "GTB/GTC" est mentionne dans REG_LABELS mais sans Explain dans tous les contextes
  - Recommandation : Ajouter `<Explain term="decret_bacs">` autour des mentions de BACS

- **Jargon interne residuel** : Certains labels utilisent du jargon technique :
  - "Connecteur RTE a brancher" (CommandCenter.jsx, ligne 421) — incomprehensible pour un DG
  - "P0", "P1", "P2" comme badges de priorite (ActionsImpact.jsx) — pas de legende
  - "RegAssessment" (CockpitHero.jsx, ligne 120) — terme technique interne affiche si la source n'est pas traduite
  - Recommandation : Traduire "Connecteur RTE a brancher" en "Donnees CO2 reseau non disponibles"

### 5.2 Parcours utilisateur

#### Points conformes

- **Cockpit -> detail -> action** :
  1. Vue executive (/cockpit) : KPIs synthetiques + CTA "Voir conformite"
  2. Conformite (/conformite) : 4 onglets (Obligations, Donnees, Execution, Preuves) avec mode guide
  3. Actions (/actions) : Table/Kanban avec filtres, assignation, export CSV/PDF
  - Navigation fluide grace aux helpers de routes.js

- **Clics sur cartes KPI** : CockpitHero rend les 4 cartes cliquables (onClick navigate). Conformite -> /conformite, Risque -> /actions, etc.

- **Mode guide** : GuidedModeBandeau + NextBestActionCard dans ConformitePage aident les utilisateurs novices a suivre un parcours etape par etape.

- **DemoSpotlight** : Composant d'onboarding pour les nouveaux utilisateurs en mode demo.

#### Avertissements

- **Trop de pages** : 30+ routes definies dans App.jsx. Un DG pourrait se sentir perdu. La navigation laterale (Sidebar/NavRegistry) devrait hierarchiser clairement.

- **Pas de parcours d'onboarding structure** : OnboardingPage existe mais le flux premier-usage (inscription -> import donnees -> premier scan conformite -> cockpit) n'est pas guide pas-a-pas.

---

## Annexe A — Fichiers audites

### Frontend (principaux)
- `frontend/src/App.jsx` — Routeur principal
- `frontend/src/pages/Cockpit.jsx` — Vue executive (1070 lignes)
- `frontend/src/pages/CommandCenter.jsx` — Tableau de bord (711 lignes)
- `frontend/src/pages/ConformitePage.jsx` — Conformite (828 lignes)
- `frontend/src/pages/ActionsPage.jsx` — Actions (1579 lignes)
- `frontend/src/hooks/useCockpitData.js` — Hook donnees cockpit
- `frontend/src/hooks/useCockpitSignals.js` — Hook signaux marche
- `frontend/src/hooks/useCommandCenterData.js` — Hook tableau de bord
- `frontend/src/models/dashboardEssentials.js` — Modele dashboard (715 lignes)
- `frontend/src/services/routes.js` — Route registry
- `frontend/src/ui/*.jsx` — Design system (40+ fichiers)
- `frontend/src/ui/glossary.js` — Glossaire (40+ termes)
- `frontend/src/ui/conventions.js` — Conventions UI
- `frontend/src/ui/colorTokens.js` — Tokens couleur
- `frontend/src/domain/compliance/complianceLabels.fr.js` — Labels conformite
- `frontend/src/lib/constants.js` — Seuils et constantes
- `frontend/src/utils/format.js` — Formatage FR

### Backend (principaux)
- `backend/services/compliance_rules.py` — Evaluateur regles conformite
- `backend/services/aper_service.py` — Logique APER
- `backend/services/compliance_engine.py` — Moteur conformite (1249 lignes)
- `backend/routes/billing.py` — Routes facturation (1863 lignes)

### Cockpit sub-components
- `pages/cockpit/CockpitHero.jsx` — Hero 4 KPIs
- `pages/cockpit/CockpitHeaderSignals.jsx` — Signaux header
- `pages/cockpit/BoutonRapportCOMEX.jsx` — Export COMEX
- `pages/cockpit/EssentialsRow.jsx` — Mini-cartes essentielles
- `pages/cockpit/ModuleLaunchers.jsx` — Tuiles navigation modules
- `pages/cockpit/AlertesPrioritaires.jsx` — Top alertes
- `pages/cockpit/ActionsImpact.jsx` — Actions prioritaires
- `pages/cockpit/PerformanceSitesCard.jsx` — Benchmark kWh/m2
- `pages/cockpit/TrajectorySection.jsx` — Trajectoire DT
- `pages/cockpit/SitesBaselineCard.jsx` — Sites vs baseline

---

## Annexe B — Plan d'action prioritaire

### CRITIQUE (a corriger avant demo/pilote)

1. **Accents manquants** dans `complianceLabels.fr.js` lignes 33-36 et 52-62
2. **Incoherence objectif DT** : CommandCenter.jsx fallback -25% au lieu de -40%
3. **CockpitHero ErrorState** : prop `description` au lieu de `message`

### ELEVE (sprint suivant)

4. Decomposer MonitoringPage.jsx (3112 lignes)
5. Decomposer Patrimoine.jsx (2243 lignes)
6. Supprimer fichiers morts (Dashboard.jsx, EnergyCopilotPage.jsx)
7. Eliminer le double fetch `/api/cockpit` dans Cockpit.jsx
8. Ameliorer le contraste des sous-textes (`text-gray-500` minimum)

### MOYEN (backlog)

9. Ajouter breakpoint `sm:` pour responsive tablette
10. Reduire les eslint-disable (74 occurrences)
11. Ajouter skip-link accessibilite
12. Traduire jargon interne ("Connecteur RTE a brancher")
13. Ajouter aria-label aux cartes cliquables
14. Deplacer pages/cockpit/ vers components/cockpit/
