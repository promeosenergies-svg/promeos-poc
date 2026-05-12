# Backlog dette P2 — PROMEOS

> Liste des dettes techniques P2 (non bloquantes, à traiter Phase 4+ après
> Sprint Grammaire v1.2). Format : 1 entrée = 1 dette identifiée, traçable
> à un commit + une mitigation en place. Mise à jour à chaque commit qui
> introduit ou éteint une dette.

---

## P2-debt-BE-sites-isdemo-filter-other-endpoints — FERMÉE Correctif #3

- **Statut final** : Fermée Phase 3.4-bis Correctif #3 (commit pending).
- **Périmètre résolu** : 5 clones `_sites_for_org(_query)` factorisés dans
  `services/scope_utils.sites_for_org_query` — désormais helper canonique
  unique qui applique le filtre `Site.is_demo == Organisation.is_demo`.
  - `backend/routes/cockpit.py` : alias import
  - `backend/routes/cockpit_v2.py` : alias import
  - `backend/routes/dashboard_2min.py` : alias import
  - `backend/services/cockpit_facts_service.py` : alias import
  - `backend/services/narrative/typology_resolver.py` : délégation `.all()`
- **Smoke test 5 callers** : tous retournent **5 sites HELIOS** (vs 7
  pré-F.4). Cohérence cross-tenant garantie via le helper canonique.
- **Périmètre restant** : requêtes directes `db.query(Site)` dans 12 routes
  (operat, intake, ems, consumption_diagnostic, billing, compliance,
  admin_users, patrimoine_crud, onboarding, tertiaire, monitoring,
  consumption_context). Volume = ~50 callsites. **Pas critique** car
  ces routes ne lisent généralement pas le `is_demo` pour aggrégation
  cosmétique (elles agissent sur des sites identifiés explicitement).
  À auditer Phase 4+ avec un nouveau backlog item ciblé si nécessaire.

---

## P2-debt-BE-cockpit-jour-charts-series-hp-hc — REQUALIFIÉ Correctif #1

- **Description** : backend `_build_cockpit_jour_charts` retourne uniquement
  `subscribed_kw`. Le frontend `ChartFrameLine` n'a PLUS de fallback
  synthétique (suppression `generateSyntheticHC()` Correctif #1 du audit
  Sprint F 7-angles, recommandation /simplify + CS).
- **Estimation** : 2-3 j-h (inchangée)
- **Fenêtre** : Phase 4 (post Sprint Grammaire v1.2)
- **Détecté en** : F.2 commit 29666297 · Requalifié : Correctif #1 post audit Sprint F.
- **Statut actuel** : si backend ne fournit pas `series_hp` / `series_hc`,
  le chart `line_24h_hp_hc` rend uniquement axes + threshold (lecture
  honnête « pas de courbe disponible » plutôt que courbe trompeuse).
  L'audit CS avait identifié ce fallback comme « bombe métier déguisée »
  (frontend générant des CDC plausibles risque démo investisseur).
- **Action requise** : étendre `_build_cockpit_jour_charts` pour retourner
  `series_hp` + `series_hc` (CDC 30 min agrégée par heure). Source EMS
  via `consumption_unified_service.get_load_curve()`. Une fois livré, le
  rendu chart sera complet (HP + HC + threshold).
