# AUDIT TOTAL PROMEOS — Passage Board / Investisseur / Prospect Premium

**Date** : 2026-03-08
**Méthode** : Audit 4 couches (Surface / Fonctionnel / Logique / Crédibilité)
**Périmètre** : Frontend (192 fichiers test, 41 697 lignes de pages), Backend (50+ routes, 14 règles billing), Navigation (71 routes, 5 modules), UI (30+ composants)

---

## 1. Executive Summary

| Critère | Valeur |
|---------|--------|
| **Note globale** | **62/100** |
| **Verdict** | Produit techniquement solide mais pas encore "board-ready" |
| **Maturité réelle** | MVP avancé — pas un produit fini |
| **Potentiel après correction** | 82/100 (en 2-3 sprints ciblés) |

### 5 risques les plus graves

1. **Fuite technique visible** — DevApiBadge + DevScopeBadge affichés à TOUS les utilisateurs sur ConformitePage (scope JSON visible)
2. **Données tronquées sans avertissement** — AnomaliesPage ignore silencieusement les sites >20 (`MAX_SITES=20`)
3. **Bypass scope sécurité** — 2 endpoints consommation ne filtrent pas par org_id (accès cross-org possible)
4. **Pages zombies** — 4 pages non routées (3 092 lignes de code mort : Dashboard, ActionPlan, CompliancePage, SiteDetail)
5. **Accents français manquants** — 15+ endroits visibles ("definie", "enregistree", "Fev", "Eleve", "duree", "marche")

### 5 forces réelles

1. **Architecture navigation** — 5 modules clairs, tint system cohérent, CommandPalette fonctionnelle (Ctrl+K)
2. **Engine billing shadow v2** — 5 composantes + catalog trace + diagnostics + top contributeurs
3. **Design system UI** — KpiCard variants, PageShell, Skeleton/Loading/Empty/Error states systématiques
4. **Test coverage** — 192 fichiers / 5 664 tests frontend green, backend golden tests
5. **Scope management** — Org/portefeuille/site hiérarchique avec localStorage persistence

---

## 2. Notes détaillées par dimension

| Dimension | Note /100 | Commentaire sévère |
|-----------|-----------|-------------------|
| **UX** | 68 | Parcours cohérent mais trop de pages (45), workflow constat→action fragmenté |
| **UI** | 72 | Design system solide mais pas de tokens centralisés, couleurs dupliquées x3+ |
| **Navigation** | 65 | 71 routes dont 20+ redirects, pages zombies, expert toggle cassé dans CommandPalette |
| **Scope / gouvernance** | 55 | Portefeuilles hardcodés (mock), favoris non scope-safe, org_id bypass sur 2 endpoints |
| **KPI / calcul** | 70 | Shadow billing crédible, mais seuils métier hardcodés et non documentés (R²≥0.6, score≥60) |
| **Facturation / achat / conformité** | 72 | Moteur 14 règles solide, mais seedBillingDemo() exposé sans gate |
| **Workflow / actionability** | 58 | Création d'action OK mais validation formulaire absente (date passée, EUR négatif) |
| **Demo credibility** | 50 | SIREN "123456789", rues génériques, badges dev visibles, seed data apparente |
| **Architecture visible** | 65 | ErrorState montre debug info (status, request_url), console.log en prod |
| **Wording / microcopy** | 55 | 15+ fautes d'accents, descriptions en anglais dans PurchasePage |
| **Responsive / densité** | 62 | Breakpoints sautent sans intermédiaire (2→6 cols), pas de tablet optimization |
| **Product story** | 68 | Cockpit crédible, mais trop de pages diluent le message produit |

---

## 3. Top problèmes critiques

