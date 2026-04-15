# Bilan Final Honnete — Conformite Decret Tertiaire

> **Date** : 31 mars 2026
> **Score auto-declare** : 9.0/10
> **Score corrige** : **8.2/10**
> **Delta** : -0.8 (3 angles morts identifies par le product owner)

---

## Les 3 angles morts corriges

### 1. UX jamais vue (9 auto-declare -> 8 corrige)

**Probleme** : 6 phases de dev, 0 screenshot. MutualisationSection (170L) et ModulationDrawer (230L)
crees mais jamais vus rendus. Violation de la regle "visual first".

**Correction** : Playwright lance post-session, 3 captures :

| Page | Screenshot | Constat |
|------|-----------|---------|
| /conformite | 05-conformite.png | Score 83, barres DT/BACS/APER, timeline reglementaire OK |
| /conformite/tertiaire | 06-conformite-tertiaire.png | 4 KPIs (dont J-183 OPERAT), 8 EFA listees OK |
| /cockpit | 01-cockpit.png | Trajectoire DT 2030 "en retard de 41.2%", graphe conso OK |

**Verdict** : Les pages renderent correctement. Mais MutualisationSection n'est pas visible
dans le screenshot (sous le fold) — il faudrait un scroll ou un test d'interaction specifique.
ModulationDrawer non capture (necessite clic sur EFA detail puis bouton). **Score UX : 8/10**.

### 2. Legacy compliance_engine.py toujours actif (9 -> 8)

**Probleme** : 1 255 lignes, 11 imports de fonctions non migres, 23 fichiers dependants.
Dire "Architecture 9" avec ce fichier en production est optimiste.

**Etat reel apres Phase 6** :
- Constantes migrees vers emission_factors.py (9 fichiers migres)
- 11 imports de fonctions restants (routes/compliance.py, coordinator, onboarding...)
- Le fichier est desormais un "stub avec logique" — les constantes viennent d'ailleurs
  mais les fonctions (recompute_site, compute_snapshot, etc.) sont toujours definies ici
- Header de depreciation avec plan de migration 4 etapes

**Verdict** : Migration partielle. Pas 9.0, plutot **8/10 en architecture**.

### 3. Trajectoire post-reset non confirmee (corrige)

**Probleme** : Test Phase 3 fait sur DB stale. Aucun curl trace apres --reset.

**Correction** : Test Python post-reset confirme :

```
EFA 5 (Paris Bureaux)      : ref_year=2020, ref_kwh=595000, consos=3 -> off_track
EFA 6 (Nice Hotel)         : ref_year=2020, ref_kwh=1120000, consos=3 -> off_track
EFA 7 (Lyon Bureaux)       : ref_year=2020, ref_kwh=204000, consos=3  -> on_track
EFA 8 (Marseille Ecole)    : ref_year=2020, ref_kwh=308000, consos=3  -> off_track
```

**Note** : `delta_kwh` et `delta_pct` retournent `None` car validate_trajectory cherche une
TertiaireEfaConsumption pour l'annee d'observation exacte (2024) et calcule le delta vs
l'objectif applicable. Le statut (on_track/off_track) est correct, le delta numerique
necessite une investigation supplementaire du service operat_trajectory.py.

**Verdict** : Trajectoire **fonctionnelle** (statuts corrects), delta a investiguer. **8.5/10 donnees demo**.

---

## Score corrige detaille

| Axe | Auto-declare | Corrige | Justification |
|-----|-------------|---------|---------------|
| Sources & tracabilite | 8 | **8** | 0 "A CLARIFIER", legal_refs, KB items — correct |
| Calculs & formules | 9 | **9** | Mutualisation + modulation + score explain — correct |
| UX/UI | 9 | **8** | Pages renderent mais MutualisationSection/ModulationDrawer non vues visuellement |
| Coherence cross-module | 9 | **8.5** | Score explain ventile OK, mais delta trajectoire = None |
| Architecture | 9 | **8** | compliance_engine.py 1255L toujours actif, 11 imports non migres |
| Verifiabilite | 9 | **8** | Evidence fixtures crees mais non testees visuellement |
| Lisibilite | 9 | **8.5** | Glossaire 8 termes OK, mais les tooltips non vus en capture |
| Donnees demo | 9 | **8.5** | Trajectoire fonctionnelle, mais delta_kwh = None |
| **GLOBAL** | **9.0** | **8.2** | |

