# PROMEOS — Résumé Sprint `fix/audit-crit-ux-sources`

**Date :** 27 mars 2026
**Branche :** `fix/audit-crit-ux-sources` (4 commits atomiques)
**Tests :** 143/143 fichiers, 3589/3589 tests verts, 0 échec

---

## Contexte

Audit UX/Architecture/Logique Métier du 27 mars 2026 — score initial **74.6/100**.
3 bugs critiques + 1 erreur de source dans le glossaire identifiés.
Ce sprint corrige les 4 et ajoute des gardes automatiques anti-régression.

---

## Commits

### Commit 1 — `7513f8b` — Accents labels conformité

**Fichier :** `frontend/src/domain/compliance/complianceLabels.fr.js`

| Label | Avant | Après |
|-------|-------|-------|
| `evaluation_incomplete` | Evaluation incomplete | **Évaluation incomplète** |
| `preparation_en_cours` | Preparation en cours | **Préparation en cours** |
| `classe_a_verifier` | Classe systeme a verifier | **Classe système à vérifier** |
| `preuves_non_tracables` | Preuves non tracables | **Preuves non traçables** |

+ 5 avertissements `CONFORMITE_WARNINGS` corrigés (réel, référence, réduction, validée, conformité, réglementaire, dépôt, système, renseignée).

---

### Commit 2 — `af12cbc` — Objectif DT -40% cohérent

**Fichiers :** `CommandCenter.jsx`, `Cockpit.jsx`

| Fichier | Avant (fallback) | Après |
|---------|-----------------|-------|
| CommandCenter.jsx (×3) | `objectifPremierJalonPct ?? -25` | `?? -40` |
| Cockpit.jsx (×1) | `objectifPremierJalonPct ?? -25` | `?? -40` |

**Source :** Décret n°2019-771 — jalons DT : -25% (2026), **-40% (2030)**, -50% (2040), -60% (2050).
Le champ `objectifPremierJalonPct` est le jalon 2030, pas 2026.

---

### Commit 3 — `c47682e` — ErrorState prop corrigée

**Fichier :** `frontend/src/pages/cockpit/CockpitHero.jsx`

```jsx
// AVANT — prop ignorée silencieusement :
<ErrorState title="..." description="Impossible de charger..." />

// APRÈS — message affiché correctement :
<ErrorState title="..." message="Impossible de charger..." />
```

`ErrorState` attend `{ title, message }`, pas `{ title, description }`.

---

### Commit 4 — `cccfce3` — Sources réglementaires corrigées + gardes

**Fichiers modifiés :** 9 fichiers (glossaire, helpers, tests)

#### Glossaire (`glossary.js`)

| Terme | Avant | Après | Source |
|-------|-------|-------|--------|
| CO₂ électricité | 0,057 kgCO₂/kWh | **0,052 kgCO₂/kWh** | ADEME Base Empreinte V23.6 |
| Accise / CSPE | 22,50 EUR/MWh | **26,58 EUR/MWh** (C4 pro) | Code des impositions, arrêté fév 2026 |
| ARENH | Prix fixe 42 €/MWh | + **Dispositif terminé 31/12/2025**, remplacé par VNU | Loi Énergie-Climat 2019 |
| TURPE | "TURPE 7 (depuis fév. 2025)" | **"TURPE 7 (depuis 1er août 2025, CRE n°2025-78)"** | CRE délibération n°2025-78 |
| TVA | 5,5% abo + 20% conso | **CTA 5,5%, abo+conso 20%** (depuis août 2025) | LFI 2025 |

#### Prix fallback (5 fichiers)

| Fichier | Avant | Après |
|---------|-------|-------|
| `consumption/helpers.js` | `DEFAULT_PRICE_EUR_KWH = 0.18` | **0.068** |
| `consumption/OverviewRow.jsx` | `EUR_FACTOR = 0.18` | **0.068** |
| `consumption/PortfolioPanel.jsx` | `_EUR_FACTOR = 0.18` | **0.068** |
| `MonitoringPage.jsx` | `price = 0.18` | **0.068** |

**Alignement backend :** le backend utilise `0.068 EUR/kWh` (spot moyen 30j bridgé).

#### Source Guard Test (`sourceGuards.test.js`) — NOUVEAU

8 assertions permanentes qui empêchent toute régression :

| Guard | Vérifie |
|-------|---------|
| CO₂ élec = 0.052 | Glossaire contient 0,052, pas 0,057 ni 0,0569 |
| CO₂ gaz = 0.227 | Glossaire contient 0,227 |
| Backend CO₂ cohérent | `emission_factors.py` contient 0.052 et 0.227 |
| Accise 26.58 | Glossaire contient 26,58, pas 22,50 |
| TURPE 7 | Glossaire mentionne "TURPE 7" |
| ARENH terminé | Glossaire mentionne fin/terminé |
| Pas de 0.18 | Scan récursif de tout `frontend/src/` — aucun `= 0.18` en production |

---

## Tableau de conformité final

| Constante | Backend | Frontend | Valeur canonique | Source | Statut |
|-----------|---------|----------|-----------------|--------|--------|
| CO₂ élec | 0.052 | 0.052 | 0.052 kgCO₂/kWh | ADEME Base Empreinte V23.6 | ✅ |
| CO₂ gaz | 0.227 | 0.227 | 0.227 kgCO₂/kWh | ADEME Base Empreinte V23.6 | ✅ |
| Prix fallback élec | 0.068 | 0.068 | 0.068 EUR/kWh | Spot 30j moyen bridgé | ✅ |
| CSPE C4 | — | 26.58 | 26.58 EUR/MWh | Arrêté fév 2026 | ✅ |
| TURPE version | — | TURPE 7 | CRE n°2025-78 | Depuis 1er août 2025 | ✅ |
| DT jalon 2030 | -40% | -40% | -40% | Décret n°2019-771 | ✅ |
| ARENH | — | Terminé | Fin 31/12/2025 | LFI 2023 | ✅ |

---

## Definition of Done

- [x] **Accents** : tous les labels FR dans complianceLabels.fr.js ont des accents corrects
- [x] **Objectif DT** : -40% partout pour objectifPremierJalonPct (pas de -25%)
- [x] **ErrorState** : `message` (pas `description`) dans CockpitHero
- [x] **CO₂ = 0.052** dans le glossaire (pas 0.057, pas 0.0569)
- [x] **CSPE = 26.58** EUR/MWh pour C4 (pas 22.50)
- [x] **TURPE 7** mentionné dans le glossaire (pas TURPE 6)
- [x] **0.18 absent** du code de production frontend
- [x] **Source guard test** (8 assertions anti-régression)
- [x] **0 régression** : 143/143 fichiers, 3589/3589 tests verts
- [x] **4 commits atomiques** sur la branche `fix/audit-crit-ux-sources`
