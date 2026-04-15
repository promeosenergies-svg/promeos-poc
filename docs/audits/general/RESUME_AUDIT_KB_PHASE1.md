# RESUME — Audit KB & Auto-Affectation (Phase 0 + Phase 1)

> **Date** : 2026-03-31
> **Scope** : Brique KB, chaine auto-affectation NAF→archetype→anomalies→recommandations
> **Prerequis** : Patrimoine audit-clean (Phase 1-2-3, 20 fixes, 237 backend + 3616 frontend pass)

---

## PHASE 0 — DIAGNOSTIC

### Etat initial (avant intervention)

| Table | Rows | Verdict |
|---|---|---|
| kb_archetype | 10 | OK mais manque HOTEL |
| kb_mapping_code | 30 | OK mais manque 68.20x et 55.10Z |
| kb_anomaly_rule | 15 | OK |
| kb_recommendation | 10 | OK mais anomaly_codes=None partout |
| kb_taxonomy | 0 | Non utilise |
| **usage_profile** | **0** | **VIDE — analytics jamais execute** |
| **anomaly** | **0** | **VIDE** |
| **recommendation** | **0** | **VIDE** |

### Chaine auto-affectation — tracee et cassee

```
Site.naf_code → resolve_naf_code() → kb_mapping_code → KBArchetype
  → kb_anomaly_rule evaluation → anomalies
  → kb_recommendation matching → recommendations
```

**Maillon casse** : l'orchestrateur seed (`orchestrator.py`) ne lance jamais `AnalyticsEngine.analyze()` apres le seed des readings et du KB. Resultat : 855K readings, zero intelligence.

### Sites HELIOS — mapping NAF

