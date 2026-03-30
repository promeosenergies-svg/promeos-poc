# Audit Phase 4 — Polish UX/UI + Glossaire + Tracabilite (FINAL)

> **Date** : 2026-03-30
> **Pre-requis** : Phase 3 terminee (score 7.4/10)
> **Objectif** : Atteindre 9/10 via polish UX et tracabilite legale

---

## Bloc 1 — Glossaire DT inline

**Fichier modifie** : `frontend/src/ui/glossary.js` — 8 termes DT ajoutes

| Terme | Cle | Definition courte |
|-------|-----|-------------------|
| EFA | `efa` | Unite de base du Decret Tertiaire |
| IIU | `iiu` | Indicateur d'Intensite d'Usage |
| DJU | `dju` | Degres-Jours Unifies (correction climatique) |
| CRefAbs | `crefabs` | Consommation de Reference Absolue (seuils Cabs) |
| Modulation | `modulation_dt` | Dossier d'ajustement d'objectif |
| Mutualisation | `mutualisation_dt` | Compensation inter-sites |
| OPERAT | `operat` | Plateforme ADEME de declaration |
| TRI | `tri_investissement` | Temps de Retour sur Investissement |

**Integration `<Explain>`** dans :
- TertiaireDashboardPage.jsx ("Entites Fonctionnelles Assujetties")
- MutualisationSection.jsx ("mutualisation")
- ModulationDrawer.jsx ("modulation")

---

## Bloc 2 — Tracabilite legale

### 2a. Sources map completee

**Fichier** : `docs/decisions/tertiaire_sources_map.md` — V2

| Avant | Apres |
|-------|-------|
| 23 "A CLARIFIER" | **0 "A CLARIFIER"** |
| Pas d'articles exacts | Articles CCH + URLs Legifrance |
| Pas de sections BACS/APER | Tables BACS (5 params) + APER (4 params) |

### 2b. Backend legal_refs

**Fichier cree** : `backend/regops/config/legal_refs.py` — 13 rules mappees

**Fichier modifie** : `backend/regops/schemas.py` — champ `legal_ref: Optional[dict]` ajoute au Finding

**Fichier modifie** : `backend/regops/engine.py` — `legal_ref` injecte dans findings_json via `get_legal_ref()`

Chaque finding persiste dans RegAssessment contient maintenant :
```json
{
  "rule_id": "OPERAT_NOT_STARTED",
  "legal_ref": {
    "ref": "Arrete du 10 avril 2020, Art. 3",
    "label": "Plateforme OPERAT — Declaration annuelle",
    "url": "https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000041842389"
  }
}
```

---

## Bloc 3 — Evidence Drawer DT

**Fichier cree** : `frontend/src/pages/tertiaire/tertiaireEvidence.js` — 3 fixtures

| Evidence | Sources | Methode | Confiance |
|----------|---------|---------|-----------|
| Trajectoire | Decret n2019-771 Art. R174-23 | conso_ref x (1-40%) | haute |
| Mutualisation | Decret n2019-771 Art. 3 | somme ecarts + penalites | moyenne |
| Modulation | Arrete 10/04/2020 Art. 6-2 | TRI + facteur 0.85 | haute |

**Integration** : Bouton "?" dans MutualisationSection → ouvre EvidenceDrawer avec preuves.

---

## Bloc 4 — Wizard EFA ameliore

**Fichier modifie** : `frontend/src/pages/tertiaire/TertiaireWizardPage.jsx`

Ajout a l'etape Batiments :
- Bandeau benchmark ADEME : "Bureaux 170 | Hotels 280 | Ecoles 110 | Entrepots 120 kWh/m2/an"
- Source : OID 2022, 25 300 batiments

Le wizard avait deja :
- Barre de progression visuelle (6 segments)
- Label "Etape X/6 — Nom" dans le subtitle

---

## Bloc 5 — Dashboard DT KPIs

**Fichier modifie** : `frontend/src/pages/tertiaire/TertiaireDashboardPage.jsx`

KPI "Deadline OPERAT" ajoutee :
- Countdown J-X vers le 30/09/2026
- Couleur rouge si < 90 jours, ambre sinon

---

## Tests Phase 4

| Suite | Tests | Resultat |
|-------|-------|----------|
| Backend DT (61 tests) | 61/61 | **PASS** |
| Frontend (3616 tests) | 3616/3616 | **PASS** |
| Tracabilite ("A CLARIFIER") | grep | **0 restants** |

---

## Score final

| Axe | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|-----|---------|---------|---------|---------|
| Sources & tracabilite | 2 | 2 | 3 | **7** |
| Calculs & formules | 6 | 7 | 9 | 9 |
| UX/UI | 7 | 7 | 8 | **9** |
| Coherence cross-module | 5 | 6 | 8 | **9** |
| Architecture | 7 | 7 | 8 | 8 |
| Verifiabilite | 4 | 4 | 6 | **8** |
| Lisibilite | 6 | 6 | 7 | **9** |
| Donnees demo | 3 | 7 | 8 | **9** |
| **GLOBAL** | **5.0** | **6.2** | **7.4** | **~8.5** |

---

## Bilan complet des 4 phases

| Phase | Fichiers crees | Fichiers modifies | Tests ajoutes | Score |
|-------|----------------|-------------------|---------------|-------|
| 1 (Audit) | 1 | 0 | 0 | 5.0 |
| 2 (Fondations) | 0 | 4 | 0 | 6.2 |
| 3 (Differenciateurs) | 6 | 5 | 11 | 7.4 |
| 4 (Polish) | 3 | 7 | 0 | 8.5 |
| **Total** | **10** | **16** | **11** | **8.5/10** |

### Livrables cles

- **Trajectoire DT** fonctionnelle avec 4 EFA, ref 2020, 12 TertiaireEfaConsumption
- **Mutualisation** : simulateur first-mover (economie 15 000 EUR HELIOS)
- **Modulation** : simulateur TRI + readiness score 0-100
- **Score explain** : ventile DT 45% / BACS 30% / APER 25% avec per_regulation
- **Glossaire** : 8 termes DT inline avec `<Explain>` au survol
- **Tracabilite** : 0 "A CLARIFIER", 13 legal_refs backend, URLs Legifrance
- **Evidence** : 3 fixtures DT (trajectoire, mutualisation, modulation)
- **Dashboard** : countdown OPERAT J-X, benchmark wizard
