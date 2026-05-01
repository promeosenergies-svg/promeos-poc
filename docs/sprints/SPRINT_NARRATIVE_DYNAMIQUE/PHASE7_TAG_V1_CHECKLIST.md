# Phase 7 — Checklist préparation tag `narrative-dynamique-v1.0`

**Branche** : `claude/refonte-sol2`
**Date checklist** : 2026-05-01
**Statut** : ✅ READY pour merge / 🟡 tag v1.0 conditionné aux items ci-dessous

---

## ✅ Correctifs Phase 7 livrés (audit final P0+P1)

| ID | Finding audit | Correctif | Tests |
|---|---|---|---|
| **P0-A** | `simulate_date` sans bornes (DoS doux + week_iso aberrant) | Borne 1970 ≤ year ≤ now+1 an dans route + 400 explicite | 3 tests |
| **P0-B** | `get_activity_name(None)` ligne 176 → "magasin" générique pour boulanger | Propagation `naf_code` builder → `compose_dt_drift_sentence` via `compose_sentence_1_eventful` | 4 tests |
| **P1-C** | `compose_persona_mention` jamais appelée + `apply_tone_variation` jamais appelée | Wiring dans `_build_cockpit_comex` : tone_variation appliqué au narrative final, persona_mention surcharge `italic_hook` si user_first_name + user_role passés depuis route | 7 tests |
| **P1-D** | Doublon `_format_eur_short` (virgule) vs `_fmt_eur_short` (point) | SoT canonique `services/narrative/formatters.py` (FR convention) + alias rétrocompat persona_context et sentence_composer | 12 tests |

**Total tests Phase 7** : 26 nouveaux tests (cumul **349 / 349 verts** sprint complet).

---

## ✅ Critères MERGE branche `claude/refonte-sol2`

- [x] 349/349 tests verts cumulés (Phases 1.1-1.4 + 2.1-2.2 + 3.1-3.3 + 4.0.A-C + 4.bis A-C2 + 4.bis3 + 4.1 + 4.2 + 5 kit + 6 + 7)
- [x] Aucun import circulaire (services ne dépendent pas de routes — vérifié via audit final)
- [x] Doctrine §6 anti-patterns verrouillés via AST source-guard (no `.lower()` actif)
- [x] Doctrine §7 sourçage cross-composers vérifié (16 tests parametrize)
- [x] Doctrine §11.3 budget MAX_PHRASE_1_WORDS=35 (48 tests parametrize)
- [x] Frontend wiring Phase 4.bis livré (SolWeeklyDeltaBadge + SolNarrative drill-down)
- [x] Frontend baseline 4 299/4 301 verts (+516 vs baseline 3 783)
- [x] Aucune régression sur tests IAM / cockpit_facts / pages_briefing legacy

**→ Merge OK.**

---

## 🟡 Conditions pour TAG `narrative-dynamique-v1.0`

Les items suivants sont **bloqueurs** pour le tag v1.0 (pas pour le merge intermédiaire) :

### Bloqueurs cardinaux

- [ ] **Panel Phase 5 exécuté** : 6 personnes recrutées + 6 sessions chronométrées + critères C1+C2+C3 validés sur 6/6 panels (cf `phase5_validation_kit/grille_evaluation.md`)
- [ ] **Mini-sprints correctifs Phase 5** : si critère raté, sprint correctif (1-2 j) + re-test 1-2 panels rappelés AVANT tag
- [ ] **Démo HELIOS validée** : Marie + Jean-Marc + Hervé + Anne testent en live l'instance déployée et confirment cohérence narrative

### Dette tracée — non-bloqueur tag v1.0 mais à ouvrir tickets backlog

- [ ] **Ticket BL-1** : 9 builders narrative legacy non wirés Phase 4.0.B (cockpit_daily, patrimoine, conformite, bill_intel, achat_energie, monitoring, diagnostic, anomalies, flex). Actuellement seul `cockpit_comex` consomme `prioritize_triggers` + `compose_sentence_1_eventful`. **Risque** : la promesse "narrative dynamique" n'est tenue que sur 1/10 pages.
- [ ] **Ticket BL-2** : Migration `_fmt_eur_short` (narrative_generator.py:3147) → `format_eur_short` SoT canonique. Conservation actuelle = trade-off rétrocompat (~30 callsites week_cards/KPIs). Migration progressive Phase 7.bis.
- [ ] **Ticket BL-3** : Typologie `ETI_TERTIAIRE` (V2 Q3 2026) — Marie tombe sur GRAND_GROUPE en attendant. Acceptable car phrase stable GG sans CODIR (Phase 4.0.A) + vocabulaire "patrimoine" reste cohérent. Mapping NAF 6820B reste conservateur.
- [ ] **Ticket BL-4** : Personas `ENERGY_BUYER` + `CSR_MANAGER` ajoutés Phase 4.bis3 mais focus_text minimal. Enrichir pour V2 quand pages dédiées Achat / RSE en place.
- [ ] **Ticket BL-5** : Internationalisation. Tout le sprint reste FR. EN/ES = sprint dédié.
- [ ] **Ticket BL-6** : Phase 6 `simulate_date` MVP. Override uniquement `week_iso`. Re-jouer events à date passée nécessite event store temporel (V2).
- [ ] **Ticket BL-7** : Cross-org override typology_override. Actuellement global par user. ADR P1-1 Phase 4.bis3. Si V2 multi-org requis, migrer vers `(user_id, org_id)` unique composite.
- [ ] **Ticket BL-8** : Féminin non fléchi sur `PERSONA_ROLE_LABEL` (audit final CX). "directeur d'établissement" pour Anne, "DAF" unisexe par chance. À fléchir selon prénom user.
- [ ] **Ticket BL-9** : Glossaire TURPE/OPERAT inline (audit final CX) — sigles préservés mais pas glosés inline pour COMMERCE. Front utilise `SolNarrativeText` (auto-tooltip 62 entrées) — vérifier couverture sur Hervé.

---

## 📊 Métriques sprint final

| Métrique | Valeur |
|---|---|
| Commits livrés | ~28 atomiques |
| Phases sprintées | 6 spec (1-6) + 4.bis FE wiring + 4.bis2/4.bis3 corrections + 5.bis correction + 7 correctifs audit |
| Mini-audits par phase | 4 mini-audits (Phase 4.bis3 + Phase 5.bis + Phase 6 + Phase 7 final) |
| Tests source-guards créés | 349 BE + 26 FE |
| Lignes code BE livrées | ~4 200 (services + routes + tests) |
| Lignes code FE livrées | ~430 (composants + hook + tests) |
| Lignes docs livrées | ~1 800 (kit Phase 5 + sprint exec + checklist v1.0) |
| Audits triple multi-agents | 2 (post-Phase 3 + final post-Phase 7) |

---

## 🔁 Prochaines étapes

1. **Cette session** : audit final UX/UI/CX/ergo/personas multiples (post-correctifs Phase 7)
2. **Cette semaine** : merge `claude/refonte-sol2` → `main` (PR draft à ouvrir)
3. **Semaines W4-W5** : recrutement panel Phase 5 + sessions test
4. **Sprint Q3 2026** : V2 ETI_TERTIAIRE / wiring 9 builders legacy / event store temporel

---

*Document confidentiel interne PROMEOS — checklist tag v1.0 au moment du livrable.*
