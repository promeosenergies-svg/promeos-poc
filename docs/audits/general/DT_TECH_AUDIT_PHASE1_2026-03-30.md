# DT_AUDIT_PHASE1 — Audit Dette Technique Phase 1

> **Date** : 2026-03-30
> **Auditeur** : Claude Opus 4.6 (multi-agent, 5 explorateurs paralleles)
> **Commit** : `c702a95` (branche `claude/audit-phase-1-sceWb`)
> **Methode** : Lecture exhaustive de ~30 fichiers critiques, zero modification appliquee
> **Perimetre** : Backend (15 fichiers), Frontend (13 fichiers), Infra (5 fichiers)

---

## 1. Executive Summary

| Critere | Valeur |
|---------|--------|
| **Note globale** | **58/100** (dette technique) |
| **Verdict** | POC fonctionnellement riche mais dette technique significative avant mise en production |
| **Constats P0 (critiques)** | **10** |
| **Constats P1 (eleves)** | **23** |
| **Constats P2 (moyens)** | **12** |
| **Effort total estime** | ~15-20 jours-dev pour atteindre 80/100 |

### Top 5 risques

1. **Securite** — JWT secret hardcode en fallback + token localStorage non chiffre + CORS wildcard
2. **Fuite de donnees** — 2 endpoints consommation sans filtrage `org_id` (acces cross-org)
3. **Fiabilite** — 40+ blocs `except Exception: pass` masquent silencieusement les erreurs
4. **Maintenabilite** — 5 fichiers > 1 500 LOC (max 2 243L), 533 `print()` au lieu de `logging`
5. **Architecture** — Double moteur conformite (deprecie mais toujours appele), services deprecies en production

### Top 5 forces

1. **Couverture de tests** — 5 587 tests frontend + 824 tests backend + 24 specs E2E Playwright
2. **Architecture backend** — 462 endpoints bien structures, separation services/routes/models
3. **Design system frontend** — KpiCard, PageShell, Skeleton/Loading/Empty/Error states systematiques
4. **Moteur billing** — Shadow billing V2 avec TURPE 7 CRE reel, 10 regles anomalie
5. **Conformite reglementaire** — 3 frameworks (Decret Tertiaire, BACS, APER) avec orchestration unifiee

---

## 2. Metriques structurelles

| Metrique | Valeur | Statut |
|----------|--------|--------|
| Endpoints API | **462** (GET: 262, POST: 153, PATCH: 21, DELETE: 14, PUT: 12) | OK |
| Modeles SQLAlchemy | **60** fichiers | OK |
| Services backend | **142** fichiers | OK |
| Pages frontend | **50** fichiers JSX (32 823 lignes) | Attention |
| Tests frontend (Vitest) | **5 587** | OK |
| Tests backend (pytest) | **824+** | OK |
| Tests E2E (Playwright) | **24** specs | OK |
| `print()` Python | **533** occurrences / 37 fichiers | Probleme |
| `console.log()` JS | **107** occurrences / 24 fichiers | Probleme |
| `datetime.utcnow()` deprecie | **10+** usages | Probleme |
| ESLint rules desactivees | **30+** violations explicites | Probleme |
| `React.memo` | **0** usage | Probleme |
| Fichiers > 1 000 LOC | **11** (max: Patrimoine.jsx 2 243L) | Probleme |
| TODO/FIXME backend | **4** | OK |
| Base de donnees | SQLite 171 MB | Attention |

---

## 3. Matrice de scoring par domaine

| Domaine | Note /10 | Commentaire |
|---------|----------|-------------|
| **Securite** | 4/10 | JWT secret fallback, CORS wildcard, token localStorage, 2 endpoints sans filtrage org_id |
| **Architecture backend** | 6/10 | Bien structure mais double moteur conformite, services deprecies actifs, cache non thread-safe |
| **Qualite code backend** | 4/10 | 533 print(), 40+ except pass, valeurs metier hardcodees partout |
| **Architecture frontend** | 5/10 | Design system solide mais 5 god files, 0 React.memo, 4 pages zombies |
| **Qualite code frontend** | 5/10 | 107 console.log, 30+ ESLint disabled, validation formulaires absente |
| **Infrastructure / DevOps** | 5/10 | CI/CD present mais SQLite en prod, pas de tracing, sourcemaps exposees |
| **Tests** | 8/10 | Excellente couverture (6 400+ tests), E2E complets |
| **Documentation** | 7/10 | 45+ fichiers MD, data dictionary 1 677L, mais audits precedents disperses |

