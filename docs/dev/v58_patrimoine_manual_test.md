# V58 Patrimoine — Checklist de test manuel

**Version** : V58
**Date** : 2026-02-23

---

## Prérequis

- Backend démarré : `uvicorn main:app --reload`
- Demo HELIOS chargée : `POST /api/demo/seed` (ou via UI)
- Frontend démarré : `npm run dev`

---

## 1. Endpoint Snapshot

### 1.1 Happy-path

```bash
curl -s http://localhost:8000/api/patrimoine/sites/1/snapshot \
  -H "X-Org-Id: 1" | python -m json.tool
```

**Attendu** :
- [ ] HTTP 200
- [ ] `site_id` présent
- [ ] `surface_sot_m2` = somme des `batiments[].surface_m2` (si bâtiments)
- [ ] `surface_site_m2` = valeur de `Site.surface_m2`
- [ ] `nb_batiments` correct
- [ ] `nb_compteurs` = compteurs actifs et non soft-deleted
- [ ] `nb_delivery_points` correct
- [ ] `nb_contracts` correct
- [ ] `computed_at` présent et format ISO 8601

### 1.2 Surface SoT sans bâtiments

Trouver un site sans bâtiment ou en créer un :
```bash
curl -s http://localhost:8000/api/patrimoine/sites/{ID_SANS_BAT}/snapshot \
  -H "X-Org-Id: 1"
```

**Attendu** :
- [ ] `nb_batiments` = 0
- [ ] `surface_sot_m2` = valeur de `Site.surface_m2` (fallback D1)

### 1.3 Scoping org (cross-org → 403)

```bash
curl -s http://localhost:8000/api/patrimoine/sites/1/snapshot \
  -H "X-Org-Id: 999"
```

**Attendu** :
- [ ] HTTP 403

### 1.4 Site inexistant → 404

```bash
curl -s http://localhost:8000/api/patrimoine/sites/99999/snapshot \
  -H "X-Org-Id: 1"
```

**Attendu** :
- [ ] HTTP 403 ou 404

---

## 2. Endpoint Anomalies site

### 2.1 Site complet → score 100

Sur le site HELIOS Siège (ou un site créé manuellement avec bâtiment + usage + compteur avec DP + contrat valide) :

```bash
curl -s http://localhost:8000/api/patrimoine/sites/1/anomalies \
  -H "X-Org-Id: 1"
```

**Attendu** :
- [ ] HTTP 200
- [ ] `completude_score` = 100
- [ ] `nb_anomalies` = 0
- [ ] `anomalies` = []

### 2.2 Site sans surface → SURFACE_MISSING

Mettre `surface_m2` à null via PATCH :
```bash
curl -s -X PATCH http://localhost:8000/api/patrimoine/sites/1 \
  -H "Content-Type: application/json" -H "X-Org-Id: 1" \
  -d '{"surface_m2": null}'
```

Puis :
```bash
curl -s http://localhost:8000/api/patrimoine/sites/1/anomalies -H "X-Org-Id: 1"
```

**Attendu** :
- [ ] `SURFACE_MISSING` dans `anomalies`
- [ ] `severity` = "HIGH"
- [ ] `cta.to` = "/patrimoine"

### 2.3 Chevauchement de contrats → CONTRACT_OVERLAP_SITE

Créer deux contrats ELEC avec dates qui se chevauchent via `POST /api/patrimoine/contracts`.

**Attendu** :
- [ ] `CONTRACT_OVERLAP_SITE` dans `anomalies`
- [ ] `severity` = "HIGH"
- [ ] `evidence.contract_id_1` et `contract_id_2` présents

### 2.4 Ordre de tri CRITICAL → LOW

Site avec plusieurs anomalies de sévérités différentes.

**Attendu** :
- [ ] Anomalies triées CRITICAL > HIGH > MEDIUM > LOW

---

## 3. Endpoint Anomalies org (liste)

### 3.1 Liste basique

```bash
curl -s http://localhost:8000/api/patrimoine/anomalies \
  -H "X-Org-Id: 1"
```

**Attendu** :
- [ ] HTTP 200
- [ ] `total` ≥ nombre de sites actifs
- [ ] `sites` triés par `completude_score` ASC
- [ ] Chaque entrée a `site_id`, `nom`, `completude_score`, `nb_anomalies`

### 3.2 Filtre min_score

```bash
curl -s "http://localhost:8000/api/patrimoine/anomalies?min_score=80" \
  -H "X-Org-Id: 1"
```

**Attendu** :
- [ ] Tous les sites dans `sites` ont `completude_score` ≤ 80

### 3.3 Pagination

```bash
curl -s "http://localhost:8000/api/patrimoine/anomalies?page=1&page_size=2" \
  -H "X-Org-Id: 1"
```

**Attendu** :
- [ ] `sites` contient au plus 2 éléments
- [ ] `page` = 1, `page_size` = 2

---

## 4. Frontend — PatrimoineHealthCard

### 4.1 Onglet Anomalies SiteDrawer

1. Aller sur `/patrimoine`
2. Cliquer sur un site dans le tableau
3. Dans le Drawer, cliquer sur l'onglet "Anomalies"

**Attendu** :
- [ ] PatrimoineHealthCard s'affiche
- [ ] Score de complétude (jauge 0-100) visible
- [ ] Si anomalies : liste avec sévérité, titre, hint, CTA
- [ ] Si score = 100 : message "Patrimoine complet"
- [ ] CTA navigue vers `/patrimoine`

### 4.2 État loading

Simuler une connexion lente (DevTools → Network → Slow 3G).

**Attendu** :
- [ ] Skeleton/spinner affiché pendant le chargement
- [ ] Pas de crash

### 4.3 État error

Couper le backend puis ouvrir le drawer.

**Attendu** :
- [ ] Message d'erreur lisible
- [ ] Bouton "Réessayer" visible et fonctionnel

### 4.4 Org null (pas de contexte)

En mode non-demo, sans authentification.

**Attendu** :
- [ ] Pas de crash React
- [ ] Message d'erreur gracieux OU aucun chargement (siteId null = pas de fetch)

---

## 5. Régression

- [ ] Onglet "Compteurs" du SiteDrawer toujours fonctionnel
- [ ] Onglet "Actions" du SiteDrawer toujours fonctionnel
- [ ] Navigation `/sites/:id` toujours fonctionnelle
- [ ] Export CSV patrimoine toujours fonctionnel
- [ ] Demo HELIOS seed/reset toujours fonctionnel
- [ ] Tests backend : `python -m pytest tests/ --tb=no -q` → 0 failed
- [ ] Tests frontend : `npm test -- --run` → 0 failed

---

## 6. Performance (optionnel)

Pour un org avec 50+ sites :
```bash
time curl -s "http://localhost:8000/api/patrimoine/anomalies?page_size=50" \
  -H "X-Org-Id: 1" > /dev/null
```

**Attendu** : < 2 s (SQLite dev). Si > 2 s → backlog V59 (cache).
