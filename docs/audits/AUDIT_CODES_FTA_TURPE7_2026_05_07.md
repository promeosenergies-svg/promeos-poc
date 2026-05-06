# Audit Codes FTA canoniques CRE TURPE 7 — Phase D-2 hotfix Tier 1 P0.2

**Date** : 2026-05-07
**Source** : `regulatory-expert` agent SDK (Pilier 6 ADR-016 audit deep)
**Périmètre** : correction nomenclature `code_fta` Phase D-1 (BT_HCH_PRO inventé)

## Verdict cardinal

Codes utilisés dans le commit Phase D-1 PROMEOS (`models/patrimoine.py:316` + `tests/test_phase_d1_patrimoine_p1_fixes.py:62`) :
- `BT_HCH_PRO` ❌ **NON CANONIQUE** (mélange poste horosaisonnier `HCH` + label `PRO`)
- `BT_BASE_PRO` ❌ **NON CANONIQUE** (`BASE` est une option fournisseur, pas une FTA d'acheminement)
- `BT_PRO_LU` ❌ **NON CANONIQUE** (approchant `BTINFLU`/`BTSUPLU` mais syntaxe non conforme CRE)
- `HTA_LU_BASE_4P` ❌ **NON CANONIQUE** (forme inventée — vrai code = `HTALU5`)

## Nomenclature canonique CRE TURPE 7

### Préfixes domaine de tension

| Préfixe | Description | Segment TURPE |
| --- | --- | --- |
| `BTINF` | Basse Tension Inférieure (≤ 36 kVA) | C5 |
| `BTSUP` | Basse Tension Supérieure (> 36 kVA) | C4 |
| `HTA` | Haute Tension A (1-50 kV) | C3 (et C2 pour gros HTA) |
| `HTB` | Haute Tension B (≥ 50 kV) | C1 (transport RTE) |

### Suffixes durée d'utilisation annuelle

| Suffixe | Description |
| --- | --- |
| `CU` | Courte Utilisation (faible nb d'heures pleines / an) |
| `MU` | Moyenne Utilisation (BT uniquement, intermédiaire) |
| `LU` | Longue Utilisation (forte régularité, profil industriel) |

### Table mapping cardinale (à figer Phase D-3 par parsing PDF délibération 2025-78)

| code_fta | segment_turpe | domaine_tension | nb_postes | usage_typique | confidence |
| --- | --- | --- | --- | --- | --- |
| `BTINFCU4` | C5 | BT ≤ 36 kVA | 4 (HPH/HCH/HPE/HCE) | Petit pro / résidentiel courte util. | medium |
| `BTINFMU4` | C5 | BT ≤ 36 kVA | 4 | Pro moyenne util. ≤ 36 kVA | medium |
| `BTINFLU` | C5 | BT ≤ 36 kVA | option | Longue util. ≤ 36 kVA (rare) | low |
| `BTSUPCU` | C4 | BT > 36 kVA | 4 ou 5 | Tertiaire moyen courte util. | medium |
| `BTSUPLU` | C4 | BT > 36 kVA | 4 ou 5 | Tertiaire moyen longue util. | medium |
| `HTACU5` | C3 / C2 | HTA (1-50 kV) | 5 (PTE/HPH/HCH/HPE/HCE) | Industriel courte util. | medium |
| `HTALU5` | C3 / C2 | HTA (1-50 kV) | 5 | Industriel longue util. | medium |

## Décision Phase D-2.2

**Stratégie cardinale** : NE PAS encore figer un Enum exhaustif (confidence des suffixes 4/5 postes = medium) → **regex permissive Phase D-1bis maintenue** + **mise à jour exemples canoniques** dans commentaires + tests.

Plan tactique :
1. Remplacer **dans les exemples / commentaires / tests** `BT_HCH_PRO` → `BTINFCU4` (canonique)
2. Conserver le validator `code_fta` regex `^(C[1-5]|BTINF|BTSUP|BT|HTA|HTB)` qui couvre les vrais codes
3. Documenter dans `models/patrimoine.py` que l'Enum exhaustif sera figé Phase D-3 post-parsing PDF délibération 2025-78
4. Ajouter constante `CANONICAL_FTA_CODES_TURPE_7` dans `backend/doctrine/constants.py` (ou équivalent) avec liste medium-confidence

## Impact sur Sprint D1-B (commit `9bc4193a`)

Le validator C64 `_CODE_FTA_PREFIX_PATTERN = re.compile(r"^(C[1-5]|BTINF|BTSUP|BT|HTA|HTB)", re.IGNORECASE)` **valide déjà correctement** les vrais codes canoniques `BTINFCU4`, `BTSUPCU`, `HTACU5` (cf. tests Phase D-1bis verts).

→ **Pas de breaking change** sur Sprint D1-B. Le fix Phase D-2.2 = mise à jour exemples + tests + documentation.

## Sources cardinales

- CRE.fr — recherche nomenclature CU/MU/LU TURPE : https://www.cre.fr/recherche?q=courte+utilisation+longue+utilisation+TURPE
- CRE.fr — page délibération TURPE 7 HTA-BT (annexes tarifaires non parsées Phase D-2) : https://www.cre.fr/documents/deliberations/tarif-dutilisation-des-reseaux-publics-de-distribution-delectricite-turpe-7-hta-bt-1.html

## À figer Phase D-3 (~30 min)

- Parser PDF délibération 2025-78 (4,29 MB) avec `pdfplumber` (pattern OPERAT annexes I/II Sprint Patrimoine v1)
- Lister exhaustivement les codes FTA + Enum strict `FtaCodeTurpe7` dans `models/enums.py`
- Mapping exhaustif `code_fta` ⟺ tarif applicable dans `tarifs_reglementaires.yaml`

**Confidence verdict global** : high sur invalidation des codes Phase D-1 (BT_HCH_PRO inventé) ; medium sur la liste canonique TURPE 7 (suffixes 4/5 à confirmer PDF).
