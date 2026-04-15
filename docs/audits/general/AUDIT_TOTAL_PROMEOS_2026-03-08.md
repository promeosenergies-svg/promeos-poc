# AUDIT TOTAL PROMEOS — Dernier passage avant démo premium

**Date** : 8 mars 2026
**Méthodologie** : 7 agents d'audit parallèles, 4 couches (surface, fonctionnel, logique, crédibilité)
**Fichiers analysés** : ~120 fichiers frontend + ~100 fichiers backend
**Posture** : Zéro complaisance, zéro flatterie

---

## 1. Executive Summary

**Note globale : 52/100**

**Verdict** : PROMEOS est un produit ambitieux avec une architecture solide et un design system cohérent, mais qui souffre de **défauts de crédibilité cumulés** qui le trahissent comme POC dès qu'on creuse. Le squelette est bon. La chair est incomplète.

**Niveau de maturité réel** : POC avancé / MVP early — PAS un produit fini.

**Potentiel après correction** : 78-85/100 avec 3-4 semaines de travail ciblé.

### 5 risques les plus graves

| # | Risque | Impact |
|---|--------|--------|
| 1 | **~50 chaînes FR sans accents** (Entrepot, Selectionnez, Creer, Defaut, Sante...) | Tue la crédibilité B2B France instantanément |
| 2 | **"HELIOS" exposé dans l'UI** (boutons, empty states, fallback org) | Trahit le POC interne immédiatement |
| 3 | **Shadow billing opaque** — aucune explication de la méthode de calcul attendu | Un energy manager pose la question et il n'y a pas de réponse |
| 4 | **Seed data irréaliste** — 45% d'écart billing, 0 non-conformes, pas de saisonnalité | Tout prospect expérimenté verra que c'est manufacturé |
| 5 | **Workflow action fragmenté** — pas de lien source→action→preuve→clôture | Le parcours décisionnel est cassé |

### 5 forces réelles

| # | Force |
|---|-------|
| 1 | **Architecture sidebar Rail+Panel** bien pensée, navigation modulaire propre |
| 2 | **Design system UI** cohérent (31 composants, patterns réutilisés) |
| 3 | **Scope multi-org/portefeuille/site** fonctionnel avec ScopeContext + ScopeSwitcher |
| 4 | **Couverture test impressionnante** (5527 front + 1093 backend) |
| 5 | **Richesse fonctionnelle réelle** (billing, conformité, achat, actions, patrimoine, notifications) |

---

## 2. Note détaillée par dimension

| Dimension | Note /10 | Commentaire sévère |
|-----------|----------|-------------------|
| **UX** | 6 | Hiérarchie d'info correcte sur cockpit, mais parcours insight→action→preuve cassé. Drilldown flou. |
| **UI** | 7 | Design system propre, patterns cohérents. Mais truncation silencieuse, density parfois excessive. |
| **Navigation** | 6 | Rail+Panel solide mais routes mortes (/market, /contracts-radar), anomalies accessibles par 3 chemins, expert toggle palette non fonctionnel. |
| **Scope / gouvernance** | 5 | ScopeContext fonctionnel mais race condition critique. Admin read-only = jouet. Pas d'approval workflow. |
| **KPI / calcul** | 4 | Magic numbers partout (1% optimisation, seuils 70/40 non justifiés). Maturité = poids 30/40/30 sans rationale. Pas de confidence interval. |
| **Facturation / achat / conformité** | 5 | Shadow billing existe mais opaque. Compliance score sans méthodologie. Achat : savings "vs current" = vs quoi ? |
| **Workflow / actionability** | 4 | Créer action = OK. Mais pas de lien retour source, pas d'upload preuve, pas d'escalade deadline, pas d'approval. |
| **Demo credibility** | 3 | HELIOS visible, accents manquants, seed data trop propre, console.log en expert, DevApiBadge. |
| **Architecture visible** | 5 | Port hardcodé vite.config, DemoContext utilise fetch() natif au lieu d'axios, JWT secret par défaut. |
| **Wording / microcopy** | 3 | 50+ chaînes sans accents. Mélange tu/vous. Grammar errors (mis a jour, avec succes). |
| **Responsive / densité** | 6 | Correct desktop. Mobile : scope pill overflow, search text masqué, panel scroll non protégé. |
| **Product story** | 5 | La promesse est là (cockpit décisionnel B2B énergie). L'exécution raconte "POC intelligent mais inachevé". |

