# Phase 0 — Audit read-only Agents Claude SDK PROMEOS

**Date** : 2026-04-24
**Branche** : `claude/agents-sdk-catalogue` (sortie de `origin/main` @ `a5e2424d`)
**Scope** : inventaire, diagnostic, mapping Paperclip → Claude SDK, catalogue cible
**Status** : ✅ STOP gate 0 validé (arbitrages utilisateur 2026-04-24) — **prêt pour Phase 1**

---

## 1. Inventaire exhaustif

| Source | Emplacement | État | Agents | Notes |
|---|---|---|---|---|
| **Claude Code SDK** | `.claude/agents/` | **VIDE** | 0 | Clean slate pour ce catalogue |
| **Python API** | `backend/ai_layer/agents/` | actif | 5 (736 L) | `regops_explainer`, `regops_recommender`, `data_quality_agent`, `reg_change_agent`, `exec_brief_agent` — API Anthropic directe, **runtime FastAPI** |
| **SDK orchestration V120** | `backend/orchestration/agents/` | absent sur main | 3 | `qa_guardian` (172 L), `regulatory` (395 L), `lead` (162 L) — existent **uniquement** sur `claude/agents-kb-integration-s1` (non mergée) |
| **Paperclip** | `~/.paperclip/instances/default/` | **OFFLINE** | 10 | KB préservée (CEO/CTO/Lead/PM/QA/UX/Data/DevOps/Regulatory/Energy Analytics) — cassé Windows, réf uniquement |
| **Skills Claude Code** | `.claude/skills/` | actif | 24 | 11 domain (promeos-* + energy-*) + 13 vendor/core |
| **CLAUDE.md racine** | `/CLAUDE.md` | actif | — | ne liste **aucun** agent → pas de routage Claude Code |

---

## 2. Baseline tests (ancrage non-régression)

- **Backend** : **5 715 tests** collectés (`pytest --collect-only`)
- **Frontend** : ~**3 870 tests** (Vitest — cf. memory + dernières sessions)
- **Total** : **≈ 9 585 tests** — baseline à ne **jamais** régresser pendant Phases 1-6

> Correctif vs prompt initial : la baseline citée (~8 314) était obsolète. Ajustement 1 de l'addendum.

---

## 3. Top 5 failles détectées

| # | Sévérité | Faille | Evidence |
|---|---|---|---|
| 1 | **P0** | V120 stranded | 11 commits locaux sur `claude/agents-kb-integration-s1` + stash. 3 agents SDK prêts mais inaccessibles depuis `main`. **Mitigation** : branche pushée + tag `v120-snapshot-agents-kb` posé 2026-04-24 |
| 2 | **P0** | Divergence source-of-truth tarifs | TURPE + accises présents dans `config/tarifs_reglementaires.yaml` **ET** `services/billing_engine/catalog.py`. Créer skill `tariff_constants` AVANT résolution = cristalliser la contradiction. Ajustement 2 addendum. Cf. [followups/tarifs_sot_consolidation.md](followups/tarifs_sot_consolidation.md) |
| 3 | **P1** | Hardcoded CO₂ frontend résiduel | `ConsoKpiHeader.jsx:12,138` importe `CO2E_FACTOR_KG_PER_KWH` depuis `pages/consumption/constants`. Migration Option C (V120) incomplète sur `main`. Cf. [followups/co2_frontend_cleanup.md](followups/co2_frontend_cleanup.md) |
| 4 | **P1** | Pas de routage Claude Code | `CLAUDE.md` racine n'a aucune section "agents disponibles / délégation". Claude Code ne peut pas router vers un agent spécialisé |
| 5 | **P2** | Skills partagées manquantes | `emission_factors.py` canonique Python mais pas exposé en skill Claude (`tariff_constants`, `regops_constants`, `helios_architecture` inexistantes dans `.claude/skills/`) |

---

## 4. Mapping Paperclip → Claude Code SDK (catalogue validé)

**11 agents cibles** (confirmé, pas de changement vs prompt audit original) :

### Core Development (5)

| Agent | Modèle | Source prompt | Provenance |
|---|---|---|---|
| `architect-helios` | Opus 4.7 | À créer | Ex-CTO Paperclip + décision arbitrage lead.py V120 |
| `implementer` | Sonnet 4.6 | À créer | Ex-Lead Engineer Paperclip + décision arbitrage lead.py V120 |
| `code-reviewer` | Sonnet 4.6 (read-only) | À créer | Nouveau (absent Paperclip) |
| `test-engineer` | Sonnet 4.6 | À créer | Nouveau |
| `qa-guardian` | Sonnet 4.6 (read-only) | **Extract V120** | `/tmp/v120_qa_guardian.py` (172 L) |

### Domain Expertise (4)

| Agent | Modèle | Source prompt | Provenance |
|---|---|---|---|
| `regulatory-expert` | Opus 4.7 | **Extract V120** | `/tmp/v120_regulatory.py` (395 L) |
| `bill-intelligence` | Sonnet 4.6 | À créer | Nouveau (pillar Bill pas couvert Paperclip) |
| `ems-expert` | Sonnet 4.6 | À créer | Ex-Energy Analytics Paperclip |
| `data-connector` | Sonnet 4.6 | À créer | Ex-Data Infra Paperclip |

### Support / Process (2)

| Agent | Modèle | Source prompt | Provenance |
|---|---|---|---|
| `security-auditor` | Sonnet 4.6 (read-only) | À créer | Nouveau |
| `prompt-architect` | Sonnet 4.6 | À créer | Nouveau (méta) |

