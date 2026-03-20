# Sprint 2 — Ajout contrat depuis le drawer site

> Date : 2026-03-15
> Commit : `bf8a15f`
> Statut : Implemente, teste, committe

---

## Objectif

Depuis le drawer site, l'utilisateur peut ajouter un contrat energie simplement, avec rattachement optionnel aux points de livraison existants.

---

## Point d'entree

| Entree | Emplacement | Resultat |
|--------|------------|----------|
| Completude "Ajouter un contrat energie" | Tab Resume, bloc completude | Ouvre DrawerAddContrat |

---

## Formulaire DrawerAddContrat

```
┌──────────────────────────────────────┐
│ ← Ajouter un contrat                │
│                                      │
│ Energie *       [Electricite ▾]      │
│ Fournisseur *   [EDF_____________]   │
│   (suggestions : EDF, Engie, Total…) │
│ Date de debut * [2025-01-01]         │
│ Date de fin     [2027-12-31]         │
│   (optionnel)                        │
│ Reference       [CT-2025-001_____]   │
│   (optionnel)                        │
│                                      │
│ POINTS DE LIVRAISON COUVERTS         │
│ (si PDL existent sur le site)        │
│ ☑ 01234567890123 (Electricite)       │
│ ☐ 21234567890123 (Gaz)               │
│                                      │
│            [Annuler] [Ajouter]       │
└──────────────────────────────────────┘
```

### Comportements cles

- Fournisseurs francais en suggestions (datalist) : EDF, Engie, TotalEnergies, Eni, Vattenfall, Alpiq, Ekwateur, Mint, OHM
- PDL charges au mount du formulaire, pre-selectionnes par type d'energie
- Changement de type d'energie → pre-selection PDL mise a jour
- Validation front : fournisseur + date debut obligatoires
- Au succes : retour tab Resume + completude rechargee

---

## Champs

| Champ | Obligatoire | Type |
|-------|-------------|------|
| Energie | Oui | Select (elec, gaz) |
| Fournisseur | Oui | Texte libre + datalist suggestions |
| Date de debut | Oui | Date |
| Date de fin | Non | Date |
| Reference contrat | Non | Texte libre |
| PDL couverts | Non | Checkboxes (si PDL existent) |

---

## Completude — etat final Sprint 2

Toutes les 5 actions de completude sont maintenant actives :

| Cle | Label | Action | Formulaire |
|-----|-------|--------|-----------|
| `delivery_point` | Ajouter un compteur (PRM/PCE) | `add_compteur` | DrawerAddCompteur |
| `contrat_actif` | Ajouter un contrat energie | `add_contrat` | DrawerAddContrat |
| `surface` | Renseigner la surface du site | `edit_site` | DrawerEditSite |
| `siret` | Completer les informations etablissement | `edit_site` | DrawerEditSite |
| `coordonnees` | Localiser le site (GPS) | `edit_site` | DrawerEditSite |

---

## Fichiers modifies

| Fichier | Changement |
|---------|-----------|
| `frontend/src/components/DrawerAddContrat.jsx` | Nouveau — formulaire ajout contrat |
| `frontend/src/pages/Patrimoine.jsx` | Import + inlineForm `add_contrat` + completude cliquable |

Zero changement backend — `POST /api/patrimoine/contracts` existait deja.

---

## Tests

| Test | Resultat |
|------|----------|
| 31 tests backend | Passe |
| Build frontend Vite | Passe |
| Smoke API : POST contrat EDF → id=10 | Passe |
| Score completude apres ajout contrat | 100% |

---

## Bilan Sprint 2

| Step | Livrable | Commit |
|------|----------|--------|
| S2-1 | Completude cliquable + formulaire edition site | `2e04088` |
| S2-1b | Micro-correctif section societe B2B France | `253e653` |
| S2-2 | Ajout compteur depuis drawer (PRM/PCE → DP auto) | `0a72c2e` |
| S2-3 | Ajout contrat depuis drawer (rattachement PDL) | `bf8a15f` |

Toutes les 5 actions de completude sont actives. Le site peut etre entierement enrichi depuis le drawer sans quitter le contexte.

### Reste a faire

| Action | Effort |
|--------|--------|
| Validation finale Sprint 2 + push origin/main | S |