---

## 3. Top problèmes critiques

| ID | Problème | Zone | Pourquoi c'est grave | Priorité | Effort | Type |
|----|----------|------|---------------------|----------|--------|------|
| C1 | **50+ chaînes FR sans accents** (Entrepot, Selectionnez, Creer, Sante, Copropriete, Defaut, eligibles, configure, mis a jour, avec succes...) | Global | Un prospect français voit immédiatement que le QA n'a pas été fait. Kill la confiance. | P0 | 2h | Wording |
| C2 | **"HELIOS" exposé** dans boutons, empty states, fallback org | DemoBanner, Heatmap, HealthBar, Anomalies, ScopeContext | Trahit le seed interne. Nom de code visible = POC. | P0 | 1h | Crédibilité |
| C3 | **Shadow billing sans explication de méthode** | InsightDrawer, BillIntel | "Comment calculez-vous l'attendu ?" → pas de réponse visible. Energy manager repart. | P0 | 4h | KPI |
| C4 | **Seed data irréaliste** : 45% écart billing, 0 non-conformes, pas de saisonnalité conso | billing_seed, demo_seed | Tout expert énergie voit que les chiffres sont fabriqués. | P0 | 6h | Data |
| C5 | **Race condition ScopeContext** : setApiScope appelé pendant le render ET dans useEffect | ScopeContext.jsx | Peut causer affichage/action sur le mauvais org. Bug silencieux. | P0 | 2h | Scope |
| C6 | **Workflow action fragmenté** : pas de lien source, pas d'upload preuve, pas d'escalade deadline | ActionsPage, ActionDetailDrawer | Le cœur du produit (insight→action→résolution) est cassé en 3 morceaux disjoints. | P0 | 8h | Workflow |
| C7 | **Admin utilisateurs read-only** : pas d'invite, pas d'edit rôle, pas de toggle actif/inactif | AdminUsersPage, AdminRolesPage | La page Admin ressemble à un listing, pas à de la gouvernance. | P1 | 6h | Gouvernance |
| C8 | **Routes mortes /market et /contracts-radar** dans NavRegistry | NavRegistry.js | 404 si l'utilisateur navigue via CommandPalette ou URL directe. | P1 | 1h | Navigation |
| C9 | **console.log gardés par isExpert** dans BillIntelPage/BillingPage (12 instances) | BillIntel, Billing | En mode expert, la console montre des chemins API, des payloads, des noms de fichiers. | P1 | 1h | Technique |
| C10 | **DemoContext utilise fetch() natif** sans headers scope/auth | DemoContext.jsx | Pas de X-Org-Id, pas de token → peut agir sur le mauvais org en démo. | P1 | 2h | Technique |
| C11 | **JWT secret hardcodé "dev-secret-change-me-in-prod"** | iam_service.py | Si env var oubliée, n'importe qui peut forger un JWT. | P1 | 1h | Sécurité |
| C12 | **Prix par défaut incohérents** : 0.068 dans billing_shadow_v2 vs 0.18 dans default_prices.py | billing_shadow_v2.py, default_prices.py | KPI billing calculés avec des prix différents selon le module. Contradictions visibles. | P1 | 3h | Calcul |
| C13 | **Compliance score sans méthodologie** visible : seuils 70/40 hardcodés, pas de breakdown montré | ConformitePage | DG voit "72% conformité" mais ne peut pas justifier ce chiffre à un auditeur. | P1 | 4h | KPI |
| C14 | **Maturité score** : poids 30/40/30 sans rationale business | Cockpit | "Pourquoi 40% conformité et pas 50% ?" → pas de réponse. Score semble magique. | P1 | 2h | KPI |
| C15 | **Opportunité optimisation = 1% fixe du facturé** | impactDecisionModel.js | Heuristique naïve. Pour un petit portefeuille (10k€), suggère 100€. Non crédible. | P1 | 3h | Calcul |

