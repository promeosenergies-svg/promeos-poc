# ADR-016 — Math + Runtime + Cross-Module Enforcement Audit Doctrine

**Statut** : Accepté + ✅ **IMPLÉMENTÉ Phase 7.6** (post 5/5 pattern fixé)
**Date** : 2026-05-06 (acté Phase 0) → 2026-05-06 (livré Phase 7.6)
**Sprint** : C-7 Phase 0 → Phase 7.6
**Personnes impliquées** : Amine (founder), Claude architect-helios + bill-intelligence + regulatory-expert + security-auditor + qa-guardian + test-engineer + general-purpose
**Tracking dette** : pattern doctrinal acquis Sprint C-5 Phase 5.5 + Phase 5.7 audit transversal

---

## Contexte

Phase C a livré 7 sprints sur 7 prévus avec **0 régression sur 18 livraisons consécutives**. Mais l'audit transversal Phase C 6 AXES (Phase 5.7, commit `22c49675`) a révélé **18 findings nouveaux** dont **10 P0 cardinaux invisibles aux 7 audits SDK pré-commit cumulés** (Phase 5.5 deep + audits BILAN sprint-end).

Pattern récurrent détecté — **5 occurrences cross-phase** :

1. PRAGMA `foreign_keys=ON` ABSENT → ondelete=SET NULL × 4 FK silencieusement non-enforced
2. Cascade Org `consentement_*_global` CASCADE_MAP déclarée mais PATCH endpoint sans wiring
3. BillAnomaly UNIQUE(invoice_id, code) absent → doublons concurrents possibles
4. RGPD `audit_log_service.log_event` event `RGPD_CONSENT_CHANGE` non câblé
5. DEMO_MODE `scope_utils.get_scope_org_id` X-Org-Id sans validation DB

→ **Pattern doctrinal "Déclaration sans enforcement runtime"** : la déclaration archi (CASCADE_MAP, ondelete, UNIQUE, ADR) ne suffit pas — il faut **tests runtime cardinaux** garantissant l'enforcement effectif.

3/5 occurrences fixées Sprint C-5 (Phase 5.6 F1 + Phase 5.8 G1+G3). 2/5 reportées Sprint C-7 (RGPD wiring + DEMO_MODE).

### Audit Phase 0 Sprint C-7 — diagnostic terrain

- Aucun `.pre-commit-config.yaml` repo PROMEOS — pre-commit hooks **greenfield**
- 11 applications audit multi-agents Phase C — pattern reproductible mais pas formalisé doctrine
- 10 migrations Alembic propres / 0 destructive cumul Phase C — discipline ANTI-DROP appliquée 10 épisodes mais **artisanale** (vérification manuelle inspect commit avant `upgrade head`)
- F3 erreur arithmétique x1000 (Capacité 3.15 → 3150 EUR/MW.an) — détectée Phase 5.5 audit deep mais aurait dû être catched par SG cardinal
- NULL ≠ 0 doctrine appliquée Phase 5.6 F2 (R19) + Phase 5.8 G2 (R20) + G6 (operat_export) — ad-hoc, à formaliser

---

## Décision

### Doctrine cardinale 5 piliers — pré-clôture phase obligatoire

#### Pilier 1 — Math verification

Tout calcul littéral documenté (formule YAML/ADR/docstring/commentaire) DOIT avoir :

- Test arithmétique reproductible (`test_*_calculation_arithmetic_correct`)
- Source-guard cohérence YAML formula ↔ runtime constant ↔ docstring (~10x tolérance max sauf justification)
- Audit dédié AXE 1 Math Verifier en pré-clôture phase

**Exemple** : `3150 × 1.2 / 8760 = 0.4315 EUR/MWh` → test arithmétique vert + SG ratio runtime/formula < 1.5 (vs 1500 historique défaillant Phase 4.2).

#### Pilier 2 — Runtime enforcement

Toute contrainte ORM/contractuelle déclarée DOIT avoir :

- Test runtime cardinal (`test_*_runtime_enforced`)
- Vérification PRAGMA SQLite (`foreign_keys=ON`, `journal_mode=WAL`, etc.) au connect engine
- FK ondelete enforcement effectif (pas seulement DDL declared)
- UNIQUE/CHECK constraints validés runtime via test concurrent insert
- Cascade `CASCADE_MAP` câblées dans **tous** les endpoints PATCH/POST mutateurs (pas seulement déclarées)

