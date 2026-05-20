# Baseline Test Debt — feat/m2-4-rollout

**État au** : 2026-05-17
**Branche** : `feat/m2-4-rollout` (issue de `claude/refonte-sol2`)
**Source** : audit M2-4.1.ter
**Suite complète courante** : 8450 PASSED · 165 FAILED · 14 ERROR (`887a4730`)

---

## 1. Verdict audit M2-4.1.ter

Comparaison **pre-M2** (commit `605122da`, parent du 1er commit M2-1) vs **current** (`887a4730`) :

| | Pre-M2 `605122da` | Current `887a4730` |
|---|---|---|
| FAILED + ERROR | **164** | **179** (164 + 15) |
| Run | worktree, DB copiée isolée | arbre principal, DB live |

Diff brut : **15 introduits, 0 disparu**.

### Les 15 « introduits » sont environnementaux — PAS des régressions M2

Les 15 (14 ERROR `test_kb_telemetry.py` + 1 FAILED `test_proof_catalog_v50.py::test_template_dedup`)
échouent **toutes** sur `sqlite3.OperationalError: database is locked`.

Cause racine identifiée (`lsof`) : deux **process zombies** tiennent des connexions
ouvertes sur `backend/data/kb.db` et `backend/data/promeos.db` :
- PID `39024` — `python main.py` lancé le 2026-05-03 (serveur dev oublié)
- PID `56869` — fork `multiprocessing` à 99 % CPU depuis le 2026-04-30 (runaway)

Le run pre-M2 a passé ces 15 tests **uniquement** parce qu'il tournait sur une
**copie isolée** de la DB (worktree), que les zombies ne touchent pas.

**Preuve** (matrice code × DB) :

| Code | DB | Résultat 15 tests |
|---|---|---|
| pre-M2 `605122da` | copie propre | 15 PASS |
| current `887a4730` | live (zombie-lock) | 15 FAIL `database is locked` |
| **current `887a4730`** | **copie propre** | **15 PASS** |

Code courant + DB propre → 15/15 verts. La différence n'est pas le code : c'est
l'état runtime de la DB live. **Régressions code introduites par M2 : 0.**

> Effet secondaire révélé (dette test pré-existante, pas M2) : `test_kb_telemetry.py`
> et `test_proof_catalog_v50.py` ouvrent des connexions SQLite brutes sans
> `busy_timeout` → fragiles à tout détenteur concurrent de la DB. À durcir en M3-DEBT.

---

## 2. Origine de la dette

`feat/m2-4-rollout` descend de `claude/refonte-sol2`, qui a introduit une refonte
massive (**589 fichiers Python** diffèrent de `main`). La suite de tests backend
complète n'a manifestement jamais tourné verte sur cette branche depuis la refonte.

Les **164 échecs pré-M2** sont la dette technique de la refonte-sol2 — présente
**avant** tout commit M2. M2 (M2-1 foundation → M2-4.1.bis seed : sécurité layer,
repository pattern org-scopé, schéma + migration V4, seed V4) est **strictement
vert sur son périmètre** : 86/86 tests V4+M2-3+seed PASSED.

---

## 3. Modules en dette (164 échecs · 53 fichiers · groupés par famille)

> Causes **présumées** — la suite a tourné en `--tb=no` (pas de traceback capturé).
> Le diagnostic fin par traceback est explicitement du ressort de M3-DEBT.

### 3.1 — EMS / séries temporelles (~35)
`test_ems_timeseries` (13), `test_ems_p1` (10), `test_ems_overlay` (8),
`test_ems_weather_multi` (3), `test_ems_weather_signature` (1).
**Cause présumée** : désync fixtures EMS / données météo / signatures vs schéma.

### 3.2 — Conformité / RegOps (~27)
`test_compliance_score_service` (18), `test_compliance_bundle` (3),
`test_regulatory_sources_loader` (3), `test_capacite_rte_cbam_vnu_yaml` (2),
`test_regops_hardening` (1).
**Cause présumée** : scoring conformité / chargement sources réglementaires désync.

### 3.3 — Orchestration (19)
`test_orchestration_regulatory` (11), `test_orchestration_lead` (5),
`test_orchestration_config` (3).
**Cause présumée** : couche orchestration agents / config.

