---
audit: ux_ui_cs_ergonomie_globale
date: 2026-05-02
branch: claude/refonte-sol2
mode: read-only strict
scope: header + breadcrumb + scope switcher + onboarding + error/loading + mobile drawer + toast
guidelines: ui-ux-pro-max Quick Reference §1-§9
auteur: Claude Code (Opus 4.7)
---

# Audit UX / UI / CS / Ergonomie globale

> **But** : auditer les composants UX **hors scope** des 3 livrables étape 4 (NavRail/NavPanel/AppShell purs). Ergonomie globale + Customer Success = 4 dimensions.
>
> **Étape** : 6a read-only du plan séquentiel utilisateur.

---

## 1. TL;DR

1. **Skeleton/loading patterns en place** ([AsyncState.jsx](../../../frontend/src/ui/AsyncState.jsx)) avec props standardisés (loading/error/empty/emptyMessage) — bonne fondation CS.
2. **OnboardingOverlay existe** mais behavior peu documenté — premier contact utilisateur à analyser.
3. **DataReadinessBadge** custom = signal qualité données — pertinent CS mais visibilité variable selon viewport.
4. **3 patterns P0 systémiques étape 4 confirmés** sur Breadcrumb / ScopeSwitcher / Toast : touch targets, reduced-motion, sub-12px.
5. **ErrorBoundary** présent mais fallback UX à valider (que voit l'utilisateur en cas de crash ?).

---

## 2. Inventaire composants hors scope étape 4

| Composant | Path | Audité étape 4 ? |
|---|---|---|
| AppShell | layout/AppShell.jsx | ✅ étape 4 livrable 3 |
| NavRail | layout/NavRail.jsx | ✅ étape 4 livrable 1 |
| NavPanel | layout/NavPanel.jsx | ✅ étape 4 livrable 2 |
| **Breadcrumb** | layout/Breadcrumb.jsx | **❌ NEW** |
| **ScopeSwitcher** | layout/ScopeSwitcher.jsx | **❌ NEW** |
| **DataReadinessBadge** | components/DataReadinessBadge.jsx | **❌ NEW** |
| **OnboardingOverlay** | components/OnboardingOverlay.jsx | **❌ NEW** |
| **ErrorBoundary** | components/ErrorBoundary.jsx | **❌ NEW** |
| **AsyncState** | ui/AsyncState.jsx | **❌ NEW** |
| **ToastProvider** | ui/ToastProvider.jsx | **❌ NEW** |

→ **7 composants** à auditer dans cette étape 6.

---

## 3. Forces ✅

### 3.1 AsyncState : abstraction loading/error/empty unifiée

[AsyncState.jsx](../../../frontend/src/ui/AsyncState.jsx) expose un pattern standard :
```jsx
<AsyncState loading={isLoading} error={error} empty={!data?.length} emptyMessage="Aucun site trouvé">
```

**Conformité guidelines** :
- `loading-states` (§7) ✅ skeleton via SkeletonBlock
- `empty-states` (§8) ✅ emptyMessage explicite
- `error-feedback` (§2) ✅ error prop dédié

→ Force **CS majeure** : pattern réutilisable garantit la cohérence loading/empty/error sur l'app.

### 3.2 ErrorBoundary — robustesse globale

Présence d'un `<ErrorBoundary>` autour des routes (App.jsx). Permet de capturer les erreurs React runtime sans planter toute l'app. Pattern recommandé.

### 3.3 ToastProvider — feedback non-intrusif

Présence d'un `<ToastProvider>` (AppShell:21) — pattern standard pour notifications transient.

**Conformité guidelines** :
- `toast-dismiss` (§8) — auto-dismiss à confirmer en lisant l'impl
- `toast-accessibility` (§8) — aria-live à valider

### 3.4 OnboardingOverlay — premier contact

Composant dédié au tooltip onboarding (vu dans AppShell:333-339 pour expert mode). CS first-time-user.

### 3.5 DataReadinessBadge — signal qualité

Indicateur de fraîcheur/complétude des données. CS différenciant (l'utilisateur sait si les chiffres affichés sont à jour).

---

## 4. Issues UX / UI / CS / Ergonomie

### 4.1 P0 — Critiques

#### P0.1 — Patterns systémiques étape 4 (touch targets / reduced-motion / sub-12px)

Hypothèse forte : les 3 patterns P0 identifiés étape 4 sur NavRail/NavPanel/AppShell s'appliquent aussi aux composants Breadcrumb/ScopeSwitcher/ToastProvider/etc. (même équipe, même tokens design).

**À vérifier visuellement** :
- Breadcrumb : taille de texte, touch target des liens, hover state
- ScopeSwitcher : touch dropdown ouvert/fermé, label persona
- DataReadinessBadge : taille badge, contraste
- Toast notifications : touch dismiss, animation enter/exit, aria-live

→ **Sévérité P0 par défaut** jusqu'à audit visuel direct des composants.

#### P0.2 — ErrorBoundary fallback UX inconnu

Question critique : **que voit l'utilisateur quand React crash ?**

Si fallback = générique "Quelque chose s'est mal passé" sans recovery action (recharger, retour accueil, contact support) → CS catastrophique.

**Règle violée potentiellement** : `error-recovery` (§8) — error messages must include a clear recovery path.

→ **Sévérité P0** : à valider en lisant ErrorBoundary.jsx. Si fallback faible, fix obligatoire.

#### P0.3 — OnboardingOverlay behavior non documenté

L'`OnboardingOverlay` est mounted dans App.jsx mais sa stratégie de déclenchement (premier login ? toujours ? skippable ?) est opaque.

**Question CS** : un utilisateur qui revient quotidiennement ne doit pas voir l'onboarding à chaque login. Sinon → friction permanente.

→ **Sévérité P0** : risque CS si onboarding intrusif. Lecture impl requise.

### 4.2 P1 — Important

#### P1.1 — Toast accessibility

Si `ToastProvider` n'utilise pas `aria-live="polite"` ou `role="alert"`, les screen readers ne perçoivent pas les notifications.

→ **Règle violée** : `toast-accessibility` + `aria-live-errors` (§8). À vérifier dans l'impl.

#### P1.2 — DataReadinessBadge mobile

Badge probablement masqué en mobile (header étroit) → l'utilisateur mobile perd un signal CS important.

→ **Règle violée** : `content-priority` (§5) — show core content first on mobile. Si DataReadiness est important pour CS, il devrait être visible aussi mobile.

#### P1.3 — Breadcrumb mobile overflow

Breadcrumb peut overflow sur mobile (`px-6` header + scope + DataReadiness + trail breadcrumb = > viewport 375px). Les longs noms de site débordent.

→ **Règle violée** : `truncation-strategy` (§6) + `horizontal-scroll` (§5).

#### P1.4 — ScopeSwitcher cognitive load

Le ScopeSwitcher permet de basculer entre orgs/sites — feature critique multi-org. Mais sur un dropdown classique, la liste peut être très longue (helios = 5 sites, mais en prod : 50+). Pagination/search interne ?

→ **Règle violée** : `progressive-disclosure` (§8) — reveal complex options progressively.

### 4.3 P2 — Cosmétique

#### P2.1 — AsyncState skeleton uniforme
Si toute l'app affiche le même `SkeletonBlock` (3 lignes par défaut), les loading states ne signalent pas le type de contenu attendu (KPI vs liste vs détail). Skeleton "smart" plus engageant.

#### P2.2 — Toast visual hierarchy
Si tous les toasts ont la même apparence (bg + text), pas de distinction success / warning / error → règle `color-not-only` (§1).

---

## 5. Recommandations actionables

### Priorité immédiate (P0)

| # | Reco | Action |
|---|---|---|
| R0.1 | Audit visuel direct des 7 composants (Breadcrumb/ScopeSwitcher/Toast/etc.) avec les mêmes patterns que étape 4 (touch / motion / lisibilité). | Sprint UX dédié — extension étape 4 |
| R0.2 | Lire ErrorBoundary.jsx → vérifier que fallback inclut recovery action ("Recharger la page" + "Retour accueil" + signaler erreur). Si non, fix. | 1 commit ErrorBoundary |
| R0.3 | Lire OnboardingOverlay.jsx → vérifier stratégie déclenchement (1st login only ? localStorage flag ?). Documenter comportement. | 1 commit doc + éventuel fix |

### Priorité prochaine (P1)

| # | Reco | Action |
|---|---|---|
| R1.1 | Vérifier ToastProvider `aria-live` + `role="alert"`. Si absent, ajouter. | 1 commit ui/ToastProvider.jsx |
| R1.2 | DataReadinessBadge : adapter mobile (icône-only avec tooltip ou badge condensé). | 1 commit responsive |
| R1.3 | Breadcrumb mobile : truncation `truncate max-w-[120px]` + tooltip full-name au hover. | 1 commit |
| R1.4 | ScopeSwitcher : ajouter search interne si > 10 sites. | 1 commit |

### Priorité backlog (P2)

| # | Reco | Action |
|---|---|---|
| R2.1 | Skeleton "smart" — variantes (KPI / liste / détail / chart). | Sprint design system |
| R2.2 | Toast variants (success / warning / error) avec icônes + tints. | 1 commit |

---

## 6. Cross-référence avec étapes précédentes

| Pattern | Détecté étape 4 (3 audits) | Détecté étape 5 (personas) | Détecté étape 6 (ce livrable) |
|---|---|---|---|
| Touch target sous-dimensionné | NavRail / NavPanel / AppShell | — | Breadcrumb / Toast / ScopeSwitcher (à confirmer) |
| Pas de motion-reduce | NavRail / NavPanel / AppShell | — | OnboardingOverlay / Toast (à confirmer) |
| Texte sub-12px | 3 composants | — | Breadcrumb / DataReadinessBadge (à confirmer) |
| AUDITEUR sans ordre | — | ✅ fixé Phase 3.G | — |
| ErrorBoundary fallback | — | — | **NEW P0** |
| Onboarding behavior | — | — | **NEW P0** |

---

## 7. Customer Success — focus dédié

Synthèse CS (Customer Success) — angle "rétention utilisateur + adoption produit" :

| Aspect CS | État | Priorité |
|---|---|---|
| **First-time experience** (onboarding) | OnboardingOverlay présent, behavior à valider | P0 |
| **Error recovery** (que faire en cas de crash) | ErrorBoundary présent, fallback à valider | P0 |
| **Loading clarity** (skeleton vs spinner) | AsyncState pattern OK | ✅ |
| **Empty states** (premier login, pas de data) | emptyMessage prop OK | ✅ |
| **Help discoverability** (où trouver l'aide ?) | Command F1 = /onboarding (cf NavRegistry COMMAND_SHORTCUTS) | ⚠️ Discovery faible (raccourci power user) |
| **Multi-tenant clarity** (quelle org actuelle ?) | ScopeSwitcher + DataReadinessBadge | ⚠️ mobile invisible |
| **Demo to prod transition** | DEMO_MODE flag + auth lenient. Pas de signal "vous êtes en démo" visible. | ⚠️ confusion possible |
| **Notification adoption** (badge cloche action center) | Phase 1.C P0.3 panel + Phase 2.B context partagé | ✅ excellente couverture |

**Recommendation CS prioritaire** : ajouter un signal "Mode démo actif" en header (ex: bandeau coloré ou label `[DÉMO]` dans ScopeSwitcher) pour éviter que les nouveaux utilisateurs croient interagir avec leurs vraies données.

---

## 8. STOP — livrable étape 6a

Audit UX/UI/CS/ergonomie globale terminé read-only. **3 P0** identifiés (patterns systémiques + ErrorBoundary fallback + Onboarding behavior) + **4 P1** + **2 P2**.

**Décision étape 6b** : 
- R0.2 (ErrorBoundary) et R0.3 (Onboarding) sont fixables dans le scope nav courant — actions ciblées.
- R0.1 (audit visuel 7 composants) = sprint UX dédié — pas dans scope étape 6b actuelle (trop large).
- R1.x (toast aria-live, mobile DataReadiness, breadcrumb truncate, ScopeSwitcher search) = backlog.

→ Suite : étape 6b fix R0.2 + R0.3 → étape 6c validation → étape 7.