**Moyenne ponderee : 5.4/10**

---

## 4. Constats P0 — Critiques

| ID | Probleme | Fichier:Ligne | Impact | Effort |
|----|----------|---------------|--------|--------|
| P0-01 | **JWT secret hardcode en fallback** `"dev-secret-change-me-in-prod"` | `backend/services/iam_service.py:35` | Compromission totale de l'authentification si env var absente | 10 min |
| P0-02 | **Mots de passe seed identiques** `"demo2024"` pour 10 users | `backend/scripts/seed_data.py:867` | Acces non autorise trivial en demo/staging | 15 min |
| P0-03 | **CORS wildcard `["*"]`** en DEMO_MODE | `backend/main.py:105` | Requetes cross-origin non restreintes | 15 min |
| P0-04 | **2 endpoints conso sans filtrage org_id** | `backend/routes/consumption*.py` | Fuite de donnees cross-organisation (red flag securite) | 30 min |
| P0-05 | **Token JWT en localStorage** non chiffre | `frontend/src/contexts/AuthContext.jsx:8,24,44` | Vol de session via XSS | 2h |
| P0-06 | **DevApiBadge + DevScopeBadge** visibles a tous les utilisateurs | `frontend/src/pages/ConformitePage.jsx:574-589` | Scope JSON expose en demo client — mort en presentation | 5 min |
| P0-07 | **MAX_SITES=20 troncature silencieuse** | `frontend/src/pages/AnomaliesPage.jsx:55` | Client 25 sites → 5 anomalies invisibles sans warning | 15 min |
| P0-08 | **MOCK_PORTEFEUILLES hardcode** comme fallback | `frontend/src/contexts/ScopeContext.jsx:27-33` | Scope casse si vrais portefeuilles different du mock | 2h |
| P0-09 | **seedBillingDemo() expose** sans gate DEMO_MODE | `frontend/src/pages/BillIntelPage.jsx:12` | Bouton "seed" visible en prod = signal POC | 10 min |
| P0-10 | **Double prix par defaut** incoherents | `backend/services/billing_service.py:36-39` vs `backend/config/default_prices.py` | Calculs de facturation divergents selon le chemin de code | 30 min |

---

## 5. Constats P1 — Eleves

### 5.1 Architecture

| ID | Probleme | Fichier:Ligne | Impact | Effort |
|----|----------|---------------|--------|--------|
| P1-01 | **Double moteur conformite** — compliance_engine.py deprecie mais toujours appele | `backend/services/compliance_engine.py:1-16` + `compliance_coordinator.py:22-78` | Double source de verite, resultats potentiellement divergents | 4h |
| P1-02 | **purchase_scenarios_service.py deprecie** mais en production | `backend/services/purchase_scenarios_service.py:1-11` | Facteurs prix hardcodes (1.05/0.95/0.88) utilises en prod | 2h |
| P1-03 | **Cache KPI non thread-safe** — dict global sans invalidation | `backend/services/kpi_service.py:54-72` | Race conditions + donnees stalees en multi-instance | 2h |
| P1-04 | **Worker sans idempotence** — pas de locking, entity/org non implemente | `backend/jobs/worker.py:49-53,104-108` | Jobs executes en double, recompute org silencieusement ignore | 3h |
| P1-05 | **AI client 100% stub** — retourne placeholder si pas d'API key | `backend/ai_layer/client.py:25,32-37` | Utilisateurs recoivent des analyses fictives sans le savoir | 2h |

### 5.2 Qualite du code

