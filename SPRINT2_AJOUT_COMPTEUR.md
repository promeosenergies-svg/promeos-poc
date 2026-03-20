# Sprint 2 — Ajout compteur depuis le drawer site

> Date : 2026-03-15
> Commit : `0a72c2e`
> Statut : Implemente, teste, committe

---

## Objectif

Depuis le drawer site, l'utilisateur peut ajouter un compteur simplement, avec PRM/PCE optionnel qui cree automatiquement le point de livraison.

---

## Points d'entree

| Entree | Emplacement | Resultat |
|--------|------------|----------|
| Completude "Ajouter un compteur (PRM/PCE)" | Tab Resume, bloc completude | Ouvre DrawerAddCompteur |
| CTA "+ Ajouter un compteur" | Tab Compteurs, en haut | Ouvre DrawerAddCompteur |

---

## Formulaire DrawerAddCompteur

```
┌──────────────────────────────────────┐
│ ← Ajouter un compteur               │
│                                      │
│ Type d'energie *  [Electricite ▾]    │
│                                      │
│ PRM (optionnel — 14 chiffres)        │
│ [01234567890123___]                  │
│ Le PDL sera cree automatiquement.    │
│                                      │
│ Puissance souscrite (kVA) (optionnel)│
│ [36_______]                          │
│                                      │
│            [Annuler] [Ajouter]       │
└──────────────────────────────────────┘
```

### Comportements cles

- Label contextuel : "PRM" pour electricite, "PCE" pour gaz
- Puissance souscrite affichee uniquement pour electricite
- Si PRM/PCE saisi → DeliveryPoint auto-cree en backend
- Message succes confirme la creation du PDL si PRM fourni
- Au succes : retour onglet Compteurs (pas Resume) + completude rechargee

---

## Patch backend (micro)

| Fichier | Changement |
|---------|-----------|
| `backend/routes/compteurs.py` | `meter_id` optionnel ajoute a `CompteurCreateRequest` |
| | Utilise `req.meter_id` au lieu de toujours generer `AUTO-*` |

`ensure_delivery_points_for_site` (existant) cree le DP automatiquement apres commit.

---

## Patch frontend

| Fichier | Changement |
|---------|-----------|
| `frontend/src/components/DrawerAddCompteur.jsx` | Nouveau — formulaire inline |
| `frontend/src/pages/Patrimoine.jsx` | Import + inlineForm `add_compteur` + completude cliquable + CTA onglet Compteurs |

---

## Completude mise a jour

| Cle | Label avant | Label apres | Cliquable |
|-----|------------|-------------|-----------|
| `delivery_point` | "Ajouter un PDL" (hint) | "Ajouter un compteur (PRM/PCE)" | Oui → add_compteur |
| `siret` | Cliquable → edit_site | Inchange | Oui |
| `surface` | Cliquable → edit_site | Inchange | Oui |
| `coordonnees` | Cliquable → edit_site | Inchange | Oui |
| `contrat_actif` | Non cliquable | Inchange | Non (Sprint 2-S3) |

---

## Tests

| Test | Resultat |
|------|----------|
| 31 tests backend | Passe |
| Build frontend Vite | Passe |
| Smoke API : POST compteur avec PRM → DP auto-cree | Passe |
| Score completude apres ajout compteur avec PRM | 100% |

---

## Ce qui reste (Sprint 2)

| Step | Action | Effort |
|------|--------|--------|
| S2-3 | Formulaire ajout contrat depuis drawer | M |
| S2-4 | Validation finale Sprint 2 + push | S |
