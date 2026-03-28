# AUDIT PROMEOS — ÉTAPE 5 : UX/UI SÉVÈRE TRANSVERSE — 24 mars 2026

> Audit UX/UI transverse du POC PROMEOS (8.6/10 métier, 0 P0 restant).
> Objectif : évaluer la démo-readiness SaaS B2B premium.
> Méthode : exploration des 8 pages métier clés + design system + navigation + états.

---

## 1. Résumé exécutif

**Verdict global UX/UI : 7.5/10** — Le POC est visuellement mature pour un prototype B2B énergie. 6 pages sur 8 sont au niveau PREMIUM. Pas de page cassée ou trompeuse. Les fondations design system sont solides (40+ composants UI, tokens centralisés, glossaire 100+ termes).

**3 faiblesses structurelles** empêchent le 9/10 UX :
1. **ErrorState sous-couvert** : seulement 14/40 pages gèrent les erreurs (35%)
2. **3 variantes KpiCard concurrentes** : KpiCard, MetricCard, UnifiedKpiCard — migration inachevée
3. **Boutons/textes démo visibles** en mode non-expert — "Seed demo", "Charger offres demo"

**0 page trompeuse** (tag TROMPEUR). Le récit produit est cohérent.

---

## 2. Forces UX/UI réelles

### PREMIUM — Ce qui impressionne déjà en démo

| Force | Preuve | Pages |
|---|---|---|
| **Skeletons universels** | `SkeletonKpi`, `SkeletonTable`, `SkeletonCard` — 66 instances sur 27 pages | Toutes pages clés |
| **Empty states contextuels** | 4 variantes (`empty`, `partial`, `unconfigured`, `error`) avec CTA adaptés, 40 pages couvertes | Patrimoine, Site360, Actions, BillIntel |
| **Glossaire pédagogique** | 100+ termes (TURPE, accise, BACS, anomalie…), 44 `<Explain>` dans les pages | BillIntel (11), Site360 (15), Conformité (3) |
| **Design tokens centralisés** | `colorTokens.js` (195L) : KPI_ACCENTS, SEVERITY_TINT, ACCENT_BAR, HERO_ACCENTS + `tint.module()` API | Toutes pages via PageShell |
| **5 modules tintés** | Pilotage (blue), Patrimoine (emerald), Énergie (indigo), Achat (amber), Admin (slate) — cohérence rail↔header↔page | NavRegistry + PageShell |
| **3 vues Actions** | Table + Kanban + Runbook (semaine) — flexible selon le profil utilisateur | ActionsPage |
| **Stepper 8 étapes** | PurchaseAssistant : progression visuelle, icônes, validation par étape, deep-link URL | PurchaseAssistant |
| **Virtual scrolling** | Patrimoine : `ROW_HEIGHT=52px`, `OVERSCAN=10` — fluide même avec 100+ sites | Patrimoine |
| **Scope persistant** | `ScopeContext` → localStorage `promeos_scope`, conservé entre pages, `applyDemoScope()` auto | Global |
| **Badges qualité données** | `ConsoSourceBadge` (metered/billed/estimated), `DataQualityBadge` (A-F), `FreshnessIndicator` (<45j/90j/365j) | Site360, Patrimoine |
| **TrustBadge** | Confiance élevée/moyenne/basse avec source + période | Site360, BillIntel, Actions |

### Tag : PREMIUM

---

## 3. Faiblesses UX/UI réelles

### 3.1 ErrorState sous-couvert

| Métrique | Valeur |
|---|---|
| Pages avec loading state | 27/40 (68%) ✅ |
| Pages avec empty state | 40/40 (100%) ✅ |
| Pages avec error state | **14/40 (35%)** ❌ |
| `AsyncState` wrapper disponible | Défini mais **0 adoption** |

**Pages clés sans ErrorState** : Patrimoine (error importé mais non branché), AnomaliesPage, AdminPages, ConnectorsPage, SegmentationPage, ImportPage, WatchersPage.

**Impact** : en cas d'erreur API, ces pages affichent soit un écran blanc soit restent en loading infini.

### Tag : À RISQUE UX

### 3.2 Trois variantes KpiCard concurrentes

| Variante | Fichier | Props | Usages |
|---|---|---|---|
| `KpiCard` | `ui/KpiCard.jsx` | icon, title/label, value, sub/sublabel, badge | 12 pages |
| `MetricCard` | `ui/MetricCard.jsx` | accent bar 3px, tinted icon pill, StatusDot | Cockpit, exécutif |
| `UnifiedKpiCard` | `ui/UnifiedKpiCard.jsx` | status-driven (success/warning/danger/info/neutral), border-left | Émergent, peu adopté |

**Problème** : migration inachevée. Certaines pages mélangent les 3. Props non alignées (`title` vs `label`, `sub` vs `sublabel`).

