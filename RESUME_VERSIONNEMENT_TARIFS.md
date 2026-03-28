# Résumé — Versionnement temporel des tarifs réglementaires

**Branche** : `feat/market-price-decomposition` → mergée dans `main` (fast-forward)
**Commit** : `768f59d` — `feat(tarifs): versionnement temporel multi-période des tarifs réglementaires`
**Date** : 2026-03-27

---

## Objectif

Chaque tarif réglementaire évolue chaque année. Le système doit appliquer **le bon tarif à la bonne période** : un calcul sur janvier 2024 doit utiliser les taux 2024, pas ceux de 2026.

---

## Fichiers modifiés (5 fichiers, +378 / -104 lignes)

### 1. `backend/referentials/market_tariffs_2026.yaml`
Restructuration complète en **multi-version avec plages temporelles** :

| Composante | Versions |
|---|---|
| **TURPE** | TURPE 6 (2021-08 → 2025-07) + TURPE 7 (2025-08+) |
| **CSPE / Accises** | 2024, 2025, 2026 (taux distincts) |
| **Capacité** | 2025, 2026 |
| **CEE** | P5 (2022-2025), P6 (2026-2030) |
| **CTA** | 21.93% (2021-2025), 27.04% (2026+) |

→ **38 tarifs** au total avec `valid_from` / `valid_to` sur chaque entrée.

### 2. `backend/services/market_tariff_loader.py`
- Fonction `_map_tariff_type()` enrichie pour gérer les suffixes de version (`turpe_v6`, `turpe_v7`, `cspe_2024`, `cspe_2025`, `cspe_2026`, etc.)
- Résolution automatique de la version applicable selon la date demandée

### 3. `backend/services/price_decomposition_service.py`
- `period_start` propagé comme paramètre `at_date` dans tous les appels `self._tariff()`
- Chaque brique de prix (TURPE, CSPE, CTA, CEE, capacité) utilise désormais le tarif valide à la date du calcul

### 4. `backend/tests/test_market_tariff_loader.py`
- Adaptation des tests existants au nouveau format versionné

### 5. `backend/tests/test_price_decomposition.py`
- **5 nouveaux tests de bascule temporelle** ajoutés :
  - TURPE 6 vs TURPE 7 (bascule août 2025)
  - CSPE 2024 < 2025 < 2026
  - CTA 21.93% → 27.04% (janvier 2026)
  - CEE P5 → P6 (janvier 2026)
  - TTC rétroactif 2024 < TTC 2026

---

## Résultats tests

```
39 passed in 11.58s ✓
```

Aucune régression. Les 5 tests de versionnement temporel valident les bascules de période.

---

## Impact métier

- **Shadow billing** : les factures reconstituées sur des périodes passées utilisent désormais les taux historiques corrects
- **Décomposition prix** : un calcul au 01/01/2024 vs 01/01/2026 donne des résultats différents (CSPE, CTA, CEE, TURPE)
- **Rétro-compatibilité** : les appels sans `period_start` utilisent par défaut la période courante (comportement inchangé)
- **Extensibilité** : ajouter un nouveau millésime = ajouter une entrée YAML avec `valid_from`/`valid_to`
