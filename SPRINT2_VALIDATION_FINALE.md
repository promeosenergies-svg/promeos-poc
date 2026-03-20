# Sprint 2 Patrimoine — Validation finale

> Date : 2026-03-15
> Release : `sprint2-patrimoine`
> Verdict : **READY TO MERGE** — pushe sur origin/main

---

## Commits Sprint 2

```
2e04088  feat(patrimoine): Sprint 2 step 1 — completude cliquable + edit site
253e653  fix(patrimoine): Sprint 2 micro-correctif — section societe B2B
0a72c2e  feat(patrimoine): Sprint 2 — ajout compteur depuis drawer
bf8a15f  feat(patrimoine): Sprint 2 — ajout contrat depuis drawer
```

---

## Tests lances

| Test | Resultat |
|------|----------|
| 31 tests backend (quick-create + soft-delete) | Passe |
| 63 tests frontend (step32_wizard + patrimoineV58) | Passe |
| Build frontend Vite | Passe |
| Smoke test API bout en bout (10 points) | Passe |

---

## Resultats smoke test

| # | Test | Resultat | Detail |
|---|------|----------|--------|
| 1 | Quick-create site | OK | `status=created id=7` |
| 2 | Completude initiale | OK | `50% missing=[delivery_point, contrat, GPS, SIRET]` |
| 3 | Patch societe (nom + SIREN) | OK | `nom=ACME SAS` |
| 4 | Patch site (SIRET + surface) | OK | `updated=[surface_m2, siret]` |
| 5 | Ajout compteur avec PRM | OK | `id=9` — DP auto-cree |
| 6 | Ajout contrat | OK | `id=10 supplier=Engie` |
| 7 | Completude finale | OK | `88%` (bloc masque car >= 80%) |
| 8 | Anti-doublons (Sprint 1) | OK | Doublon case-insensitive detecte |
| 9 | Archive/Restore (soft-delete) | OK | Archive puis restaure |
| 10 | Cockpit visibilite | OK | `total=6 actifs=6` |

---

## Parcours complet valide

```
Quick-create site (50%)
    │
    ├── Completer etablissement (SIRET, SIREN, NAF)
    ├── Renseigner surface (m2)
    ├── Ajouter compteur (PRM/PCE → DP auto)
    ├── Ajouter contrat (fournisseur, dates, PDL)
    └── Localiser (GPS auto via geocoding)
    │
    ▼
Completude >= 80% → bloc masque → site exploitable
```

---

## Composants livres Sprint 2

| Composant | Fichier | Role |
|-----------|---------|------|
| DrawerEditSite | `components/DrawerEditSite.jsx` | Edition societe/SIRET/surface/localisation |
| DrawerAddCompteur | `components/DrawerAddCompteur.jsx` | Ajout compteur avec PRM/PCE optionnel |
| DrawerAddContrat | `components/DrawerAddContrat.jsx` | Ajout contrat avec rattachement PDL |
| SiteCompletude | `pages/Patrimoine.jsx` | 5 actions cliquables, barre progression |

---

## Completude — etat final

Toutes les 5 actions actives :

| Cle | Label | Formulaire |
|-----|-------|-----------|
| `delivery_point` | Ajouter un compteur (PRM/PCE) | DrawerAddCompteur |
| `contrat_actif` | Ajouter un contrat energie | DrawerAddContrat |
| `surface` | Renseigner la surface du site | DrawerEditSite |
| `siret` | Completer les informations etablissement | DrawerEditSite |
| `coordonnees` | Localiser le site (GPS) | DrawerEditSite |

---

## Risques residuels

| Risque | Severite | Mitigation |
|--------|----------|-----------|
| Contrat sans end_date ne compte pas comme actif | Faible | Champ propose dans le formulaire |
| Geocoding BAN peut echouer sur adresses partielles | Faible | GPS optionnel, completude >= 80% suffit |
| window.location.reload() apres enrichissement | Faible | Fonctionnel, refresh cible en Sprint 3 |

---

## Follow-ups

| # | P | Action | Effort |
|---|---|--------|--------|
| 1 | P3 | Contrat sans end_date considere comme actif | S |
| 2 | P3 | Refresh cible au lieu de reload complet | M |
| 3 | P3 | Import simplifie (1 entree, auto-detection) | M |

---

## Bilan complet Sprint 1 + Sprint 2

| Sprint | Commits | Fonctionnalites |
|--------|---------|----------------|
| Sprint 1 | 9 | Quick-create, anti-doublons, completude, renommages UI, Portefeuille retire |
| Issues | 1 | #104-108 traites et fermes |
| Sprint 2 | 4 | Completude cliquable, edit site/societe, ajout compteur, ajout contrat |
| **Total** | **14** | Parcours creation → enrichissement complet sans friction |

---

## Smoke test manuel 5 min

1. Seed : `cd backend && python -m services.demo_seed --pack helios --size S --reset`
2. Quick-create : Patrimoine > Nouveau site > nom + usage + adresse > Creer
3. Drawer completude : clic sur le site > 5 actions cliquables
4. Enrichir societe : clic "Completer etablissement" > SIRET + nom societe > Enregistrer
5. Ajouter compteur : clic "Ajouter compteur" > PRM 14 chiffres > Ajouter
6. Ajouter contrat : clic "Ajouter contrat" > fournisseur + dates > cocher PDL > Ajouter
7. Verification : bloc completude masque (>= 80%), cockpit a jour