### Tag : PARTIEL

### 3.3 Badge status inconsistant

Le composant `Badge.jsx` définit 5 statuts (`ok`, `warn`, `crit`, `info`, `neutral`) mais les pages utilisent **7 variantes** :

| Utilisé | Sémantique | Problème |
|---|---|---|
| `ok` | Vert (conforme) | ✅ |
| `success` | Vert (aussi) | **Doublon de `ok`** |
| `warn` | Amber | ✅ |
| `warning` | Amber (aussi) | **Doublon de `warn`** |
| `crit` | Rouge | ✅ |
| `info` | Bleu | ✅ |
| `neutral` | Gris | ✅ |

### Tag : PARTIEL

### 3.4 Boutons/textes démo visibles en production

| Page | Élément visible | Risque |
|---|---|---|
| BillIntelPage | Bouton "Seed demo" | ⚠️ Visible sans gate `DEMO_MODE` |
| PurchasePage | "Charger les N offres demo" | ⚠️ Visible |
| PurchaseAssistantPage | "En mode demo, N offres sont pré-chargées" | ⚠️ Visible |

**Impact** : en rendez-vous client réel, ces textes cassent l'illusion de produit finalisé.

### Tag : À RISQUE CRÉDIBILITÉ

### 3.5 Accessibilité minimale

| Métrique | Valeur |
|---|---|
| Pages avec `sr-only` | 4/40 (10%) |
| `aria-label` dans pages | 39 instances (concentrées sur PurchaseAssistant) |
| `aria-live` régions | 1 seule (ToastProvider) |
| Tables avec `scope`/`rowheader` | 0 |

### Tag : PARTIEL

---

## 4. KPI / graphes / cartes — Analyse détaillée

### Cockpit — Hiérarchie KPI

Le cockpit est structuré en **3 niveaux de densité** (expert mode gate) :

| Niveau | Composant | KPIs | Visible par défaut |
|---|---|---|---|
| **Héros** | `CockpitHero` | Score santé, Risque €, Réduction DT %, Actions en cours | ✅ Toujours |
| **Trajectoire** | `TrajectorySection` | Courbe conso/% vs objectif DT | ✅ Toujours |
| **Détail expert** | `EssentialsRow` + `ExecutiveKpiRow` + `TopSitesCard` + `ModuleLaunchers` + 5 cards | 15+ KPIs | ❌ Derrière toggle "Analyse détaillée" |

**Verdict** : PREMIUM — La hiérarchie visuelle est bien gérée. Le non-expert voit 4 KPIs héros + trajectoire. L'expert peut déplier 15+ cartes.

**Point d'attention** : le toggle "Analyse détaillée" n'est pas assez visible. Un DAF pourrait ne jamais le trouver.

### Tag : PREMIUM (cockpit héros), CORRECT MAIS DENSE (section détail expert)

### KPIs potentiellement fragiles

| KPI | Page | Source | Risque |
|---|---|---|---|
| Score santé (gauge) | Cockpit | `compliance_score_service.py` A.2 | ✅ Calculé dynamiquement |
| Risque financier € | Cockpit | `kpi_service.get_financial_risk_eur()` | ⚠️ Label manque "théorique maximum" (P2-3) |
| Réduction DT % | Cockpit | `update_site_avancement()` via `dt_trajectory_service` | ✅ Câblé (sprint XS) |
| billing_anomalies_eur | Cockpit (breakdown) | `SUM(BillingInsight.estimated_loss_eur)` | ✅ Scopé (sprint S) |
| Maturité % | Cockpit essentials | Formule pondérée coverage+conformité+actions | ⚠️ Formule non exposée en UI |

---

## 5. Navigation et continuité inter-briques

### CTA inter-modules existants

| Depuis | Vers | CTA | Scope conservé |
|---|---|---|---|
| Cockpit hero | `/conformite` | Alerte prioritaire non-conformité | ✅ |
| Cockpit hero | `/actions` | "Actions en cours" click | ✅ |
| Cockpit sites table | `/sites/{id}` | Ligne cliquable | ✅ |
| Cockpit essentials | `/consommations` | Card "Consommation" | ✅ |
| Cockpit essentials | `/patrimoine` | Card "Patrimoine" | ✅ |
| Conformité badge risque | `/bill-intel` | **"Vérifier les factures →"** | ✅ (sprint S) |
| BillIntel bandeau | `/conformite` | **"Voir conformité →"** | ✅ (sprint S) |
| BillIntel CTA | `/achat` | "Optimiser l'achat énergie →" | ✅ |
| Site360 factures tab | `/billing?site_id=X` | "Voir timeline complète" | ✅ |
| Site360 factures tab | `/achat-assistant?site_id=X` | "Créer scénario d'achat" | ✅ |
| ActionsPage détail | Source via `buildSourceDeepLink()` | "Voir la source" | ✅ |
| AnomaliesPage row | Source page (BillIntel/Conformité/Patrimoine) | Click anomalie | ✅ |

