# Audit Phase 3 — Trajectoire + Mutualisation + Modulation + Score Explain

> **Date** : 2026-03-30
> **Pre-requis** : Phase 2 terminee (score 6.2/10, 0 P0 restants)
> **Methode** : 4 parties — verification trajectoire, score explain, mutualisation, modulation

---

## Partie A — Trajectoire verificee

Le seed Phase 2 a rendu la trajectoire calculable. Test sur EFA Paris (id=5 dans DB stale) :
- `validate_trajectory(db, 5, 2024)` → `status = "off_track"` (confirme)
- La DB doit etre re-seedee (`--reset`) pour un test E2E propre
- Le service `operat_trajectory.py` fonctionne correctement avec les nouvelles donnees

**Donnees trajectoire seedees** :

| EFA | Ref 2020 | Conso 2024 | Obj 2030 | Ecart | Statut attendu |
|-----|----------|------------|----------|-------|----------------|
| Paris Bureaux | 595 000 | 500 000 | 357 000 | +143 000 | off_track |
| Lyon Bureaux | 204 000 | 110 000 | 122 400 | -12 400 | **on_track** |
| Nice Hotel | 1 120 000 | 700 000 | 672 000 | +28 000 | off_track |
| Marseille Ecole | 308 000 | 250 000 | 184 800 | +65 200 | off_track |

---

## Partie B — Score explain enrichi

**Endpoint modifie** : `GET /api/regops/score_explain`

Nouveau champ `per_regulation` dans la reponse :

```json
{
  "per_regulation": [
    {
      "regulation": "tertiaire_operat",
      "label": "Decret Tertiaire",
      "weight": 0.45,
      "sub_score": 65,
      "penalties_count": 3,
      "worst_finding_label": "OPERAT_NOT_STARTED",
      "next_deadline": "2026-09-30"
    },
    {
      "regulation": "bacs",
      "label": "Decret BACS (GTB)",
      "weight": 0.30,
      "sub_score": 80,
      "penalties_count": 1,
      "worst_finding_label": "...",
      "next_deadline": "2030-01-01"
    },
    {
      "regulation": "aper",
      "label": "Loi APER (solaire)",
      "weight": 0.25,
      "sub_score": 75,
      "penalties_count": 1,
      "worst_finding_label": "...",
      "next_deadline": "2028-07-01"
    }
  ],
  "formula_explain": "Score = sum(65x0.45 + 80x0.30 + 75x0.25) - 0.0 penalty = 72.5"
}
```

**Fichier modifie** : `backend/routes/regops.py` (lignes 140-180)

---

## Partie C — Simulateur mutualisation

**Nouveau service** : `backend/services/tertiaire_mutualisation_service.py` (~160 lignes)
**Endpoint** : `GET /api/tertiaire/mutualisation?org_id=X&jalon=2030`
**Composant frontend** : `frontend/src/components/conformite/MutualisationSection.jsx`

### Logique

Pour chaque EFA avec reference_year + conso :
- `objectif_kwh = ref_kwh * (1 - reduction_pct)`
- `ecart_kwh = conso_actuelle - objectif`
- Penalites : sans mutualisation = 7500 * nb sites deficit | avec = 7500 si deficit residuel

### Donnees HELIOS attendues (jalon 2030)

| Site | Ecart kWh | Statut |
|------|-----------|--------|
| Paris | +143 000 | deficit |
| Lyon | **-12 400** | **surplus** |
| Nice | +28 000 | deficit |
| Marseille | +65 200 | deficit |
| **Total** | **+223 800** | deficit residuel |

- Sans mutualisation : 3 * 7 500 = **22 500 EUR**
- Avec mutualisation : 1 * 7 500 = **7 500 EUR**
- **Economie : 15 000 EUR**

### Integration frontend

Section ajoutee dans `TertiaireDashboardPage.jsx` sous les EFA.
Contient : tableau sites, KPIs, comparaison penalites, note pedagogique.

---

## Partie D — Simulateur modulation

**Nouveau service** : `backend/services/tertiaire_modulation_service.py` (~190 lignes)
**Endpoint** : `POST /api/tertiaire/modulation-simulation`
**Composant frontend** : `frontend/src/components/conformite/ModulationDrawer.jsx`

