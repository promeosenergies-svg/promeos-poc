# Sprint 3 Step 3 — Import simplifie

> Date : 2026-03-15
> Commit : `8602838`
> Statut : Implemente, teste, committe

---

## Probleme

L'ecran d'entree import proposait 4 modes en grille 2x2 :
- Express (fonctionnel)
- Import complet (fonctionnel)
- Assiste (non implemente — source de confusion)
- Demo (edge case — pas un vrai import)

L'utilisateur ne savait pas lequel choisir.

---

## Decision produit

| Mode | Avant | Apres |
|------|-------|-------|
| Express | "Express" — 2 min | **"Import rapide"** — badge Recommande |
| Import complet | "Import complet" — 5 min | **"Import avec verification"** |
| Assiste | Visible, non implemente | **Retire** |
| Demo | Dans le wizard | **Retire du wizard** |

---

## Changements UI

| Element | Avant | Apres |
|---------|-------|-------|
| Titre step 0 | "Choisissez le mode d'import" | "Importer votre patrimoine" |
| Sous-titre | "Comment souhaitez-vous alimenter..." | "Glissez un fichier CSV ou Excel pour creer vos sites" |
| Layout | Grille 2x2 (4 cartes) | 2 cartes empilees |
| Badge | Aucun | "Recommande" sur Import rapide |
| Empty state bouton | "Demo" (ouvre wizard) | "Importer un fichier" |

---

## Fichiers modifies

| Fichier | Changement |
|---------|-----------|
| `components/PatrimoineWizard.jsx` | MODES reduit a 2, layout empile, titres, retrait cas demo de handleNext |
| `pages/Patrimoine.jsx` | Bouton empty state renomme |

Zero changement backend — le mode est un flag passe a `stagingImport(file, mode)`.

---

## Tests

| Test | Resultat |
|------|----------|
| 63 tests frontend | Passe |
| Build Vite | Passe |

---

## Bilan Sprint 3

| Step | Livrable | Commit |
|------|----------|--------|
| S3-1 | Contrat sans end_date = actif | `39b1171` |
| S3-2 | Refresh cible (3 reload → refreshSites) | `258cf06` |
| S3-3 | Import simplifie (4 → 2 modes) | `8602838` |

Reste : validation finale Sprint 3.
