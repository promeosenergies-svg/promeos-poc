# Prompt Claude Code — Consolidation SoT tarifs (YAML vs catalog.py)

**Cible** : session Claude Code séparée (worktree dédié).
**Branche** : `claude/tarifs-sot-consolidation` (depuis `origin/main`).
**Worktree recommandé** : `git worktree add ../promeos-turpe claude/tarifs-sot-consolidation`
**Scope** : consolidation unique source-of-truth pour TURPE + accises + CTA + CSPE entre `backend/config/tarifs_reglementaires.yaml` et `backend/services/billing_engine/catalog.py`.
**MCP obligatoires** : Context7, code-review, simplify.
**Durée estimée** : 4-6 h.

---

## Contexte

Followup P0 identifié en Phase 0 de l'audit Agents SDK (PR #260) :
[docs/audit/followups/tarifs_sot_consolidation.md](../audit/followups/tarifs_sot_consolidation.md).

**Problème** : deux sources concurrentes de vérité tarifaire.

| Source | Format | Utilisée par |
|---|---|---|
| `backend/config/tarifs_reglementaires.yaml` | YAML versionné | ParameterStore, agent V120 regulatory.py |
| `backend/services/billing_engine/catalog.py` | Python hardcodé | Shadow billing, recalcs |

**Divergences connues** (memory `project_agent_sdk_migration_2026_04_15.md`) :
- Accise élec 2025 gap (YAML incomplet 01/08/2025 → 31/01/2026) corrigé queue 1 V120
- TURPE 7 LU c_HPH : `0.0569` € /kWh dans `catalog.py:155`, version non explicite côté YAML
- CTA : double présence (cta_2021 + cta post fév 2026) — routage temporel encore à valider
- TICGN deprecated vs accise gaz active
- TVA : valid_from 2025-08-01 ajouté queue 1, à vérifier sur catalog

**Pourquoi bloquant** : skill `.claude/skills/tariff_constants/` ne peut pas être créée tant que les 2 sources ne sont pas alignées (cristalliserait une contradiction). Phase 3B de l'audit agents bloquée.

---

## Non-négociables

- Phase 0 **read-only** bloquante — zéro modif avant STOP gate utilisateur
- Baseline tests jamais régresser (actuellement sur `origin/main` : 5 691 BE)
- Atomic commits format `fix(turpe-pN): Phase X.Y — description`
- Aucune valeur hardcodée ajoutée — que des migrations vers ParameterStore
- Branche `claude/tarifs-sot-consolidation` (pas sur `claude/agents-sdk-catalogue`)
- Commit + push + draft PR immédiat (doctrine `feedback_commit_push_immediately.md`)
- Pre-merge obligatoire : `/code-review:code-review` + `/simplify`

---

## PHASE 0 — Diff YAML vs catalog.py (read-only, STOP gate)

### 0.1 Inventaire des clefs

```bash
# Top-level sections YAML
grep -E "^[a-z_]+:" backend/config/tarifs_reglementaires.yaml | sort -u
# Fonctions + constantes catalog.py
grep -E "^(def |[A-Z_]+\s*=)" backend/services/billing_engine/catalog.py
```

### 0.2 Table de divergences

Pour chaque grille (TURPE 7, ATRD gaz, ATRT8, accise élec T1/T2, accise gaz, CTA, TICGN, TVA, CEE, capacité) :

| Grille | YAML valeur | catalog.py valeur | Source officielle | Date effet | Divergence |
|---|---|---|---|---|---|

### 0.3 Rapport `docs/audit/tarifs_sot_divergences.md`