### Logique

- Parse contraintes + actions
- Calcule TRI par action (`cout / economie_annuelle_eur`)
- Applique facteur interaction 0.85 sur economies cumulees
- Determine objectif module si conso apres actions > objectif initial
- Score readiness dossier : 6 criteres a ~16.7 pts chacun

### 6 criteres readiness

1. Perimetre precis (EFA + surface)
2. Donnees fiables (>= 2 annees conso)
3. Actions documentees (cout + economie)
4. Justification technique (description)
5. TRI calcule (toutes actions)
6. Coherence strategie globale (org rattachee)

### Integration frontend

Bouton "Simuler une modulation" dans `TertiaireEfaDetailPage.jsx`.
Drawer avec formulaire contraintes/actions, bouton simuler, resultat visuel.

---

## Tests Phase 3

### Backend

| Suite | Tests | Resultat |
|-------|-------|----------|
| test_mutualisation_modulation.py | 11 | **11/11 PASS** |
| test_regops_rules.py | 16 | **16/16 PASS** |
| test_conformite_source_guards.py | 22 | **22/22 PASS** |
| test_router_mount_tertiaire.py | 12 | **12/12 PASS** |
| **Total DT Phase 3** | **61** | **61/61 PASS** |

### Frontend

| Resultat | Valeur |
|----------|--------|
| Fichiers de test | 145/145 PASS |
| Tests individuels | 3616/3616 PASS |
| Regression | Zero |

---

## Fichiers crees / modifies

### Crees
- `backend/services/tertiaire_mutualisation_service.py` (160 lignes)
- `backend/services/tertiaire_modulation_service.py` (190 lignes)
- `backend/tests/test_mutualisation_modulation.py` (11 tests)
- `frontend/src/components/conformite/MutualisationSection.jsx` (170 lignes)
- `frontend/src/components/conformite/ModulationDrawer.jsx` (230 lignes)

### Modifies
- `backend/routes/tertiaire.py` (+55 lignes : 2 endpoints)
- `backend/routes/regops.py` (+40 lignes : per_regulation dans score_explain)
- `frontend/src/services/api/conformite.js` (+4 lignes : 2 appels API)
- `frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx` (+8 lignes : MutualisationSection)
- `frontend/src/pages/tertiaire/TertiaireEfaDetailPage.jsx` (+15 lignes : ModulationDrawer)

---

## Score revise Phase 3

| Axe | Phase 2 | Phase 3 | Delta | Justification |
|-----|---------|---------|-------|---------------|
| Sources & tracabilite | 2/10 | 3/10 | +1 | formula_explain dans score_explain, legal refs dans per_regulation |
| Calculs & formules | 7/10 | 9/10 | +2 | Trajectoire verifiee + mutualisation + modulation + TRI |
| UX/UI | 7/10 | 8/10 | +1 | MutualisationSection, ModulationDrawer, score breakdown |
| Coherence cross-module | 6/10 | 8/10 | +2 | Score explain ventile DT/BACS/APER |
| Architecture | 7/10 | 8/10 | +1 | 2 services dedies, endpoints propres |
| Verifiabilite | 4/10 | 6/10 | +2 | Score explain + readiness_score checklist |
| Lisibilite | 6/10 | 7/10 | +1 | Note pedagogique mutualisation, deadline modulation |
| Donnees demo | 7/10 | 8/10 | +1 | Trajectoire fonctionnelle, 1 surplus + 3 deficit |

### Score global

| Methode | Phase 2 | Phase 3 |
|---------|---------|---------|
| Moyenne simple | 6.2/10 | **7.1/10** |
| Moyenne ponderee | 6.2/10 | **7.4/10** |

---

## Prochaines etapes (Phase 4 — Polish)

Pour atteindre 9/10 :
- Glossaire DT inline (EFA, IIU, DJU, CRefAbs, modulation, mutualisation)
- Evidence Drawer enrichi pour trajectoire
- Tracabilite legale page/section (tertiaire_sources_map.md)
- Wizard EFA ameliore (progression, brouillon)
- Dashboard DT avec 4 KPIs + jalons explicites