### Récit patrimoine → conso → conformité → facture → achat → actions

| Maillon | Statut | Preuve navigation |
|---|---|---|
| Patrimoine → Conso | ✅ | Cockpit "Consommation" card, Site360 tab "Consommation" |
| Conso → Conformité | ✅ | MonitoringPage → "Voir conformité", DT trajectoire utilise conso |
| Conformité → Facture | ✅ | CTA "Vérifier les factures →" (sprint S P0-2) |
| Facture → Achat | ✅ | BillIntel → "Optimiser l'achat énergie →" |
| Achat → Actions | ✅ | Auto-sync actions achat, PurchaseActions dans action hub |
| Facture → Actions | ✅ | "Créer une action" depuis insight, `idempotency_key` |
| Conformité → Actions | ✅ | "Créer une action" depuis ConformitePage, ActionDrawer prefill |

**Verdict** : le fil conducteur est **complet en navigation**. Chaque maillon a au moins un CTA fonctionnel.

### Tag : PREMIUM (continuité navigation)

### Points de friction restants

| Friction | Impact | Fix |
|---|---|---|
| Toggle "Analyse détaillée" peu visible dans le cockpit | DAF ne voit pas les KPIs détaillés | Renommer en "Plus de détails ▾" avec couleur accent |
| Pas de breadcrumb contextuel dans Site360 | L'utilisateur oublie d'où il vient | Ajouter fil d'Ariane : Patrimoine > Site X > Tab |
| ConformitePage 4 tabs sans guidage initial | Nouvel utilisateur ne sait pas par quel tab commencer | GuidedModeBandeau existe mais expert-only |

---

## 6. Démo-readiness

### Ce qui impressionne en 30 secondes

1. **Cockpit héros** : 4 KPIs visuels + trajectoire DT → "le produit comprend mon risque"
2. **Patrimoine** : table virtualisée + carte + risk-first sorting → "je vois tout mon parc"
3. **BillIntel** : anomalies color-coded + shadow breakdown composant par composant → "il audite mes factures"
4. **PurchaseAssistant** : stepper 8 étapes + corridor P10/P50/P90 → "il m'aide à acheter"
5. **Actions Kanban** : drag-drop + 3 vues → "je pilote mes actions"

### Ce qui peut se faire démonter en 30 secondes

| # | Point faible | Scénario de démolition | Fix |
|---|---|---|---|
| 1 | Bouton "Seed demo" visible dans BillIntel | "Pourquoi il y a un bouton 'demo' dans votre produit ?" | Gater sur `DEMO_MODE` |
| 2 | "Charger offres demo" dans PurchasePage | "Ce sont de vraies offres marché ou du fake ?" | Gater sur `DEMO_MODE` |
| 3 | Risque financier sans qualification | "7 500 € c'est le max ? Le probable ? Le moyen ?" | Ajouter tooltip "amende maximale personne morale" |
| 4 | ConformitePage score formule cachée | "Comment vous calculez ce score ?" (hover-only) | Afficher formule inline ou panel dédié |
| 5 | Pas de benchmark sectoriel visible | "Comment je me compare à mon secteur ?" | P2-2 (effort L) |

---

## 7. Top P0 / P1 / P2 UX

### P0 UX — 0 trouvé

Aucun bloquant UX critique. Toutes les pages clés sont fonctionnelles et navigables.

### P1 UX — Crédibilité démo

| # | Problème | Pages | Impact | Effort |
|---|---|---|---|---|
| P1-UX-1 | **Boutons/textes démo visibles** sans gate `DEMO_MODE` | BillIntel, Purchase, PurchaseAssistant | Crédibilité tuée en RDV | XS |
| P1-UX-2 | **ErrorState manquant** sur 26 pages (écran blanc si API down) | Patrimoine, Anomalies, 24 autres | Impression d'instabilité | S |
| P1-UX-3 | **3 variantes KpiCard** concurrentes | Global | Incohérence visuelle subtile | M |
| P1-UX-4 | **Badge statuts dédoublés** (ok/success, warn/warning) | Global | Incohérence couleur | XS |

### P2 UX — Premium

| # | Problème | Impact | Effort |
|---|---|---|---|
| P2-UX-1 | Risque financier sans label "théorique max" | Crédibilité KPI | XS |
| P2-UX-2 | Score conformité formule hover-only | Transparence | S |
| P2-UX-3 | Toggle "Analyse détaillée" peu visible | DAF rate les détails | XS |
| P2-UX-4 | GuidedModeBandeau caché aux non-experts | Onboarding raté | XS |
| P2-UX-5 | Pas de breadcrumb dans Site360 | Navigation retour | S |
| P2-UX-6 | TrustBadge absent sur Conformité et Purchase | Confiance données | S |
| P2-UX-7 | FreshnessIndicator en texte plat (pas composant) | Lisibilité | XS |
| P2-UX-8 | Accessibilité : sr-only sur 4 pages seulement | Conformité RGAA | M |

