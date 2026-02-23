# ADR V60 — Cockpit Patrimoine : Portfolio Health Bar

**Statut :** Accepté
**Date :** 2026-02-23
**Auteurs :** équipe PROMEOS

---

## Contexte

V58/V59 ont livré les anomalies patrimoniales enrichies (priority_score, business_impact, regulatory_impact)
au niveau site. La page `/patrimoine` affiche déjà une table de sites avec risques et un SiteDrawer
avec l'onglet Anomalies.

**Problème :** il n'y a pas de vue agrégée "portfolio" permettant en un coup d'œil de connaître :
- le risque financier global du patrimoine,
- quels sites sont les plus à risque,
- quel cadre réglementaire domine les anomalies.

---

## Décision

### Option retenue : agrégation backend à la demande, zéro DB nouvelle

**`GET /api/patrimoine/portfolio-summary`** — endpoint dédié qui :
1. Récupère les sites du scope (org + filtres optionnels) via une requête SQL jointurée.
2. Pour chaque site, appelle `compute_site_anomalies()` + `enrich_anomalies_with_impact()`.
3. Agrège en mémoire : total_risk, sites_at_risk par sévérité, framework_breakdown, top_sites.
4. Retourne un payload compact (pas les anomalies complètes).

**Composant frontend :** `PatrimoinePortfolioHealthBar` affiché en tête de `/patrimoine`.

---

## Alternatives considérées

### Option A — Agrégation frontend (boucle sur tous les sites)
❌ Rejeté : N requêtes API pour N sites → N+1 côté réseau. Payload énorme si 200 sites.
Inacceptable en prod.

### Option B — Précalcul en DB (nouvelle table `portfolio_summary`)
❌ Rejeté : Nécessiterait une migration DB + job de refresh. Hors scope POC.
Ajouterait une dépendance de fraîcheur (stale data).

### Option C — Réutiliser `/anomalies` paginé + calcul frontend
❌ Rejeté : Pagination masque les sites hors première page → totaux incomplets.
Le tri risk DESC n'est pas garanti sur l'ensemble du portfolio.

### Option D (retenue) — Endpoint dédié, calcul à la demande, zéro DB
✅ Retenu :
- Pure function `enrich_anomalies_with_impact()` déjà produite en V59 — réutilisée sans modification.
- Payload compact : seulement les agrégats + top_n sites (pas les anomalies complètes).
- Multi-org safe : même scope chain que tous les autres endpoints patrimoine.
- Pas de migration DB.
- Cache frontend 5s (TTL `_cachedGet`) pour éviter les doubles fetches.

---

## Conséquences

### Positives
- Cockpit risque visible immédiatement sur `/patrimoine` après import HELIOS.
- CTA "Voir anomalies" ouvre directement le SiteDrawer sur l'onglet Anomalies (`initialTab='anomalies'`).
- Cas critique géré : `sites_count === 0` → bandeau "0 €" + CTA "Charger HELIOS".
- Backward compat : endpoint additionnel, aucune régression V58/V59.

### Limites acceptées
- **Pas temps réel** : les risk estimates sont les mêmes que V59 (hypothèses statiques).
- **Linéaire en nombre de sites** : O(N) × `compute_site_anomalies`. Au-delà de ~500 sites,
  envisager un job de précalcul nocturne stocké dans Redis ou une table `portfolio_cache`.
- **top_n max 10** : limite stricte pour garder le payload léger.

---

## Périmètre technique

| Fichier | Modification |
|---------|-------------|
| `backend/routes/patrimoine.py` | +4 Pydantic models V60 + endpoint `GET /portfolio-summary` |
| `frontend/src/services/api.js` | +1 wrapper `getPatrimoinePortfolioSummary` |
| `frontend/src/components/PatrimoinePortfolioHealthBar.jsx` | NEW — bandeau cockpit |
| `frontend/src/pages/Patrimoine.jsx` | +import, +drawerInitialTab state, +openDrawerOnAnomalies, +HealthBar dans render |
| `backend/tests/test_patrimoine_portfolio_v60.py` | NEW — 16 tests (empty, nominal, filters, multi-org) |
| `frontend/src/pages/__tests__/patrimoineV60.test.js` | NEW — 30 source guards |

---

## Checklist E2E (HELIOS)

1. `/import` → Charger HELIOS
2. `/patrimoine` → bandeau risque global visible (ex: ~43 k€), top 3 sites listés
3. Clic "Voir anomalies" sur un top site → SiteDrawer s'ouvre sur l'onglet Anomalies
4. Reset org → `/patrimoine` affiche bandeau "0 €" + CTA "Charger HELIOS", pas de crash
5. Filtre portefeuille → bandeau se recharge avec le scope réduit

---

## Évolutions futures

- **V61** : Ajouter `top_n` dans le composant (exposer le param dans l'UI).
- **V62** : Job nocturne de précalcul pour portfolios > 500 sites.
- **V63** : Drill-down framework → filtre la table de sites par framework réglementaire.
