# Sprint 2 Micro-correctif — Section societe complete B2B France

> Date : 2026-03-15
> Commit : `253e653`
> Statut : Implemente, teste, committe

---

## Objectif

Completer la section "Etablissement" du formulaire d'enrichissement site (DrawerEditSite) pour couvrir les informations societe minimales attendues en B2B France.

---

## Champs ajoutes

| Champ | Avant | Apres |
|-------|-------|-------|
| Nom de la societe | Absent | Texte libre, prerempli depuis l'org courante |
| SIREN (optionnel) | Absent | 9 car., masque placeholder "000000000" |
| SIRET | Existait | Inchange |
| Code NAF (optionnel) | Existait | Inchange, label "(optionnel)" explicite |
| Section title | "Etablissement" | "Societe / Etablissement" |

---

## Mecanique technique

### Double PATCH en un seul clic "Enregistrer"

1. **PATCH /patrimoine/crud/organisations/{id}** — si nom societe ou SIREN modifie
   - Accepte : `nom`, `siren`
   - Endpoint existant, zero changement backend

2. **PATCH /patrimoine/sites/{id}** — si SIRET, NAF, surface ou adresse modifie
   - Accepte : `siret`, `naf_code`, `surface_m2`, `adresse`, `code_postal`, `ville`
   - Endpoint existant, zero changement backend

3. **Geocoding auto** — si adresse/CP/ville modifie
   - POST /api/sites/{id}/geocode
   - Non bloquant en cas d'echec

### Chargement des donnees societe

- Au mount du formulaire, `crudListOrganisations()` charge l'org courante via `orgId`
- Preremplissage : nom societe + SIREN (masque "000000000" si placeholder)
- `orgId` passe en prop depuis `SiteDrawerContent`

---

## Fichiers modifies

| Fichier | Changement |
|---------|-----------|
| `frontend/src/components/DrawerEditSite.jsx` | +2 champs (nom societe, SIREN), double PATCH, chargement org |
| `frontend/src/pages/Patrimoine.jsx` | Prop `orgId` passee a DrawerEditSite |

Zero changement backend.

---

## Formulaire final

```
┌──────────────────────────────────────┐
│ ← Completer les informations        │
│                                      │
│ SOCIETE / ETABLISSEMENT              │
│ Nom de la societe [Groupe ACME____]  │
│ SIREN (optionnel) [123456789]        │
│ SIRET [12345678901234] NAF [69.20Z]  │
│                                      │
│ SURFACE                              │
│ Surface totale (m2) [1000_________]  │
│                                      │
│ LOCALISATION                         │
│ Adresse [12 rue de la Paix________]  │
│ Code postal [75002] Ville [Paris___] │
│ GPS calcule automatiquement          │
│                                      │
│            [Annuler] [Enregistrer]   │
└──────────────────────────────────────┘
```

---

## Tests

| Test | Resultat |
|------|----------|
| 31 tests backend | Passe |
| Build frontend Vite | Passe |
| Smoke API : PATCH org (nom+SIREN) + PATCH site (SIRET) | Passe |
| Score completude apres enrichissement | 100% |

---

## Ce qui reste (Sprint 2)

| Step | Action | Effort |
|------|--------|--------|
| S2-2 | Formulaire ajout compteur depuis drawer | M |
| S2-3 | Formulaire ajout contrat depuis drawer | M |
| S2-4 | CTA "Ajouter compteur" dans onglet Compteurs | S |
| S2-5 | Validation finale Sprint 2 | S |