| ID | Probleme | Fichier(s) | Impact | Effort |
|----|----------|------------|--------|--------|
| P1-06 | **533 `print()` au lieu de `logging`** | 37 fichiers Python (top: `scripts/` 73, `kb_service.py` 8) | Pas de filtrage, routage ni audit trail | 4h |
| P1-07 | **40+ blocs `except Exception: pass`** silencieux | `billing_service.py:56,89,106`, `billing_shadow_v2.py` (12 occ.), `compliance_score_service.py` | Erreurs masquees, debugging impossible | 4h |
| P1-08 | **107 `console.log()` en production** | 24 fichiers JS (top: `audit-agent.mjs` 24, `core.js` 2) | Fuite d'info en console navigateur, bruit en monitoring | 2h |
| P1-09 | **30+ ESLint rules desactivees** (`exhaustive-deps`) | `ConformitePage.jsx:142,211`, `Patrimoine.jsx:302`, `MonitoringPage.jsx` | Hooks React potentiellement bugges (deps manquantes) | 3h |
| P1-10 | **5 god files > 1 500 LOC** | `Patrimoine.jsx` (2243L), `PurchasePage.jsx` (2024L), `Site360.jsx` (1620L), `ActionsPage.jsx` (1579L), `BillIntelPage.jsx` (1267L) | Maintenabilite degradee, risque de regression eleve | 8h |

### 5.3 Valeurs metier hardcodees

| ID | Probleme | Fichier:Ligne | Valeur hardcodee |
|----|----------|---------------|------------------|
| P1-11 | **Seuils BACS** | `compliance_engine.py:49-52` | 290kW / 70kW, deadlines 2025-01-01 / 2030-01-01 |
| P1-12 | **Penalite financiere** | `compliance_engine.py:56-58` | BASE_PENALTY_EURO = 7 500 EUR flat, ratio 0.5 |
| P1-13 | **Facteurs prix achat** | `purchase_scenarios_service.py:48,77,108` | 1.05 / 0.95 / 0.88 identiques tous sites/periodes |
| P1-14 | **Seuils severite anomalies** | `notification_service.py:163-168` + `billing_service.py` | >= 5 000 EUR CRITICAL, >= 1 000 EUR WARN (duplique) |
| P1-15 | **Alertes renouvellement contrat** | `notification_service.py:215-219` | 30/60/90 jours hardcode |
| P1-16 | **Heures nuit** | `consumption analysis` | 22h-6h hardcode |
| P1-17 | **Cache TTL KPI** | `kpi_service.py:55` | 300s (5 min) non configurable |

### 5.4 Frontend

| ID | Probleme | Fichier(s) | Impact |
|----|----------|------------|--------|
| P1-18 | **0 `React.memo`** dans tout le frontend | Global | Re-renders en cascade sur chaque changement d'etat |
| P1-19 | **HEATMAP_MAX_SITES=10** hardcode | `Patrimoine.jsx:304` | Heatmap tronquee sans avertissement pour gros portefeuilles |
| P1-20 | **4 pages zombies** (3 092 lignes de code mort) | `Dashboard.jsx`, `ActionPlan.jsx`, `CompliancePage.jsx`, `SiteDetail.jsx` | Code mort maintenu inutilement, confusion navigation |
| P1-21 | **15+ accents francais manquants** | Global UI | "definie", "enregistree", "Fev", "Eleve", "duree", "marche" |
| P1-22 | **Tabs sans ARIA roles** | Global UI | WCAG AA failure, inaccessible clavier/lecteur ecran |
| P1-23 | **Validation formulaires absente** | `ActionsPage.jsx`, `CreateActionDrawer.jsx` | Date passee, EUR negatif acceptes sans feedback |

---

## 6. Constats P2 — Moyens

