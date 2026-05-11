# Phase 3.4 — HARD STOP : audit + extraction avant Phase 3.5

> **Prompt Claude Code** à exécuter en séquence atomique sur la branche `claude/refonte-sol2` (HEAD = `0018f45e`).
> Objectif : valider que la Phase 3.4 cockpit/jour V2 est prête à servir de gabarit pour Phase 3.5 (les 5 hubs restants).

---

## Contexte cardinal

Tu es **Claude Code**. La Phase 3.4 vient d'être livrée : commit `0018f45e`, 7 fichiers, +1 569/−474. Hub Page L11 cockpit/jour V2 est en production sur la branche.

**Amine a déclenché un HARD STOP** avant de scaler L11 sur les 5 hubs restants (energie, conformite, factures, achat, patrimoine).

Lis impérativement avant tout code :

- `CLAUDE.md` (racine repo)
- `docs/design-system/PROMEOS_DESIGN_SYSTEM_TECHNICAL_SPEC.md`
- `docs/doctrine/sol_v1_1_addendum_hub_page.md`
- `docs/adr/ADR-021-hub-page-grammar-l11.md`

---

## Séquence d'exécution (8 phases atomiques)

### Phase A — Capture Playwright "after" (Phase 3.4 actuelle)

```bash
# 1. Vérifier que la branche est sur HEAD Phase 3.4
git log --oneline -1  # doit afficher 0018f45e

# 2. Lancer le serveur dev
npm run dev &
sleep 5

# 3. Copier le script de capture
cp /chemin/vers/phase_3_4_before_after.spec.js \
   frontend/tests/visual/

# 4. Créer le dossier des snapshots
mkdir -p frontend/tests/visual/snapshots/{before,after}/{2xl,xl,lg}

# 5. Lancer la capture "after"
PHASE_LABEL=after BASE_URL=http://localhost:5173 \
  npx playwright test frontend/tests/visual/phase_3_4_before_after.spec.js

# Vérifier 6 captures à 3 viewports à 5 states = ~80 PNGs générés
ls frontend/tests/visual/snapshots/after/ -R | head -30

# 6. Stopper le serveur
kill %1
```

**Commit atomic A** : `chore(p3.4): capture playwright after for cockpit/jour V2`

---

### Phase B — Capture Playwright "before" (état avant Phase 3.4)

```bash
# 1. Stash tout changement non commité
git stash push -m "Phase 3.4 audit temp"

# 2. Checkout l'état pré-Phase 3.4 (7 commits avant)
git log --oneline -10 claude/refonte-sol2
# identifier le commit AVANT 0018f45e (probablement 0018f45e~7)

git checkout 0018f45e~7  # → détaché HEAD volontaire

# 3. Relancer serveur dev
npm run dev &
sleep 5

# 4. Lancer la capture "before"
PHASE_LABEL=before BASE_URL=http://localhost:5173 \
  npx playwright test frontend/tests/visual/phase_3_4_before_after.spec.js

# 5. Stopper et revenir
kill %1
git checkout claude/refonte-sol2
git stash pop
```

**Pas de commit ici** (state pre-Phase 3.4 non modifié).

---

### Phase C — Composition de la planche before/after

Voir script `scripts/compose_before_after_phase_3_4.js` (à créer).

**Commit atomic C** : `docs(p3.4): compose before/after visual diff`

---

### Phase D — Audit UX/UI/CX/CS

Voir grille `docs/audits/phase_3_4_audit_grid.md`.

**Commit atomic D** : `docs(p3.4): audit UX/UI/CX/CS rempli — score X/96`

---

### Phase E — Décision GO/NO-GO `<HubKpiCard>` extraction

Voir `docs/audits/phase_3_4_decision_hubkpicard.md`.

---

### Phase F — Extraction `<HubKpiCard>` (si GO)

Si **GO extraction** → créer `frontend/src/components/grammar/hub/HubKpiCard.jsx`
+ stories + tests + source guard. Migrer CockpitJour.jsx.

**Commit atomic F** : `feat(p3.4)!: extract HubKpiCard primitive from CockpitJour inline`

---

### Phase G — Recapture Playwright "after extraction"

```bash
PHASE_LABEL=after_extraction BASE_URL=http://localhost:5175 \
  npx playwright test frontend/tests/visual/phase_3_4_before_after.spec.js
```

**Commit atomic G** : `test(p3.4): recapture validates zero visual regression post-extraction`

---

### Phase H — Synthèse + décision Phase 3.5

Créer `docs/audits/PHASE_3_4_GO_NO_GO_REPORT.md`.

**Commit atomic H** : `docs(p3.4): GO/NO-GO report — décision Phase 3.5`

---

## Récapitulatif effort estimé

| Phase | Description | Durée | Commit |
|---|---|---|---|
| A | Capture Playwright "after" | 45min | ✅ |
| B | Capture Playwright "before" | 30min | — |
| C | Composition planche before/after | 30min | ✅ |
| D | Audit UX/UI/CX/CS (32 critères) | 2-3h | ✅ |
| E | Décision HubKpiCard extraction | 30min | — |
| F | Extraction HubKpiCard (si GO) | 3-4h | ✅ |
| G | Recapture post-extraction | 30min | ✅ |
| H | GO/NO-GO report Phase 3.5 | 30min | ✅ |
| **TOTAL** | **Audit complet Phase 3.4** | **8-11h** | **6 commits** |

---

## Definition of Done

- [ ] Captures before/after sur 3 viewports à 5 states = 30+ PNGs
- [ ] Planche HTML comparative générée
- [ ] Grille d'audit 32 critères remplie avec score /96
- [ ] Décision HubKpiCard tranchée (GO ou NO-GO documenté ADR)
- [ ] Si GO extraction : HubKpiCard.jsx + .stories.jsx + .test.jsx créés
- [ ] Vitest baseline +6 tests (4 686+)
- [ ] Source guard `kpi-not-inline-in-hub-pages` ajouté
- [ ] Recapture post-extraction = zéro régression pixel-near
- [ ] PHASE_3_4_GO_NO_GO_REPORT.md rédigé avec décision Phase 3.5
- [ ] 6 commits atomiques propres avec messages conformes
