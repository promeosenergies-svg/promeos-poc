# PROMEOS POC — QA Smoke Tests (Checklist manuelle)

> Version: V113.1 | Date: 2026-03-04

## Pre-requis

```bash
# Backend (terminal 1)
cd backend && python main.py
# → http://localhost:8001

# Frontend (terminal 2)
cd frontend && npm run dev
# → http://localhost:5173

# Seed (si necessaire)
cd backend && python -m services.demo_seed --pack helios --size S --reset
```

---

## Demo 2 min (Executive)

| # | Etape | Resultat attendu | Status |
|---|-------|-------------------|--------|
| 1 | Ouvrir http://localhost:5173 | Page Command Center s'affiche | [ ] |
| 2 | Verifier les KPIs executifs | Conformite %, Couverture %, Risque k€ affiches | [ ] |
| 3 | Cliquer sur un site dans la carte | Navigation vers Site360 avec donnees du site | [ ] |
| 4 | Retour via breadcrumb/menu | Retour au Command Center | [ ] |

---

## Demo 10 min (Product Tour)

| # | Parcours | Etapes | Resultat attendu | Status |
|---|----------|--------|-------------------|--------|
| 5 | **Login → Scope** | Login promeos@promeos.io, verifier org HELIOS | Org selectionnee, 5 sites visibles | [ ] |
| 6 | **Cockpit** | Naviguer /cockpit | KPIs, alertes, widget qualite donnees | [ ] |
| 7 | **Patrimoine** | /patrimoine → voir carte + tableau | Sites sur carte, health heatmap | [ ] |
| 8 | **Consommations** | /consommations/explorer → selectionner 1 site, 30j | Graphe conso horaire, KPIs header | [ ] |
| 9 | **Changer granularite** | Passer de "Jour" a "Heure" | Graphe se met a jour, plus de points | [ ] |
| 10 | **Conformite** | /conformite → voir obligations | Liste obligations, statuts colores | [ ] |
| 11 | **Actions** | /actions → voir plan d'actions | Actions listees avec priorite/statut | [ ] |
| 12 | **Billing** | /billing → timeline factures | Timeline avec periodes couvertes/manquantes | [ ] |
| 13 | **Monitoring** | /monitoring → KPIs site | Load factor, Pmax, data quality scores | [ ] |
| 14 | **Energy Copilot** | /energy-copilot → lancer analyse | Propositions generees, boutons valider/rejeter | [ ] |

---

## Demo 30 min (Deep Dive)

| # | Parcours | Etapes | Resultat attendu | Status |
|---|----------|--------|-------------------|--------|
| 15 | **Data Quality** | Cockpit → widget Qualite | Coverage %, issues rouges, bouton "Corriger" | [ ] |
| 16 | **Export OPERAT** | Conformite → Tertiaire → Export | Modal apercu, preview table, CSV telecharge | [ ] |
| 17 | **Copilot Validate** | /energy-copilot → Valider une action | Action passe en "Converti", ActionItem cree | [ ] |
| 18 | **Copilot Reject** | /energy-copilot → Rejeter une action | Prompt motif, action passe en "Rejete" | [ ] |
| 19 | **Action Templates** | API /api/action-templates → seed | 20 templates crees, GET les liste | [ ] |
| 20 | **Onboarding** | /onboarding → detection auto | 6 etapes, progression auto-detectee | [ ] |
| 21 | **Filtres consommation** | Explorer → multi-sites, changer periode | Graphes se mettent a jour, URL persiste | [ ] |
| 22 | **Bill Intelligence** | /bill-intel → anomalies factures | Anomalies listees, detail accessible | [ ] |
| 23 | **Achat Energie** | /achat-energie → scenarios | Scenarios de purchase compares | [ ] |
| 24 | **Segmentation** | /segmentation → questionnaire | Profil B2B genere | [ ] |
| 25 | **Admin** | /admin/users → gestion users | Liste users, roles assignes | [ ] |
| 26 | **Notifications** | /notifications → voir alertes | Liste notifications avec badges | [ ] |

---

## Tests fonctionnels critiques

| # | Test | Verification | Pass? |
|---|------|-------------|-------|
| 27 | **Scope persistence** | Changer d'org → refresh page → org toujours selectionnee | [ ] |
| 28 | **Empty state** | Selectionner org sans donnees → messages vides actionables | [ ] |
| 29 | **Error recovery** | Couper backend → pages affichent erreur → relancer → retry fonctionne | [ ] |
| 30 | **CSV export** | OPERAT export → ouvrir dans Excel → separateur `;`, UTF-8, 17 colonnes | [ ] |
| 31 | **Copilot idempotence** | Valider 2x la meme action → pas d'erreur, retourne `already_converted` | [ ] |
| 32 | **Reject reason** | Rejeter sans motif → prompt refuse → avec motif → action rejetee | [ ] |

---

## Validation des Quality Gates

```bash
# Gate 1: Backend import
cd backend && python -c "from main import app; print(f'{len(app.routes)} routes')"

# Gate 2: Backend tests
cd backend && python -m pytest tests/test_v113_data_quality_causes.py tests/test_v113_operat_golden.py -v

# Gate 3: Ruff lint
cd backend && python -m ruff check routes/ models/ services/

# Gate 4: Frontend build
cd frontend && npm run build

# Gate 5: Frontend tests
cd frontend && npx vitest run

# Gate 6: Frontend lint
cd frontend && npx eslint src --ext js,jsx --max-warnings=5
```