---

## 8. Quick wins par effort

### XS (< 1 heure chacun)

| # | Action | Impact | Fichier |
|---|---|---|---|
| 1 | Gater boutons/textes démo sur `DEMO_MODE` | **+0.3 crédibilité** | BillIntelPage, PurchasePage, PurchaseAssistantPage |
| 2 | Unifier Badge : supprimer `success` (→ `ok`) et `warning` (→ `warn`) | Cohérence | Badge.jsx + pages appelantes |
| 3 | Tooltip risque financier "amende maximale PM" | Crédibilité KPI | Cockpit, ConformitePage |
| 4 | Renommer toggle "Analyse détaillée" → "Plus de détails ▾" | Discoverability | Cockpit.jsx |
| 5 | Afficher GuidedModeBandeau pour tous (pas expert-only) | Onboarding | ConformitePage.jsx |
| 6 | Utiliser `FreshnessIndicator` composant au lieu de `<span>` | Cohérence | BillIntelPage, ConformitePage |

### S (1-3 jours)

| # | Action | Impact |
|---|---|---|
| 7 | ErrorState sur les 26 pages manquantes (pattern `AsyncState`) | Robustesse perçue |
| 8 | TrustBadge sur ConformitePage et PurchasePage | Confiance données |
| 9 | Score conformité : panel "Comment c'est calculé" (toujours visible) | Transparence |
| 10 | Breadcrumb dans Site360 (Patrimoine > Site X > Tab) | Navigation retour |

### M (1-2 semaines)

| # | Action | Impact |
|---|---|---|
| 11 | Unifier sur UnifiedKpiCard, déprécier KpiCard/MetricCard | Cohérence long terme |
| 12 | Accessibilité : sr-only + aria-label sur pages critiques | Conformité RGAA |

---

## 9. Plan de correction priorisé

### Sprint UX immédiat (XS, < 1 jour)

Corrections 1-6 ci-dessus. Gain estimé : **+0.3 points** (8.6 → 8.9).

### Sprint UX court terme (S, 1 semaine)

Corrections 7-10. Gain estimé : **+0.2 points** (8.9 → 9.1).

### Sprint UX moyen terme (M, 2 semaines)

Corrections 11-12. Consolidation design system.

---

## 10. Verdicts par page

| Page | Lignes | Verdict | Justification |
|---|---|---|---|
| **Cockpit** | 1000+ | **PREMIUM** | Hiérarchie 3 niveaux, hero 4 KPIs, expert gate, trajectoire |
| **Patrimoine** | 2243 | **PREMIUM** | Virtual scroll, risk-first, map, DQ badges, 6 KPIs compacts |
| **Site360** | 1619 | **PREMIUM** | 6 tabs, 15 Explain, TrustBadge, FreshnessIndicator, deep drill-down |
| **ConformitePage** | 836 | **CORRECT MAIS DENSE** | Score /100 clair mais formule hover-only, 4 tabs dense |
| **BillIntelPage** | 1276 | **PREMIUM** | 5 KPIs, 11 Explain, workflow pills, TrustBadge |
| **PurchasePage** | 2024 | **CORRECT MAIS DENSE** | 4 tabs, scénarios riches mais expert-heavy, 2024L |
| **PurchaseAssistant** | 1864 | **PREMIUM** | Stepper 8 étapes, progression claire, deep-link |
| **ActionsPage** | 1592 | **PREMIUM** | 3 vues (table/kanban/runbook), ROI bar, empty states contextuels |
| **AnomaliesPage** | 720 | **PREMIUM** | Hub unifié, smart routing, severity color-coding |

**Score** : 6/8 PREMIUM, 2/8 CORRECT MAIS DENSE, 0 TROMPEUR, 0 À RISQUE UX critique.

---

## 11. Definition of Done UX

Le POC sera considéré **UX-ready pour démo B2B** quand :

1. ✅ 0 texte/bouton "demo" visible hors `DEMO_MODE`
2. ✅ ErrorState sur toutes les pages avec appels API
3. ✅ Badge statuts unifiés (5 valeurs : ok, warn, crit, info, neutral)
4. ✅ Risque financier qualifié ("amende maximale PM")
5. ✅ Score conformité formule visible sans hover
6. ✅ TrustBadge sur ConformitePage et PurchasePage
7. ✅ Un non-expert comprend le cockpit en < 60 secondes

---

*Audit UX/UI sévère transverse — 24 mars 2026. Verdict : 7.5/10 UX, 6/8 pages PREMIUM, 0 trompeuse.*