| ID | Problème | Zone | Pourquoi c'est grave | Priorité | Effort | Type |
|----|----------|------|---------------------|----------|--------|------|
| C1 | DevApiBadge + DevScopeBadge visible à tous sur ConformitePage L63-127 | Conformité | Scope JSON affiché = mort en démo | P0 | 5 min | Technique visible |
| C2 | MAX_SITES=20 silencieux sur AnomaliesPage L28 | Anomalies | Client 25 sites → 5 anomalies invisibles | P0 | 15 min | Data |
| C3 | 2 endpoints consommation sans filtrage org_id | API | Cross-org data leak = red flag sécurité | P0 | 30 min | Scope |
| C4 | seedBillingDemo() / generateMonitoringDemo() sans gate DEMO_MODE | Billing/Monitoring | Bouton "seed" visible en prod = POC signal | P0 | 10 min | Crédibilité |
| C5 | 15+ accents français manquants visibles dans l'UI | Global | "definie", "enregistree", "Fev" = amateur | P0 | 30 min | Wording |
| C6 | 4 pages zombies non routées (3 092 lignes) | Navigation | Dashboard.jsx, ActionPlan.jsx, CompliancePage.jsx, SiteDetail.jsx | P1 | 15 min | Navigation |
| C7 | Portefeuilles hardcodés dans ScopeContext (MOCK_PORTEFEUILLES) | Scope | Production → scope cassé si vrais portefeuilles ≠ mock | P1 | 2h | Gouvernance |
| C8 | Expert toggle cassé dans CommandPalette (Ctrl+Shift+X) | Navigation | Raccourci ne fait rien | P1 | 10 min | UX |
| C9 | SIREN "123456789" et rues génériques dans seed | Démo | Prospect voit immédiatement que c'est fake | P1 | 1h | Crédibilité |
| C10 | Tabs sans ARIA roles (tablist, tab, aria-selected) | UI | WCAG AA fail, inaccessible clavier | P1 | 30 min | UI |
| C11 | /contracts-radar dans ROUTE_MODULE_MAP mais pas dans App.jsx | Navigation | Bookmark → 404 | P1 | 5 min | Navigation |
| C12 | Input/Select sans état erreur ni aria-invalid | UI | Formulaires soumis sans feedback | P1 | 1h | UI |
| C13 | ErrorState affiche debug info (status, request_url) sans gate | UI | Info technique visible à l'utilisateur final | P1 | 10 min | Technique visible |
| C14 | NAV_SECTIONS vs NAV_MAIN_SECTIONS duplication | Navigation | 2 sources de vérité parallèles | P2 | 1h | Navigation |
| C15 | Formule modulo hardcodée patrimoine L275 | Patrimoine | IDs non séquentiels → affectation portfolio cassée | P2 | 30 min | Data |

---

## 4. Audit détaillé par zone

### 4.1 Cockpit (CommandCenter.jsx — 440L, Cockpit.jsx — 837L)

- **Ce qui fonctionne** : Briefing du jour, KPI row, module launchers, compliance score trend, market context
- **Ce qui est faible** : 2 pages cockpit (CommandCenter = "/" et Cockpit = "/cockpit") — confusion sur laquelle est la "vraie"
- **Ce qui est trompeur** : "Source : Moteur de conformité v2" affiché en mode expert — texte non paramétré
- **Ce qui manque** : Pas de "data updated at" timestamp sur les KPI
- **Ce qu'un prospect remarquera** : Double cockpit → "pourquoi 2 dashboards ?"

### 4.2 Patrimoine (Patrimoine.jsx — 2000+L)