| ID | Probleme | Fichier(s) | Impact | Effort |
|----|----------|------------|--------|--------|
| P2-01 | **SQLite en production** — pas de migration Alembic active | `database/connection.py:37` | Pas de concurrence, pas de scalabilite | 3h |
| P2-02 | **Pas de tracing distribue** ni metriques | Global backend | Impossible de tracer les requetes ou detecter les degradations | 4h |
| P2-03 | **NAV_SECTIONS vs NAV_MAIN_SECTIONS** duplication | Navigation frontend | 2 sources de verite paralleles | 1h |
| P2-04 | **Formule modulo** `((s.id-1)%5)+1` pour affectation portfolio | `Patrimoine.jsx:275` | IDs non sequentiels → affectation portfolio cassee | 30 min |
| P2-05 | **ErrorState affiche debug info** (status, request_url) | UI components | Info technique visible a l'utilisateur final | 10 min |
| P2-06 | **SIREN "123456789"** et rues generiques dans seed | `seed_data.py` | Prospect voit immediatement que c'est fake | 1h |
| P2-07 | **/contracts-radar** dans ROUTE_MODULE_MAP mais absent de App.jsx | Navigation | Bookmark → 404 | 5 min |
| P2-08 | **Pas de CSRF tokens** pour operations state-changing | Global backend | Risque CSRF sur endpoints POST/PATCH/DELETE | 2h |
| P2-09 | **API Anthropic version** hardcodee `"2023-06-01"` | `ai_layer/client.py:16` | Version potentiellement obsolete | 5 min |
| P2-10 | **Sourcemaps en production** | `frontend/vite.config.js` | Exposition du code source en prod | 5 min |
| P2-11 | **10+ `datetime.utcnow()`** deprecie Python 3.12 | `onboarding_stepper.py`, `data_quality_service.py`, etc. | DeprecationWarning en Python 3.12+ | 30 min |
| P2-12 | **PII partiellement masquee** — email[:3] + "***" insuffisant | `routes/auth.py:305` | Email de 4 caracteres avant @ non masque | 10 min |

---

## 7. Roadmap de remediation

### Phase A — Securite & Stabilite (Sprint 1-2, ~5 jours)

| # | Action | Effort | Impact | Constats |
|---|--------|--------|--------|----------|
| A1 | Forcer `PROMEOS_JWT_SECRET` env var (crash si absent en prod) | 10 min | Securite | P0-01 |
| A2 | Generer mots de passe seed uniques par utilisateur | 15 min | Securite | P0-02 |
| A3 | Restreindre CORS origins meme en DEMO_MODE | 15 min | Securite | P0-03 |
| A4 | Ajouter filtrage `org_id` sur 2 endpoints consommation | 30 min | Securite | P0-04 |
| A5 | Migrer token vers httpOnly cookie ou chiffrement localStorage | 2h | Securite | P0-05 |
| A6 | Gater DevApiBadge/DevScopeBadge derriere `DEMO_MODE && expertMode` | 5 min | Credibilite | P0-06 |
| A7 | Ajouter warning UI si MAX_SITES atteint + rendre configurable | 15 min | Data | P0-07 |
| A8 | Fetcher portefeuilles depuis l'API au lieu de MOCK | 2h | Gouvernance | P0-08 |
| A9 | Gater seedBillingDemo() derriere flag DEMO_MODE | 10 min | Credibilite | P0-09 |
| A10 | Unifier source de verite prix default (config unique) | 30 min | Data | P0-10 |
| A11 | Remplacer 40+ `except Exception: pass` par logging explicite | 4h | Stabilite | P1-07 |
| A12 | Supprimer sourcemaps en production | 5 min | Securite | P2-10 |

### Phase B — Architecture & Code Quality (Sprint 3-4, ~6 jours)

