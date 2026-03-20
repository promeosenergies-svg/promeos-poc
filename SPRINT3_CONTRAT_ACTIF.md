# Sprint 3 Step 1 — Contrat sans end_date considere comme actif

> Date : 2026-03-15
> Commit : `39b1171`
> Statut : Implemente, teste, committe

---

## Probleme

Un contrat energie sans date de fin (`end_date = NULL`) n'etait pas considere comme actif.
En B2B France, un contrat sans echeance = contrat en cours (tacite reconduction).

Consequence : la ligne `contrat_actif` de la completude restait rouge meme apres ajout d'un contrat sans date de fin.

---

## Regle cible

Un contrat est **actif** si :
- `start_date` est NULL ou <= aujourd'hui
- ET `end_date` est NULL ou >= aujourd'hui

Alignee sur `reconciliation_service.py:134` (deja correct).

---

## Corrections

| Fichier | Ligne | Avant | Apres |
|---------|-------|-------|-------|
| `patrimoine.py` | 2557 | `end_date >= today` | `(end_date >= today) \| (end_date IS NULL)` |
| `patrimoine.py` | 1281-1282 | `end_date >= today, start_date <= today` | Idem avec `\| IS NULL` sur les deux |

---

## Endroits verifies et non modifies

| Fichier | Ligne | Usage | Pourquoi pas modifie |
|---------|-------|-------|---------------------|
| `dashboard_2min.py` | 389 | Prochain contrat a expirer | Filtre `end_date IS NOT NULL` volontaire |
| `reconciliation_service.py` | 134 | Contrats actifs reconciliation | Deja correct (`end_date is None or >= today`) |
| `notification_service.py` | 206 | Alertes expiration | Besoin d'une date reelle pour alerter |

---

## Impact

| Element | Avant | Apres |
|---------|-------|-------|
| Completude avec contrat sans end_date | `contrat_actif` = missing | `contrat_actif` = OK |
| KPI nb_contrats_actifs | Excluait les contrats sans date | Les inclut |
| Score completude | 50% (4 manquants) | 62% (3 manquants) |

---

## Tests

| Test | Resultat |
|------|----------|
| 31 tests backend | Passe |
| Smoke API : contrat sans end_date → completude OK | Passe |
| KPI : actifs=11 total=11 (tous actifs) | Passe |

---

## Ce qui reste Sprint 3

| Step | Action | Effort |
|------|--------|--------|
| S3-2 | Refresh cible (3 reload → refreshSites) | S |
| S3-3 | Import simplifie (retirer Assiste + Demo du wizard) | M |
| S3-4 | Validation finale Sprint 3 | S |
