# Audit postfix — Sprint S1 Conformité P0 OPERAT/DEET (2026-05-27)

**Branche** : `claude/conformite-s1-operat-deet-p0`
**Base** : `claude/refonte-sol2` après merge chaîne brique Énergie #321→#322→#323 puis audit Phase 0 #324
**Verdict** : 🟢 **GO MERGE** — 4 divergences P0 OPERAT/DEET corrigées + cross-check Légifrance officiel + tests source-guards + endpoint + unitaires verts.

---

## 1 — Chantier 0 — Cross-check officiel Légifrance

📄 `docs/audits/crosscheck_legifrance_operat_deet_2026_05_27.md`

**Verdict cross-check** : les 4 divergences D1/D2/D4/D5 sont **toutes confirmées** par sources officielles Légifrance. Aucun report en « à clarifier ». Tous les chantiers du sprint peuvent être codés sans approximation.

| # | Divergence | Statut | Valeur confirmée | Source officielle |
|---|---|---|---|---|
| D1 | CO2 élec OPERAT | ✅ | **0,064 kgCO2/kWh EF PCI** | Annexe VII Tableau VII-2, arrêté 10/04/2020 modifié (NOR DEVR2007365A consolidé 07/09/2025) |
| D2 | EP élec OPERAT | ✅ | **2,3** (Article 16 changement source) | Annexe VII, arrêté 10/04/2020 |
| D4 | Année référence + butoir | ✅ | Plage **[2010 ; 2022]** + butoir **30/09/2027** + fallback **1ère année pleine d'exploitation** | Article 3.I, arrêté 10/04/2020 |
| D5 | TRI par typologie | ✅ | **30 ans** enveloppe / **15 ans** équipements / **10 ans** systèmes optim+exploitation | Article 11.I, arrêté 10/04/2020 |

Sources Légifrance utilisées (verbatim et URLs dans le crosscheck) :
- https://www.legifrance.gouv.fr/loda/id/JORFTEXT000041842389 (arrêté principal)
- https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000045682100 (Annexe VII)
- https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052198856 (consolidation 01/08/2025)
- https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000052134589 (DPE bascule EP 2,3→1,9 au 01/01/2026)

---

## 2 — Chantier 1 — Constantes OPERAT séparées

**Fichier NEW** : [`backend/config/operat_constants.py`](backend/config/operat_constants.py) (~210 l)

Expose **4 catégories de constantes** séparées des constantes ADEME (Bilan GES / CSRD) et RE2020 (DPE 2026+) :

- `EMISSION_FACTORS_OPERAT` — 5 vecteurs (ELEC 0,064 / GAZ 0,227 / FIOUL 0,324 / BOIS 0,030 / CHARBON 0,385) avec métadonnées `source / source_url / unit / scope / consolidation_date`.
- `EP_COEFFICIENTS_OPERAT` — 4 vecteurs Article 16 (ELEC 2,3 / GAZ 1,0 / FIOUL 1,0 / BOIS 0,0).
- `OPERAT_REFERENCE_YEAR_*` — bornes 2010-2022, butoir 30/09/2027, règle fallback texte.
- `OPERAT_TRI_TYPOLOGIES` — 3 typologies STRUCTURAL_ENVELOPE / ENERGY_EQUIPMENT / OPTIMIZATION_SYSTEM avec seuils 30/15/10 et `label_fr / source / source_url`.

**4 helpers d'accès doctrinés** :
- `get_operat_emission_factor(vector)` → fail-closed `KeyError` si vecteur hors Annexe VII (pas de fallback silencieux).
- `get_operat_ep_coefficient(vector)` → fail-closed.
- `get_operat_tri_threshold(typology)` → fail-closed.
- `is_valid_operat_reference_year(year, is_first_full_year=False)` → booléen.

**Préservation des autres référentiels** :
- [`backend/config/emission_factors.py`](backend/config/emission_factors.py) — **inchangé sur les valeurs** (ADEME 0,052 préservé pour Bilan GES / CSRD). Docstring enrichie avec avertissement explicite pointant vers `operat_constants` pour les calculs OPERAT.
- [`backend/services/energy_intensity_service.py`](backend/services/energy_intensity_service.py) — **inchangé sur les valeurs** (EP RE2020 1,9 préservé pour DPE 2026+). Docstring enrichie avec avertissement explicite.

**Audit silencieux des consumers** : `grep` exhaustif des usages de `EP_COEFFICIENTS` et `get_emission_factor` → 0 consumer hors fichiers eux-mêmes + tests. Aucun risque de « mauvais EP utilisé pour OPERAT en silence ».