**Pattern à généraliser** : pour chaque entrée `CASCADE_MAP_MVP_SPRINT_C1["X.field"]`, tester qu'au moins 1 endpoint PATCH déclenche `cascade_recompute_on_change(field_modified=...)`.

#### Pilier 3 — Cross-module SoT (1 SoT par concept)

Tout terme cardinal (CO2 factors, accises, weights, seuils RGPD, capacité tarif) DOIT avoir :

- 1 SoT unique (YAML `sources_reglementaires.yaml` ou `doctrine/constants.py`)
- Source-guard cohérence cross-callsites (au moins 2 occurrences = SG `test_*_yaml_constants_coherence`)
- Mention TraceTooltip FE pour différenciateur R10 (couverture cible 30+ termes Sprint C-7)
- Tests `test_*_no_phantom` (pattern Phase 4.3d COEFF_KWH_EF_TO_KWH_EP_ELEC=1.9 supprimé)

#### Pilier 4 — NULL vs 0 distinction

Tout calcul métier DOIT distinguer explicitement :

- `value is None` (donnée inconnue / non mesurée / acompte sans relève) → comportement métier dédié (skip, raise, return None)
- `value == 0` (mesuré à 0, valeur explicite)
- `value or 0` (anti-pattern collapse silencieux à supprimer Sprint C-7+)

**Source-guard** : `grep " or 0\b\| or 0\.0\| or \[\]\| or {}" backend/services/` cible critique = **0 occurrences** dans services calcul métier réglementaire (OPERAT export, billing agrégats, anomaly detector).

**Cas légitimes** (allowlist explicite SG) : `count or 0` pour stat agrégats UI, `description or ""` pour chaînes optionnelles, etc.

#### Pilier 6 — Audit deep multi-agents non-négociable Phase D+ (NOUVEAU Sprint C-8)

**Acquis Sprint C-7 audit deep multi-agents (commit `abdf449f`)** : 6 agents SDK parallèles
ont détecté **24 findings nouveaux invisibles aux 11 audits cumulés Phase 5.5+5.7+Phase 7** dont
**6 P0 critiques bloquants pré-pilote** (4 SEC IDOR + 2 REG terminologie/codes).

**Pattern doctrinal "Audit logging ≠ Authorization enforcement"** — 6e occurrence émergente du
pattern "Déclaration sans enforcement runtime" :

> Phase 7.5 décorateur `audit_external_api_call` (ADR-018) loggue les appels externes mais
> ne valide PAS l'authz cross-tenant. Les 5 endpoints DataConnect + 2 endpoints GRDF ont
> donc été audit-trackés mais IDOR-vulnérables. La présence d'un audit trail crée une
> illusion de sécurité.

→ **Cardinal** : audit logging et authz enforcement sont **2 préoccupations distinctes**.
Toujours wirer `resolve_org_id` + JOIN chain anti-IDOR, **indépendamment** du décorateur audit.

**Mandat doctrinal Sprint D+** :

- **Audit deep multi-agents avant clôture phase dense (>15 commits cumul)** : NON-NÉGOCIABLE
- **Méthode** : 6 agents SDK parallèles (1 / axe : code-reviewer + security-auditor + qa-guardian
  + regulatory-expert + bill-intelligence + architect-helios) avec read-only strict
- **ROI cardinal** : ~40 min vs séquentiel ~4-5 h = gain ×7 efficacité
- **Format livraison** : document `AUDIT_<scope>_<date>.md` avec tableau exhaustif findings
  (P0/P1/P2) + verdict consolidé + plan correction Tier 1+2+3
- **Trigger** : avant chaque tag `sprint-X-end` ou avant pilote/release externe

**Critères déclenchement audit deep multi-agents** :

| Trigger | Action |
|---|---|
| Sprint > 15 commits | Audit deep obligatoire |
| Pré-pilote externe | Audit deep + PII/RGPD focus |
| Pré-démo investisseur | Audit deep + sécurité cross-tenant + cohérence réglementaire |
| ADR cardinal nouveau | Audit deep ciblé + cross-pillar coherence |
| Migration Alembic destructive | Audit deep + data integrity focus |

**Anti-pattern à proscrire** : "1 commit = 1 audit unique" (audit séquentiel léger). Sans audit
deep multi-agents, les angles morts cross-fichiers/cross-modules restent invisibles (cf. les
5 sprints C-3/C-4/C-5/C-6/C-7 audits cumulatifs ayant manqué les 6 P0 audit deep).

