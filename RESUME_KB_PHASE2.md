# RESUME — KB Phase 2 : Intelligence visible + credibilite demo

> **Date** : 2026-03-31
> **Prerequis** : KB Phase 1 terminee (19 usage_profiles, 60 anomalies, 158 recos)

---

## 5 FIXES APPLIQUES

### Fix 1 — NAF Toulouse corrige
- **Fichier** : `backend/services/demo_seed/packs.py`
- **Avant** : NAF `2511Z` (fabrication structures metalliques) → archetype INDUSTRIE_LEGERE
- **Apres** : NAF `5210B` (entreposage non frigorifique) → archetype LOGISTIQUE_ENTREPOT
- Corrige aussi l'entite juridique "HELIOS Industrie SARL" pour coherence cascade

### Fix 2 — Scores archetype differencies
- **Fichier** : `backend/services/analytics_engine.py`
- **Avant** : Score fixe `0.85` pour tout match NAF
- **Apres** : Score dynamique via `_compute_match_score(features, archetype)` :
  - Base 0.70 + bonus kWh/m2 dans plage (+0.15) + pattern temporel coherent (+0.10) + talon nocturne (+0.05)
  - Clamp [0.40, 0.98]
- **Resultat** : 7 scores distincts (0.55 a 0.95) au lieu de 0.85 uniforme

### Fix 3 — Endpoint GET /api/sites/{id}/intelligence
- **Fichier cree** : `backend/routes/site_intelligence.py`
- **Monte dans** : `backend/routes/__init__.py` + `backend/main.py`
- **Retourne** : archetype detecte, anomalies KB actives, recommandations triees par ICE, resume avec compteurs et economies
- 200 pour chaque site HELIOS, 404 pour site inexistant

### Fix 4 — Frontend Intelligence Panel
- **API wrapper** : `frontend/src/services/api/energy.js` (+`getSiteIntelligence`)
- **Composant cree** : `frontend/src/components/SiteIntelligencePanel.jsx`
  - Badge archetype avec score %
  - 3 KPI cards : anomalies, recommandations, economies potentielles
  - Top 5 anomalies par severite avec deviation %
  - Top 5 recommandations avec ICE score
  - Empty states pour no_meters et pending_analysis
- **Integration** : `frontend/src/pages/Site360.jsx` — ajoute dans TabResume apres la section anomalies

### Fix 5 — Re-seed + verifications + tests
- Re-seed complet avec les 4 fixes
- 9 tests backend (`test_site_intelligence.py`) : endpoint shape, 404, archetype, anomalies fields, recos fields, summary counts, status
- 2 tests frontend (`SiteIntelligencePanel.test.js`) : API call shape, response validation

---

## RESULTATS

### Sites HELIOS — affectation post-Phase 2

| Site | NAF | Archetype | Score |
|---|---|---|---|
| Paris (BUREAU) | 6820B | BUREAU_STANDARD | **0.95** |
| Lyon (BUREAU) | 6820B | BUREAU_STANDARD | **0.95** |
| Toulouse (ENTREPOT) | **5210B** | **LOGISTIQUE_ENTREPOT** | **0.80** |
| Nice (HOTEL) | 5510Z | HOTEL_STANDARD | **0.95** |
| Marseille (ENSEIGNEMENT) | 8520Z | ENSEIGNEMENT | **0.95** |

### Endpoint intelligence — reponses

| Site | Anomalies | Recos | Status |
|---|---|---|---|
| Paris | 12 | 34 | 200 analyzed |
| Lyon | 6 | 18 | 200 analyzed |
| Toulouse | 20 | 50 | 200 analyzed |
| Nice | 20 | 50 | 200 analyzed |
| Marseille | 2 | 6 | 200 analyzed |
| Site 99999 | - | - | 404 |

### Tests

| Suite | Resultat |
|---|---|
| Backend intelligence | **9 passed** |
| Frontend complet | **3618 passed**, 2 skipped, 0 failed |
| Frontend intelligence | **2 passed** |

---

## FICHIERS MODIFIES / CREES

| Fichier | Action | Lignes |
|---|---|---|
| `backend/services/demo_seed/packs.py` | MODIFIER | 2 lignes (NAF Toulouse) |
| `backend/services/analytics_engine.py` | MODIFIER | +35 lignes (_compute_match_score) |
| `backend/routes/site_intelligence.py` | **CREER** | 130 lignes |
| `backend/routes/__init__.py` | MODIFIER | +2 lignes |
| `backend/main.py` | MODIFIER | +2 lignes |
| `backend/tests/test_site_intelligence.py` | **CREER** | 120 lignes, 9 tests |
| `frontend/src/services/api/energy.js` | MODIFIER | +3 lignes |
| `frontend/src/components/SiteIntelligencePanel.jsx` | **CREER** | 160 lignes |
| `frontend/src/pages/Site360.jsx` | MODIFIER | +2 lignes (import + render) |
| `frontend/src/components/__tests__/SiteIntelligencePanel.test.js` | **CREER** | 65 lignes, 2 tests |

---

## CUMUL PHASE 1 + PHASE 2

| Metrique | Avant Phase 1 | Apres Phase 1 | Apres Phase 2 |
|---|---|---|---|
| kb_archetype | 10 | 11 | 11 |
| kb_mapping_code | 30 | 34 | 34 |
| usage_profile | **0** | 19 | 19 (scores differencies) |
| anomaly | **0** | 60 | 60 |
| recommendation | **0** | 158 | 158 |
| Sites orphelins NAF | 3/5 | 0/5 | 0/5 |
| Toulouse archetype | default | INDUSTRIE_LEGERE | **LOGISTIQUE_ENTREPOT** |
| Scores distincts | - | 1 (0.85) | **7** (0.55-0.95) |
| Endpoint intelligence | inexistant | inexistant | **operationnel** |
| UI intelligence | invisible | invisible | **visible dans Site360** |
| Frontend tests | 3616 | 3616 | **3618** (+2) |
| Backend tests intel | 0 | 0 | **9** |
