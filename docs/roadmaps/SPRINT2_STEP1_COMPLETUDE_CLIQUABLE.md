# Sprint 2 Step 1 — Completude cliquable + enrichissement site

> Date : 2026-03-15
> Commit : `2e04088`
> Statut : Implemente, teste, committe

---

## Objectif

Depuis le drawer site, l'utilisateur peut cliquer sur les actions manquantes de completude et ouvrir un mini-formulaire d'enrichissement, sans quitter le contexte.

---

## Lignes de completude activees

| Cle | Label | Cliquable | Comportement |
|-----|-------|-----------|-------------|
| `siret` | Completer les informations etablissement | Oui | Ouvre formulaire edition site |
| `surface` | Renseigner la surface du site | Oui | Ouvre formulaire edition site |
| `coordonnees` | Localiser le site (GPS) | Oui | Ouvre formulaire edition site |
| `delivery_point` | Ajouter un PDL (PRM/PCE) | Non | Hint : "Ajoutez un compteur avec PRM/PCE pour creer le PDL automatiquement" |
| `contrat_actif` | Associer un contrat energie | Non | Sprint 2-S3 |

---

## Composants

### DrawerEditSite.jsx (nouveau)

Mini-formulaire inline dans le drawer, 3 sections :

1. **Etablissement** : SIRET (14 car.), Code NAF
2. **Surface** : Surface totale (m2)
3. **Localisation** : Adresse, Code postal, Ville + geocoding auto GPS

Comportements :
- Remplace le contenu du drawer (pas d'empilement)
- N'envoie que les champs modifies (diff intelligent)
- Geocoding auto si adresse/CP/ville modifie
- Au succes : check vert (600ms) → retour resume → completude rechargee

### SiteCompletude (modifie)

- Prop `onAction` : callback quand une action cliquable est cliquee
- Prop `refreshKey` : force le rechargement apres enrichissement
- Actions cliquables : hover bleu, cursor pointer
- Actions non-cliquables : texte gris + hint explicatif

### SiteDrawerContent (modifie)

- Etat `inlineForm` : `'edit_site'` ou `null`
- Si `inlineForm === 'edit_site'` : rend `DrawerEditSite` a la place du contenu
- Prop `onSiteUpdated` : callback pour rafraichir la page apres enrichissement

---

## Fichiers modifies

| Fichier | Changement |
|---------|-----------|
| `frontend/src/components/DrawerEditSite.jsx` | Nouveau — formulaire enrichissement |
| `frontend/src/pages/Patrimoine.jsx` | SiteCompletude cliquable + DrawerEditSite branche |

Zero changement backend — endpoints existants reutilises :
- `PATCH /api/patrimoine/sites/{id}`
- `POST /api/sites/{id}/geocode`
- `GET /api/patrimoine/sites/{id}/completeness`

---

## Parcours UX

```
Drawer site → Tab Resume
    │
    ├── Completude 4/8
    │   ├── [►] Completer les informations etablissement
    │   ├── [►] Renseigner la surface
    │   ├── [►] Localiser le site (GPS)
    │   ├── [i] Ajouter un PDL → hint "ajoutez un compteur avec PRM/PCE"
    │   └── [ ] Associer un contrat → Sprint 2-S3
    │
    ▼ (clic sur action cliquable)
    │
    Formulaire inline :
    ├── Etablissement : SIRET, NAF
    ├── Surface : m2
    ├── Localisation : adresse, CP, ville
    └── [Annuler] [Enregistrer]
    │
    ▼ (succes)
    │
    ✓ Site mis a jour → retour resume → completude rechargee
```

---

## Tests

| Test | Resultat |
|------|----------|
| 31 tests backend (quick-create + soft-delete) | Passe |
| Build frontend Vite | Passe |
| Smoke API : PATCH siret+surface → score 100% | Passe |

---

## Ce qui reste (Sprint 2)

| Step | Action | Effort |
|------|--------|--------|
| S2-2 | Formulaire ajout compteur depuis drawer | M |
| S2-3 | Formulaire ajout contrat depuis drawer | M |
| S2-4 | CTA "Ajouter compteur" dans onglet Compteurs | S |
| S2-5 | Validation finale Sprint 2 | S |