- 20-30 divergences attendues (estimation V120 findings)
- Classer par sévérité P0 (valeur différente) / P1 (manquant d'un côté) / P2 (metadata)

### STOP GATE 0

Valider avec utilisateur :
- Liste divergences complète
- Stratégie SoT cible : **YAML comme SoT unique** (proposition par défaut)
- `catalog.py` devient **consumer** (lit YAML via ParameterStore)

---

## PHASE 1 — Décisions par ligne

Pour chaque divergence P0/P1 du rapport Phase 0 :

- **Décision** : keep YAML / keep catalog / fusion / deprecate
- **Source justificative** : Légifrance / CRE / BOI (décret ou délibération)
- **Migration path** : rename YAML key ? ajouter metadata ? flag deprecated ?

Produire `docs/audit/tarifs_sot_decisions.md` (tableau décision par ligne).

**Atomic commit** : `fix(turpe-p1): Phase 1 — decisions par divergence + sources`

---

## PHASE 2 — Refacto loader (catalog.py → YAML consumer)

### 2.1 Migrer `catalog.py` en consumer

Remplacer les literals Python par des lectures YAML via ParameterStore :

```python
# AVANT
TURPE_7_LU_C_HPH = 0.0569

# APRÈS
from backend.config.parameter_store import get_tariff
turpe_7_lu_c_hph = get_tariff("turpe_7.lu.c_hph", date=today)
```

### 2.2 Enrichir YAML avec champs manquants

Ajouter `valid_from`, `valid_to`, `version`, `source`, `is_regulatory`, `deprecated` sur sections incomplètes.

### 2.3 Source-guards renforcés

Ajouter test pytest dans `tests/source_guards/` :

- `test_no_tariff_literal_in_code.py` — fail si un literal TURPE/accise apparaît hors YAML

**Atomic commit** : `fix(turpe-p2): Phase 2 — catalog.py consumes ParameterStore + YAML enrichi`

---

## PHASE 3 — Tests cohérence + baseline

- Test pytest qui lit YAML + appelle `catalog.py` + vérifie égalité valeurs
- Test temporalité : césures `valid_from` / `valid_to` cohérentes
- Test versioning : `turpe_7` vs `turpe_6` coexistent, pas d'écrasement
- Baseline BE ≥ 5 691 → +~15 tests nouveaux
- `/code-review:code-review` + `/simplify`

**Atomic commit** : `fix(turpe-p3): Phase 3 — tests cohérence YAML/consumer + baseline`

---

## PHASE 4 — Création skill `tariff_constants`

`.claude/skills/tariff_constants/SKILL.md` (< 200L) selon template Phase 3A audit agents :

```yaml
---
name: tariff_constants
description: Tarifs énergie France canoniques — TURPE 7, ATRD gaz, ATRT8, accises, CTA, TICGN, TVA, CEE. Wrapper de tarifs_reglementaires.yaml (SoT unique post-consolidation).
triggers: [TURPE, accise, CTA, TICGN, TVA, CEE, ATRD, ATRT, capacité, VNU, prix, tariff, shadow billing]
source_of_truth: backend/config/tarifs_reglementaires.yaml
last_verified: YYYY-MM-DD
---
```

Contenu : table des grilles + exemples usage `ParameterStore.get_tariff()` + anti-patterns (jamais hardcode, jamais duplication catalog.py literal, etc).

**Atomic commit** : `fix(turpe-p4): Phase 4 — skill tariff_constants (débloque Phase 3B audit agents)`

---

## DoD globale

- [ ] Phase 0 rapport produit + STOP gate validé utilisateur
- [ ] Phase 1 décisions documentées ligne par ligne
- [ ] Phase 2 `catalog.py` ne contient plus de literal tarifaire (source-guard PASS)
- [ ] Phase 3 tests cohérence YAML↔consumer PASS
- [ ] Phase 4 skill `tariff_constants` créée + référencée dans agents `bill-intelligence` + `regulatory-expert`
- [ ] PR draft ouverte `claude/tarifs-sot-consolidation` → `main`
- [ ] Baseline tests jamais régresser
- [ ] 4 commits atomiques + push
- [ ] Après merge : session agents-sdk-catalogue fait `git merge main` + ajoute skill ref + **Phase 3B** audit agents débloquée

---

## Post-merge signal vers PR #260

Une fois `claude/tarifs-sot-consolidation` mergée sur `main`, signaler à la session audit agents SDK pour :

1. `git checkout claude/agents-sdk-catalogue && git merge main`
2. Updater `agents_sdk_phase0_report.md` followups → `tarifs_sot_consolidation` status = CLOSED
3. Lancer Phase 3B : ajouter `tariff_constants` dans CLAUDE.md (section skills partagées canoniques) + remplacer placeholder dans les agents qui le réfèrent (`bill-intelligence`, `regulatory-expert`, `implementer`)
4. Atomic commit : `fix(agents-p3b): Phase 3B — skill tariff_constants référencée post-consolidation SoT`

---

**Début exécution** : Phase 0 maintenant. STOP à la gate 0.
