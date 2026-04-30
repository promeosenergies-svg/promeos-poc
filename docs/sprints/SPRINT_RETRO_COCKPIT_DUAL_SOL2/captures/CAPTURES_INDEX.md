# Captures Sprint Retro — Refonte Cockpit Dual Sol2

## sprint-end/ — captures fin de sprint (Phase 24, 2026-04-30)

| Fichier | Route | État |
|---|---|---|
| `cockpit-pilotage.png` | `/cockpit/jour` | ✅ Hydratée (Briefing Jour Energy Manager 30s) |
| `cockpit-strategique.png` | `/cockpit/strategique` | ✅ Hydratée (Vue exécutive CFO 3min) |
| `conformite.png` | `/conformite` | ✅ Hydratée (Conformité réglementaire) |

Origine : `tools/playwright/captures/phase17_all_routes/` post-Phase 24.1.
Audit Phase 17 capture 16 routes mais 13/16 timeout sur Vite dev (root
cause : recompile lazy bundles per-route, fix futur = `vite build &&
vite preview` au lieu de `npm run dev`).

## phase-0-end/ — captures pré-refonte Sol (2026-04-28, branche `claude/refonte-sol2`)

| Fichier | Route legacy | Cible refonte |
|---|---|---|
| `01-cockpit.png` | `/cockpit` (avant refonte) | `/cockpit/strategique` |
| `02-patrimoine.png` | `/patrimoine` | inchangée |
| `03-conformite.png` | `/conformite` | inchangée |
| `04-bill-intel.png` | `/bill-intel` (capture vide post-refresh) | inchangée |

## Outputs annexes

- `../outputs/playwright_phase17_manifest.json` : manifest 16 routes
  (statut HTTP, latency, titles, acronymes détectés, valeurs €/MWh).

## Captures non disponibles

- `phase-2-end/`, `phase-3-end/` : pas créés pendant le sprint
  (mode itératif sans phases distinctes 2/3 archivées).