---

## 3 — Chantier 2 — Année de référence OPERAT

**Fichier modifié** : [`backend/services/operat_trajectory.py`](backend/services/operat_trajectory.py)

- Plage `2000-2060` (trop permissive) **remplacée** par règle Article 3.I :
  - Cas standard (référence) : `[2010 ; 2022]` strict.
  - Cas bâtiment neuf (flag `is_first_full_year_of_operation=True`) : `[2010 ; current_year]`.
  - Cas conso non-référence : `[2010 ; current_year + 1]` (suivi annuel post-référence).
- Message FR doctriné en cas de rejet : cite la période autorisée, le butoir 30/09/2027, et guide vers le flag `is_first_full_year_of_operation`. **Aucun fallback silencieux**.

**Fichier modifié** : [`backend/routes/tertiaire.py`](backend/routes/tertiaire.py)

- `ConsumptionDeclareRequest` enrichi du champ `is_first_full_year_of_operation: bool = False`.
- Endpoint `/api/tertiaire/efa/{efa_id}/consumption/declare` :
  - Renvoie `422 Unprocessable Entity` (au lieu de 400 générique) sur violation Article 3.I.
  - Propage le message FR doctriné du service (cite source légale).

### Curl de validation

```bash
# T1 — Année valide 2019 → 200
curl -s -X POST http://localhost:8001/api/tertiaire/efa/1/consumption/declare \
  -H "Content-Type: application/json" \
  -d '{"year":2019,"kwh_total":500000,"is_reference":true,"source":"factures"}'

# T2 — Année trop ancienne → 422 + message FR
curl -s -X POST http://localhost:8001/api/tertiaire/efa/1/consumption/declare \
  -H "Content-Type: application/json" \
  -d '{"year":2005,"kwh_total":500000,"is_reference":true}'
# Réponse attendue :
# 422 {"code":"VALIDATION","message":"L'annee de reference 2005 doit etre comprise dans la periode autorisee pour OPERAT (2010-2022, Article 3.I de l'arrete 10/04/2020). Pour un batiment neuf dont la 1ere annee pleine d'exploitation est posterieure, declarer explicitement is_first_full_year_of_operation=True. A defaut de declaration avant le 30 septembre 2027, OPERAT applique la 1ere annee pleine d'exploitation par defaut."}

# T4 — Bâtiment neuf 2024 → 200
curl -s -X POST http://localhost:8001/api/tertiaire/efa/1/consumption/declare \
  -H "Content-Type: application/json" \
  -d '{"year":2024,"kwh_total":500000,"is_reference":true,"is_first_full_year_of_operation":true,"source":"factures"}'
```

---

## 4 — Chantier 3 — TRI par typologie

**Fichier modifié** : [`backend/services/tertiaire_modulation_service.py`](backend/services/tertiaire_modulation_service.py)

- `ModulationAction` enrichi du champ `typologie: str = TYPOLOGY_DEFAULT` (UNKNOWN).
- `ModulationResult` enrichi de :
  - `tri_par_typologie: list[dict]` — décomposition (typologie, label_fr, tri_ans, seuil_disproportion_ans, is_disproportionate, source, source_url, actions_count, cout/economie agrégés).
  - `disproportion_globale: bool` — True si au moins une typologie dépasse son seuil Article 11.I.
  - `disproportion_explication: str` — message FR clair listant les typologies disproportionnées (ou indiquant que la décision n'est pas calculable si aucune action n'est typologisée).
