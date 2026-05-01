# Audit post-merge J+7 — PR #264 P0 démo-ready
**Date** : 2026-05-01  
**Branche auditée** : `claude/refonte-visuelle-sol`  
**Auditeur** : Agent Claude Code (post-merge J+7 automatisé)

---

## 1. État PR #264

| Champ | Valeur |
|-------|--------|
| Statut | **merged** ✅ |
| Mergé le | 2026-04-25T09:13:34Z |
| Commit merge | `7309165c` |
| Source → Cible | `claude/fix-p0-demo-ready` → `claude/refonte-visuelle-sol` |
| Additions / Suppressions | +4 343 / -896 lignes, 32 fichiers |

---

## 2. Checklist 6 fixes P0

| ID | Fichier | Pattern attendu | Résultat | Ligne |
|----|---------|-----------------|----------|-------|
| M-01 | `frontend/src/components/OnboardingOverlay.jsx` | `function shouldShowOnboarding()` | ✅ PRÉSENT | L13 |
| M-02 | `frontend/src/components/pilotage/NebcoSimulationCard.jsx` | `DEMO_FALLBACK_SITE = '1'` | ✅ PRÉSENT | L26 |
| M-02 | `frontend/src/components/pilotage/RoiFlexReadyCard.jsx` | `DEMO_FALLBACK_SITE = '1'` | ✅ PRÉSENT | L20 |
| M-02bis | `frontend/src/pages/CockpitSol.jsx` | `hasSite = Boolean(siteId)` + `isoDate` | ⚠️ SUPPLANTÉ — voir note | — |
| M-03 | `frontend/src/services/api/admin.js` | `if (!q \|\| q === '*')` | ✅ PRÉSENT | L103 |
| M-05 | `frontend/src/App.jsx` | `<Route path="/energy-copilot"` + `Navigate to="/cockpit"` | ✅ PRÉSENT | L726-727 |

### Note M-02bis — Supplanté, non régressé

Le commit atomique `bfd00beb` avait introduit `const isoDate = (d) => ...` + `const hasSite = Boolean(siteId)` dans `useCockpitSolData`. Ces patterns ne sont **plus présents** dans la version actuelle de `CockpitSol.jsx` car le fichier a été entièrement réécrit (**refonte from-scratch**) dans la branche `claude/refonte-visuelle-sol`.

La version actuelle ne contient **aucun appel `getEmsTimeseries`** — vérification :
```bash
grep -n "getEmsTimeseries\|ems/timeseries" frontend/src/pages/CockpitSol.jsx → (vide)
```

L'objectif du fix (éviter le 422 `/api/ems/timeseries`) est atteint par suppression totale de l'appel. C'est une résolution plus robuste que le guard d'origine. **Pas de régression.**

---

## 3. Commits semaine écoulée (depuis 2026-04-25) touchant les fichiers P0

```
7309165c 2026-04-25 11:13:34 +0200  fix(p0-demo-ready): 6 P0 démo blockers → 36/36 routes clean (#264)
  frontend/src/App.jsx
  frontend/src/components/OnboardingOverlay.jsx
  frontend/src/components/pilotage/NebcoSimulationCard.jsx
  frontend/src/components/pilotage/RoiFlexReadyCard.jsx
  frontend/src/pages/CockpitSol.jsx
  frontend/src/services/api/admin.js
```

**Aucun commit ultérieur** n'a modifié ces fichiers depuis le merge. Le commit `7309165c` est le merge de PR #264 lui-même.

| Commit | Verdict risque |
|--------|----------------|
| `7309165c` — merge PR #264 | ✅ Introduce les fixes P0, pas de régression |

---

## 4. Anti-patterns détectés

| Anti-pattern | Statut |
|---|---|
| `DEMO_FALLBACK_SITE = 'retail-001'` (régression M-02) | ✅ ABSENT |
| `localStorage.getItem` sans guard `shouldShowOnboarding` (régression M-01) | ✅ Appels dans la fonction `shouldShowOnboarding()` elle-même — gardés |
| Recréation de `pages/EnergyCopilotPage.jsx` (régression M-05) | ✅ ABSENT |
| Dates > 2026-04 sans `date.today()` dans `gen_billing.py` (régression M-04) | ✅ `date.today()` présent L61 + L171 |

---

## 5. Verdict global

```
VERDICT: NO-REGRESSION
```

- 5/6 patterns détectés textuellement ✅
- 1/6 (M-02bis) supplanté par refonte from-scratch avec résolution plus robuste ✅
- 0 anti-pattern détecté ✅
- 0 commit post-merge modifiant les fichiers P0 ✅
- Baseline scorecard 36/36 routes non altérée (aucune modification des fichiers concernés)

---

## 6. Recommandation

Mettre à jour le pattern de vérification M-02bis pour la prochaine itération : remplacer le grep `hasSite/isoDate` par `grep -L "getEmsTimeseries" frontend/src/pages/CockpitSol.jsx` (absence de l'appel EMS comme critère).