#### Pilier 5 — Pre-commit hooks systémiques

3 hooks cardinaux Sprint C-7 (greenfield `.pre-commit-config.yaml`) :

- **Anti-DROP autogenerate** : si Alembic revision contient > 0 `op.drop_table` / `op.drop_index` non motivé par migration intentionnelle (label commit `migration:destructive` requis), bloquer commit
- **Anti-PRAGMA-OFF** : vérifier que `database/connection.py` event listener `connect` SQLite contient `PRAGMA foreign_keys=ON` (ligne grep)
- **Anti-erreur-arithmétique** : run `pytest tests/source_guards/test_*_yaml_runtime_consistency*` + `tests/source_guards/test_capacite_*` à chaque commit (rapide, ciblé)

### Audit deep multi-AXES en pré-clôture phase obligatoire

Pattern Sprint C-5 Phase 5.5 + Phase 5.7 transversal acté en doctrine :

- **6 AXES audit** : Math Verifier + Runtime Enforcer + Edge Cases NULL + Security & Org-Scoping + RGPD & Audit Trail + Cohérence Cross-Modules
- **Méthode** : 6 agents SDK spécialisés en parallèle (general-purpose + security-auditor + architect-helios + autres)
- **Trigger** : avant chaque tag `sprint-X-end` ou avant chaque pilote/release
- **Format livraison** : document `AUDIT_TRANSVERSAL_<scope>_<date>.md` avec tableau exhaustif findings + plan action priorisé

---

## Conséquences

### Positives

- **Pattern "déclaration sans enforcement" éradiqué** : tout déclaratif → enforcement runtime testé
- **Pre-commit hooks** = filet de sécurité automatisé contre récidives Phase C (anti-DROP, PRAGMA, math)
- **ROI audit deep doctrinal** : Phase 5.7 transversal a démontré **1:40 ratio** (~1.5 h investis = ~80 h économisés au pilote)
- **Crédibilité B2B** : audit consultant énergie pré-pilote ne peut plus catch erreur ×1000 type F3 (Capacité)
- **Conformité CNIL** : RGPD enforcement runtime + audit trail wiring complet (cardinal pilote investisseur)

### Négatives

- **Effort initial Sprint C-7** : ~3-4 h dédiés ADR-016 + 3 hooks (vs gain durable Phase D+)
- **Slowdown commits** : 3 hooks ajoutent ~1-2s par commit (acceptable, configurable `--no-verify` pour urgences explicites)
- **Discipline organisationnelle** : pré-clôture phase obligatoire = nouveau gate à respecter (gérable, déjà appliqué Sprint C-5)

### Mitigation

- Pre-commit hooks `--no-verify` autorisé pour urgences explicites (audit trail commit message)
- Audit deep multi-AXES = ~1-2 h / sprint (vs ~80 h économisés post-incident pilote)
- Source-guards parametrized (pas de duplication tests par concept — pattern factorisé)

---

## Implémentation Sprint C-7

**Phase 7.6 — ADR-016 doctrine + 3 pre-commit hooks (~3-4 h)** :

1. Créer `.pre-commit-config.yaml` racine repo (greenfield)
2. Implémenter 3 hooks Python (`scripts/pre_commit_hooks/`) :
   - `check_alembic_no_drop.py` (anti-DROP)
   - `check_sqlite_pragma_fk.py` (anti-PRAGMA-OFF)
   - `check_math_consistency.py` (anti-erreur-arithmétique)
3. Tests cardinaux 3 hooks
4. Source-guard `test_pre_commit_hooks_installed_source_guards.py`
5. Documentation `docs/dev/pre_commit_hooks.md`

### Application audit deep multi-AXES

Pattern formalisé Sprint C-7 + à reproduire Phase D :

- Sprint C-7 BILAN audit deep 6 AXES (~1.5-2 h cumul)
- Phase D pré-pilote audit transversal complet (~2-3 h)
- Tag sprint/phase end **après** audit deep (vs avant comme Sprint C-5 P5.5)

---

## Implémentation livrée Sprint C-7 Phase 7.6 (2026-05-06)

### Composants livrés (post 5/5 pattern fixé)