- Le seuil hardcodé `tri > 15` (appliqué à tout) est **remplacé** par `get_operat_tri_threshold(typologie)` (30/15/10 selon Article 11.I).
- Compat retrocompat préservée : `tri_moyen_ans` est conservé (utilisé par l'UI existante), enrichi par la décomposition typologique.
- Anti-fallback silencieux : actions sans typologie déclarée → warning + exclusion de la décomposition (la décision de disproportion par typologie n'est pas inventée).

### Curl de validation

```bash
# T1 — Multi-typologie → 3 TRI distincts + decision composite
curl -s -X POST http://localhost:8001/api/tertiaire/efa/1/modulation/simulate \
  -H "Content-Type: application/json" \
  -d '{"contraintes":[{"type":"economique","description":"Multi-typo","actions":[
    {"label":"ITE","cout_eur":200000,"economie_annuelle_kwh":80000,"economie_annuelle_eur":8000,"duree_vie_ans":35,"typologie":"STRUCTURAL_ENVELOPE"},
    {"label":"CVC","cout_eur":60000,"economie_annuelle_kwh":40000,"economie_annuelle_eur":4000,"duree_vie_ans":18,"typologie":"ENERGY_EQUIPMENT"},
    {"label":"GTB","cout_eur":50000,"economie_annuelle_kwh":30000,"economie_annuelle_eur":3000,"duree_vie_ans":12,"typologie":"OPTIMIZATION_SYSTEM"}
  ]}]}'
# Réponse : tri_par_typologie = 3 entrées + disproportion_globale + explication FR
```

---

## 5 — Chantier 4 — Rapatriement PHASE_0BIS

**Fichier copié** : [`docs/base_documentaire/PHASE_0BIS_EXPLORATION_DRIVE.md`](docs/base_documentaire/PHASE_0BIS_EXPLORATION_DRIVE.md) (171 l)

Source : `/Users/amine/projects/promeos-audit-main/docs/base_documentaire/PHASE_0BIS_EXPLORATION_DRIVE.md` (livré 2026-05-23, 60+ docs Drive analysés).

Contenu rapatrié verbatim, aucune modification logique. Permet de garder le contexte complet de la brique dans le repo `promeos-poc`.

---

## 6 — Tests (24 nouveaux + 63 cumul + 22 anti-régression)

### Source-guards G1-G7

📄 [`backend/tests/source_guards/test_conformite_s1_operat_deet_source_guards.py`](backend/tests/source_guards/test_conformite_s1_operat_deet_source_guards.py)

| ID | Vérification | Résultat |
|---|---|---|
| G1 | Constantes OPERAT CO2 séparées d'ADEME (0,064 vs 0,052) | ✅ |
| G2 | Constantes EP OPERAT séparées de RE2020 (2,3 vs 1,9) | ✅ |
| G3 | 4 helpers exposés + fail-closed (KeyError) | ✅ |
| G4 | Validation année référence (plage 2010-2022 + flag is_first_full_year + butoir 2027-09-30) | ✅ |
| G5 | 3 typologies TRI avec seuils 30/15/10 (Article 11.I) | ✅ |
| G6 | `ModulationAction.typologie` + `ModulationResult.tri_par_typologie/disproportion_*` + import canonique | ✅ |
| G7 | Aucun mélange silencieux : 3 fichiers de constantes se référencent mutuellement | ✅ |

### Tests unitaires constantes

📄 [`backend/tests/test_operat_constants_separation.py`](backend/tests/test_operat_constants_separation.py) — **6/6 ✅**

### Tests endpoint année référence

📄 [`backend/tests/test_operat_year_validation_endpoint.py`](backend/tests/test_operat_year_validation_endpoint.py) — **6/6 ✅**

- T1 année valide 2019 → 200
- T2 année trop ancienne 2005 → 422 + message FR cite période autorisée
- T3 année 2024 sans flag → 422 + message FR guide vers le flag
- T4 année 2024 avec `is_first_full_year=True` → 200
- T5 année future avec flag → 422
- T6 conso non-référence 2025 → 200 (plage large préservée)

### Tests TRI par typologie

📄 [`backend/tests/test_tertiaire_modulation_typology.py`](backend/tests/test_tertiaire_modulation_typology.py) — **5/5 ✅**

- T1 portefeuille multi-typologie → 3 TRI distincts
- T2 chaque entrée a label_fr + source + source_url + seuil
- T3 `disproportion_globale=True` si typologie dépasse son seuil
- T4 action sans typologie → warning + pas dans décomposition
- T5 typologie inconnue → fallback UNKNOWN + warning

### Anti-régression

- `tests/test_operat_normalization.py` + `tests/test_compliance_evidence.py` : **22/22 ✅** (toutes les déclarations existantes utilisent années dans la plage 2010-2022, validées).
- Cumul source-guards `-k "conformite or operat or tertiaire or compliance or bacs or aper"` : **63/63 ✅**.

**Total nouveaux + cumul** : 24 nouveaux + 22 anti-régression + 63 source-guards cumul = **109+ tests verts**.

---

## 7 — Critères d'acceptation brief (8/8 ✅)

| # | Critère | État |
|---|---|---|
| 1 | D1/D2/D4/D5 documentées officiellement | ✅ Cross-check Légifrance verbatim |
| 2 | Aucun correctif non sourcé | ✅ Chaque constante a `source / source_url / consolidation_date` |
| 3 | OPERAT séparé de ADEME/RE2020 | ✅ G1 + G2 + G7 |
| 4 | Année de référence validée côté serveur | ✅ G4 + 6 tests endpoint |
| 5 | TRI par typologie implémenté | ✅ G5 + G6 + 5 tests typologie |
| 6 | Hub `/conformite` inchangé | ✅ Aucune modification UI ce sprint |
| 7 | Aucun nouveau menu | ✅ Aucune modification sidebar |
| 8 | Tests verts + audit livré | ✅ 109+ tests + audit postfix ci-présent |

---

## 8 — Décisions clés / non-décisions

1. **Cross-check Légifrance fait avant tout code** — règle non négociable du brief respectée. Tous les chantiers procèdent uniquement après confirmation officielle.
2. **EP OPERAT scope strict Article 16** — la valeur 2,3 n'est appliquée que dans le contexte de l'Article 16 (changement de source énergétique). Pas d'application aveugle aux calculs RE2020 / DPE qui restent à 1,9.
3. **Fail-closed sur vecteur/typologie inconnu** — pas de fallback silencieux à une valeur par défaut. KeyError remonté pour forcer l'appelant à expliciter.
4. **Conso non-référence : plage large [2010 ; current_year+1]** — décision pragmatique pour ne pas casser le suivi annuel OPERAT post-référence (les conso 2023-2025 doivent pouvoir être saisies). Seule la `is_reference=True` est strictement encadrée à [2010 ; 2022].
5. **`is_first_full_year_of_operation` flag explicite** — le cas bâtiment neuf nécessite une déclaration utilisateur, pas une inférence (qui pourrait masquer une erreur de saisie d'année).
6. **`disproportion_globale` = OR sur typologies** — décision conservative : si **une seule** typologie dépasse son seuil, la disproportion est invocable globalement. L'arrêté ne précise pas de règle composite plus fine — c'est au cas par cas du dossier technique OPERAT.
7. **Pas de migration de données existantes** — les actions historiques sans `typologie` héritent de `UNKNOWN` et sont exclues de la décomposition. Pas de réécriture automatique (anti-fallback). Le saisisseur peut renseigner la typologie au prochain update.
8. **Helpers `get_*` retournent valeurs brutes, pas dicts complets** — l'appelant qui veut la source/URL accède au dict `EMISSION_FACTORS_OPERAT["ELEC"]` directement. Helpers minimaux pour calcul, dicts complets pour reporting.

---

## 9 — Dette résiduelle

| # | Item | Statut |
|---|---|---|
| 1 | Migration des actions existantes : ajouter `typologie` au backend du DataModel `ModulationAction` persistée (si stockée en DB) | Si stockée → P1 micro-migration. Si calculée à la volée → rien à faire. À vérifier au sprint S2 |
| 2 | Audit endpoint `/api/operat/export` : truth contract granulaire `{unit, source, formula_ref, period, confidence}` par ligne CSV | P2 (S3) — séparé brief |
| 3 | UI conformité : exposer la décomposition `tri_par_typologie` dans `ModulationDrawer` (composant existant) | P1 (S2) — sans complexification UX |
| 4 | Tests endpoint `/api/tertiaire/modulation/simulate` (smoke + IDOR si exposée) | P2 |
| 5 | Ingestion drafts `DT_OPERAT_2026` (1 011 l) en `backend/regops/rules/tertiaire_operat.py` | P3 (S4) — séparé brief |

**Aucune dette critique. 4/4 divergences P0 OPERAT résolues.**

---

## Verdict

🟢 **GO MERGE** — Sprint S1 P0 OPERAT/DEET livré :

- **Cross-check Légifrance officiel** sur 4 divergences D1/D2/D4/D5 (verbatim Annexe VII + Article 3.I + Article 11.I).
- **3 fichiers de constantes coexistent proprement** : `emission_factors.py` (ADEME), `energy_intensity_service.py` (RE2020), `operat_constants.py` (OPERAT/DEET). Mutuelle référence anti-confusion.
- **Validation année référence server-side** avec message FR doctriné + flag `is_first_full_year_of_operation` explicite + 422 sur violation.
- **TRI par typologie** Article 11.I (30/15/10) avec décision composite + warnings explicites + anti-fallback.
- **PHASE_0BIS rapatrié** dans le repo poc.
- **24 nouveaux tests** + 63 source-guards cumul + 22 anti-régression = 109+ tests verts.
- **0 modification UI** ce sprint (le brief explicite « pas de big bang UX, pas de nouveau menu » est respecté).
- **0 fallback silencieux**, **0 mélange ADEME/OPERAT/RE2020**.

La brique Conformité est désormais conforme OPERAT/DEET sur ses fondations réglementaires. Le sprint S2 P1 (simplicité métier — réorg tabs ConformitePage + NextBestAction 1-clic) peut démarrer après merge.
