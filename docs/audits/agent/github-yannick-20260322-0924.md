# Rapport Agent GitHub — Surveillance Yannick
**Date** : 2026-03-22 09:24
**Branche locale** : `main`
**Remote** : `origin` → `https://github.com/promeosenergies-svg/promeos-poc.git`

---

## ALERTE NOUVEAUTÉ YANNICK : OUI

### Commits détectés (1)

| SHA | Auteur | Sujet |
|-----|--------|-------|
| `00f9951` | Akuesson et Soumah De Brito Avila <yannick.avila@endesa.fr> | Specs ingestion flux Enedis V1 |

### Catégorisation des changements

| Catégorie | Fichiers | Impact |
|-----------|----------|--------|
| **Backend / Config** | `patrimoine_assumptions.py` (supprimé contenu), `enums.py` (modifié), `patrimoine.py` (vidé), `tou_schedule.py` (modifié) | Suppressions massives de modèles et config |
| **Backend / Routes** | `cockpit.py` (vidé — 69 lignes supprimées) | Route cockpit supprimée |
| **Backend / Services** | `billing_engine/catalog.py` (-658 +93), `billing_engine/engine.py` (-206 +7) | Réécriture majeure du moteur billing |
| **Backend / Services** | `co2_service.py` (SUPPRIMÉ), `dt_trajectory_service.py` (SUPPRIMÉ) | Services entiers supprimés |
| **Backend / Tests** | `test_co2_service.py` (SUPPRIMÉ), `test_shadow_billing_gas.py` (SUPPRIMÉ) | Tests supprimés |
| **Docs / Specs** | `feature-enedis-sge-raw-ingestion.md` (AJOUTÉ, 155 lignes) | Nouvelle spec ingestion flux Enedis SGE |

### Bilan chiffré
- **12 fichiers** touchés
- **263 insertions** / **1 719 suppressions** (net : -1 456 lignes)
- **2 services supprimés** : co2_service, dt_trajectory_service
- **2 tests supprimés** : test_co2_service, test_shadow_billing_gas
- **1 route vidée** : cockpit.py
- **1 spec ajoutée** : ingestion flux Enedis

### Niveau de risque : ÉLEVÉ

**Justification :**
1. **Suppressions massives** : 1 719 lignes supprimées, dont des services entiers (CO2, trajectoire DT) et leurs tests associés
2. **Moteur de facturation réécrit** : catalog.py perd 658 lignes (tarifs TURPE 7 détaillés remplacés par version simplifiée), engine.py perd 206 lignes
3. **Route cockpit vidée** : endpoint cockpit supprimé (69 lignes)
4. **Tests supprimés sans remplacement** : 2 fichiers de tests supprimés — régression de couverture
5. **Conflit local** : `backend/models/enums.py` est modifié à la fois localement et dans le commit distant

---

## FAITS

1. 1 commit Yannick détecté sur origin/main (00f9951, 2026-03-22)
2. Commit principalement destructif : suppression de services, tests, routes, simplification billing
3. Ajout d'une spec d'ingestion Enedis SGE (nouvelle feature production)
4. 12 fichiers modifiés localement (travail BACS en cours, non commité)
5. 1 fichier en conflit : `backend/models/enums.py` (modifié des deux côtés)

## RISQUES

1. **Conflit de merge** sur `enums.py` — résolution manuelle nécessaire
2. **Régression fonctionnelle** — services CO2 et trajectoire DT supprimés, cockpit vidé
3. **Couverture tests** en baisse — 267 lignes de tests supprimées
4. **Billing engine** profondément modifié — tarifs TURPE 7 simplifiés, impact facturation
5. **Travail local non sauvegardé** pourrait être perdu si mal géré

## ACTIONS EFFECTUÉES

- [x] Fetch origin avec prune
- [x] Détection et analyse du commit Yannick
- [x] Identification du conflit potentiel sur enums.py
- [x] Génération du rapport
- [ ] ~~Backup~~ — BLOQUÉ (changements non commités)
- [ ] ~~Synchro git pull --ff-only~~ — BLOQUÉ (changements non commités + conflit)

## PROCHAINES ACTIONS RECOMMANDÉES

1. **Commiter ou stasher le travail local BACS** avant toute synchro :
   ```bash
   git stash push -m "WIP-bacs-regulatory-$(date +%Y%m%d)"
   ```
2. **Créer le backup** puis synchroniser :
   ```bash
   git branch backup/main-before-sync-$(date +%Y%m%d-%H%M%S)
   git pull --ff-only origin main
   ```
3. **Restaurer le travail local** :
   ```bash
   git stash pop
   ```
4. **Résoudre le conflit** sur `backend/models/enums.py` manuellement
5. **Vérifier la régression** : lancer `python -m pytest tests/ -v` pour mesurer l'impact des suppressions
6. **Examiner la spec Enedis** (`docs/specs/feature-enedis-sge-raw-ingestion.md`) pour comprendre la direction technique
7. **Discuter avec Yannick** des suppressions massives (CO2, trajectoire DT, cockpit) — intentionnelles ou nettoyage de branche ?