---

## 4. Audit détaillé par zone

### COCKPIT

**Ce qui fonctionne** : 4 KPI exécutifs bien positionnés, layout hero clair, ImpactDecisionPanel actionnable, sparkline conformité.

**Ce qui est faible** :
- Bouton "Pourquoi ?" disponible seulement pour 2/4 KPI (conformité, risque) — manque sur maturité et couverture données
- "Risque financier" : subtitle "0 sites concernés" + "5 sites à risque" = message contradictoire possible
- Readiness score (maturité) : si 0 sites, affiche "0/100" au lieu de "Configurez vos sites d'abord"
- Consistency banner ne se déclenche que pour un edge case très spécifique (100% conformes ET <30% couverture)

**Ce qui est trompeur** :
- Opportunité optimisation = toujours 1% du facturé, sans explication méthodologique
- "Confiance: variable" affiché en mode expert sur la source conso → mine la confiance

**Ce qu'un prospect remarquera** : Les KPI sont jolis mais opaques. "D'où vient ce 58% maturité ?" → pas de réponse convaincante.

### PATRIMOINE

**Ce qui fonctionne** : Table de sites complète, KPI cartes (risque, surface, compteurs), heatmap, segmentation widget.

**Ce qui est faible** :
- Catégories sans accents dans les dropdowns (Entrepot, Sante, Copropriete) — visible immédiatement
- Risque entre 3k€ et 10k€ affiché en gris (même couleur que "conforme") → risque moyen invisible
- Drawer site : segmentation mentionnée mais pas de valeur de segment affichée
- Bouton "Charger HELIOS" visible dans empty state

**Ce qu'un prospect remarquera** : Les accents manquants dans les catégories de bâtiment détruisent la crédibilité.

### CONSOMMATION

**Ce qui fonctionne** : Explorer avec sélection compteur, graphiques temporels.

