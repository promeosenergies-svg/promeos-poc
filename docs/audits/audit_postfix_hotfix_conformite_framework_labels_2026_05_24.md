# Audit postfix — Hotfix labels frameworks réglementaires (2026-05-25)

**Branche** : `claude/hotfix-conformite-framework-labels`
**Base** : `claude/refonte-sol2` (post merge #296+#297+#298+#299+#300)
**Verdict** : 🟢 **GO** — 11/11 contrôles hotfix verts (1 endpoint 500 hors scope sur `/api/kb/apply`)

## Contexte du bug

Capture utilisateur (avant fix) : **3 lignes APER** dans le bloc « Score conformité » de `/conformite` alors qu'il n'y a qu'une obligation APER.

```
Décret Tertiaire ──────────── 70
BACS ──────────────────────── 70
APER ──────────  50        ← vrai APER
APER                    0   ← en fait audit_sme (étiqueté APER par bug FE)
APER                    0   ← en fait solar_toiture (étiqueté APER par bug FE)
```

### Cause racine

[ComplianceScoreHeader.jsx:94-99](../../frontend/src/components/conformite/ComplianceScoreHeader.jsx#L94-L99) (pré-hotfix) utilisait un mapping ternaire avec **fallback métier faux** :

```js
const fwCode =
  fw.framework === 'tertiaire_operat' ? 'Décret Tertiaire'
  : fw.framework === 'bacs' ? 'BACS'
  : 'APER';   // ← tout framework non-DT/non-BACS étiqueté "APER"
```

Le backend `_compute_v2_adaptive()` ([compliance_score_service.py:739-842](../../backend/services/compliance_score_service.py#L739-L842)) (Sprint C-1 V2) émet jusqu'à 7 frameworks : `tertiaire_operat`, `bacs`, `aper`, `audit_sme`, `iso_50001`, `solar_toiture`, `beges`. Le FE n'en mappait que 3 — les 4 autres devenaient "APER".

**Doctrine §8.1 violée** : zero business logic frontend. Le mapping code→label est métier réglementaire et doit venir du backend.

## Chantiers livrés (6/6)

| # | Chantier | Fichier(s) clé(s) |
|---|---|---|
| C1 | Backend : `FRAMEWORK_LABELS_FR` (SoT) + `get_framework_label_fr()` + `label_fr` injecté dans `FrameworkScore.to_dict()` + `breakdown_avg_labeled[]` ajouté au portfolio | [compliance_score_service.py:73-105, 113-127, 405-413](../../backend/services/compliance_score_service.py) |
| C2 | Frontend : suppression fallback `: 'APER'`, ajout `formatFrameworkCode()` neutre + utilisation `fw.label_fr` | [ComplianceScoreHeader.jsx](../../frontend/src/components/conformite/ComplianceScoreHeader.jsx) |
| C3 | Source-guard test interdisant pattern `: 'APER'` + vérification SoT backend exhaustive (7 frameworks) | [conformite_framework_labels_hotfix.test.js](../../frontend/src/__tests__/source_guards/conformite_framework_labels_hotfix.test.js) — 7 tests ✅ |
| C4 | Tests backend (`label_fr` exhaustif pour les 7 frameworks + fallback code brut pour inconnu + portfolio + endpoint live) | [test_compliance_framework_labels_hotfix.py](../../backend/tests/test_compliance_framework_labels_hotfix.py) — 16 tests ✅ |
| C5 | Tests frontend (render Audit SMÉ / Solarisation toiture / ISO 50001 / BEGES + APER unique + fallback legacy) | [ComplianceScoreHeader_framework_labels.test.jsx](../../frontend/src/components/conformite/__tests__/ComplianceScoreHeader_framework_labels.test.jsx) — 9 tests ✅ |
| C6 | Audit Playwright postfix (ce document + script) | [audit_postfix_hotfix_framework_labels.mjs](../../scripts/audit_postfix_hotfix_framework_labels.mjs) — 11/11 verts hotfix |

## Mapping FR canonique (SoT backend)

```python
FRAMEWORK_LABELS_FR: dict[str, str] = {
    "tertiaire_operat": "Décret Tertiaire",
    "bacs": "BACS",
    "aper": "APER",
    "audit_sme": "Audit SMÉ",
    "iso_50001": "ISO 50001",
    "solar_toiture": "Solarisation toiture",
    "beges": "BEGES",
}
```

Frameworks inconnus → `formatFrameworkCode(code)` côté FE (humanisation neutre : `new_obligation_2027` → `New Obligation 2027`). **Jamais de fallback "APER"**.

## Avant / Après — capture HELIOS portfolio

### Backend `/api/compliance/portfolio/score` (avant)
```json
{
  "breakdown_avg": {
    "tertiaire_operat": 70.0,
    "bacs": 70.0,
    "aper": 50.0,
    "audit_sme": 0.0,
    "solar_toiture": 0.0
  }
}
```

### Backend (après hotfix — rétro-compat preservée)
```json
{
  "breakdown_avg": { ... identique ... },
  "breakdown_avg_labeled": [
    { "framework": "tertiaire_operat", "label_fr": "Décret Tertiaire", "score": 70.0 },
    { "framework": "bacs",             "label_fr": "BACS",             "score": 70.0 },
    { "framework": "aper",             "label_fr": "APER",             "score": 50.0 },
    { "framework": "audit_sme",        "label_fr": "Audit SMÉ",        "score": 0.0  },
    { "framework": "solar_toiture",    "label_fr": "Solarisation toiture", "score": 0.0  }
  ]
}
```

### Frontend rendu (après hotfix)
```
Décret Tertiaire ──────────── 70
BACS ──────────────────────── 70
APER ──────────  50
Audit SMÉ                  0
Solarisation toiture       0
```

APER apparaît **une seule fois**. Plus aucune ambiguïté pour le DAF.

## Tests

| Suite | Avant | Après | Δ |
|---|---|---|---|
| Source-guard `conformite_framework_labels_hotfix.test.js` (NEW) | — | 7 ✓ | +7 |
| BE `test_compliance_framework_labels_hotfix.py` (NEW) | — | 16 ✓ | +16 |
| FE `ComplianceScoreHeader_framework_labels.test.jsx` (NEW) | — | 9 ✓ | +9 |
| **Total nouveaux verts** | — | **32** | **+32** |
| Suite FE complète (non-régression) | 5302 ✓ + 3 fails | 5325 ✓ + 3 fails | 0 régression (les 3 fails sont pré-existants : CompliancePage.jsx not found, taxes_mismatch CSPE) |
| Suite BE billing+cockpit+compliance hotfix | — | **595 ✓** + 7 pré-existants (`test_billing_v68` PDF/shadow) | 0 régression |

## Audit Playwright postfix (11/11 verts hotfix)

```
✅ Backend /api/compliance/portfolio/score → 200
✅ portfolio expose breakdown_avg_labeled (liste typée)
✅ chaque breakdown_avg_labeled.label_fr est non-vide (0 manquant)
✅ audit_sme → label_fr="Audit SMÉ"
✅ solar_toiture → label_fr="Solarisation toiture"
✅ Backend /api/compliance/sites/1/score → 200
✅ chaque site breakdown[].label_fr est non-vide (0 manquant sur 5)
✅ 5 lignes breakdown affichées (>= 3 attendu)
✅ audit_sme rendu : "Audit SMÉ"
✅ solar_toiture rendu : "Solarisation toiture"
✅ APER apparaît au plus 1 fois (compté 1)
⚠️  1 endpoint 500 hors scope : /api/kb/apply (problème pré-existant KB, sans lien avec le hotfix)
```

## Critères d'acceptation (8/8 ✅)

| # | Critère | État |
|---|---|---|
| 1 | Plus aucune répétition APER injustifiée | ✅ |
| 2 | audit_sme affiche "Audit SMÉ" | ✅ |
| 3 | solar_toiture affiche "Solarisation toiture" | ✅ |
| 4 | iso_50001 affiche "ISO 50001" | ✅ (testé render FE) |
| 5 | beges futur est couvert | ✅ (FRAMEWORK_LABELS_FR + tests FE/BE) |
| 6 | Aucun mapping métier dur dans ComplianceScoreHeader | ✅ (source-guard 7/7) |
| 7 | Tests nouveaux verts | ✅ (32 tests) |
| 8 | Non-régression Conformité, Cockpit, Patrimoine | ✅ (FE 5325 + BE 595 verts, 0 régression hotfix) |

## Doctrine respectée

- ✅ Zero business logic frontend (§8.1) : le mapping est dans le backend, le FE ne fait que rendre `fw.label_fr`
- ✅ Aucun fallback métier faux (formatFrameworkCode humanise sans introduire de label réglementaire)
- ✅ Aucun nouveau menu, aucun écran fantôme
- ✅ Français clair (Audit SMÉ avec accent, Solarisation toiture, ISO 50001)
- ✅ Tests obligatoires (16 BE + 9 FE render + 7 source-guard)

## Verdict

🟢 **GO** — le bug visuel signalé (3 lignes APER) est intégralement corrigé. Le mapping est maintenant centralisé backend, futur-proof pour BEGES et tout nouveau framework v2 (il suffit d'ajouter une ligne à `FRAMEWORK_LABELS_FR` sans toucher le FE).
