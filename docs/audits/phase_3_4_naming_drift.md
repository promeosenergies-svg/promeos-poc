# Phase 3.4 — Naming drift `KpiTriptychCard` → `HubKpiCard`

> Trade-off documenté · pas une violation doctrinale.
> Date : 2026-05-11 · Commit Phase 3.4 : `0018f45e` · Audit HARD STOP en cours.

## Constat

La page `frontend/src/pages/CockpitJour.jsx` (Phase 3.4) définit un composant
**local** `KpiTriptychCard` qui rend chaque carte du triptyque KPI (slot
`<HubPage.KpiTriptych>`). Le nom canonique cible du Design System (cf
`PROMEOS_DESIGN_SYSTEM_TECHNICAL_SPEC.md`) est `KPISol` côté spec et
**`HubKpiCard`** côté primitif L11 (alignement namespace `grammar/hub/`).

## Décision

`KpiTriptychCard` est **un nom temporaire volontairement local**, conservé
tant que le composant n'est pas extrait dans `frontend/src/components/grammar/hub/`.
L'extraction est l'objet de la **Phase F** du HARD STOP (cf
`docs/audits/phase_3_4_decision_hubkpicard.md`). À l'extraction, le composant
sera renommé `HubKpiCard` (nom Design System exécutable, déjà attendu par les
source-guards CI futurs et par les 5 hubs Phase 3.5).

## Rationnel

1. **Anti-prématuration** — ADR-021 stipule explicitement « KpiTriptychCard
   inline (pas dans `grammar/hub/`) tant que la 2nde Hub Page n'est pas livrée :
   extraction prévue Phase 3.5 quand un second consommateur existera ». Le
   HARD STOP avance cette extraction à la Phase F du présent audit (économie
   réelle ×3 ROI vs après-Phase 3.5), mais le nom reste local jusqu'au move.
2. **Données data-component cohérentes** — le source-guard `SG_HUB_L11_01`
   vérifie l'import de `HubPage`, `SolHeroPremiumNight`, `ChartFrame`,
   `HubHighlight`, `HubPageFooter` depuis `components/grammar`. Il ne mentionne
   PAS `HubKpiCard` (qui n'existe pas encore). Le `data-component="KpiTriptychCard"`
   sert seulement aux captures Playwright Phase A — il sera renommé en
   `HubKpiCard` à l'extraction.
3. **Pas de duplication terminologique** — `KPISol` est le nom **conceptuel
   Design System** (spec doctrine §7.2), `HubKpiCard` est le nom **primitif
   exécutable** (namespace `grammar/hub/`). `KpiTriptychCard` est le nom
   **transitoire local** d'une factorisation de page non-encore extraite.
   Trois noms = trois calques de maturité : spec → primitif → local.

## Impact captures Phase A

Les captures Playwright Phase A utilisent `[data-component="KpiTriptychCard"]`
pour extraire les 3 cartes KPI. Après Phase F (extraction), le sélecteur
deviendra `[data-component="HubKpiCard"]` et un mass-replace traversera :

- `tools/playwright/phase_3_4_capture.mjs`
- `frontend/tests/visual/phase_3_4_before_after.spec.js`
- éventuels source-guards Vitest ajoutés Phase F

## Validation

- [x] ADR-021 mentionne l'extraction prévue Phase 3.5 (devancée par HARD STOP F)
- [x] `KpiTriptychCard` est encapsulé dans `CockpitJour.jsx` (zéro import externe)
- [x] Le pattern Playwright (`data-component`) sert les captures audit sans
       imposer un nom définitif côté Design System
- [ ] Renommage `HubKpiCard` à exécuter Phase F si décision GO extraction

## Trade-off accepté

Risque : un développeur futur lit `KpiTriptychCard` et croit que c'est le nom
canonique. Mitigation : ce document + commentaire JSDoc top-of-component
(`Inline (pas dans grammar/hub/) tant que la 2nde Hub Page n'est pas livrée :
extraction prévue Phase 3.5 quand un second consommateur existera.`) +
extraction Phase F qui efface définitivement le nom temporaire.

Pas une violation doctrinale — un calque de maturité explicité.
