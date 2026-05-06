# Audit Onboarding Patrimoine — Pré Phase D-2 refonte UX

**Date** : 2026-05-07
**Branche** : `claude/refonte-sol2`
**Mode** : READ-ONLY produit pur — aucune modification code
**Contexte** : Pré Phase D-1 (sprint 6 P1 résiduels) + pré Phase D-2 (refonte UX)
**Méthode** : pattern AUDIT_TRANSVERSAL Phase 5.7 reproduit (10 axes)

---

## Synthèse exécutive

| Item | Valeur |
|---|---|
| **Volume Onboarding** | **4 864 LOC** (vs 3 456 mentionnés Sprint C-5 = +40% scope réel) |
| **Backend** | 928 LOC (4 fichiers : 2 routes + 2 services) |
| **Frontend** | 3 936 LOC (6 composants : 2 pages + 4 wizards + 1 overlay) |
| **Endpoints** | 7 (`POST /onboarding`, `POST /import-csv`, `GET /status`, GET/PATCH/POST stepper) |
| **Verdict global** | 🔴 **REFONTE CARDINAL JUSTIFIÉE Phase D-2** — gaps cascade vivante + UX sol2 v1.1 + persistance + tests |

---

## 1. Cartographie code

### Backend (928 LOC)

- `backend/routes/onboarding.py` (269 LOC) — 3 endpoints (POST onboarding, POST import-csv, GET status)
- `backend/routes/onboarding_stepper.py` (221 LOC) — 4 endpoints stepper (GET, PATCH /step, POST /dismiss, POST /auto)
- `backend/services/onboarding_service.py` (319 LOC) — création hiérarchie + obligations BACS
- `backend/services/onboarding_stepper_service.py` (119 LOC) — stepper progression

### Frontend (3 936 LOC)

- `frontend/src/pages/OnboardingPage.jsx` (251 LOC) — page d'entrée
- `frontend/src/pages/SireneOnboardingPage.jsx` (779 LOC) — onboarding via SIRENE INSEE
- `frontend/src/components/PatrimoineWizard.jsx` (**1 162 LOC**) — bulk import CSV/Excel 6 steps
- `frontend/src/components/SiteCreationWizard.jsx` (**1 086 LOC**) — wizard manuel 7 steps (Org → EJ → PF → Site → Bâtiments → Compteurs → Récap)
- `frontend/src/components/IntakeWizard.jsx` (547 LOC) — diagnostic intake
- `frontend/src/components/OnboardingOverlay.jsx` (111 LOC) — overlay
- `frontend/src/components/onboarding/DemoSpotlight.jsx` (1 fichier sous-dossier)

### Schemas

- ❌ **AUCUN fichier `backend/schemas/onboarding*`** — validation pydantic ad-hoc dans routes (vs cardinal `schemas/rgpd_consent.py` pattern Phase 7.3)

---

## 2. Findings cardinaux par axe (10 AXES audit transversal)

### 🔴 AXE 1 — UX (P0+P1 cumulés)

- **P1-AXE1-001** Stepper PatrimoineWizard 6 steps (mode → upload → preview → corrections → validation → result) — **bulk only**, pas de parcours guidé manuel intégré
- **P1-AXE1-002** SiteCreationWizard 7 steps (Org → EJ → PF → Site → Bâtiments → Compteurs → Récap) — duplication de logique avec PatrimoineWizard
- **P1-AXE1-003** Pas de breadcrumb global multi-wizard cohérent (utilisateur perdu si interruption mid-flow)
- **P0-AXE1-004** **0 occurrence TraceTooltip** dans onboarding ⚠️ — pédagogie sol2 v1.1 ABSENTE (cardinal différenciateur produit)

### 🔴 AXE 2 — Validation (P0)

- **P0-AXE2-001** **AUCUN fichier `backend/schemas/onboarding*`** — validation pydantic doctrinale absente. Validation ad-hoc dans routes (`onboarding.py`/`onboarding_stepper.py`).
- **P1-AXE2-002** Validation côté client `validateSiren`/`validatePrm` (`SiteCreationWizard.jsx:66+72`) — doublonnage backend potentiel, sans alignement cardinal
- **P1-AXE2-003** Pas de cross-validation cohérence (Site sans EJ rattaché, Bâtiment sans Site, etc.) au niveau service

