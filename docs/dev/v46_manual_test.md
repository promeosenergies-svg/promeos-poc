# V46 — OPERAT Actions Bridge — Test manuel

## Pre-requis

- Backend demarre (`python main.py`)
- Frontend demarre (`npm run dev`)
- Au moins 1 EFA creee avec anomalies (lancer controles)

---

## 1. EFA Detail — Creer une action

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 1.1 | Ouvrir `/conformite/tertiaire/efa/{id}` | Page charge, issues visibles |
| 1.2 | Sur une issue, cliquer "Créer une action" | Spinner, puis toast vert "Action créée dans le plan d'actions" |
| 1.3 | Toast contient bouton "Ouvrir le plan d'actions" | Clic navigue vers `/actions?source=operat&efa_id=...` |
| 1.4 | Re-cliquer "Créer une action" sur la meme issue | Toast bleu "Action déjà existante dans le plan d'actions" (dedup) |
| 1.5 | Verifier bloc "Plan d'actions OPERAT" | Present, bouton "Voir dans le plan d'actions" |

## 2. Anomalies — Creer une action

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 2.1 | Ouvrir `/conformite/tertiaire/anomalies` | Page charge, issues visibles |
| 2.2 | Sur une anomalie, cliquer "Créer une action" | Spinner, puis toast "Action créée" |
| 2.3 | Re-cliquer sur la meme anomalie | Toast "Action déjà existante" (dedup) |
| 2.4 | "Déposer la preuve" fonctionne toujours | Navigue vers Memobox (V45, non cassé) |

## 3. Plan d'actions — Filtre OPERAT

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 3.1 | Ouvrir `/actions` | Page charge, toutes les actions |
| 3.2 | Filtre type → selectionner "OPERAT" | Seules les actions OPERAT affichees |
| 3.3 | Ouvrir `/actions?source=operat` | Filtre OPERAT pre-selectionne |
| 3.4 | Badge type "OPERAT" visible sur les actions creees | Badge rouge "OPERAT" (status: crit) |

## 4. Dedup / Idempotence

| # | Action | Resultat attendu |
|---|--------|-----------------|
| 4.1 | Creer action depuis EFA (issue X) | Status: created |
| 4.2 | Creer action depuis Anomalies (meme issue X) | Status: existing (pas de doublon) |
| 4.3 | Verifier dans `/actions` filtre OPERAT | 1 seule action pour cette issue |

## 5. Chaine complete (30s demo DG/DAF)

1. Ouvrir fiche EFA → voir anomalies + preuves
2. Cliquer "Créer une action" sur une anomalie critique
3. Toast: "Action créée" → clic "Ouvrir le plan d'actions"
4. Plan d'actions filtre OPERAT → action visible avec badge OPERAT, titre FR, echeance
5. Re-cliquer "Créer une action" → "Action déjà existante" (pas de doublon)

---

## Suites de tests automatisees

```bash
# Frontend (59 tests V46 + 1663 regression = 1722 total)
cd frontend && npx vitest run

# Backend (aucune modification backend V46 — regression uniquement)
cd backend && venv/Scripts/python -m pytest tests/ -q -p no:warnings
```

Criteres de validation : 0 fail, 0 regression, UI 100% FR, dedup OK.