---

## Ce qui est incontestable (5.0 -> 8.2)

Le gain de +3.2 points en ~10h est reel et mesurable :

### Backend cree
- `tertiaire_mutualisation_service.py` — simulateur first-mover (economie 15k EUR HELIOS)
- `tertiaire_modulation_service.py` — simulateur TRI + readiness 0-100
- `regops/config/legal_refs.py` — 13 references legales avec kb_item_id
- 4 items KB reglementaires (sanctions, arrete, modulation, mutualisation)
- Endpoints GET /api/tertiaire/mutualisation + POST /api/tertiaire/modulation-simulation
- Score explain enrichi avec per_regulation (DT 45% / BACS 30% / APER 25%)
- Constantes migrees vers source canonique emission_factors.py

### Frontend cree
- `MutualisationSection.jsx` — tableau sites + penalites + note pedagogique
- `ModulationDrawer.jsx` — formulaire contraintes/actions + score readiness
- `tertiaireEvidence.js` — 3 fixtures Evidence DT
- Glossaire 8 termes DT dans glossary.js + integration `<Explain>`
- KPI countdown OPERAT J-X + benchmark ADEME dans wizard

### Seed enrichi
- 4 EFA avec reference_year=2020 + 12 TertiaireEfaConsumption
- Lyon EN AVANCE (on_track), 3 autres EN RETARD (off_track)
- Usage cree pour chaque nouveau batiment

### Documentation
- tertiaire_sources_map.md V2 : 0 "A CLARIFIER" (vs 23 avant)
- 6 rapports d'audit (Phase 1 a 6)
- compliance_engine.py : plan de migration documente

### Tests
- 110 tests backend DT PASS (vs 60 avant)
- 3616 tests frontend PASS (0 regression)
- /simplify : 6 issues corrigees par code-review automatise

---

## Ce qui reste pour 9.0

| Action | Impact score | Effort |
|--------|-------------|--------|
| Screenshot interactif MutualisationSection (scroll + clic) | UX 8 -> 9 | 30 min |
| Screenshot ModulationDrawer (clic EFA detail + simuler) | UX 8 -> 9 | 30 min |
| Investiguer delta_kwh = None dans validate_trajectory | Donnees 8.5 -> 9 | 1h |
| Migrer 11 imports fonctions compliance_engine | Archi 8 -> 9 | 3h |
| Test E2E parcours complet (seed -> cockpit -> DT -> EFA -> modulation) | Verifiabilite 8 -> 9 | 2h |

**Effort total pour 9.0 : ~7h supplementaires.**

---

## Screenshots Playwright (captures reelles post-reset)

Dossier : `artifacts/audits/captures/dt-phase6/`

- `05-conformite.png` — Page conformite reglementaire, score 83, barres DT/BACS/APER
- `06-conformite-tertiaire.png` — Dashboard DT, 4 KPIs, J-183 OPERAT, 8 EFA
- `01-cockpit.png` — Vue executive, trajectoire DT "en retard de 41.2%", graphe conso

---

## Chronologie

| Heure | Phase | Score |
|-------|-------|-------|
| T+0h | Phase 1 (Audit) | 5.0 |
| T+2h | Phase 2 (Fondations) | 6.2 |
| T+5h | Phase 3 (Differenciateurs) | 7.4 |
| T+7h | Phase 4 (Polish) | 8.5 |
| T+8h | Phase 5 (Consolidation) | 8.8 |
| T+10h | Phase 6 (Migration + /simplify) | 8.8 (corrige de 9.0) |
| T+10.5h | Correction angles morts | **8.2** (score honnete) |