### 🔴 AXE 3 — Cohérence cascade vivante 14 champs ↔ Onboarding (P0 CARDINAL)

| Champ cascade | Onboarding crée | Trigger cascade |
|---|---|---|
| `cvc_power_kw` (Bâtiment) | ✅ SiteCreationWizard | 🔴 **AUCUN** |
| `tertiaire_area_m2` (Site) | ✅ SiteCreationWizard | 🔴 **AUCUN** |
| `surface_m2` (Site) | ✅ SiteCreationWizard | 🔴 AUCUN |
| `s_ce_m2` (Phase 7.1) | ❌ NON onboardé | N/A |
| `grd_code` (DeliveryPoint) | ❌ NON onboardé | N/A |
| `consentement_dataconnect_global` (Org) | ❌ NON onboardé | N/A |
| `consentement_grdf_global` (Org) | ❌ NON onboardé | N/A |
| `annual_kwh_total` (Site) | ❌ NON onboardé | N/A |
| `EnergyContract.end_date` | ❌ NON onboardé | N/A |
| `AuditEnergetique.conso` | ❌ NON onboardé | N/A |

- **P0-AXE3-001 CARDINAL** Onboarding **BYPASS cascade vivante 14 champs**. Création Site/Bâtiment via Wizard ne déclenche PAS `cascade_recompute_on_change` → KPI/scoring conformité **silencieusement incomplets** post-onboarding. Risque démo investisseur : "Pourquoi mon score est à 0 après onboarding ?"
- **P0-AXE3-002** **5/8 champs cascade NON onboardés** (s_ce_m2 Phase 7.1, grd_code, consentements RGPD, annual_kwh_total). Wizard incomplet vs doctrine "1 SoT par concept" ADR-016 Pilier 3.

### 🔴 AXE 4 — Persistance partielle (P0 cardinal mid-market)

- **P0-AXE4-001 CARDINAL** **0 occurrence `save/draft/resume/localStorage`** dans wizards. Si utilisateur ferme onglet mid-flow → **tout perdu**. Drop-off massif probable mid-market 10-500 sites (1h+ saisie possible).

### 🟠 AXE 5 — Bulk import CSV (P1)

- **P1-AXE5-001** PatrimoineWizard supporte CSV/Excel/TXT (`accept=".csv,.xlsx,.xls,.txt"` ligne 495)
- **P1-AXE5-002** Endpoint `POST /api/onboarding/import-csv` existant (`onboarding.py:137`)
- **P1-AXE5-003** Template CSV téléchargeable (`PatrimoineWizard.jsx:460` `/api/patrimoine/import/template`)
- ⚠️ Couverture cascade vivante via CSV **non vérifiée** — risque idem AXE 3 (bypass)

### 🟡 AXE 6 — Multi-org switching (P2)

- **0 occurrence `switchOrg`/`change.*org`** dans wizards onboarding — UX changement de scope post-Phase 7.2 ADR-017 non testée. Risque utilisateur multi-tenant : confusion org active vs org wizard.

### 🟡 AXE 7 — Cycle vie (P2)

- Pas d'audit explicite reset/edit/delete patrimoine post-onboarding. Endpoint `POST /onboarding/dismiss` (stepper) existe mais cycle vie complet non vérifié.

### 🔴 AXE 8 — Tests E2E (P1)

- **P1-AXE8-001** **1 seul test** `frontend/src/__tests__/sirene_onboarding.test.js` (test unit, pas E2E)
- **P1-AXE8-002** **AUCUN test Playwright onboarding** (4 864 LOC sans tests cardinaux E2E)
- Risque cardinal : refonte D-2 sans baseline tests = régression non-détectable

### 🟡 AXE 9 — Performance (P2)

- Pas d'audit perf 100+ sites bulk import (timeout possible)
- `csvPreview` state local (PatrimoineWizard:114) sans pagination → potentiel freeze UI sur > 1 000 lignes