- `.pre-commit-config.yaml` (greenfield racine repo) — 3 hooks systémiques
- `scripts/pre_commit_hooks/__init__.py` (package)
- `scripts/pre_commit_hooks/check_alembic_no_drop.py` (~115 LOC) — Hook 1 anti-DROP
  - Détection `op.drop_table` / `op.drop_index` / `op.drop_constraint`
  - **Skip légitime cardinal** : drops dans `def downgrade()` autorisés (reverse upgrade — pattern Alembic standard)
  - Override autorisé via commentaire `# ALEMBIC_DROP_AUTHORIZED: <justification>` (3 lignes amont)
  - Skip backups `*.original-autogenerate` (audit trail préservé)
- `scripts/pre_commit_hooks/check_sqlite_pragma_fk.py` (~80 LOC) — Hook 2 anti-PRAGMA-OFF
  - Vérifie `@event.listens_for("connect")` + `PRAGMA foreign_keys=ON` dans `connection.py`
  - Cardinal Phase 5.6 F1 : RGPD `ondelete=SET NULL × 4` FK runtime
- `scripts/pre_commit_hooks/check_math_consistency.py` (~110 LOC) — Hook 3 anti-erreur-arithmétique
  - Pattern `X * A / B = R` (ASCII *) ET `X × A / B = R` (Unicode ×)
  - Support virgule décimale FR (`3,15`)
  - Tolérance 5% (arrondis acceptables)
- `.github/workflows/precommit.yml` — CI intégration GitHub Actions
- `backend/requirements-dev.txt` — `pre-commit>=3.6.0`

### Tests cardinaux Phase 7.6 (15 tests verts)

- `backend/tests/test_precommit_hooks_phase76.py` (15 tests)
  - **Hook 1** : block drop_table sans override + allow override comment + block drop_index/drop_constraint + **allow drops inside def downgrade()** + skip `.original-autogenerate` backups
  - **Hook 2** : block connection.py sans PRAGMA + allow event listener + skip autres fichiers
  - **Hook 3** : block Phase 5.6 F3 erreur cardinale (3.15 × 1.2 / 8760 = 0.43) + allow correction (3150 × 1.2 / 8760 ≈ 0.4315) + tolerance 5% + Unicode × + virgule décimale FR <!-- math-check: skip -->
    *(le marqueur `<!-- math-check: skip -->` ci-dessus est honoré par le hook pour permettre de citer la formule erronée sciemment, sinon le hook se mordrait la queue en scannant sa propre doc.)*
  - **Infrastructure** : `.pre-commit-config.yaml` racine + 3 hooks executables

### Validation runtime end-to-end

- `pre-commit run --all-files` → 3/3 hooks Passed sur état actuel repo
  - Hook 1 : vérifié sur 11 migrations Alembic Phase C (toutes downgrade() exemptes)
  - Hook 2 : vérifié sur `backend/database/connection.py:59` (PRAGMA Phase 5.6 F1 actif)
  - Hook 3 : vérifié sur YAML + 5 ADR Sprint C-7 (formules cohérentes post Phase 5.6 F3)

### Évolution doctrine post 5/5 pattern fixé

- Phase 0 (acté) → Phase 7.6 (livré) : ADR-016 transitionne de **doctrine théorique** à **patrimoine méthodologique exécutable**
- 3 hooks = filet de sécurité automatisé Phase D+ contre récidives 5 angles morts Phase C
- Métriques cumulées Phase C+ acquises : **24 livraisons consécutives sans régression**, **11 audits multi-agents**, **5/5 occurrences pattern doctrinal fixées**, **4 IDOR** + **9 ADR** (007 → 015 + 016/017/018/019)

---

## Références

- Pattern audit deep Phase 5.5 : `docs/audits/BILAN_SPRINT_C5_2026_05_06.md` Découverte cardinale §2
- Pattern audit transversal : `docs/audits/AUDIT_TRANSVERSAL_PHASE_C_2026_05_06.md` 6 AXES + 18 findings
- 5 occurrences "déclaration sans enforcement" : `BILAN_PHASE_C_7_7_LIVRES_2026_05_06.md` découverte doctrinale §4
- Phase 5.6 fix F1/F2/F3/F4 : commit `579b81a1`
- Phase 5.8 fix G1/G2/G3/G4/G5/G6 : commit `a1671aca`
- Implémentation Phase 7.6 : commit `<hash-phase-7-6>` + tests `backend/tests/test_precommit_hooks_phase76.py`