### Archives / fusions

- **CEO**, **Product Manager**, **UX Designer** → archivés (pas de besoin dev direct / non-exécutable texte)
- **DevOps Engineer** → fusion dans `qa-guardian` (overlap CI/tests)

### Ajustement 3 addendum — stratégie V120

**Extract system prompts, pas cherry-pick fichiers**. 3 fichiers extraits dans `/tmp/` le 2026-04-24 :
- `/tmp/v120_qa_guardian.py` (172 L)
- `/tmp/v120_regulatory.py` (395 L)
- `/tmp/v120_lead.py` (162 L — à trancher architect vs implementer en Phase 2)

Arbitrage `lead.py` → documenté en Phase 2 dans `docs/audit/agents_sdk_phase2_decisions.md`.

---

## 5. Constantes / skills à mutualiser

- ✅ **CO₂ élec/gaz** (0.052 / 0.227) — canonique `backend/config/emission_factors.py` (ADEME V23.6). **À exposer** en skill `tariff_constants` (après consolidation SoT cf. followup)
- ❌ **TURPE / accises / CTA / TICGN** — divergence YAML `tarifs_reglementaires.yaml` vs `services/billing_engine/catalog.py`. **Bloquant pour skill tariff_constants** — traiter via followup dédié
- ✅ **NAF** — canonique `backend/utils/naf_resolver.py:resolve_naf_code()`. À référencer dans skill `helios_architecture`
- ❌ **Archi HELIOS** — `docs/architecture/` existe mais non référencé par CLAUDE.md. À wrapper en skill

---

## 6. Distinction `ai_layer/` vs `orchestration/` vs `.claude/agents/`

| Couche | Usage | Ne pas mélanger avec |
|---|---|---|
| `ai_layer/` — 5 agents API Anthropic directe | **Runtime FastAPI** (regops_explainer sur endpoint) | SDK CLI |
| `orchestration/` — 3 agents SDK (V120) | **CI / dev / audits** (spawn CLI) | FastAPI runtime |
| `.claude/agents/*.md` — 11 agents à créer | **Délégation Claude Code interactive** | Runtime |

**Les 5 agents `ai_layer/` ne migrent pas vers `.claude/agents/`**. Ils restent en runtime API. Le catalogue SDK est **additif**, pas un remplacement.

---

## 7. Arbitrages STOP gate 0

| Question | Arbitrage | Ajustement addendum |
|---|---|---|
| Catalogue 11 agents | ✅ Confirmé | — |
| Branche | ✅ `claude/agents-sdk-catalogue` depuis `main` après sécurisation V120 | Pré-requis |
| Ordre Phases 1-6 | ✅ Respecter prompt, atomic commits `fix(agents-pN): Phase X — description` | — |
| Faille #3 (CO₂ FE résiduel) | Source-guard xfail en Phase 4 + followup P0 dédié, pas de fix ici | Ajustement 4 |
| Baseline | 9 585 tests (5 715 BE + ~3 870 FE) | Ajustement 1 |
| TURPE/accises SoT | Consolider YAML→SoT avant skill `tariff_constants` | Ajustement 2 |
| Contenu V120 | Extract system prompts, pas cherry-pick fichiers | Ajustement 3 |

---

## 8. Sécurisation V120 (pré-requis exécuté)

```bash
# Exécuté 2026-04-24
git checkout claude/agents-kb-integration-s1
git push -u origin claude/agents-kb-integration-s1        # ✅ nouveau ref origin
git tag v120-snapshot-agents-kb && git push origin v120-snapshot-agents-kb  # ✅ tag pushé
git stash show -p stash@{0} > /tmp/v120-stash-20260424.patch  # ✅ patch sauvé
```

Statut :
- ✅ Branche sur origin : `refs/heads/claude/agents-kb-integration-s1`
- ✅ Tag sur origin : `v120-snapshot-agents-kb`
- ✅ Stash patch local : `/tmp/v120-stash-20260424.patch` (2866 bytes)
- ✅ 3 extracts agent : `/tmp/v120_{qa_guardian,regulatory,lead}.py`

---

## 9. Definition of Done — Phase 0

- [x] Inventaire exhaustif produit (tableau section 1)
- [x] Top 5 failles avec sévérité (P0/P1/P2)
- [x] Mapping Paperclip → Claude SDK (keep / fusion / archive)
- [x] Constantes / skills à mutualiser listées
- [x] Recommandation catalogue cible = 11 agents validée
- [x] V120 sécurisée (push + tag + stash patch + extracts)
- [x] Baseline tests ancrée (9 585)
- [x] 4 followups créés (3 prévus + 1 ajouté : local_main_hygiene)
- [x] STOP gate 0 validé par utilisateur

## 10. Followups détaillés

- [followups/co2_frontend_cleanup.md](followups/co2_frontend_cleanup.md) — P0 résiduel frontend
- [followups/tarifs_sot_consolidation.md](followups/tarifs_sot_consolidation.md) — P0 bloquant skill tariff_constants
- [followups/v120_orchestration_merge.md](followups/v120_orchestration_merge.md) — P1 plan de merge V120 sur main
- [followups/local_main_hygiene.md](followups/local_main_hygiene.md) — P2 pollution locale main + incident IDE switch

---

**Phase 0 clôturée 2026-04-24. Prochaine étape : Phase 1 — création des 11 AgentDefinitions en `.claude/agents/*.md`.**
