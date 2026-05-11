# Backlog dette P2 — PROMEOS

> Liste des dettes techniques P2 (non bloquantes, à traiter Phase 4+ après
> Sprint Grammaire v1.2). Format : 1 entrée = 1 dette identifiée, traçable
> à un commit + une mitigation en place. Mise à jour à chaque commit qui
> introduit ou éteint une dette.

---

## P2-debt-BE-sites-isdemo-filter-other-endpoints

- **Description** : Phase F.4 a appliqué le filtre `Site.is_demo ==
  Organisation.is_demo` UNIQUEMENT dans `backend/routes/cockpit.py:_sites_for_org`.
  D'autres helpers et requêtes directes du repo n'appliquent PAS encore ce
  filtre — risque de fuite cross-tenant cosmétique ailleurs.
- **Estimation** : 4-6 j-h
- **Fenêtre** : Phase 3.5+ (avant scaling sur les 5 hubs restants, pour
  garantir la cohérence) ou Phase 4 (post Sprint Grammaire v1.2).
- **Détecté en** : F.4 commit [pending]
- **Mitigation** : aucun client réel actuellement (HELIOS demo seule org),
  l'impact est limité aux 2 sites "Site Test Phase 2" parasites orphelins
  de tests d'intégration. Le cockpit/jour est maintenant cohérent (5 sites).
- **Action requise** : appliquer le même filtre `Site.is_demo == Organisation.is_demo`
  aux helpers suivants :
  - `backend/routes/dashboard_2min.py:_sites_for_org_query`
  - `backend/routes/cockpit_v2.py:_sites_for_org` (clone)
  - `backend/services/cockpit_facts_service.py:_sites_for_org` (clone)
  - `backend/services/narrative/typology_resolver.py:_sites_for_org` (clone)
  - Requêtes directes `db.query(Site)` dans : `operat.py`, `intake.py`,
    `ems.py`, `consumption_diagnostic.py`, `billing.py`, `compliance.py`,
    `admin_users.py`, `patrimoine_crud.py`, `onboarding.py`, `tertiaire.py`,
    `monitoring.py`, `consumption_context.py` (audit grep nécessaire).
- **Recommandation** : factoriser `_sites_for_org` dans un service partagé
  `backend/services/scope_utils.py` au lieu de cloner par fichier (déduplication
  et garantie d'application uniforme du filtre).

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