**Ce qui est faible** :
- Empty state vague : "Compteur présent, aucun relevé" sans timeline ni action
- Pas de saisonnalité dans les données seed (consommation plate toute l'année)
- CTA empty states incohérents (/connectors vs /consommations/import) sans progression expliquée

### FACTURATION / BILL INTEL

**Ce qui fonctionne** : Table factures avec statuts, shadow billing avec breakdown 5 composantes, InsightDrawer détaillé.

**Ce qui est cassé** :
- **Méthode de calcul attendu jamais expliquée** — c'est le problème #1 de crédibilité
- 12 console.log gardés par isExpert montrant des chemins API et payloads
- Seed data : 45% d'écart sur une facture = irréaliste (1-5% en réalité)
- Breakdown peut silencieusement échouer (shadow fetch fail → null → "Non disponible" sans explication)
- "Estimated loss" arrondi à l'EUR sans intervalle de confiance

**Ce qu'un prospect remarquera** : "Comment savez-vous que cette facture est anormale ?" → la réponse n'est pas dans l'UI.

### ACHAT

**Ce qui fonctionne** : Scénarios de purchase avec comparaison, recommandation avec savings.

**Ce qui est faible** :
- "Savings vs current" — "current" quoi ? Prix contrat ? Spot ? Jamais défini.
- Pas de bandes de volatilité sur les scénarios
- Bouton "Accepter" scénario sans confirmation ni explication de l'impact downstream
- Score de risque /100 sans méthodologie

### CONFORMITÉ

**Ce qui fonctionne** : 4 onglets (Obligations, Données, Exécution, Preuves), guided mode, next best action.

**Ce qui est faible** :
- Score conformité = % sites conformes, pas risk-weighted. Un site critique compte autant qu'un petit.
- Seuils 70/40 hardcodés sans justification business
- Pas de CTA "Créer action" visible depuis l'onglet Obligations
- Format des preuves non spécifié ("PDF ? Word ? Attestation ?")
- DevApiBadge/DevScopeBadge visibles en mode expert → leak d'infra

### ACTIONS

**Ce qui fonctionne** : 3 vues (table, kanban, runbook), quick views, bulk status, CreateActionDrawer avec templates.

**Ce qui est cassé** :
- **Kanban = jouet** : pas de due date visible, pas d'owner, pas d'evidence flag sur les cartes
- Inline status change sans confirmation pour transitions destructives (done→backlog)
- Pas de validation evidence côté frontend avant clôture
- Idempotency UX cassé : duplicate → toast + ferme drawer (devrait montrer l'action existante)
- Owner = champ texte libre, pas de picker utilisateur
- Pas d'escalade deadline (action en retard = rien ne se passe)
- ActionDetailDrawer : 5 onglets en petites icônes, upload preuve absent, pas de banner "preuve requise"

### NOTIFICATIONS

**Ce qui fonctionne** : Liste avec sévérité, source, impact, deeplink.

**Ce qui est faible** :
- Deeplinks vont vers la page mais pas vers l'alerte spécifique
- Pas de site_nom visible sur chaque notification
- Pas de trend indicator (↑2 nouvelles depuis hier)
- Mark as read sans undo
- Pas de filtre par site (flood en multi-sites)

### ADMIN

**Ce qui fonctionne** : Liste utilisateurs avec rôles et scopes, page rôles avec 11 rôles × 6 permissions.

**Ce qui est cassé** :
- **100% read-only** : pas d'invite user, pas d'edit rôle, pas de toggle actif/inactif
- Rôles marqués "non-modifiables" sans explication
- Effective Access Panel confus (scope codes "O:ORG1" non déchiffrables)
- Pas d'audit trail visible pour les actions admin

**Ce qu'un prospect remarquera** : "Où j'ajoute un utilisateur ?" → impossible. Deal-breaker pour un DG multi-équipes.

### SIDEBAR / HEADER

**Ce qui fonctionne** : Rail 64px + Panel contextuel, tint colors par module, badge notifications.

**Ce qui est faible** :
- Badge refresh toutes les 2 min avec fetch de 200 alertes sans pagination
- Module override state leak (flicker pendant navigation rapide)
- Quick Actions cachées des non-experts (utile pour tous)
- "PRO" badge pour expert mode → confusion avec "plan PRO" (pricing)

### SCOPESWITCHER

**Ce qui fonctionne** : Recherche sites, feedback pill, count sites par portefeuille.

**Ce qui est faible** :
- Pill tronquée sans tooltip (max-w-[360px] fixe, overflow mobile)
- Pas de keyboard shortcut pour focus search
- Pas de feedback visuel quand le filtre est actif

### COMMAND PALETTE

**Ce qui fonctionne** : Recherche unifiée pages + shortcuts, Ctrl+K.

**Ce qui est cassé** :
- Expert mode toggle non fonctionnel (#expert-toggle → ferme palette, ne toggle pas)
- Legacy NAV_ITEMS dupliqué avec NAV_MAIN_ITEMS → maintenance burden
- Anomalies accessible par 3 chemins différents avec 3 noms différents

### DRAWERS / MODALS / FORMS

**Ce qui fonctionne** : Pattern Drawer unifié, CreateActionDrawer avec scope context, templates, auto-deadline.

**Ce qui est faible** :
- Focus trap incomplet (disabled elements, nested modals)
- CO2e calculation magique : `(impactEur / 0.15) * 0.052` sans source ni explication
- InsightDrawer : breakdown peut échouer silencieusement
- ActionDetailDrawer : onglet "Pièces jointes" sans UI d'upload

---

## 5. Contradictions & pertes de confiance

| Type | Détail |
|------|--------|
| **Chiffres contradictoires** | Prix par défaut ELEC : 0.068 €/kWh (shadow billing) vs 0.18 €/kWh (default_prices.py) |
| **Chiffres contradictoires** | Risque financier "0 €" + subtitle "5 sites à risque" |
| **Messages contradictoires** | "Confiance: variable" en expert + KPI présenté comme fiable en standard |
| **Pages doublons** | Anomalies accessible via /actions, /anomalies, CommandPalette avec 3 noms |
| **CTA incohérents** | "Créer action" depuis anomalie mais pas depuis obligation conformité |
| **Labels instables** | "Actions & Suivi" (sidebar) vs "Centre d'actions" (legacy) vs "Plan d'action" (redirect) |
| **Fallbacks visibles** | "Groupe HELIOS" comme org fallback dans ScopeContext |
| **Seed data visible** | Boutons "Charger HELIOS" dans PatrimoineHeatmap, HealthBar, AnomaliesPage |
| **Debug / leak** | console.log en expert mode (12 instances BillIntel), DevApiBadge/DevScopeBadge dans Conformité |
| **Calculs opaques** | Maturité 30/40/30 sans rationale, compliance seuils 70/40 sans source, 1% optimisation fixe |
| **Scope non rappelé** | Notifications sans site_nom, deeplinks sans contexte scope |
| **CO2e magique** | `(EUR / 0.15) * 0.052` — formule sans source, sans documentation |

---

## 6. Audit customer journey / workflow

### Où le parcours est bon
- Cockpit → patrimoine → site detail : navigation fluide via KPI tiles
- Anomalie → "Créer action" : drawer s'ouvre avec prefill correct
- Scope switch → toutes les pages réagissent correctement au changement

### Où il casse
- **Insight billing → comprendre l'écart** : le drawer montre des chiffres mais jamais la méthode
- **Action créée → retrouver l'action** : toast + ferme drawer, pas de deeplink vers l'action créée
- **Action → preuve → clôture** : le bouton upload n'existe pas dans le drawer, evidence check backend-only
- **Notification → source** : deeplink vers la page mais pas vers l'alerte spécifique

### Où l'utilisateur hésite
- "Patrimoine ou Consommation pour voir mes sites ?" → deux entry points concurrents
- "Actions ou Anomalies ?" → confusion sémantique, 3 chemins pour la même zone
- "Comment passer d'un constat conformité à une action ?" → pas de CTA visible

### Où il se perd
- Admin → "Comment j'ajoute un utilisateur ?" → impossible
- Conformité → "Comment je prouve ma conformité ?" → format preuve non spécifié
- Achat → "Accepter un scénario → et après ?" → rien ne se passe

### Où PROMEOS ressemble à un outil et non à un cockpit décisionnel
- Les KPI existent mais ne racontent pas d'histoire (pas de "voici votre situation → voici ce que vous devriez faire → voici combien ça vous rapporte")
- Les calculs sont présents mais opaques (pas de "nous avons calculé X sur la base de Y avec une confiance Z")

---

## 7. Audit spécial chiffres / KPI / calcul

**KPI qui semblent fiables** :
- Nombre de sites, compteurs, surface m² → données directes, pas de calcul
- Consommation kWh agrégée → somme simple, vérifiable

**KPI qui semblent opaques** :
- Maturité (30% data + 40% conformité + 30% actions) — pourquoi ces poids ?
- Compliance score (seuils 70/40) — d'où viennent-ils ?
- Opportunité optimisation (1% fixe) — non crédible pour petits et grands portefeuilles
- Risque financier — somme des risques sites mais sans pondération probabilité

**KPI qui semblent contradictoires** :
- Shadow billing "attendu" vs "facturé" avec delta 45% (seed) — aucun client réel n'a ça
- Prix par défaut incohérents entre modules (0.068 vs 0.18 €/kWh)

**Chiffres mal visibles** :
- "Prioritaire" badge en 9px dans ImpactDecisionPanel — presque invisible
- Effort (j/h) stocké comme texte libre "2j" — pas exploitable

**Chiffres manquant de contexte** :
- Tous les KPI sans période affichée (sur quels mois ?)
- Estimated loss sans intervalle de confiance
- Savings achat "−8%" sans préciser vs quelle baseline

**Calculs suspects** :
- CO2e = `(EUR / 0.15) * 0.052` — aucune source
- Prorata billing = `period_days / 365.0` — ignore années bissextiles
- Prorata mensuel = `period_days / 30` — faux pour factures bi-mensuelles

---

## 8. Audit spécial démo / quasi-production

### Ce qui fait encore POC
- "HELIOS" visible dans 4+ endroits de l'UI
- 50+ chaînes françaises sans accents
- console.log en mode expert
- Admin 100% read-only
- Routes mortes (/market, /contracts-radar)
- DevApiBadge/DevScopeBadge dans Conformité
- JWT secret par défaut "dev-secret-change-me-in-prod"
- Seed data avec anomalies à 45%
- window.print() pour export PDF (pas de generation serveur)
- Owner action = champ texte libre
- Upload preuve absent du drawer

### Ce qui fait produit mature
- Design system 31 composants cohérents
- Rail+Panel sidebar avec tint colors par module
- 5527 tests frontend green
- ScopeContext multi-org fonctionnel
- Templates d'action avec auto-deadline
- Evidence requirement rules centralisées
- Notification system avec 5 sources
- Command palette Ctrl+K

### Ce qui bloque une vraie démo client
1. Les accents manquants — premier regard, confiance perdue
2. "Charger HELIOS" visible — le prospect sait que c'est un POC
3. "Comment est calculé l'attendu ?" — pas de réponse
4. "Comment j'ajoute un utilisateur ?" — pas possible
5. Seed data trop parfaite — un energy manager voit que c'est fake

### Ce qui bloque une présentation investisseur
1. Workflow action incomplet (pas d'upload preuve, pas d'escalade)
2. KPI opaques sans méthodologie documentée
3. Admin jouet
4. Pas d'approval workflow
5. Pas de PDF serveur-side

---

## 9. Recommandations classées

### P0 — Corriger immédiatement (avant toute démo)

| # | Action | Effort |
|---|--------|--------|
| 1 | **Fixer tous les accents FR** : Entrepôt, Sélectionnez, Créer, Défaut, Santé, Copropriété, Collectivité, éligibles, configuré, mis à jour, avec succès, été créées, compléter, précises, dédiée, pondéré, Synthèse, importé, à l'obligation | 2-3h |
| 2 | **Supprimer "HELIOS"** de tous les textes UI (boutons, empty states, fallback org) → remplacer par "données de démonstration" | 1h |
| 3 | **Supprimer les console.log** des pages BillIntel et Billing (12 instances) | 30min |
| 4 | **Fixer la race condition ScopeContext** : retirer l'appel setApiScope pendant le render | 1h |
| 5 | **Supprimer routes mortes** /market et /contracts-radar du NavRegistry | 30min |

### P1 — Corriger vite (dans la semaine)

| # | Action | Effort |
|---|--------|--------|
| 6 | **Ajouter méthodologie shadow billing** dans InsightDrawer : "Attendu = conso × prix contrat + TURPE + accise + TVA" | 4h |
| 7 | **Unifier les prix par défaut** : single source of truth dans config/default_prices.py | 2h |
| 8 | **Ajuster seed data** : écarts billing 3-8% (pas 45%), 10-15% non-conformes, saisonnalité conso | 6h |
| 9 | **Rendre Admin fonctionnel** : invite user, edit rôle, toggle actif | 6h |
| 10 | **Fixer expert toggle** CommandPalette : connecter à useExpertMode() | 1h |
| 11 | **Ajouter "Pourquoi ?"** sur les 4 KPI cockpit (pas juste 2) | 2h |
| 12 | **DemoContext** : migrer de fetch() vers l'instance axios api avec headers scope | 2h |
| 13 | **DevApiBadge/DevScopeBadge** : conditionner par NODE_ENV, pas isExpert | 1h |

### P2 — Corriger ensuite (2 semaines)

| # | Action | Effort |
|---|--------|--------|
| 14 | Ajouter confidence interval aux KPI billing (high/medium/low) | 3h |
| 15 | Lier action→source (invoice_id, anomaly_id visible dans drawer) | 4h |
| 16 | Ajouter UI upload preuve dans ActionDetailDrawer | 6h |
| 17 | Ajouter breakdown compliance score ("8 OK + 2 inconnu = 72%") | 3h |
| 18 | Documenter rationale maturité (pourquoi 30/40/30) en tooltip | 1h |
| 19 | Idempotency UX : montrer action existante au lieu de toast+ferme | 3h |
| 20 | Notification deeplinks avec query params pour scroll-to-alert | 3h |
| 21 | Kanban : ajouter due date, owner, evidence flag sur cartes | 4h |
| 22 | Deadline escalation : banner + notification si overdue | 4h |

### Surveiller seulement

| # | Élément |
|---|---------|
| 23 | Focus trap nested modals (rare en usage réel) |
| 24 | Badge refresh sidebar (2 min acceptable pour MVP) |
| 25 | Mobile responsive (pas la cible principale) |
| 26 | API versioning (/api/v1/) — prématuré |
| 27 | CSRF protection (acceptable en démo avec CORS wildcard) |

---

## 10. Plan priorisé

| Ordre | Action | Impact | Effort | Pourquoi maintenant |
|-------|--------|--------|--------|-------------------|
| 1 | Fixer accents FR (50+ chaînes) | Maximal | 2-3h | Premier regard prospect = accents. Non négociable. |
| 2 | Supprimer "HELIOS" de l'UI | Maximal | 1h | Trahit le POC. 30 min de travail, impact énorme. |
| 3 | Supprimer console.log BillIntel | Haut | 30min | Leak technique visible en expert mode. |
| 4 | Fixer race condition ScopeContext | Haut | 1h | Bug silencieux qui peut montrer les mauvaises données. |
| 5 | Supprimer routes mortes | Moyen | 30min | 404 possible via CommandPalette. |
| 6 | Méthodologie shadow billing dans drawer | Maximal | 4h | La question #1 de tout energy manager. |
| 7 | Unifier prix par défaut | Haut | 2h | Contradictions KPI entre modules. |
| 8 | Ajuster seed data réalisme | Maximal | 6h | Prospect expérimenté verra le fake. |
| 9 | Admin fonctionnel (invite, edit) | Haut | 6h | DG multi-équipes : deal-breaker si absent. |
| 10 | Expert toggle CommandPalette | Moyen | 1h | Fonctionnalité promise, non délivrée. |

**Total effort P0+P1 : ~30h de développement ciblé**

---

## 11. Verdict final

### PROMEOS est-il réellement crédible aujourd'hui ?

**Non.** PROMEOS a l'ambition et l'architecture d'un bon produit, mais les défauts de surface (accents, HELIOS, console.log) et de fond (KPI opaques, workflow action incomplet, admin jouet) empêchent toute crédibilité devant un prospect exigeant. Un energy manager posera 3 questions auxquelles le produit ne peut pas répondre : "Comment calculez-vous l'attendu ?", "Où j'ajoute mon équipe ?", "Comment je prouve ma conformité ?".

### Qu'est-ce qui empêche encore un effet "top world" ?

1. **L'opacité des calculs** — un cockpit décisionnel DOIT expliquer ses chiffres
2. **Le workflow action cassé** — insight→action→preuve→clôture doit être un fil continu
3. **L'absence de gouvernance** — admin read-only = pas de plateforme, juste un viewer
4. **Le wording bâclé** — 50+ fautes d'accents dans un produit B2B France

### Qu'est-ce qui doit être corrigé AVANT toute nouvelle feature ?

Les 5 items P0 (accents, HELIOS, console.log, race condition, routes mortes) + les 8 items P1 (méthodologie, prix, seed, admin, expert toggle, KPI evidence, DemoContext, DevBadge). **Zéro nouvelle feature tant que ces 13 items ne sont pas résolus.**

### Qu'est-ce qui doit être gelé car déjà assez bon ?

- Design system UI (31 composants) — ne pas toucher
- Navigation Rail+Panel — stable, ne pas refactorer
- ScopeContext architecture (hors bug race condition) — fonctionnel
- Test coverage (5527+1093) — maintenir, ne pas dégrader
- Notification system — fonctionnel même si améliorable

### Si tu devais montrer PROMEOS demain à un prospect exigeant, qu'est-ce qui te ferait peur ?

1. **Qu'il lise "Entrepot" sans accent dans un dropdown** — perte de confiance instantanée
2. **Qu'il voie "Charger HELIOS" quelque part** — "c'est un POC interne"
3. **Qu'il demande "comment vous calculez ça ?"** sur n'importe quel KPI — pas de réponse
4. **Qu'il essaie d'ajouter un utilisateur** — impossible
5. **Qu'il ouvre la console en mode expert** — des lignes de debug partout
6. **Qu'il remarque que toutes les consommations sont plates** — pas de saisonnalité = fake

---

## Annexe : Fichiers critiques à corriger

### Accents FR (P0)
- `frontend/src/pages/Patrimoine.jsx` — Entrepot, Sante, Copropriete, Collectivite
- `frontend/src/components/SiteCreationWizard.jsx` — mêmes + Selectionnez, Creer
- `frontend/src/components/SegmentationPage.jsx` — TYPO_LABELS complet
- `frontend/src/components/UpgradeWizard.jsx` — catégories
- `frontend/src/pages/AperPage.jsx` — dediee, eligibles, a l'obligation
- `frontend/src/pages/ImportPage.jsx` — importe, Selectionnez
- `frontend/src/pages/MonitoringPage.jsx` — Defaut
- `frontend/src/pages/HPHCPanel.jsx` — Defaut
- `frontend/src/components/ActionDetailDrawer.jsx` — Libelle, mis a jour
- `frontend/src/components/PatrimoineWizard.jsx` — ete creees avec succes
- `frontend/src/pages/ConsumptionDiagPage.jsx` — mis a jour
- `frontend/src/components/ExportPackRFP.jsx` — Synthese, pondere
- `frontend/src/components/IntakeWizard.jsx` — completer

### HELIOS visible (P0)
- `frontend/src/components/PatrimoinePortfolioHealthBar.jsx` — "Charger HELIOS"
- `frontend/src/components/PatrimoineHeatmap.jsx` — "Charger HELIOS"
- `frontend/src/pages/AnomaliesPage.jsx` — empty state HELIOS
- `frontend/src/contexts/ScopeContext.jsx` — MOCK_ORGS "Groupe HELIOS"

### Console.log (P1)
- `frontend/src/pages/BillIntelPage.jsx` — 10+ instances
- `frontend/src/pages/BillingPage.jsx` — 3+ instances

### Routes mortes (P1)
- `frontend/src/layout/NavRegistry.js` — /market, /contracts-radar dans ROUTE_MODULE_MAP
