# Bilan Sprint — Shadow Billing TURPE 7 Bridge

**Date** : 28 mars 2026
**Branche** : `fix/billing-shadow-turpe7-bridge`
**Statut** : Complet, prêt à commiter

---

## Contexte

Le shadow billing V2 de PROMEOS recalcule chaque facture énergie pour détecter les écarts (règles R1, R13, R14). Il utilisait des constantes hardcodées obsolètes (TURPE 6, CTA 21.93%, CSPE 2025) au lieu des tarifs versionnés en DB (`regulated_tariffs`, 38 entrées).

## Problèmes identifiés (Phase 0)

| Paramètre | Avant (YAML/hardcodé) | Après (DB/corrigé) | Impact |
|-----------|----------------------|-------------------|--------|
| **CTA élec** | 21.93% | **27.04%** (jan 2026) | +5.11 pts — sous-estimation systématique |
| **CSPE/Accise PME** | 0.02623 EUR/kWh | **0.02658** (fév 2026) | +1.3% |
| **TVA abo/CTA** | 5.5% (réduite) | **20%** (supprimée août 2025) | TVA sous-estimée de ~15% sur abo |
| **TURPE** | Moyenne pondérée YAML fixe | **Composantes DB par plage HP/HC** | Plus précis par segment |
| **Source tarifs** | Non tracée | **`tariff_source` dans chaque retour** | Traçabilité audit |

## Architecture mise en place (Phase 1)

```
Facture → shadow_billing_v2(invoice, lines, contract, db=?)
                │
                ├─ db fourni? → regulated_tariffs (DB versionnée par date)
                │                 └─ TURPE: weighted avg HPH/HCH/HPB/HCB par segment
                │                 └─ CSPE: par catégorie C5/C4/C2
                │                 └─ CTA: 27.04% (versionné)
                │                 └─ TVA: 20% uniforme post-août 2025
                │
                ├─ sinon → tarifs_reglementaires.yaml (YAML référentiel, lru_cache)
                │
                └─ sinon → constantes hardcodées à jour (dernier recours)
```

**Principe** : `db=None` est optionnel — backward-compatible. Les appelants existants qui ont une session DB la passent maintenant.

## Fichiers modifiés

| Fichier | Changement |
|---------|-----------|
| `config/tarifs_reglementaires.yaml` | CTA 21.93→27.04%, CSPE 0.02623→0.02658 |
| `config/tarif_loader.py` | `get_tva_reduite(at_date)` : retourne 0.20 post-août 2025 |
| `services/billing_shadow_v2.py` | Bridge DB, `_resolve_from_db()`, `_resolve_turpe_from_db()`, `_has_db_tariffs()`, `tariff_source` |
| `services/billing_service.py` | `db=db` passé à `shadow_billing_v2` (R1) |
| `routes/billing.py` | `db=db` passé à `shadow_billing_v2` (insights) |
| `services/offer_invoice_reconcile_v1.py` | `db=db` passé à `shadow_billing_v2` |
| `tests/test_shadow_billing_bridge.py` | **18 nouveaux tests** |
| `tests/test_billing_invariants_p0.py` | Adapté aux taux versionnés |
| `tests/test_billing_v68.py` | R13/R14 adaptés aux taux versionnés |

## Tests (Phase 2)

### 18 nouveaux tests (`test_shadow_billing_bridge.py`)

| Suite | Tests | Couverture |
|-------|:-----:|-----------|
| `TestShadowBillingBridge` | 7 | Composantes, source, segment, fallback |
| `TestShadowBillingRealism` | 3 | Réseau >3% HT, taxes >3% HT, TVA ~20% |
| `TestShadowBillingTVA` | 2 | TVA 20% post-août 2025, TVA 5.5% pré-août 2025 |
| `TestShadowBillingFallback` | 1 | Fonctionne sans DB |
| `TestShadowBillingSourceGuards` | 5 | CTA != 21.93%, CSPE != 0.02623, TVA réduite = 0.20 |

### Résultat global

```
147 passed, 0 régressions
(2 tests pré-existants exclus : test_c4_cu_option, test_invalid_status_rejected)
```

## Vérification cohérence (Phase 4)

```
Shadow TURPE C4_BT:    17.20 EUR/MWh (weighted avg DB)
Calcul manuel:         17.21 EUR/MWh (HPH×0.20 + HCH×0.15 + HPB×0.40 + HCB×0.25)
Delta:                 < 0.1% ✓

Shadow CSPE C4:        25.80 EUR/MWh (DB)
DB brute CSPE_C4:      25.79 EUR/MWh
Delta:                 < 0.1% ✓

CTA DB:                27.04% ✓
TVA abo (jan 2026):    20% (uniforme) ✓
TVA abo (jun 2025):    5.5% (réduite) ✓
```

## Definition of Done

| Critère | Statut |
|---------|:------:|
| Bridge actif : shadow_v2 lit `regulated_tariffs` (DB) | **OK** |
| Fallback à jour : CTA=27.04%, CSPE=0.02658, TVA=20% | **OK** |
| Traçabilité : `tariff_source` dans chaque retour | **OK** |
| Versionnement temporel : facture jul 2025 → TURPE 6, sept 2025 → TURPE 7 | **OK** |
| TVA post-août 2025 : 20% uniforme | **OK** |
| Cohérence shadow vs DB brute < 0.1% | **OK** |
| Source guards : anciennes valeurs absentes des fallbacks | **OK** |
| 0 régression sur 147 tests billing | **OK** |
| 18 nouveaux tests bridge | **OK** |

## Limites connues

1. **ATRD/ATRT gaz** : pas encore en `regulated_tariffs` DB (uniquement YAML) — bridge non activé pour le gaz réseau
2. **TICGN** : taux résolu via `billing_engine.catalog`, pas via `regulated_tariffs`
3. **TURPE gestion** (part fixe) : pas encore bridgé vers DB (reste YAML)
4. **Profils HP/HC** : pondérations fixes par segment (C5: 60/40, C4: 20/15/40/25) — à affiner avec les profils CRE réels par site
5. **UX** : `tariff_source` est dans les métriques d'anomalie mais pas affiché en micro-texte dédié dans BillIntelPage