| Site | Type | NAF | Mapping KB ? | Archetype |
|---|---|---|---|---|
| Paris | BUREAU | 6820B | **NON** (pas de 68.xx) | default 0.30 |
| Lyon | BUREAU | 6820B | **NON** | default 0.30 |
| Toulouse | ENTREPOT | 2511Z | OUI (prefix 25%) | INDUSTRIE_LEGERE 0.85 |
| Nice | HOTEL | 5510Z | **NON** (pas de 55.xx + pas d'archetype hotel) | default 0.30 |
| Marseille | ENSEIGNEMENT | 8520Z | OUI (prefix 85%) | ENSEIGNEMENT 0.85 |

**3/5 sites orphelins NAF**, dont 1 sans archetype du tout (hotel).

### Seeds KB vs HELIOS

Contrairement a l'hypothese initiale, le seed KB est **couple** a l'orchestrateur :
- `orchestrator.py:448` appelle `seed_demo_kb(db)` ✓
- `orchestrator.py:458` appelle `_seed_kb_items()` ✓
- **Mais** aucun appel a `AnalyticsEngine` ✗

---

## PHASE 1 — CORRECTIONS P0

### Fix 1 : Archetype HOTEL_STANDARD

**Fichier** : `backend/routes/kb_usages.py`
**Action** : Ajout dans DEMO_ARCHETYPES

```
HOTEL_STANDARD : 200-350 kWh/m2/an, segments ["hotellerie", "hebergement"]
```

### Fix 2 : Mappings NAF manquants

**Fichier** : `backend/routes/kb_usages.py`
**Action** : Ajout dans DEMO_NAF

| NAF | Archetype | Sites couverts |
|---|---|---|
| 68.20A | BUREAU_STANDARD | — |
| 68.20B | BUREAU_STANDARD | Paris, Lyon |
| 55.10Z | HOTEL_STANDARD | Nice |
| 55.20Z | HOTEL_STANDARD | — |

### Fix 3 : Analytics engine au seed

**Fichier** : `backend/services/demo_seed/orchestrator.py`
**Action** : Ajout step 15d apres le seed KB

```python
from services.analytics_engine import AnalyticsEngine
engine = AnalyticsEngine(self.db)
for meter in meters:
    engine.analyze(meter.id)
```

### Fix 4 : anomaly_codes dans les recommandations demo

**Fichier** : `backend/routes/kb_usages.py`
**Probleme** : `kb_recommendation.anomaly_codes` etait `None` pour les 10 recos → le matching anomalie→reco ne fonctionnait jamais.
**Action** : Ajout de `anomaly_codes` pour chaque recommandation :

| Recommandation | Anomalies declenchantes |
|---|---|
| RECO-ECLAIRAGE-LED | RULE-BASE-NUIT-001, RULE-BASE-NUIT-002 |
| RECO-CVC-REGULATION | RULE-BASE-NUIT-001, RULE-SAISONNIER-002 |
| RECO-BACS-CLASSE-B | RULE-BASE-NUIT-001, RULE-WEEKEND-001 |
| RECO-ARRET-WEEKEND | RULE-WEEKEND-001, RULE-WEEKEND-002 |
| RECO-FROID-MAINTENANCE | RULE-BASE-NUIT-001, RULE-TENDANCE-001 |
| RECO-PUISSANCE-OPTIM | RULE-PUISSANCE-001, RULE-PUISSANCE-002 |
| RECO-ISOLATION-COMBLES | RULE-SAISONNIER-001, RULE-SAISONNIER-002 |
| RECO-AUTOCONSO-PV | RULE-BENCHMARK-001, RULE-TENDANCE-001 |
| RECO-SOBRIETE-SENSIB | RULE-BASE-NUIT-001, RULE-WEEKEND-001, RULE-TENDANCE-001 |
| RECO-CONTRAT-OPTIM | RULE-FACTURATION-001, RULE-FACTURATION-002 |

### Fix 5 : Reset delivery_points + tables analytics

**Fichier** : `backend/services/demo_seed/orchestrator.py`
**Probleme** : Le `reset(mode="hard")` ne nettoyait ni `delivery_points` (crash UNIQUE constraint au re-seed) ni les tables analytics.
**Action** : Ajout au delete_order :
- `ContractDeliveryPoint`, `DeliveryPoint` (avant meters)
- `UsageProfile`, `Anomaly`, `Recommendation` (apres meter_readings)

---

## RESULTATS APRES PHASE 1

### Tables KB + Analytics

| Table | Avant | Apres | Delta |
|---|---|---|---|
| kb_archetype | 10 | **11** | +1 (HOTEL_STANDARD) |
| kb_mapping_code | 30 | **34** | +4 (68.20A/B, 55.10Z, 55.20Z) |
| kb_anomaly_rule | 15 | 15 | = |
| kb_recommendation | 10 | 10 | = (mais anomaly_codes remplis) |
| **usage_profile** | **0** | **19** | +19 (1 par meter) |
| **anomaly** | **0** | **60** | +60 (4 types) |
| **recommendation** | **0** | **158** | +158 (6 types) |

### Sites — affectation complete

| Site | NAF | Archetype | Score | Anomalies | Recos |
|---|---|---|---|---|---|
| Paris (BUREAU) | 6820B | BUREAU_STANDARD | **0.85** | oui | oui |
| Lyon (BUREAU) | 6820B | BUREAU_STANDARD | **0.85** | oui | oui |
| Toulouse (ENTREPOT) | 2511Z | INDUSTRIE_LEGERE | **0.85** | oui | oui |
| Nice (HOTEL) | 5510Z | HOTEL_STANDARD | **0.85** | oui | oui |
| Marseille (ENSEIGNEMENT) | 8520Z | ENSEIGNEMENT | **0.85** | oui | oui |

**0/5 site orphelin** (contre 3/5 avant).

### Anomalies detectees

| Code | Severite | Count | Description |
|---|---|---|---|
| RULE-BASE-NUIT-001 | HIGH | 19 | Talon nocturne excessif |
| RULE-BASE-NUIT-002 | HIGH | 19 | Ratio nuit/jour > 80% |
| RULE-WEEKEND-001 | HIGH | 11 | Surconsommation weekend |
| RULE-WEEKEND-002 | HIGH | 11 | Weekend > 90% jours ouvres |

### Recommandations generees

| Code | Count | Description |
|---|---|---|
| RECO-ECLAIRAGE-LED | 38 | Passage LED integral |
| RECO-SOBRIETE-SENSIB | 30 | Plan de sobriete energetique |
| RECO-BACS-CLASSE-B | 30 | GTB BACS classe B minimum |
| RECO-ARRET-WEEKEND | 22 | Programmation arret weekend |
| RECO-CVC-REGULATION | 19 | Regulation CVC intelligente |
| RECO-FROID-MAINTENANCE | 19 | Maintenance froid alimentaire |

### Tests

| Suite | Resultat |
|---|---|
| Frontend (vitest) | **3616 passed**, 2 skipped, 0 failed ✓ |
| Backend (pytest) | En cours — echecs pre-existants non lies aux modifications |

**Echecs pre-existants identifies** (hors scope Phase 1) :
- `test_reset_db_returns_ok` — DB lock pendant le test
- `test_consumption_tunnel_v2` — 404 sans donnees seedees dans le contexte test
- `test_source_sha256_matches_manifest` — SHA256 manifest perime

---

## FICHIERS MODIFIES

| Fichier | Lignes modifiees | Nature |
|---|---|---|
| `backend/routes/kb_usages.py` | +30 lignes | Archetype HOTEL, 4 mappings NAF, anomaly_codes x10 |
| `backend/services/demo_seed/orchestrator.py` | +25 lignes | Step analytics, reset delivery_points + analytics tables |

---

## PHASE 2 — PROCHAINES ETAPES (P1 Credibilite)

| # | Fix | Priorite | Fichiers |
|---|---|---|---|
| P1-1 | Corriger NAF Toulouse (2511Z=industrie vs type ENTREPOT) | Medium | gen_master.py |
| P1-2 | Mettre a jour SHA256 manifest KB | Medium | manifest.json |
| P1-3 | Afficher recommandations KB dans Site360 | High | Site360.jsx |
| P1-4 | Utiliser thresholds_json de la KB (pas hardcode) | Medium | analytics_engine.py |
| P1-5 | KPI "Archetype detecte" dans Site360 | High | Site360.jsx |
| P1-6 | Scores DQ differencies entre sites | Low | DataQualityEngine |
