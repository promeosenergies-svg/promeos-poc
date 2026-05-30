# Sprint Énergie P2.3 — Migration MarketPrice legacy (rapport)

**Date** : 2026-05-30
**Sprint** : P2.3 — Migration progressive `MarketPrice` legacy vers `MktPrice` canonique
**Branche** : `claude/energie-p2-3-market-price-legacy` depuis `b1732c32`
**Périmètre** : backend uniquement (aucune modification FE ni UI)

## 1. Usages `MarketPrice` audités

Grep complet `rg "MarketPrice" backend/` + `rg "from models.market_price"` :

| Fichier | Ligne(s) | Type d'usage | Action P2.3 |
|---|---|---|---|
| `backend/models/market_price.py` | 16 | définition classe legacy | **DEPRECATED renforcé** |
| `backend/models/__init__.py` | 296, 607 | import + export `__all__` | **DEPRECATED renforcé + noqa: F401** |
| `backend/tests/test_step17_market_prices.py` | 25, 30, 32, 69 | tests legacy explicites | conservé (whitelist) |
| `backend/tests/source_guards/test_market_price_canonical_source_guards.py` | 7, 14, 23, 39, 64, 67, 68, 73 | source-guard lui-même | conservé (whitelist) |
| `backend/tests/api/test_energy_market_exposure_endpoint.py` | 511, 518, 527, 529 | test API asserte ABSENCE | conservé |
| `backend/services/billing_service.py` | 176 | commentaire docstring obsolète | **mis à jour vers MktPrice** |
| `backend/services/energy_orchestration/market_exposure.py` | 643 | commentaire dans warning | conservé (commentaire informatif) |

## 2. Usages migrés (P2.3)