| # | Action | Effort | Impact | Constats |
|---|--------|--------|--------|----------|
| B1 | Retirer appels a compliance_engine.py deprecie | 4h | Architecture | P1-01 |
| B2 | Retirer purchase_scenarios_service.py deprecie | 2h | Architecture | P1-02 |
| B3 | Thread-safe cache KPI (TTLCache ou Redis) + invalidation | 2h | Fiabilite | P1-03 |
| B4 | Ajouter locking worker + implementer entity/org recompute | 3h | Fiabilite | P1-04 |
| B5 | Remplacer 533 `print()` par `logging` module | 4h | Observabilite | P1-06 |
| B6 | Remplacer 107 `console.log()` par logger conditionnel | 2h | Observabilite | P1-08 |
| B7 | Corriger 30+ ESLint `exhaustive-deps` violations | 3h | Stabilite | P1-09 |
| B8 | Externaliser valeurs metier hardcodees dans config/DB | 4h | Maintenabilite | P1-11 a P1-17 |
| B9 | Migrer `datetime.utcnow()` → `datetime.now(timezone.utc)` | 30 min | Hygiene | P2-11 |

### Phase C — Frontend & UX (Sprint 5-6, ~5 jours)

| # | Action | Effort | Impact | Constats |
|---|--------|--------|--------|----------|
| C1 | Splitter 5 god files en sous-composants (<500L chacun) | 8h | Maintenabilite | P1-10 |
| C2 | Ajouter `React.memo` sur composants listes/tableaux | 4h | Performance | P1-18 |
| C3 | Supprimer 4 pages zombies (3 092 lignes) | 1h | Hygiene | P1-20 |
| C4 | Corriger 15+ accents francais manquants | 30 min | UX | P1-21 |
| C5 | Ajouter ARIA roles sur tabs et modals | 2h | Accessibilite | P1-22 |
| C6 | Implementer validation formulaires (dates, montants) | 3h | UX | P1-23 |
| C7 | Migrer vers Alembic pour PostgreSQL | 3h | Infrastructure | P2-01 |

---

## 8. Annexes

### 8.1 Fichiers analyses

**Backend (15 fichiers) :**
1. `backend/main.py` (437L)
2. `backend/database/connection.py` (57L)
3. `backend/services/iam_service.py` (504L)
4. `backend/routes/auth.py` (377L)
5. `backend/services/billing_service.py` (928L)
6. `backend/services/compliance_engine.py` (1 255L)
7. `backend/services/purchase_scenarios_service.py` (184L)
8. `backend/services/kpi_service.py` (316L)
9. `backend/ai_layer/client.py` (123L)
10. `backend/services/notification_service.py` (521L)
11. `backend/routes/cockpit.py`
12. `backend/config/default_prices.py` (27L)
13. `backend/config/patrimoine_assumptions.py` (151L)
14. `backend/services/compliance_coordinator.py` (105L)
15. `backend/jobs/worker.py` (134L)

**Frontend (13 fichiers) :**
16. `frontend/src/pages/Cockpit.jsx` (938L)
17. `frontend/src/pages/ConformitePage.jsx` (828L)
18. `frontend/src/pages/BillIntelPage.jsx` (1 267L)
19. `frontend/src/pages/PurchasePage.jsx` (2 024L)
20. `frontend/src/pages/Site360.jsx` (1 620L)
21. `frontend/src/pages/ActionsPage.jsx` (1 579L)
22. `frontend/src/pages/Patrimoine.jsx` (2 243L)
23. `frontend/src/pages/AnomaliesPage.jsx` (720L)
24. `frontend/src/contexts/ScopeContext.jsx` (360L)
25. `frontend/src/contexts/AuthContext.jsx` (100L)
26. `frontend/src/App.jsx`
27. `frontend/src/layout/Sidebar.jsx`
28. `frontend/vite.config.js` (37L)

**Infra (5 fichiers) :**
29. `.github/workflows/quality-gate.yml`
30. `Makefile`
31. `.env.example`
32. `backend/pyproject.toml`
33. `package.json` (root)

### 8.2 Outils et methode

- **Exploration** : 5 agents paralleles (Explore) pour couverture exhaustive
- **Recherche** : Grep systematique (`print(`, `console.log(`, `TODO`, `FIXME`, `datetime.utcnow`, `password`, `secret`)
- **Comptage** : Metriques automatisees via ripgrep sur l'ensemble du repo
- **Zero modification** : Aucun fichier source modifie durant cet audit

---

*Fin du rapport DT_AUDIT_PHASE1 — Phase 1 lecture seule terminee.*