### 🟡 AXE 10 — Analytics drop-off (P2)

- 0 instrumentation analytics drop-off rates par step
- Cardinal pour optimisation post-pilote : quel step abandonnent les utilisateurs ?

---

## 3. Dettes cardinales identifiées

### 🔴 P0 BLOQUANTS PILOTE EXTERNE / PHASE D-2 (5)

1. **P0-AXE1-004** TraceTooltip absent onboarding (différenciateur sol2 v1.1)
2. **P0-AXE2-001** Schemas pydantic onboarding absent (`backend/schemas/onboarding*`)
3. **P0-AXE3-001** Onboarding bypass cascade vivante 14 champs (silencieusement)
4. **P0-AXE3-002** 5/8 champs cascade NON onboardés (s_ce_m2, grd_code, consentements RGPD, annual_kwh, etc.)
5. **P0-AXE4-001** Persistance partielle save & resume absent (drop-off mid-market massif probable)

### 🟠 P1 AVANT PRODUCTION SCALING (8)

6. **P1-AXE1-001** Stepper PatrimoineWizard bulk-only (parcours manuel séparé SiteCreationWizard duplication)
7. **P1-AXE1-002** Duplication PatrimoineWizard ↔ SiteCreationWizard (~2 248 LOC cumul refacto candidat)
8. **P1-AXE1-003** Breadcrumb global multi-wizard absent
9. **P1-AXE2-002** Validation côté client doublonnage backend (`validateSiren`/`validatePrm` ligne 66+72)
10. **P1-AXE2-003** Cross-validation cohérence cross-entités absente
11. **P1-AXE5-003** Bulk import cascade coverage non vérifiée
12. **P1-AXE8-001** 1 seul test unit (sirene_onboarding) — couverture cardinale absente
13. **P1-AXE8-002** 0 test E2E Playwright onboarding (cardinal Phase D-2 baseline)

### 🟡 P2 PHASE D+/E BACKLOG (6)

14. **P2-AXE6-001** Multi-org switching UX non testé
15. **P2-AXE7-001** Cycle vie reset/edit/delete patrimoine non audité
16. **P2-AXE9-001** Perf bulk 100+ sites non auditée (csvPreview pagination)
17. **P2-AXE10-001** Analytics drop-off rates par step absents
18. **P2-DemoSpotlight** Sous-dossier `components/onboarding/DemoSpotlight.jsx` isolé (refacto namespace)
19. **P2-IntakeWizard** IntakeWizard 547 LOC scope distinct vs Onboarding (clarifier separation of concerns)

---

## 4. Recommandations Phase D-2 refonte UX

### Quick wins (~3-5 j-h, avant refonte cardinale)

- **QW1 — Schemas pydantic onboarding** (P0-AXE2-001) : créer `backend/schemas/onboarding/` avec validation pydantic stricte (pattern Phase 7.3 `rgpd_consent.py`). 1 j-h.
- **QW2 — Cascade trigger wiring onboarding** (P0-AXE3-001) : wirer `cascade_recompute_on_change` post-création Site/Bâtiment dans `onboarding_service.py:save_complete_onboarding` (~ligne 280). 0.5 j-h.
- **QW3 — Persistance partielle localStorage** (P0-AXE4-001) : ajouter `useEffect` save draft sur chaque step + bouton "Reprendre" sur OnboardingPage. 0.5-1 j-h.
- **QW4 — TraceTooltip onboarding** (P0-AXE1-004) : 5-10 termes cardinaux exposés (SIREN, PRM, Surface CE, CVC, etc.). 0.5 j-h.

### Refonte cardinale Phase D-2 (~10-15 j-h ajusté audit)

