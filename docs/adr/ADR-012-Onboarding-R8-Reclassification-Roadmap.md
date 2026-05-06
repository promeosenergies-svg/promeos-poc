# ADR-012 — Onboarding R8 reclassification + roadmap UX refonte-sol2

**Statut** : Accepté
**Date** : 2026-05-05
**Sprint** : C-5 Phase 0
**Personnes impliquées** : Amine (founder), Claude architect-helios
**Tracking dette** : aucune (re-cadrage scope sprint)

---

## Contexte

**Plan Phase B** (référence audit `docs/audits/AUDIT_PATRIMOINE_PHASE_B_2026_05_03.md`) liste **R8 Onboarding wizard 3 parcours** comme dernier GAP Phase B non comblé Sprints C-1 → C-4 (13/14 GAPS comblés). Estimation initiale Plan : ~6 j-h pour livrer wizard 5 étapes (Org → Entité → Portefeuille → Site → Bâtiment → Compteur).

### Audit Phase 0 Sprint C-5 — diagnostic terrain T0

Le diagnostic Phase 0 Sprint C-5 (read-only, ~10 min) révèle **~3 456 lignes d'onboarding/wizard EXISTANT déjà** sur la branche `claude/refonte-sol2` pré-Sprint C-5 :

#### Backend (793 LOC cumul)

- `routes/onboarding.py` (269L) :
  - `POST /api/onboarding` — création org + entité juridique + portefeuilles + sites en 1 call (V1 mono-org)
  - `POST /api/onboarding/import-csv` — import massif sites
  - `GET /api/onboarding/status` — état d'avancement
- `routes/onboarding_stepper.py` (205L) :
  - `GET /api/onboarding-progress` — status wizard
  - `PATCH /api/onboarding-progress/step` — update step
  - `POST /api/onboarding-progress/dismiss` — dismiss stepper
  - `POST /api/onboarding-progress/auto` — auto-detect completed steps
- `services/onboarding_service.py` (319L) — `is_tertiaire`, `create_organisation_full`, `create_site_from_data`, `provision_site`

#### Frontend (~2 663 LOC cumul)

- `pages/OnboardingPage.jsx` (251L) — page d'entrée
- `pages/SireneOnboardingPage.jsx` (779L) — wizard SIREN-driven (pre-fill via `recherche-entreprises.api.gouv.fr`)
- `components/SiteCreationWizard.jsx` (1 086L) — wizard détaillé création site
- `components/IntakeWizard.jsx` (547L) — wizard intake compteurs/factures
- `components/BacsWizard.jsx` — wizard conformité BACS
- `components/PatrimoineWizard.jsx` — wizard patrimoine
- `components/UpgradeWizard.jsx` — wizard upgrade plan
- `components/OnboardingOverlay.jsx` — overlay UI

#### SIREN API integration (déjà acquise)

5 endpoints `/api/reference/sirene/*` consomment `recherche-entreprises.api.gouv.fr` (gratuit, public) :

- `GET /api/reference/sirene/search` — recherche libre
- `GET /api/reference/sirene/unites-legales/{siren}` — fiche SIREN
- `GET /api/reference/sirene/etablissements-by-siren/{siren}` — établissements
- `GET /api/reference/sirene/etablissements/{siret}` — fiche SIRET
- `GET /api/reference/sirene/lead-score/{siren}` — scoring commercial
- `POST /api/admin/sirene/hydrate/{siren}` — hydratation cache

Services backend : `services/sirene_hydrate.py` (hydratation API + cache local) et `services/sirene_lookup.py` (lookup direct API).

→ **ADR-014 prévu Phase 0 Sprint C-5 = OBSOLÈTE** (décision déjà actée historiquement, implémentée et opérationnelle).

---

## Décision

### Option retenue : **Skip R8 — déclarer "MVP livré historique"**

3 options arbitrées Phase 0 Sprint C-5 :

