# Audit chaine Patrimoine → Conformite (OPERAT + BACS)

> Date : 2026-03-16
> Methode : Exploration systematique repo (modeles, services, routes)
> Verdict : **40/100** — La chaine est structurellement presente mais operationnellement fragile

---

# 1. VERDICT EXECUTIF

**Note continuite patrimoine → conformite : 40/100**

**Verdict sans filtre :** Les modeles existent et les FK sont en place, mais la chaine patrimoine → conformite est **passive, non propagee et fragile**. Aucune modification de patrimoine (surface, usage, batiment, archivage) ne se propage automatiquement aux entites OPERAT ou BACS. Un site peut etre archive avec des EFA et BacsAssets qui restent actifs et visibles — des entites orphelines. Il n'y a aucun mecanisme de resynchro, aucun event listener, aucun job de coherence. Le systeme fonctionne tant que l'utilisateur fait tout manuellement dans le bon ordre, mais il se desynchronise silencieusement des qu'un changement patrimoine n'est pas suivi d'une action conformite manuelle.

---

# 2. MATRICE DES LIENS

| Lien attendu | Statut | Preuve repo | Risque |
|---|---|---|---|
| Site → TertiaireEfa (site_id) | PARTIEL | FK nullable, pas de cascade soft-delete | EFA orpheline si site archive |
| Site → BacsAsset (site_id) | KO | FK required mais pas de soft-delete, pas de cascade | BacsAsset visible apres archive site |
| Batiment → TertiaireEfaBuilding | PARTIEL | FK nullable, pas de cascade | Dangling FK si batiment supprime |
| Batiment → BacsAsset (building_id) | PARTIEL | FK nullable, pas de cascade | Dangling FK |
| Site.surface_m2 → EfaBuilding.surface_m2 | KO | Snapshotted a la creation, jamais synchro | Divergence silencieuse |
| Site.type → BACS eligibilite | KO | is_tertiary_non_residential = flag manuel | Desynchronise si usage change |
| Site.type → Tertiaire eligibilite | KO | tertiaire_area_m2 statique | Pas de re-evaluation |
| CVC ajout/modif → BACS assessment | KO | Recompute manuel uniquement | Putile obsolete |
| Batiment ajout → EFA recalcul | KO | Pas de propagation | EFA surface diverge |
| Site archive → EFA archive | KO | Pas de cascade soft-delete | EFA orpheline |
| Site archive → BACS archive | KO | BacsAsset n'a pas SoftDeleteMixin | Toujours visible |
| Quick-create site → EFA auto | KO | Pas d'auto-creation | Manuel uniquement |
| Quick-create site → BACS auto | KO | Pas d'auto-creation | Manuel uniquement |
| EFA supprimee → Consumptions | OK | CASCADE sur FK | Nettoyage correct |
| BacsAsset supprime → Remediation | OK | CASCADE sur FK | Nettoyage correct |

---

# 3. FAILS CRITIQUES

| # | Fail | Gravite | Impact |
|---|------|---------|--------|
| **F1** | **Site archive → EFA + BACS restent actifs** — entites orphelines visibles dans les API et l'UI | **Critique** | Donnees fantomes, evaluations sur site supprime |
| **F2** | **BacsAsset n'a pas SoftDeleteMixin** — impossible de l'archiver proprement | **Critique** | BACS toujours visible meme si site supprime |
| **F3** | **Aucune propagation de surface** — EfaBuilding snapshot a la creation, jamais synchro | **Majeur** | Divergence surface → fausse evaluation OPERAT |
| **F4** | **CVC modifie → BACS non recalcule** — putile obsolete entre 2 recomputes manuels | **Majeur** | Score BACS incorrect |
| **F5** | **Site usage change → eligibilite non re-evaluee** — is_tertiary flag statique | **Majeur** | Site devenu non-tertiaire reste assujetti |
| **F6** | **Batiment supprime → EfaBuilding dangling FK** — pas de cascade ni SET NULL | **Majeur** | Erreur DB potentielle |
| **F7** | **Aucun orphan detection** — le systeme ne detecte jamais les entites desynchronisees | **Majeur** | Accumulation silencieuse d'incoherences |