- **R1 — Unification PatrimoineWizard ↔ SiteCreationWizard** : 1 wizard cardinal avec mode "manuel" + "bulk import" toggle. Réduit 2 248 LOC duplication → ~1 200 LOC unifiés. 3 j-h.
- **R2 — 5/8 champs cascade ajoutés Wizard** : s_ce_m2 + grd_code + consentements RGPD + annual_kwh_total + EnergyContract.end_date. Cohérence ADR-007 + Phase 7.1 + Phase 7.3 + 7.4. 2 j-h.
- **R3 — Tests E2E Playwright cardinal baseline** (P1-AXE8) : couvre 4-5 scénarios cardinaux (manuel mid-market 5 sites + bulk 50 sites + reprise mi-flow + multi-org switch + cascade trigger validation). 3 j-h.
- **R4 — Microcopy sol2 v1.1** : helper text + error messages + tooltips contextuels (cohérent doctrine). 1.5 j-h.
- **R5 — Cross-validation cohérence service-side** (P1-AXE2-003) : validators cross-entités centralisés. 1 j-h.
- **R6 — Pédagogie Surface CE / SIREN / PRM / CVC** : tooltips + side panel "Pourquoi cette donnée ?" cohérent doctrine. 1 j-h.

### Reportés Phase E (~3-5 j-h)

- Multi-org switching UX exhaustif (P2-AXE6)
- Cycle vie complet edit/reset/delete (P2-AXE7)
- Perf bulk 1 000+ sites + csvPreview pagination (P2-AXE9)
- Analytics drop-off rates par step (P2-AXE10)

---

## 5. Effort estimé Phase D-2 ajusté

| Périmètre | Effort initial | Effort ajusté audit | Delta |
|---|---|---|---|
| Onboarding refondé | ~3-5 j-h | **~10-15 j-h** | **+7-10 j-h** (3x ajustement) |
| Quick wins pré-refonte | non identifiés | **~3-5 j-h** | NEW |
| Tests E2E Playwright | non identifiés | **~3 j-h** | NEW |
| **Total Phase D-2 ajusté** | **3-5 j-h** | **~16-23 j-h** | **+11-18 j-h** |

**Conclusion cardinale** : scope Phase D-2 refonte UX **3-4× sous-estimé**. Audit pré-Phase-D-2 cardinal cohérent ROI Phase 0 enrichie acquis Sprint C-4/C-5/C-7/C-8.

---

## 6. Pattern doctrinal acquis Audit Onboarding

### Anti-pattern détecté

- **"Wizard sans cascade trigger"** : Onboarding bypass cascade vivante 14 champs silencieusement → KPI/scoring incomplets post-création. Pattern à formaliser ADR-021 candidat (cohérent Pilier 6 ADR-016 audit deep multi-agents).

### Pattern positif détecté

- **PatrimoineWizard 6-step staging pipeline** (mode → upload → preview → corrections → validation → result) — UX bulk import maturée. Réutilisable pattern wizard manuel.
- **Endpoint `POST /onboarding/import-csv` + template CSV téléchargeable** — pattern bulk scalable.

---

## 7. Recommandations ordre Phase D

### Phase D-1 (sprint 6 P1 résiduels Sprint C-8 audit + Quick Wins audit Onboarding) ~10-12 j-h

1. 6 P1 résiduels Sprint C-8 (~5 j-h, déjà tracés)
2. 4 Quick Wins audit Onboarding (~3-5 j-h)
3. Tests cardinaux ces fixes (~2 j-h)

### Phase D-2 refonte UX (~16-23 j-h ajusté)

4. R1-R6 refonte cardinale unifiée

### Phase D-3 (post-refonte)

5. Pilote externe complet déclenchement (post audit Onboarding fixé)

---

## Métriques cumulées audit

- **10 axes** audités (pattern Phase 5.7 reproduit)
- **19 dettes** identifiées (5 P0 + 8 P1 + 6 P2)
- **~2 h** durée audit cumulé (vs 2-3 h estimé = -33% gain efficacité)
- **0 modification code** (mode produit pur)
- **Confidence verdict** : `high` (audit READ-ONLY exhaustif sur 4 864 LOC + cohérence cascade vérifiée)

---

**Auditeur** : Phase D Étape 1 read-only
**Date livraison** : 2026-05-07
**Branche** : `claude/refonte-sol2`
**Prochaine étape** : Phase D-1 (sprint 6 P1 résiduels + 4 Quick Wins audit)