| Option | Périmètre | Effort estimé | Verdict |
|---|---|---|---|
| A | QA + Hardening Onboarding existant (audit gaps doctrinaux refonte-sol2, complétion étapes manquantes) | ~3-5 j-h | Reportée Sprint refonte-sol2 |
| B | Refonte UX sous Doctrine Sol v1.0 (3 wizards séparés → 1 unifié 7 étapes) | ~6-8 j-h | Scope creep — refusée Phase C |
| **C** | **Skip R8 + focus 2 P0 + dettes** | **~3-5 j-h** | ✅ **RETENUE** |

### Justifications Option C

1. **Onboarding existant = MVP suffisant pré-pilote** — Wizard SIREN-driven + SiteCreationWizard couvrent le flux Org → Site complet avec pre-fill API publique gratuite. Dataset HELIOS (`services/demo_seed/`) idempotent fournit démo investisseur.
2. **ADR-014 obsolète** — Pre-fill SIREN api.gouv.fr déjà actée historiquement. Aucun nouveau choix archi requis.
3. **Bill Intelligence anomaly_detector = différenciateur produit cardinal** — CFO scrute anomalies factures (R19 VNU dormant + R20 capacité variance >5%). Pas de runtime existant. Vs Deepki / Spacewell généralistes sans Bill Intelligence dédié.
4. **Refonte UX onboarding = scope refonte-sol2 séparé** — Doctrine Sol v1.0 (12 principes + grammaire éditoriale §5 + anti-patterns §6) appliquée hors Phase C dans sprint dédié. Mélange pollutions Phase C.
5. **Pattern ROI Phase C validé** — Sprints C-1 à C-4 : densité backend (cascade + scoring + YAML SoT) > UX rework. Sprint C-5 doit consolider ce ROI.

---

## Conséquences

### Positives

- **R8 reclassifié "MVP livré historique"** → GAPS Phase B comblés cumul **14/14** (vs 13/14 précédent, post-Sprint C-4)
- **Périmètre Sprint C-5 raccourci** : ~3-5 j-h vs 12-16 j-h estimé initial = gain cardinal **-70%**
- **Focus différenciateur produit** : Bill Intelligence anomaly_detector P0 = priorité cardinale Sprint C-5 (Phase 5.1, ~2-3 j-h)
- **Pas de dette UX onboarding ajoutée Phase C** — clean separation refonte-sol2

### Négatives

- **Hardening UX onboarging existant pas adressé** — gaps doctrinaux refonte-sol2 (12 principes, FindingCard, TraceTooltip patterns) restent à corriger sprint séparé
- **Pas de wizard unifié 7 étapes** — 6 wizards séparés (Sirene, SiteCreation, Intake, Bacs, Patrimoine, Upgrade) cohabitent sans hiérarchie claire
- **Documentation onboarding fragmentée** — pas de guide consolidé "comment onboarder un client" (à produire Sprint refonte-sol2)

### Mitigation

- **Sprint refonte-sol2 dédié post-Phase C** : audit doctrine (ACAF, FindingCard, TraceTooltip, simplicité §1) + refonte UX progressive
- **Dette tracée** : `D-Sprint-RefonteSol2-Onboarding-UX-Hardening-001` P2 (créer Sprint refonte-sol2 backlog) — référence cet ADR-012
- **Capture audit Playwright actuel** : screenshots wizards existants (`tools/playwright/captures/`) pour traçabilité avant refonte

---

## Implémentation Sprint C-5

**Phase 5.0** : ADR-012 (cet ADR) commit.
**Phase 5.1** : Bill Intelligence anomaly_detector R19+R20 (ADR-013).
**Phase 5.2** : Capacité EUR/MW disambiguation (ADR-015).
**Phase 5.3** : ADR-007 ext consentement_*_by + cgu_version.
**Phase 5.4** : Polish 2-3 dettes P1 sélectionnées.

**Aucune modification code onboarding Sprint C-5** (skip R8 intégral).

---

## Références

- Plan Phase B : `docs/audits/AUDIT_PATRIMOINE_PHASE_B_2026_05_03.md`
- Bilan Sprint C-4 : `docs/audits/BILAN_SPRINT_C4_2026_05_05.md`
- Doctrine Sol v1.0 : `docs/vision/promeos_sol_doctrine.md`
- Memory KB : `project_refonte_sol_doctrine_3mois.md`, `project_audit_complet_refonte_sol2_2026_05_03.md`