---

# 4. AUDIT DETAILLE

## 4.1 Creation / import

- Quick-create site cree : Site + Batiment + Obligations + Compliance score
- **NE cree PAS** : TertiaireEfa, BacsAsset — 100% manuel
- Import CSV : idem — pas de creation automatique conformite
- Le Wizard EFA valide que les batiments existent (`not_deleted(Batiment)`) — correct
- Le Wizard EFA snapshot les surfaces a la creation — correct mais non synchro

## 4.2 Modification / propagation

- **PATCH site** : met a jour les champs site, pas de propagation conformite
- **Ajout batiment** : pas de mise a jour EFA
- **Modif CVC** : pas de recalcul BACS automatique
- **Changement usage** : pas de re-evaluation eligibilite
- **Aucun event listener** SQLAlchemy detecte
- **Aucun job background** de resynchro

## 4.3 Archivage / historique

- Site soft-delete : EFA et BacsAsset **non cascades**
- BacsAsset n'a **pas de SoftDeleteMixin** — hard delete seul possible
- Pas de detection d'EFA orpheline apres archive site
- Pas de warning UI si EFA pointe vers site archive

## 4.4 Integrite des relations

- FK TertiaireEfaBuilding.building_id : nullable, pas de ondelete → dangling possible
- FK BacsAsset.site_id : required, pas de ondelete → FK violation si hard delete
- FK BacsAsset.building_id : nullable, pas de ondelete → dangling possible
- CASCADE correct sur : EfaConsumption, RemediationAction (ondelete CASCADE)

## 4.5 UX de tracabilite

- L'utilisateur ne voit PAS si une EFA pointe vers un site archive
- L'utilisateur ne voit PAS si le BACS est calcule sur des donnees obsoletes
- Pas de badge "desynchronise" ou "a recalculer"
- Pas de lien visuel entre patrimoine modifie et conformite impactee

---

# 5. TOP 10 DES CORRECTIONS

| # | Objectif | Fichiers | Effort | Risque si non fait |
|---|----------|----------|--------|-------------------|
| 1 | **Cascader soft-delete site → EFA + BACS** | `patrimoine.py`, `patrimoine_crud.py` | M | Entites orphelines |
| 2 | **Ajouter SoftDeleteMixin a BacsAsset** | `bacs_models.py`, migrations | S | BACS non archivable |
| 3 | **Ajouter ondelete SET NULL sur TertiaireEfaBuilding.building_id** | `tertiaire.py`, migrations | S | Dangling FK |
| 4 | **Recalcul automatique BACS apres modif CVC** | `routes/bacs.py` | S | Putile obsolete |
| 5 | **Propagation surface site → EfaBuilding** | `routes/patrimoine.py` | M | Surface diverge |
| 6 | **Detection orphelins (EFA sans site actif)** | Nouveau service | M | Incoherences cachees |
| 7 | **Re-evaluation eligibilite si usage/type change** | `routes/patrimoine.py` | M | Eligibilite statique |
| 8 | **Badge "a recalculer" dans UI conformite** | Front | S | Pas de visibilite |
| 9 | **Auto-creation EFA/BACS a la provision site si eligible** | `onboarding_service.py` | L | Creation manuelle seule |
| 10 | **Job coherence periodique patrimoine ↔ conformite** | Nouveau service | L | Accumulation drift |

---

# 6. PLAN D'EXECUTION

## Quick wins (effort S, impact immediat)

1. Ajouter SoftDeleteMixin a BacsAsset + migration
2. Recalcul BACS auto apres ajout/modif/suppression CVC
3. ondelete SET NULL sur TertiaireEfaBuilding.building_id

## Chantiers structurants (effort M)

4. Cascader soft-delete site → archiver EFA + BACS lies
5. Propagation surface site → EfaBuilding
6. Detection orphelins (service + alerte)
7. Re-evaluation eligibilite si usage change

## Criteres de done

- Aucune EFA orpheline apres archive site
- Aucun BacsAsset visible apres archive site
- CVC modifie → putile recalcule automatiquement
- Surface site modifiee → EfaBuilding mise a jour
- Tests de non-regression sur tous les cas