- **Ce qui fonctionne** : Heatmap anomalies, virtual scrolling, site drawer, filtres URL-synced
- **Ce qui est cassé** : Formule modulo `((s.id-1)%5)+1` pour affectation portfolio
- **Ce qui est faible** : Heatmap limitée à 10 sites sans warning
- **Ce qui manque** : Favoris non scope-safe (persistent après changement d'org)

### 4.3 Consommation (8 sous-pages)

- **Ce qui fonctionne** : Explorer, Portfolio, TimeSeries, Heatmap, Signature, Tunnel
- **Ce qui est faible** : P95 calculation sans null-safety, horaires nuit hardcodés 22h-6h
- **Ce qui manque** : Timestamps de fraîcheur des données

### 4.4 Facturation / Bill Intel (BillIntelPage.jsx — 1200+L)

- **Ce qui fonctionne** : Shadow billing v2, insight drawer avec breakdown 5 composantes, top contributeurs, diagnostics
- **Ce qui est cassé** : `seedBillingDemo()` importé sans gate DEMO_MODE
- **Ce qui est trompeur** : Confiance "medium" sans explication statistique

### 4.5 Achat (PurchasePage.jsx — 1200+L)

- **Ce qui fonctionne** : 4 stratégies (Fixe/Indexé/Spot/Solaire), scoring, export RFP
- **Ce qui est cassé** : Descriptions de stratégies en anglais sans accents ("duree", "marche")
- **Ce qui manque** : Purchase scenarios endpoint renvoie 404 (identifié dans DAF scenario)

### 4.6 Actions (ActionsPage.jsx — 200+L)

- **Ce qui fonctionne** : Kanban/table toggle, bulk update, CSV export, print audit
- **Ce qui est faible** : Validation formulaire absente (date passée, EUR négatif accepté)
- **Ce qui est trompeur** : Formatage EUR incohérent (`fmtEur()` vs hardcodé " EUR")

### 4.7 Conformité (ConformitePage.jsx — 300L)

- **Ce qui fonctionne** : Obligations par réglementation, severity distribution, evidence drawer
- **Ce qui est CASSÉ** : **DevApiBadge et DevScopeBadge visibles par TOUS les utilisateurs** (P0)
- **Ce qui manque** : "Élevé" écrit "Eleve" (accent manquant)

### 4.8 Notifications (NotificationsPage.jsx)

- **Ce qui fonctionne** : Sync, bulk mark, drawer, source filtering — **Aucun problème trouvé**
- **Ce qui est faible** : "Non definie" au lieu de "Non définie" (L572)

### 4.9 Admin (4 pages)

- **Ce qui fonctionne** : Users, roles, assignments, audit log
- **Ce qui est faible** : `/admin/roles`, `/admin/assignments`, `/admin/audit` absents du sidebar (accessibles uniquement via URL directe)
- **Ce qui manque** : Audit log affiche "?" pour utilisateurs supprimés

### 4.10 Sidebar

- **Ce qui fonctionne** : 5 modules tintés, pins, badges, sections always-open, responsive width
- **Ce qui est faible** : 20 items dans le sidebar vs 45 pages existantes — beaucoup de pages orphelines
- **Ce qui manque** : Certaines pages admin et énergie inaccessibles sans URL directe

### 4.11 Header

- **Ce qui fonctionne** : Breadcrumb dynamique, scope switcher, search, expert toggle
- **Ce qui est faible** : Breadcrumb sans section pour pages cachées (/diagnostic-conso → pas de "Énergie >")

### 4.12 ScopeSwitcher

- **Ce qui fonctionne** : Hiérarchie org/portefeuille/site, search, persistence localStorage
- **Ce qui est cassé** : Portefeuilles hardcodés (MOCK_PORTEFEUILLES), jamais fetched depuis l'API

### 4.13 Drawers / Modals / Forms

- **Ce qui fonctionne** : InsightDrawer (breakdown + contributeurs + diagnostics), EvidenceDrawer
- **Ce qui est faible** : Pas de validation formulaire, pas d'état erreur sur Input/Select
- **Ce qui manque** : Sticky headers dans les tableaux longs des drawers

### 4.14 Recherche / Command Palette

- **Ce qui fonctionne** : Ctrl+K, 14 actions rapides, 10 raccourcis, search par keywords
- **Ce qui est CASSÉ** : **Expert toggle (Ctrl+Shift+X) ne fait rien** — ferme juste la palette

---

## 5. Contradictions & pertes de confiance

| # | Type | Détail |
|---|------|--------|
| 1 | Pages doublons | CommandCenter (/) et Cockpit (/cockpit) — 2 dashboards pour le même usage |
| 2 | Seed data visible | SIREN "123456789", "Groupe HELIOS" hardcodé dans ScopeContext, rues génériques |
| 3 | Debug/localhost leak | ErrorState montre `status`, `error_code`, `request_url` sans gate expert |
| 4 | DevBadges visibles | ConformitePage L63-127 : "API : Connectée" et scope JSON visibles par tous |
| 5 | console.log en prod | tracker.js L32, api.js L227 — logs console visibles dans DevTools |
| 6 | Labels instables | "Actions & Suivi" (sidebar) vs "Détection automatique" (anomalies) vs "Actions" (page) — 3 noms |
| 7 | Calculs opaques | Score conformité, readiness score, compliance score — 3 scores sans explication |
| 8 | Accents incohérents | "défini" correct dans DevPanel, "definie" incorrect dans NotificationsPage |
| 9 | CTA incohérents | Formatage EUR : parfois `fmtEur()`, parfois `" EUR"` hardcodé |
| 10 | Scope non rappelé | Dans les drawers d'insight et d'action, aucun rappel du scope actif |
| 11 | Fallbacks visibles | "catalogue POC (pas de contrat)" visible dans les hypothèses shadow billing |
| 12 | Mocks en prod | `MOCK_ORGS = [{ id: 1, nom: 'Groupe HELIOS' }]` et `MOCK_PORTEFEUILLES` dans ScopeContext |

---

## 6. Audit customer journey / workflow

### Où le parcours est bon
- Cockpit → Anomalies → Insight drawer → "Comprendre l'écart" → Breakdown composantes
- Patrimoine → Site drawer → Anomalies tab → Toast scope warning
- CommandPalette (Ctrl+K) → Navigation rapide entre modules

### Où il casse
- **Anomalies → Actions** : Pas de lien direct "Créer action depuis cette anomalie" dans le drawer insight
- **Cockpit → Détail** : "Voir toutes les échéances" mène à Conformité, mais le lien est fragile
- **Achat → Scénarios** : Purchase scenarios endpoint 404 (identifié dans DAF scenario)

### Où l'utilisateur se perd
- **2 dashboards** : "/" (CommandCenter) et "/cockpit" (Cockpit) — lequel est le bon ?
- **3 noms pour les actions** : "Actions & Suivi" / "Détection automatique" / "Actions"
- **Pages cachées** : /diagnostic-conso, /usages-horaires, /kb, /segmentation — accessibles uniquement via Ctrl+K

### Où il ne comprend pas
- **Scores opaques** : Score conformité = ? Score de maturité = ? Score readiness = ? Aucune documentation inline
- **Confidence badges** : "Élevée" / "Moyenne" / "Basse" — basé sur quoi exactement ?

---

## 7. Audit spécial chiffres / KPI / calcul

### KPI fiables
- Shadow billing v2 (5 composantes, catalog trace, prorata jours) — méthodologie solide
- Consommation kWh par période — données factuelles
- Surface patrimoine (m²) — donnée structurelle
- Nombre de sites / contrats / factures — comptages directs

### KPI opaques
- **Score conformité** : Formule non exposée, pas de breakdown visible
- **Score de maturité** (readiness_score) : Pourcentage sans explication
- **Data coverage %** : Comment est calculé le taux de couverture ?
- **Risk exposure EUR** : Somme des estimated_loss_eur des insights — mais certains sont à 0

### KPI potentiellement trompeurs
- **"99+"** affiché pour badges >99 — sur un portfolio de 1 000 sites, 99+ est insuffisant
- **Économies estimées** dans PurchasePage — pas de disclaimer "estimation indicative"
- **P95 puissance** : Calculé sur tunnel.envelope sans vérification de la taille d'échantillon

### Chiffres mal visibles
- Pas de "dernière mise à jour" sur aucun KPI
- Pas de tooltip "source de la donnée" systématique
- Valeurs tronquées par `break-words` mais pas de `title` attribute partout

---

## 8. Audit spécial démo / quasi-production

### Ce qui fait encore POC
1. SIREN "123456789" — immédiatement identifiable comme fake
2. DevApiBadge visible à tous les utilisateurs
3. `seedBillingDemo()` accessible sans protection
4. "catalogue POC (pas de contrat)" dans les hypothèses billing
5. `MOCK_PORTEFEUILLES` hardcodé dans le code
6. console.log en production (tracker, api)
7. ErrorState montre `request_url` et `status` aux utilisateurs
8. 4 pages zombies (3 000+ lignes de code mort)
9. Rues génériques dans les données de démo
10. "Environnement de démonstration" visible dans DemoBanner

### Ce qui fait produit mature
1. Architecture navigation 5 modules avec tint system
2. Shadow billing v2 avec catalog trace et diagnostics
3. 5 664 tests automatisés green
4. Evidence drawers "Pourquoi ce chiffre ?"
5. Glossaire 90+ termes avec définitions métier
6. CommandPalette avec raccourcis clavier
7. Virtual scrolling sur Patrimoine
8. Scope hiérarchique org/portfolio/site

### Ce qui bloque une vraie démo client
1. **DevBadges sur ConformitePage** — prospect voit "API : Connectée" et scope JSON
2. **Double cockpit** — "c'est quoi la différence entre / et /cockpit ?"
3. **Accents manquants** — "definie", "enregistree" = manque de professionnalisme
4. **Seed visible** — "Groupe HELIOS" hardcodé, SIREN fake
5. **Pages mortes** — si un utilisateur tape /action-plan, redirect vers /anomalies (why ?)

---

## 9. Recommandations classées

### P0 — Corriger immédiatement (avant toute démo)

| # | Action | Fichier | Effort |
|---|--------|---------|--------|
| 1 | Gater DevApiBadge + DevScopeBadge avec `isExpert` | ConformitePage.jsx L63-127 | 5 min |
| 2 | Ajouter warning si MAX_SITES atteint | AnomaliesPage.jsx L28 | 15 min |
| 3 | Filtrer org_id sur 2 endpoints consommation | consumption_unified.py L49, L98 | 30 min |
| 4 | Gater seedBillingDemo / generateMonitoringDemo avec DEMO_MODE | BillIntelPage, MonitoringPage | 10 min |
| 5 | Corriger 15+ accents français | NotificationsPage, PurchasePage, glossary, mocks, etc. | 30 min |
| 6 | Gater ErrorState debug info avec isExpert | ErrorState.jsx L20-28 | 5 min |

### P1 — Corriger vite (cette semaine)

| # | Action | Fichier | Effort |
|---|--------|---------|--------|
| 7 | Supprimer 4 pages zombies | Dashboard, ActionPlan, CompliancePage, SiteDetail | 15 min |
| 8 | Fetcher portefeuilles depuis API | ScopeContext.jsx | 2h |
| 9 | Fixer expert toggle CommandPalette | CommandPalette.jsx L63-66 | 10 min |
| 10 | SIREN crédibles dans seed | packs.py L105 | 30 min |
| 11 | Ajouter ARIA sur Tabs | Tabs.jsx | 30 min |
| 12 | Ajouter /contracts-radar route ou supprimer du map | App.jsx + NavRegistry.js | 5 min |
| 13 | Supprimer console.log en prod | tracker.js, api.js | 10 min |

### P2 — Corriger ensuite (sprint suivant)

| # | Action | Effort |
|---|--------|--------|
| 14 | Unifier NAV_SECTIONS / NAV_MAIN_SECTIONS | 1h |
| 15 | Ajouter validation formulaire (dates, EUR) | 2h |
| 16 | Centraliser color tokens (severity, status) | 2h |
| 17 | Ajouter Input/Select error state + aria-invalid | 1h |
| 18 | Ajouter timestamps "dernière mise à jour" sur KPI | 2h |
| 19 | Documenter seuils métier (R², score≥60) | 1h |
| 20 | Ajouter breadcrumb section pour pages cachées | 30 min |

### Surveiller seulement

- i18n (acceptable en v1 France-only)
- Dark mode (nice-to-have, pas bloquant)
- Storybook design system (long terme)
- Pagination API stricte (200 sites max suffisant pour POC)

---

## 10. Plan priorisé

| Ordre | Action | Impact | Effort | Pourquoi maintenant |
|-------|--------|--------|--------|-------------------|
| 1 | Gater DevBadges ConformitePage | Élimine signal POC le plus visible | 5 min | Visible sur CHAQUE démo |
| 2 | Gater ErrorState debug | Élimine leak technique | 5 min | Visible sur chaque erreur |
| 3 | Gater seed functions | Élimine boutons dangereux | 10 min | Seed accidentel = catastrophe |
| 4 | Corriger accents français (15+) | Professionnalisme | 30 min | Visible partout |
| 5 | Fix org_id bypass (2 endpoints) | Sécurité | 30 min | Red flag audit sécurité |
| 6 | Warning MAX_SITES AnomaliesPage | Intégrité données | 15 min | Client 25 sites = problème |
| 7 | Supprimer pages zombies | Nettoyage, -3 092 lignes | 15 min | Réduit confusion future |
| 8 | Fix CommandPalette expert toggle | UX complète | 10 min | Raccourci promis mais cassé |
| 9 | SIREN crédibles dans seed | Crédibilité démo | 30 min | Prospect voit immédiatement |
| 10 | Fetch portefeuilles depuis API | Scope fonctionnel | 2h | Production impossible sans |

**Total effort P0+P1** : ~6h de travail ciblé

---

## 11. Verdict final

### PROMEOS est-il réellement crédible aujourd'hui ?

**Non, pas encore.** Le moteur métier (shadow billing, anomaly engine, compliance) est solide et crédible. Mais la couche de présentation trahit le POC : badges dev visibles, accents manquants, seed data apparente, 2 dashboards, pages mortes, debug info dans les erreurs. Un prospect attentif verrait ces signaux en 5 minutes.

### Qu'est-ce qui empêche un effet "top world" ?

1. **Manque de polish** — Les 15+ accents manquants et les badges dev visibles cassent immédiatement l'impression de produit fini
2. **Trop de pages** — 45 pages diluent le message produit. Un cockpit B2B best-in-class a 8-12 vues maximum
3. **Scores opaques** — 3 scores de conformité/maturité/readiness sans aucune documentation inline
4. **Données de démo faibles** — SIREN fake, rues génériques, pas de storytelling dans les données

### Qu'est-ce qui doit être corrigé AVANT toute nouvelle feature ?

Les 6 actions P0 du plan (2h de travail total) :
1. Gater DevBadges
2. Gater ErrorState debug
3. Gater seed functions
4. Corriger accents
5. Fix org_id bypass
6. Warning MAX_SITES

### Qu'est-ce qui doit être gelé car déjà assez bon ?

- **Shadow billing v2** — ne plus toucher, fonctionne et est crédible
- **Architecture navigation** — 5 modules stables, ne pas en ajouter
- **Design system UI** — KpiCard, PageShell, Skeleton, EmptyState, ErrorState — matures
- **Test suite** — 5 664 tests, ne pas régresser
- **Glossaire** — 90+ termes, complet

### Si je devais montrer PROMEOS demain à un prospect exigeant, qu'est-ce qui me ferait peur ?

1. **ConformitePage avec les badges dev** — game over en 3 secondes
2. **"Non definie"** dans les notifications — signal amateur
3. **Le prospect tape /cockpit puis /dashboard** — "pourquoi 2 dashboards identiques ?"
4. **Le prospect remarque "Groupe HELIOS" et SIREN 123456789** — "c'est du fake"
5. **Ctrl+Shift+X ne fait rien** — "vos raccourcis ne marchent pas"
6. **25 sites dans le scope → anomalies manquantes** — "il me manque des alertes"

---

## Annexe : Fichiers touchés par les corrections P0

```
frontend/src/pages/ConformitePage.jsx          → Gater DevApiBadge/DevScopeBadge
frontend/src/ui/ErrorState.jsx                 → Gater debug info
frontend/src/pages/BillIntelPage.jsx           → Gater seedBillingDemo
frontend/src/pages/MonitoringPage.jsx          → Gater generateMonitoringDemo
frontend/src/pages/AnomaliesPage.jsx           → Warning MAX_SITES
frontend/src/pages/NotificationsPage.jsx       → "Non définie"
frontend/src/pages/PurchasePage.jsx            → "durée", "marché"
frontend/src/pages/PurchaseAssistantPage.jsx   → "enregistrée"
frontend/src/pages/SiteDetail.jsx              → "enregistrée"
frontend/src/pages/AperPage.jsx                → "Fév"
frontend/src/ui/glossary.js                    → accents descriptions
frontend/src/mocks/obligations.js              → "Déclarer", "définir"
frontend/src/mocks/actions.js                  → accents
backend/routes/consumption_unified.py          → Filtrage org_id
```

---

*Audit réalisé par analyse statique + structurelle du code source, sans exécution live.*
*192 fichiers test (5 664 tests) validés green. Backend 18/18 Phase 2 green.*
