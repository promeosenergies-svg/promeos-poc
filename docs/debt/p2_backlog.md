# Backlog dette P2 — PROMEOS

> Liste des dettes techniques P2 (non bloquantes, à traiter Phase 4+ après
> Sprint Grammaire v1.2). Format : 1 entrée = 1 dette identifiée, traçable
> à un commit + une mitigation en place. Mise à jour à chaque commit qui
> introduit ou éteint une dette.

---

## P2-debt-BE-cockpit-jour-charts-series-hp-hc

- **Description** : backend `_build_cockpit_jour_charts` retourne uniquement
  `subscribed_kw`, `ChartFrameLine` génère `series_hp` / `series_hc` via
  `generateSyntheticHC()` fallback côté frontend.
- **Estimation** : 2-3 j-h
- **Fenêtre** : Phase 4 (post Sprint Grammaire v1.2)
- **Détecté en** : F.2 commit 29666297
- **Mitigation** : fallback synthétique HELIOS demo en place, visuellement
  correct (creux 0h-6h, plateau jour, pic 18h-20h). Pas de divergence
  visuelle vs vraies données attendues.
- **Action requise** : étendre `_build_cockpit_jour_charts` pour retourner
  `series_hp` + `series_hc` (CDC 30 min agrégée par heure). Source EMS
  via `consumption_unified_service.get_load_curve()`. Supprimer
  `generateSyntheticHC()` dans `ChartFrameLine.jsx` une fois données
  réelles disponibles.