| Fichier | Avant | Après |
|---|---|---|
| `backend/services/billing_service.py:176` | « 2. MarketPrice moyenne 30 jours (EPEX Spot FR) » | « 2. MktPrice moyenne 30 jours (EPEX Spot FR — table canonique 'mkt_prices' depuis Sprint Énergie P1.S2d ; remplace l'ancien MarketPrice legacy marqué DEPRECATED P2.3) » |
| `backend/models/market_price.py` (docstring) | mention DEPRECATED minimale + 6 lignes | doctrine 40+ lignes encadrée : interdits, autorisés (whitelist), cible suppression, migration de référence vers `MktPrice` |
| `backend/models/__init__.py:294-296` | 3 lignes commentaire + import | 7 lignes commentaire + `noqa: F401` (import compat ORM table legacy) |
| `backend/models/market_price.py` (classe) | docstring 1 ligne | docstring renforcée + référence vers doctrine in-file |

**Aucun usage applicatif `MarketPrice` n'a été détecté hors whitelist** — la migration applicative `MktPrice` est complète depuis P1.S2d (cf. `services/energy_orchestration/market_exposure.py` qui utilise déjà `from models.market_models import MktPrice`).

## 3. Usages legacy conservés

| Fichier | Justification |
|---|---|
| `backend/models/market_price.py` | Modèle DEPRECATED conservé pour préservation data (table `market_prices` non droppée — cf. brief P2.3 « Ne pas dropper »). |
| `backend/models/__init__.py` | Import compat ORM nécessaire pour que SQLAlchemy reconnaisse la table legacy en DB. Marqué `noqa: F401` (jamais utilisé directement). |
| `backend/tests/test_step17_market_prices.py` | Tests legacy explicites Step 17 — préservation data testée. |
| `backend/tests/source_guards/test_market_price_canonical_source_guards.py` | Source-guard lui-même — référence le nom interdit pour le détecter. |
| `backend/services/demo_seed/gen_market_prices.py` | Seed démo legacy. À migrer vers `mkt_prices` avant DROP TABLE (cible P2.x ultérieur). |

## 4. Whitelist finale

`LEGACY_MARKET_PRICE_WHITELIST` (dans `test_market_price_canonical_source_guards.py`) — **3 entrées documentées** :

1. `backend/models/market_price.py` — modèle lui-même (DEPRECATED docstring)
2. `backend/tests/source_guards/test_market_price_canonical_source_guards.py` — source-guard lui-même
3. `backend/services/demo_seed/gen_market_prices.py` — seed démo legacy (à migrer ultérieurement)

## 5. Source-guard renforcé

Nouvelle classe `TestMarketPriceCanonicalP2_3` ajoute **6 tests** :

- `test_energy_orchestration_no_market_price_import` — aucun import dans `services/energy_orchestration/*`
- `test_billing_service_no_market_price_import` — `billing_service.py` n'importe pas `MarketPrice`
- `test_market_data_service_uses_canonical_if_exists` — `market_data_service.py` (si existe) utilise `MktPrice`
- `test_legacy_model_has_p2_3_deprecation_marker` — modèle legacy porte le marqueur Sprint P2.3 + référence source-guard
- `test_models_init_marks_legacy_import_as_compat` — `models/__init__.py` documente l'import legacy comme compat-only
- `test_p2_3_doc_references_canonical_fields` — la doctrine in-file cite ≥ 3 champs canoniques (`market_type`, `zone`, `delivery_start`, `price_eur_mwh`)

## 6. Tests verts

| Suite | Résultat |
|---|---|
| `pytest tests/source_guards/ -k "market_price or energy_orchestration or frontend_no_business or cdc_timezone"` | **58/58 ✅** (+6 vs P2.2 : tests `TestMarketPriceCanonicalP2_3`) |
| `pytest tests/api/test_energy_market_exposure_endpoint.py` | **27/27 ✅** (aucune régression endpoint Marché & exposition) |

Détails endpoint `/api/energy/market-exposure` :
- ✅ HTTP 200 sur site valide
- ✅ Coût spot théorique calculé (€)
- ✅ Prix spot pondéré sans division par zéro
- ✅ Écart vs baseload disponible
- ✅ Top heures chères triées
- ✅ Prix négatifs détectés
- ✅ Score exposition borné [0,100]
- ✅ Provenance complète par KPI

## 7. Risques restants

| Risque | Sévérité | Mitigation |
|---|---|---|
| Données orphelines dans `market_prices` qui ne sont pas dans `mkt_prices` | Faible | Avant DROP TABLE Alembic (P2.x ultérieur) : script de migration data `market_prices` → `mkt_prices` avec validation. |
| Seed démo `gen_market_prices.py` peuple encore la table legacy | Moyenne | Migrer le seed vers `mkt_prices` en même temps que DROP TABLE. Whitelist temporaire documentée. |
| Import compat ORM dans `models/__init__.py` reste obligatoire | Faible | Tant que la table existe, SQLAlchemy a besoin du modèle pour son metadata. Disparaîtra avec le DROP. |
| Test `test_step17_market_prices.py` continuera à valider le modèle legacy | Faible | À supprimer après DROP TABLE. Validation préservation data utile en attendant. |

## 8. Recommandation pour suppression future

**Cible P2.x ultérieur (post-P2.5)** : DROP TABLE `market_prices` + suppression complète du modèle.

**Critères préalables** (à valider AVANT DROP) :

1. **Audit data orpheline** : `SELECT count(*) FROM market_prices WHERE NOT EXISTS (SELECT 1 FROM mkt_prices WHERE ...)` — résultat doit être 0 OU plan de migration data documenté.
2. **Backup triple-artefact** : binaire DB + dump SQL + JSON export (cf. ADR Cutover Mois 4 — Q2-α : backup hors Git non négociable).
3. **Source-guard 0 violation pendant 2 sprints consécutifs** : la whitelist a été réduite à 0 (seed migré).
4. **Migration Alembic** : `DROP TABLE market_prices` avec `--no-rollback` désactivé (revert possible 24h).
5. **Tests legacy supprimés** : `test_step17_market_prices.py` retiré dans le même commit.

**Bénéfices attendus** :
- Réduction surface de code legacy (~50 LoC modèle + ~30 LoC test)
- HELPER_WHITELIST source-guard à 2 entrées (modèle + source-guard) au lieu de 3
- Doctrine « source de vérité unique » 100 % effective

## 9. Verdict

🟢 **P2.3 COMPLET** :

- ✅ Modèle legacy marqué DEPRECATED P2.3 renforcé (doctrine 40+ lignes)
- ✅ `models/__init__.py` import compat ORM documenté (noqa: F401)
- ✅ `billing_service.py` commentaire docstring corrigé (MarketPrice → MktPrice)
- ✅ Source-guard renforcé (+6 tests P2.3, 58/58 total verts)
- ✅ Tests API endpoint Marché & exposition 27/27 verts (aucune régression)
- ✅ Whitelist documentée 3 entrées, dont 1 à migrer (seed démo)
- ✅ Aucun usage applicatif `MarketPrice` détecté hors whitelist

**Migration data** non couverte par P2.3 (préservation table legacy conservée selon brief). Cible P2.x ultérieur post-validation critères §8.

---

Rapport généré le 2026-05-30 dans le cadre du sprint P2.3.
