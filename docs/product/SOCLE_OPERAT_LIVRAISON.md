# Socle OPERAT — Livraison

> Date : 2026-03-16
> Commit : `7b604bd`
> Statut : Implemente, teste, pushe

---

## Fichiers crees

| Fichier | Role |
|---------|------|
| `backend/services/operat_trajectory.py` | Service trajectoire (declare, validate, history, helpers) |
| `backend/tests/test_operat_trajectory.py` | 16 tests unitaires |

## Fichiers modifies

| Fichier | Modification |
|---------|-------------|
| `backend/models/tertiaire.py` | +TertiaireEfaConsumption, +4 champs trajectoire sur TertiaireEfa |
| `backend/models/__init__.py` | Export TertiaireEfaConsumption |
| `backend/database/migrations.py` | Migration table + colonnes (idempotente) |
| `backend/routes/tertiaire.py` | +3 endpoints (declare, validate, history) |
| `backend/services/operat_export_service.py` | Refactoring source conso (EfaConsumption prioritaire, objectifs sur baseline) |

---

## Nouveau modele

### TertiaireEfaConsumption

```
id, efa_id, year, kwh_total, kwh_elec, kwh_gaz, kwh_reseau,
is_reference, is_normalized, source, created_at, updated_at
UNIQUE(efa_id, year)
```

### Champs ajoutes sur TertiaireEfa

```
reference_year, reference_year_kwh, trajectory_status, trajectory_last_calculated_at
```

---

## Regles metier

| Regle | Implementation |
|-------|---------------|
| Objectif 2030 = baseline * 0.60 (-40%) | `operat_trajectory.py:TARGETS` |
| Objectif 2040 = baseline * 0.50 (-50%) | idem |
| Objectif 2050 = baseline * 0.40 (-60%) | idem |
| 1 seule annee reference par EFA | `declare_consumption()` : check + raise ValueError |
| kwh_total >= 0 | Validation dans `declare_consumption()` |
| Annee 2000-2060 | Validation dans `declare_consumption()` |
| Statut on_track si conso <= objectif | `validate_trajectory()` |
| Statut off_track si conso > objectif | idem |
| Statut not_evaluable si baseline ou courant absent | idem |
| Warning "non normalise" si is_normalized=False | idem |
| Export utilise baseline pour objectifs (pas conso courante) | `operat_export_service.py` refactore |

---

## Endpoints

| Methode | Path | Role |
|---------|------|------|
| POST | `/api/tertiaire/efa/{id}/consumption/declare` | Declarer conso annuelle |
| GET | `/api/tertiaire/efa/{id}/targets/validate?year=2025` | Calcul trajectoire |
| GET | `/api/tertiaire/efa/{id}/consumption` | Historique consommations |

---

## Tests (16 passes)

| Test | Verifie |
|------|---------|
| declare_reference_year | Conso reference + cache EFA |
| declare_current_year | Conso courante |
| refuse_two_reference_years | Unicite reference |
| update_same_year | Upsert |
| refuse_negative_kwh | Validation |
| refuse_invalid_year | Validation |
| not_evaluable_without_baseline | Garde-fou |
| not_evaluable_without_current | Garde-fou |
| on_track | Trajectoire atteinte |
| off_track | Trajectoire non atteinte |
| targets_2030_2040_2050 | Calcul objectifs |
| applicable_target_year_2045 | Objectif applicable |
| warning_non_normalized | Avertissement |
| baseline_kwh_none_if_absent | Helper |
| baseline_kwh_returns_value | Helper |
| history_ordered_by_year | Historique |

---

## Refactoring export

| Avant | Apres |
|-------|-------|
| Objectifs calcules sur `total_kwh` (conso courante) | Objectifs calcules sur `baseline_kwh` (reference) |
| Source conso : factures → Site.annual_kwh_total | Source : EfaConsumption → factures → Site (fallback) |
| Pas de distinction reference/courante | `reference_year_kwh` utilise si disponible |

---

## Limites restantes

| Limite | Impact | Sprint suivant |
|--------|--------|---------------|
| Pas de normalisation climatique | Comparaisons biaisees par meteo | Sprint conformite 2 |
| Pas d'UI trajectoire | Donnees non visibles dans le frontend | Patch UI rapide |
| Pas d'audit-trail conso | Modifications non tracees | Sprint conformite 2 |
| Objectifs hardcodes (0.60/0.50/0.40) | Non configurable si regle change | Futur |
| Pas de depot OPERAT reel | Simulation uniquement | Futur |
