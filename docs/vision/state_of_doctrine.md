# State of Doctrine — PROMEOS Sol v1.0.1

> Document hebdomadaire vivant. Mis à jour chaque vendredi pendant la
> refonte 12 semaines (Sprint 0bis → Sprint 6 démo juillet 2026).
>
> **Source de vérité** progress refonte. Intentionnellement court — pas
> de roman, juste les chiffres et les blocages.

---

## Snapshot baseline — 2026-04-26 (Sprint 0bis fin)

### Score doctrine global : **4.2/10** (cible 9.0+/10)

Distance restante : **+4.8 points sur 12 semaines** = **0.4 pts/semaine**

### Scores par pilier (audit Sprint 0)

| Pilier | Score | Backend | Frontend doctrinal |
|---|---|---|---|
| Cockpit | 4.2 | ✅ solide | ❌ dashboard B2B classique |
| Patrimoine | 3.4 | ✅ mature hiérarchie complète | ❌ table risk-first |
| EMS | 3.5 | ✅ signature 3P/4P/5P + DJU | ❌ Tier 2 invisibles |
| Conformité | 5.4 | ✅ RegOps canonique | ❌ acronymes bruts |
| Bill-Intel | 4.5 | ✅ shadow v4.2 17 mécanismes | ❌ moteur caché |
| Achat | 4.2 | ✅ 11 services post-ARENH | ❌ pas SolPageHeader |
| Flex | 3.2 | ✅ engine NEBCO sourcé CRE | ❌ pilier masqué nav |
| Transverse | 5.4 | — | ❌ 2/10 pages grammaire Sol |

### Tests doctrinaux §7 — état général

| Test | PASS sur 7 piliers |
|---|---|
| T1 — 3 secondes | 0/7 |
| T2 — Dirigeant non-sachant | 0/7 |
| T3 — Grand écart archetype | 0/7 (chantier β manquant) |
| T4 — Densité | 4/7 partiels |
| T5 — Standalone | 4/7 |
| T6 — J vs J+1 | 0/7 (chantier α manquant) |
| T7 — Transformation acronymes | 0/7 |
| T8 — Emplacement | 5/7 |

### Couverture KB existante mobilisable (inventaire Sprint 0bis)

| Chantier | % existant |
|---|---|
| β multi-archetype | 85% |
| Narrative/briefing | 92% |
| α events/signaux backend | 65% (lacune scheduler) |
| δ glossaire/transformation | 88% |
| Sources veille KB | 78% |

**Moyenne mobilisable : 81.6%** — beaucoup à surfacer, peu à reconstruire.

---

## Sprint 0bis — livré 2026-04-26

- [x] Patch doctrine v1.0.1 — triptyque `Fraunces + DM Sans + JetBrains Mono`
- [x] 4 ADR — `docs/adr/ADR-001` à `ADR-004` (grammaire / α events / β archetype / δ acronymes)
- [x] Inventaire KB+skills+memory — couverture 81.6% existant
- [x] PR template doctrine compliance §11.3 — `.github/PULL_REQUEST_TEMPLATE.md`
- [x] Tests source-guards pytest — `backend/tests/test_doctrine_sol_source_guards.py` (8 PASS)
- [x] Tests doctrinaux 1-8 automatisés — T4 + T7 livrés, T1/T2/T6/T8 patterns posés (activation S1.1+)
- [x] Memory updated — `project_sprint0_audit_doctrine_synthese.md`, `reference_doctrine_sol_v1.md`

## Sprint 1 — démarrage prévu lundi 2026-04-27 (semaines 2-3)

Cible Sprint 1 : grammaire industrialisée + sortir 3 calculs frontend backend + collapse `/` → `/cockpit`.

Livrables attendus :

- `frontend/src/ui/sol/SolPageFooter.jsx` + `SolNarrative.jsx` + `SolWeekCards.jsx` (avec fallback densifié §4)
- `backend/services/narrative/narrative_generator.py` orchestrateur
- `backend/services/data_provenance/provenance_service.py` envelope SCM
- 3 migrations frontend → backend : `RegulatoryCalendarCard` + `normalizeDashboardModel` + `BriefCodexCard.buildBrief*`
- Collapse `/` → `/cockpit?angle=daily` redirect 301
- 8 PRs atomiques (un par page Sol migrée), chaque PR utilise PR template doctrine compliance

Score doctrine cible fin S1 : **5.5/10** (+1.3 pts)

---

## Garde-fous opérationnels actifs

1. **PR template doctrine compliance §11.3** — `.github/PULL_REQUEST_TEMPLATE.md` obligatoire
2. **Source-guards pytest** — `backend/tests/test_doctrine_sol_source_guards.py` bloquants en CI
3. **Tests doctrinaux Playwright** — `tools/playwright/doctrine/runner.mjs` (T4+T7 actifs, T1/T2/T6/T8 S1.1+)
4. **Synchronisation hebdomadaire** — ce fichier (`state_of_doctrine.md`) mis à jour chaque vendredi
5. **7-agents persona audit fin de sprint** — protocole obligatoire à chaque clôture de sprint sur le scope migré :
   - Agent **Persona Marie** (DAF tertiaire 5 sites, briefing daily 8h45)
   - Agent **Persona Jean-Marc** (CFO ETI, vue COMEX, brief CODIR)
   - Agent **Persona Investisseur** (vision produit, différenciation Mix-E)
   - Agent **UX** (parcours utilisateur, friction cognitive)
   - Agent **UI / Visual** (signature Sol, palette journal, typo)
   - Agent **Navigation** (déambulation guidée §3 P2, mapping intention→emplacement §11)
   - Agent **CX** (TTFV, scorecard 10 critères, cohérence cross-pages)
   - Agent **Densité** (§4 — pas de zone vide >200px, week-cards toujours pleines)
   - Agent **Ergonomie** (a11y WCAG AA, motion reduced, drill-down accessible)

   Score consolidé /10 pour chaque agent + top 3 frictions résiduelles
   + top 3 quick wins next sprint. Synthèse archivée dans
   `memory/project_sprint{N}_audit_doctrine.md`.

---

## Délégations agents Claude

Routage canonique cf `CLAUDE.md` :

- **Implémentation S1+** : `implementer` (chaîné)
- **Pre-merge** : `code-reviewer` + `qa-guardian`
- **Tests** : `test-engineer`
- **Source-guards / org-scoping** : `security-auditor`
- **Conformité** : `regulatory-expert`
- **Bill-Intel** : `bill-intelligence`
- **EMS** : `ems-expert`
- **Sources externes 28 KB** : `data-connector`
- **Architecture cross-pillar** : `architect-helios`
- **Génération prompts** : `prompt-architect`

## Référence

- Doctrine : `docs/vision/promeos_sol_doctrine.md`
- ADR : `docs/adr/ADR-{001..004}-*.md`
- Memory cadre 3 mois : `memory/project_refonte_sol_doctrine_3mois.md`
- Memory audit Sprint 0 : `memory/project_sprint0_audit_doctrine_synthese.md`