### 3.4 — Seed / Démo (~26)
`test_demo_seed_packs` (11), `test_demo_reset_unified` (6), `test_step30_efa_seed` (5),
`test_helios_surface` (2), `test_helios_seed_v83` (1), `test_demo_fixes` (1).
**Cause présumée** : packs de seed / reset désync vs modèles refonte.

### 3.5 — Billing / Achat / Marché (~15)
`test_vague2_atrd` (6), `test_billing_v68` (2), `test_market_data_service` (2),
`test_offer_pricing_v1_p0` (1), `test_purchase` (1), `test_purchase_upgrade` (1),
`test_losses_service` (1), `test_nebco_migration` (1).
**Cause présumée** : `test_billing_v68` = `pymupdf.FileDataError` (PyMuPDF/fixture PDF) ;
ATRD = colonnes/seed gaz.

### 3.6 — Usage (8)
`test_usage_suggest` (5), `test_usage_anomaly_detector` (2), `test_usage_disaggregation` (1).

### 3.7 — Intégrité / invariants / pipeline (~9)
`test_invariants` (3), `test_integrity_hardening` (1), `test_integrity_constraints` (1),
`test_integration_pipeline` (1), `test_cascade_recompute` (1), `test_event_bus` (1),
`test_events_upcoming` (1).

### 3.8 — Flex (5) · RGPD/Consent (4)
`test_flex_foundation` (3), `test_flex_mini` (2) · `test_rgpd_consent_endpoints_phase73` (4).

### 3.9 — Divers long-tail (~16)
`test_onboarding` (3), `test_reports` (2), `test_patrimoine*` (2), et ~9 fichiers
à 1 échec (`test_v42_site_signals`, `test_unified_anomalies`, `test_sprint2`,
`test_phase77/83/84`, `test_kb_usages`, `test_enedis_api`, `test_consumption_context_v1`…).

---

## 4. Règle adaptée pour M2-4.2 → M2-4.7

> **« 0 régression » pour M2-4 ne signifie PAS « 0 fail total ».**
>
> Baseline acceptée : **164 échecs pré-existants** (dette refonte-sol2, §3),
> liste de référence figée dans `docs/test-debt/baseline_m2-4-1-ter_failures.txt`.
>
> Critère DoD pour chaque commit M2-4.X :
>
> 1. Tests V4 / M2 / seed / security : **100 % verts**.
> 2. Aucun NOUVEAU test failed introduit — total ≤ 164 (hors bruit environnemental).
> 3. Aucun test précédemment vert ne devient rouge.
>
> **Vérification** : à chaque sprint, `diff` entre la liste de fails actuelle et
> `docs/test-debt/baseline_m2-4-1-ter_failures.txt`. Tout test devenu rouge qui
> n'y figure pas = STOP, sauf si prouvé environnemental (cf. §1).
>
> **Bruit environnemental** : un échec `database is locked` n'est pas une
> régression — vérifier `lsof backend/data/*.db` pour des process zombies, et
> re-tester sur DB isolée avant de conclure.

---

## 5. Plan de rattrapage M3

Hors scope M2-4. Sprint dédié **M3-DEBT** à planifier (~10-15 h estimé).
Prérequis : finaliser M2-4. Première étape obligatoire = re-run `--tb=short`
pour capturer les tracebacks (le présent audit a tourné `--tb=no`).

Ordre de priorité proposé :
1. EMS (§3.1, ~35) — plus gros bloc.
2. Conformité / RegOps (§3.2, ~27) — impact compliance.
3. Seed / Démo (§3.4, ~26) — bloque la reproductibilité des démos.
4. Orchestration (§3.3, 19).
5. Reste (§3.5-3.9).
6. Durcir `test_kb_telemetry` / `test_proof_catalog_v50` (`busy_timeout` sur les
   connexions SQLite brutes — cf. §1).

---

## 6. Fichier de référence

`docs/test-debt/baseline_m2-4-1-ter_failures.txt` — liste exhaustive des **164
échecs pré-existants** (capture pre-M2 `605122da`, code-déterministe, sans bruit
environnemental). Référence pour le diff de non-régression des sprints futurs.

Les 15 échecs environnementaux (§1) ne sont **pas** dans cette liste : ils
disparaissent dès que les process zombies sont tués — ce ne sont pas de la dette.
