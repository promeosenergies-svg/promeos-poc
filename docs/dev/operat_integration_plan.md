# V39 — Plan d'intégration OPERAT / Décret tertiaire

**Date** : 2026-02-20
**Baseline** : commit `9762e15` (backup before operat module)
**Tests verts** : 1684 backend + 1413 frontend = 3097 tests, 0 fail

---

## 1. ÉTAT DES LIEUX — CE QUI EXISTE DÉJÀ

### 1.1 Backend — RegOps tertiaire (partiel)

| Fichier | État | Détail |
|---------|------|--------|
| `regops/rules/tertiaire_operat.py` | OK | 4 findings : SCOPE_UNKNOWN, OUT_OF_SCOPE, OPERAT_NOT_STARTED, ENERGY_DATA_MISSING, MULTI_OCCUPIED_GOVERNANCE |
| `regops/config/regs.yaml` | OK | scope_threshold_m2=1000, deadlines (attestation 2026-07-01, declaration 2026-09-30), penalties (7500/1500) |
| `regops/engine.py` | OK | Orchestre tertiaire_operat + bacs + aper + cee_p6 via evaluate_site() |
| `models/enums.py` | OK | OperatStatus (NOT_STARTED, IN_PROGRESS, SUBMITTED, VERIFIED), TypeObligation.DECRET_TERTIAIRE, RegulationType.TERTIAIRE_OPERAT |
| `models/site.py` | OK | Champs : tertiaire_area_m2, operat_status, annual_kwh_total, is_multi_occupied |
| `models/conformite.py` | OK | Obligation (site_id, type=DECRET_TERTIAIRE, echeance, statut, avancement_pct) |

### 1.2 Backend — KB / Memobox (V38)

| Fichier | État | Détail |
|---------|------|--------|
| `app/kb/models.py` | OK | kb_docs avec status (draft/review/validated/decisional/deprecated), domain, used_by_modules |
| `app/kb/store.py` | OK | upsert_doc, update_doc_status, get_docs_filtered |
| `app/kb/router.py` | OK | POST /upload (max 10Mo), POST /docs/{id}/status, GET /docs (filtres) |
| `app/kb/doc_ingest.py` | OK | ingest_document() + kb_doc_allows_deterministic() gating |

### 1.3 Backend — Patterns de code

| Pattern | Fichier référence | Détail |
|---------|-------------------|--------|
| Migration additive | `database/migrations.py` | ALTER TABLE ADD COLUMN, CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS |
| Route FastAPI | `routes/sites.py` | APIRouter + prefix + Depends(get_db) |
| Service métier | `services/compliance_engine.py` | Class avec db: Session, méthodes compute_* |
| Modèle SQLAlchemy | `models/base.py` | Base + TimestampMixin + SoftDeleteMixin |
| Demo seed | `services/demo_seed/orchestrator.py` | gen_*.py modules appelés par orchestrator |
| Montage router | `main.py` | app.include_router(router) — 38 routers existants |

### 1.4 Frontend — Lever Engine + Cockpit

| Fichier | État | Point d'intégration |
|---------|------|---------------------|
| `models/leverEngineModel.js` | OK | 5 types : conformite, facturation, optimisation, achat, data_activation. Accepte complianceSignals (V35) |
| `models/leverActionModel.js` | OK | 8 templates (lev-conf-nc, lev-conf-ar, lev-fact-*, lev-optim-*, lev-achat-*, lev-data-cover). Fallback template |
| `models/complianceSignalsContract.js` | OK | Accepte source:'operat'. Normalise severity, proof_expected, deadline |
| `models/billingInsightsContract.js` | OK | Anomalies + proof_links |
| `models/purchaseSignalsContract.js` | OK | Renewals + coverage |
| `models/proofLinkModel.js` | OK | buildProofLink(lever) → /kb?context=proof&domain=X. TYPE_TO_DOMAIN: conformite→reglementaire |
| `models/dataActivationModel.js` | OK | 5 briques : patrimoine, conformite, consommation, facturation, achat |
| `pages/cockpit/ImpactDecisionPanel.jsx` | OK | Affiche levers + micro-bloc preuve "Déposer" (V38) |
| `pages/ConformitePage.jsx` | OK | 4 tabs : Obligations, Données & Qualité, Plan d'Exécution, Preuves & Rapports |

