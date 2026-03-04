# PROMEOS POC — Script de Demo

> Version: V113.1 | Date: 2026-03-04

## Pre-requis

```bash
# Terminal 1 — Backend
cd backend && python main.py
# → http://localhost:8001

# Terminal 2 — Frontend
cd frontend && npm run dev
# → http://localhost:5173

# Seed (si besoin)
cd backend && python -m services.demo_seed --pack helios --size S --reset
```

Login: `promeos@promeos.io` / `promeos2024`

---

## Demo 2 min (Executive)

| Temps | Action | Ce qu'on montre |
|-------|--------|-----------------|
| 0:00 | Ouvrir http://localhost:5173 | **Command Center** — KPIs executifs (Conformite %, Couverture %, Risque k€) |
| 0:20 | Pointer "Impact & Decision" | 3 KPIs finances (risque, surcout, optimisation), levier dominant en surbrillance |
| 0:40 | Cliquer sur un site carte | **Site360** — fiche complete du site (conformite, compteurs, factures) |
| 1:00 | Onglet "Consommations" | Courbe conso 30j + switch granularite Heure/Jour |
| 1:20 | Retour Cockpit | Widget "Qualite donnees" avec coverage % + boutons "Corriger" |
| 1:40 | Montrer "N leviers activables" | Actions recommandees avec impact € et CTA "Creer une action" |
| 2:00 | Fin | *"Tout est centralise, actionnable, zero Excel"* |

---

## Demo 10 min (Product Tour)

### 1. Cockpit (2 min)
- KPIs executifs (conformite, couverture, risque financier)
- Widget Qualite Donnees (coverage %, causes rouges, CTA "Corriger")
- Impact & Decision (3 KPIs €, leviers activables, recommandation)
- Achats energie (contrats expirants, couverture, sites sans contrat)

### 2. Patrimoine (1 min)
- Carte des sites avec health heatmap
- Filtres (type batiment, conformite)
- Clic site → Site360

### 3. Consommations (2 min)
- Selection site + periode + granularite
- Onglets: Conso, Meteo, Signature, Objectifs, HP/HC, Tunnel, Insights
- Switch Electricite / Gaz
- Explorer multi-sites

### 4. Conformite (2 min)
- Mode Guide (7 etapes) vs Mode Expert
- Obligations par reglementation (Tertiaire, BACS, APER, CEE)
- Onglet "Donnees & Qualite" — coverage, freshness, causes, remediation
- Export OPERAT (preview + validation + CSV)

### 5. Actions (1.5 min)
- Centre d'actions — inbox (filtre source: copilot, manuel, auto)
- Plan d'actions — portfolio view
- Creation action avec template (dropdown + preremplissage)
- Detail action (priorite, impact, statut, preuve)

### 6. Marche (1.5 min)
- Bill Intelligence — anomalies factures
- Achat Energie — scenarios de purchase
- Monitoring — KPIs site (load factor, Pmax, data quality)

---

## Demo 30 min (Deep Dive)

Reprendre le Product Tour ci-dessus, en ajoutant :

### Data Quality (5 min)
- Cockpit widget → CTA vers Conformite onglet "Donnees"
- Coverage par site + freshness
- Causes detaillees (pas de compteur, donnees partielles, factures manquantes)
- CTA remediation → onboarding step ou import

### Export OPERAT (3 min)
- Conformite → Tertiaire → bouton "Exporter OPERAT"
- Modal preview (validation warnings, apercu 17 colonnes)
- Telecharger CSV (separateur `;`, UTF-8)
- Ouvrir dans Excel → verifier les colonnes

### Energy Copilot (5 min)
- Actions generees automatiquement (par mois, par site)
- Valider une action → convertie en ActionItem
- Rejeter une action → motif obligatoire
- Idempotence (valider 2x → `already_converted`)
- Filtrer dans Centre d'actions par source=copilot

### Onboarding (3 min)
- 6 etapes (org, sites, compteurs, factures, users, action)
- Auto-detection depuis les donnees reelles
- Data Quality gating (coverage < 50% → alerte)
- TTFV analytics (temps avant premiere valeur)

### Admin (2 min)
- Gestion users + roles
- Modeles d'actions (CRUD admin)
- Journal d'audit

---

## Scenarios QA critiques

| # | Scenario | Verification |
|---|----------|-------------|
| 1 | Scope persistence | Changer org → refresh → org toujours selectionnee |
| 2 | Empty state | Org sans donnees → messages vides actionables |
| 3 | Error recovery | Couper backend → erreur → relancer → retry OK |
| 4 | CSV OPERAT | Export → Excel → `;` separator, UTF-8, 17 colonnes |
| 5 | Copilot idempotence | Valider 2x → pas d'erreur, `already_converted` |
| 6 | Reject reason | Rejeter sans motif → refuse → avec motif → OK |
| 7 | Filtre Centre d'actions | source=copilot → uniquement actions Copilot |
| 8 | Navigation 2 clics | Depuis Cockpit → n'importe quelle feature en 2 clics max |
| 9 | KPI coherence | Meme chiffre partout (Cockpit = Site360 = Detail) |
| 10 | Responsive | UI lisible sur 1280px minimum |

---

## Quality Gates (validation rapide)

```bash
# Backend
cd backend && python -c "from main import app; print(f'{len(app.routes)} routes')"
cd backend && python -m ruff check . --config pyproject.toml
cd backend && python -m pytest tests/ -x -q

# Frontend
cd frontend && npm run lint
cd frontend && npm run build
cd frontend && npx vitest run
```