### 1.5 Frontend — Navigation & Routing

| Fichier | État | Détail |
|---------|------|--------|
| `layout/NavRegistry.js` | OK | Module "operations" contient /conformite, /actions |
| `App.jsx` | OK | Route /conformite → ConformitePage. Pas de sous-routes /conformite/* |

---

## 2. CE QUI MANQUE (GAPS)

### 2.1 Backend

| Gap | Priorité | Description |
|-----|----------|-------------|
| **Tables EFA** | P0 | Aucune table tertiaire_efa, tertiaire_efa_link, etc. L'EFA (Entité Fonctionnelle Assujettie) est le concept central du Décret tertiaire |
| **Service tertiaire** | P0 | Pas de qualify_efa(), run_controls(), precheck_declaration(), generate_operat_pack() |
| **Routes /api/tertiaire** | P0 | Aucun endpoint CRUD EFA ni controls/precheck/export |
| **Seed tertiaire** | P1 | Le demo seed ne crée pas d'EFA, pas de scénarios multi-occupation/vacance/turnover |
| **KB domain tertiaire** | P1 | Pas de docs KB taggés domain="conformite/tertiaire-operat" |

### 2.2 Frontend

| Gap | Priorité | Description |
|-----|----------|-------------|
| **Pages tertiaire** | P0 | /conformite/tertiaire (dashboard), /wizard, /efa/:id, /anomalies |
| **Composants** | P0 | TertiaireStatusCard, ChecklistCard, TimelinePerimetre, ProofsPanel, ExportPackCard |
| **Levier tertiaire** | P1 | Pas de levier spécifique "tertiaire_operat" dans leverEngine |
| **Nav entry** | P1 | Pas d'entrée "Tertiaire / OPERAT" dans le menu Conformité |
| **API client** | P1 | Pas de fonctions tertiaire dans services/api.js |
| **Activation dim** | P2 | dataActivationModel n'a pas de dimension "tertiaire" |

---

## 3. ARCHITECTURE CIBLE

### 3.1 Modèle de données (nouvelles tables)

```
tertiaire_efa
├── id, org_id, site_id?, nom, statut, role_assujetti
├── reporting_start, reporting_end, created_at, closed_at, notes
└── FK: organisation_id, site_id (nullable — EFA peut être cross-sites)

tertiaire_efa_link
├── child_efa_id, parent_efa_id, reason
└── Cas: turnover, scission, fusion

tertiaire_efa_building
├── efa_id, building_id, usage_label, surface_m2
└── FK: tertiaire_efa.id, batiments.id

tertiaire_responsibility
├── efa_id, role (proprietaire|locataire|mandataire)
├── entity_type, entity_value, contact_email, scope_json
└── Multi-acteurs sur une même EFA

tertiaire_perimeter_event
├── efa_id, type, effective_date, description
├── justification, attachments_json
└── Événements: changement de périmètre, vacance, rénovation

tertiaire_declaration
├── efa_id, year, status (draft|prechecked|exported|submitted_simulated)
├── checklist_json, exported_pack_path
└── Lifecycle déclaration annuelle

tertiaire_proof_artifact
├── efa_id, type, file_path OR kb_doc_id
├── owner_role, valid_from, valid_to, tags_json
└── Pont vers Memobox (kb_doc_id → kb_docs.doc_id)

data_quality_issue
├── efa_id, year, code, severity, message_fr
├── impact_fr, action_fr, status, created_at
├── proof_required_json, proof_owner_role
└── Issues générées par run_controls()
```

### 3.2 Services backend

```
services/tertiaire_service.py
├── qualify_efa(efa_id)      → statut + explication (complétude données)
├── run_controls(efa_id, year) → issues[] (manquants/cohérences)
├── precheck_declaration(efa_id, year) → checklist + statut
└── generate_operat_pack(efa_id, year) → zip simulé + attestation HTML
```

### 3.3 Routes API

```
/api/tertiaire
├── GET  /efa                      → Liste EFA (filtres org_id, statut)
├── POST /efa                      → Créer EFA
├── GET  /efa/{id}                 → Détail EFA + buildings + responsibilities
├── PATCH /efa/{id}                → Modifier EFA
├── DELETE /efa/{id}               → Soft-delete EFA
├── POST /efa/{id}/buildings       → Associer bâtiment
├── POST /efa/{id}/responsibilities → Ajouter responsable
├── POST /efa/{id}/events          → Ajouter événement périmètre
├── POST /efa/{id}/controls?year=  → Lancer contrôles → issues[]
├── POST /efa/{id}/precheck?year=  → Pré-vérification déclaration
├── POST /efa/{id}/export-pack?year= → Générer pack export (simulé)
└── GET  /dashboard                → Vue agrégée (KPIs tertiaire)
```

### 3.4 Pages frontend

```
/conformite/tertiaire           → Dashboard tertiaire (KPIs, feu tricolore, liste EFA)
/conformite/tertiaire/wizard    → Assistant 7 étapes création EFA
/conformite/tertiaire/efa/:id   → Fiche détaillée EFA
/conformite/tertiaire/anomalies → Liste issues data_quality_issue
```

### 3.5 Intégration cockpit

```
LeverEngine (conformite type)
├── Nouveau levier: lev-tertiaire-efa quand issues severity >= medium
├── proofHint: "Attestation OPERAT" ou issue-specific
└── ctaPath: /conformite/tertiaire

ImpactDecisionPanel
├── Levier tertiaire affiché dans section leviers
├── "Créer une action" → leverActionModel (nouveau template)
└── "Déposer" → buildProofLink(lever) → /kb?domain=reglementaire&lever=lev-tertiaire-*

DataActivation (V37 extension)
└── Nouvelle dimension optionnelle "tertiaire" (EFA définies + surfaces + rôles + preuves)
```

---

## 4. POINTS D'INTÉGRATION (OÙ BRANCHER)

### 4.1 Preuves → Memobox

| Depuis | Vers | Mécanisme |
|--------|------|-----------|
| Fiche EFA > ProofsPanel | Memobox /kb | `buildProofLink(lever)` avec domain=conformite/tertiaire-operat |
| Dashboard tertiaire > Levier | Memobox /kb | hasProofData(lever) → micro-bloc "Déposer" |
| Issues tertiaire | Memobox /kb | proof_required_json → CTA deep-link vers /kb?context=proof&hint=... |

### 4.2 Leviers → Cockpit

| Condition | Levier | Impact € |
|-----------|--------|----------|
| issues tertiaire severity >= medium | lev-tertiaire-efa | Prorata risqueConformite (HYPOTHÈSE V1) |
| EFA sans déclaration && deadline < 90j | lev-tertiaire-deadline | Amende non_declaration: 7500€ (regs.yaml) |

### 4.3 Page Conformité existante

ConformitePage affiche déjà les findings TERTIAIRE_OPERAT via getComplianceBundle(). Pas de changement nécessaire. Le dashboard tertiaire (/conformite/tertiaire) est une vue spécialisée **complémentaire**, pas un remplacement.

### 4.4 Navigation

NavRegistry > module "operations" > ajouter sous-entrée :
```
{ path: '/conformite/tertiaire', label: 'Tertiaire / OPERAT', icon: Building2 }
```

---

## 5. PLAN D'EXÉCUTION (PHASES)

### Phase 1 : KB / Memobox (2 fichiers)
- `docs/decisions/tertiaire_sources_map.md` — mapping traçable règle → source → confiance
- Seed KB docs taggés domain="conformite/tertiaire-operat"

### Phase 2 : Backend modèles + migrations (3 fichiers)
- `models/tertiaire.py` — SQLAlchemy models (8 tables)
- `models/enums.py` — nouveaux enums (EfaStatut, EfaRole, DeclarationStatus, etc.)
- `database/migrations.py` — _create_tertiaire_tables()

### Phase 3 : Backend service + routes (3 fichiers)
- `services/tertiaire_service.py` — qualify, controls, precheck, export-pack
- `routes/tertiaire.py` — /api/tertiaire/* endpoints
- `main.py` — mount tertiaire_router

### Phase 4 : Frontend API + modèles (4 fichiers)
- `services/api.js` — fonctions tertiaire
- `models/leverEngineModel.js` — levier tertiaire
- `models/leverActionModel.js` — template lev-tertiaire-*
- `models/proofLinkModel.js` — si besoin (conformite→reglementaire déjà mappé)

### Phase 5 : Frontend pages + composants (5+ fichiers)
- `pages/TertiaireDashboardPage.jsx`
- `pages/TertiaireWizardPage.jsx`
- `pages/TertiaireEfaDetailPage.jsx`
- `pages/TertiaireAnomaliesPage.jsx`
- Composants : TertiaireStatusCard, ChecklistCard, etc.

### Phase 6 : Intégration nav + cockpit (3 fichiers)
- `layout/NavRegistry.js` — entrée tertiaire
- `App.jsx` — routes /conformite/tertiaire/*
- `models/dataActivationModel.js` — dimension tertiaire (optionnel)

### Phase 7 : Seed démo (2 fichiers)
- `services/demo_seed/gen_tertiaire.py`
- `services/demo_seed/orchestrator.py` — appel gen_tertiaire

### Phase 8 : Tests + docs (3+ fichiers)
- `tests/test_tertiaire.py` — backend (turnover, EFA fermée, checklist, cohérences)
- `pages/__tests__/tertiaireV39.test.js` — frontend (pages, CTA, deep-links, FR)
- `docs/dev/tertiaire_architecture.md`
- `docs/user_guides/tertiaire_grand_public.md`

---

## 6. FAITS / HYPOTHÈSES / DÉCISIONS

### FAITS
- RegOps tertiaire_operat.py évalue déjà scope, status, energy, multi-occupation (4 findings)
- Site model a tertiaire_area_m2, operat_status, annual_kwh_total (champs existants)
- Enums OperatStatus, TypeObligation.DECRET_TERTIAIRE, RegulationType.TERTIAIRE_OPERAT existent
- regs.yaml contient scope_threshold_m2=1000, penalties non_declaration=7500€, non_affichage=1500€
- KB Memobox (V38) supporte upload + lifecycle + proof deep-link
- complianceSignalsContract accepte source:'operat'
- ConformitePage affiche déjà les findings TERTIAIRE_OPERAT via bundle

### HYPOTHÈSES
- EFA est le concept central (pas le site) — un site peut contenir N EFA
- Multi-occupation → N EFA sur 1 bâtiment (1 bailleur + N locataires)
- Vacance = EFA active sans occupant (périodes tracées via perimeter_event)
- Turnover = EFA liée via efa_link (parent→child, reason="turnover")
- Impact €: prorata risqueConformite sur nb d'issues (HYPOTHÈSE V1, pas amende directe)
- Export pack SIMULÉ (pas de soumission réelle OPERAT — marqué "simulation")

### DÉCISIONS
- D1: Tables préfixées tertiaire_ (pas dans le schéma existant obligations)
- D2: Service séparé tertiaire_service.py (pas dans compliance_engine)
- D3: Routes sous /api/tertiaire (namespace dédié)
- D4: Pages sous /conformite/tertiaire/* (sous-routes de la section conformité)
- D5: Levier type='conformite' avec actionKey='lev-tertiaire-*' (pas un nouveau type)
- D6: Proof deep-link via proofLinkModel existant (domain=reglementaire suffisant)
- D7: Migration additive (pattern existant database/migrations.py)
- D8: Zero modification de regops/rules/tertiaire_operat.py existant (continue de fonctionner)
