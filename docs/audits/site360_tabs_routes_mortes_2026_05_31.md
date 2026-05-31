# PROMEOS — Audit Site360 P0 · onglets vides / routes mortes

**Date** : 2026-05-31
**Branche** : `claude/site360-p0-tabs-routes-mortes`
**Base** : `claude/refonte-sol2` tip `052e078f` (post-P3.2)
**Périmètre** : page Site360 (`/sites/:id`) — vue 360° d'un site
patrimoine (ex. Siège HELIOS Paris).

---

## 1. Onglets audités

9 onglets visibles dans la TabBar Site360 : Résumé · Consommation ·
Analytics → **Analyse énergétique** · Factures · Réconciliation ·
Conformité · Actions · Puissance · Usages.

| # | Onglet | Composant rendu | Données réelles | État après P0 |
|---|---|---|---|---|
| 1 | Résumé | `TabResume` (inline `Site360.jsx:133-568`) | KPIs + anomalies + intelligence KB | ✅ OK |
| 2 | Consommation | `TabConsoSite` | EMS API courbe 30j + KPIs | ✅ OK |
| 3 | **Analyse énergétique** *(renommé)* | `TabAnalytics` | Load profile + signature + recommandations | ✅ OK |
| 4 | Factures | `SiteContractsSummary` + `SiteBillingMini` | Contrats + factures mini | ✅ OK |
| 5 | Réconciliation | `TabReconciliation` (inline) | Score + checks + fixes | ✅ OK |
| 6 | Conformité | `TabConformite` (inline) | KB items + BACS + Décret Tertiaire | ✅ OK |
| 7 | Actions | `TabActionsSite` | Liste actions site | ✅ OK |
| 8 | Puissance | `TabPuissance` | PowerPanel + FlexScore + NEBCO | ✅ OK |
| 9 | Usages | `MiniSignaturePanel` (inline) | Signature énergétique mini | ✅ OK |

**Verdict** : 9/9 onglets ont des composants réels et des données. **Aucun
onglet vraiment vide ou mort.** Le problème observé venait du jargon de
label « Analytics » et de routes mortes côté CTA.

---

## 2. Routes mortes détectées

| Cas | Localisation | Route morte | Route canonique | Statut |
|---|---|---|---|---|
| Quick-link « Radar contrats » (TabResume) | `Site360.jsx:441` | `/achat-assistant` | `/achat-energie` | ✅ Corrigé |
| CTA « Créer scénario d'achat » (TabFactures) | `Site360.jsx:2170` | `/achat-assistant?site_id=…` | `/achat-energie?site_id=…` | ✅ Corrigé |

**Total** : 1 route fantôme `/achat-assistant` × 2 occurrences. Aucune
autre route morte ni `href="#"` détectée.

---

## 3. Onglets masqués ou redirigés

**Aucun masquage P0** — les 9 onglets sont opérationnels. La registry
prévoit le `status: 'hidden'` pour usage futur (ex. Réconciliation si
module débranché), mais à l'état actuel **tous sont `status: 'enabled'`**.

Le brief mentionnait « afficher uniquement si module raccordé, sinon
masquer » pour Réconciliation : module réel `TabReconciliation` confirmé,
pas de masquage nécessaire.

---

## 4. Corrections réalisées

### 4.1 Registry canonique (NEW)

[frontend/src/pages/site360/site360TabsRegistry.js](frontend/src/pages/site360/site360TabsRegistry.js) — source de
vérité unique avec contrat enrichi par tab :

```
{
  id, label, status, renderMode,
  targetRoute?, emptyState?, testId
}
```

+ table `SITE360_CANONICAL_ROUTES` qui centralise les routes
applicatives (consommation / monitoring / factures / achatEnergie /
conformite / actionsCenter / usages / patrimoine / kb / regops).

### 4.2 Site360.jsx — branchement registry

- Import `getEnabledSite360Tabs` + `SITE360_CANONICAL_ROUTES`.
- `const TABS = [...]` codé en dur **remplacé** par `getEnabledSite360Tabs().map(...)`.
- `label: 'Analytics'` → `label: 'Analyse énergétique'` (via registry).
- `navigate('/achat-assistant?...')` → `navigate(\`${SITE360_CANONICAL_ROUTES.achatEnergie}?...\`)`.
- `to: 'achat-assistant'` → `to: 'achat-energie'` (TabResume quick-link).
- `Evaluation RegOps` → `Évaluation RegOps` (accent canonique).
- `navigate(\`/regops/\${site.id}\`)` → `navigate(\`${SITE360_CANONICAL_ROUTES.regops}/${site.id}\`)`.

### 4.3 Hors scope (déjà OK)

- Boutons top « Évaluer BACS » + « Compléter les données » → modals
  internes `BacsWizard` / `IntakeWizard` (pas de route → pas de risque
  404).
- 9 panels ont déjà des composants réels avec données via les APIs
  existantes (`/api/energy/*`, `/api/monitoring/*`, `/api/bill-intel/*`).

---

## 5. Tests

### 5.1 Vitest (22/22 GREEN)

[`frontend/src/__tests__/Site360Tabs.test.jsx`](frontend/src/__tests__/Site360Tabs.test.jsx) :

- Registry expose 9 onglets dans l'ordre attendu.
- Chaque tab respecte le contrat (id/label/status/renderMode/testId).
- Aucun label dans la liste interdite (`Analytics`, `TODO`, `Coming soon`, …).
- L'analytics est libellé `Analyse énergétique`.
- Chaque tab visible a un `emptyState` FR métier non vide.
- Aucune route canonique ne vaut `#` / `undefined`.
- **Chaque route canonique existe dans App.jsx** (test segments nested).
- La route morte `/achat-assistant` est bannie.
- Site360.jsx importe la registry et n'expose plus le jargon
  « Analytics » ni « Evaluation RegOps » sans accent.

### 5.2 Source-guards Python (8/8 GREEN)

[`backend/tests/source_guards/test_site360_no_dead_tabs_source_guard.py`](backend/tests/source_guards/test_site360_no_dead_tabs_source_guard.py)
verrouille :

- `label: 'Analytics'` interdit dans la registry.
- `achat-assistant` interdit partout dans Site360.
- JSX `>Evaluation RegOps<` sans accent interdit.
- `href="#"` interdit.
- Placeholders rendus (`À venir`, `Coming soon`, `TODO`, `undefined`, …) interdits.
- Site360.jsx importe `site360TabsRegistry` et utilise
  `getEnabledSite360Tabs`.
- Les 9 IDs attendus déclarés avec `status` + `renderMode` + `testId`.

### 5.3 Playwright (4/4 GREEN)

[`e2e/site360_tabs_routes.spec.js`](e2e/site360_tabs_routes.spec.js) +
[`e2e/playwright.site360_tabs_routes.config.js`](e2e/playwright.site360_tabs_routes.config.js)
sur desktop 1440 :

- 01 — Site360 charge et expose les 9 onglets FR métier visibles dans
  le body, aucun jargon interdit.
- 02 — Boutons top : `Évaluation RegOps` (accent), aucun
  `/achat-assistant`, aucun `href="#"`.
- 03 — Cycle clic sur chaque onglet : body > 200 caractères, aucun
  placeholder interdit.
- 04 — Capture documentaire 1440.

---

## 6. Captures

- [`docs/audits/site360_p0_tabs/site360-resume-1440.png`](site360_p0_tabs/site360-resume-1440.png)
  — TabBar 9 onglets dont **« Analyse énergétique »** + bouton
  **« Évaluation RegOps »** avec accent.
- [`docs/audits/site360_p0_tabs/site360-tabs-audit-1440.png`](site360_p0_tabs/site360-tabs-audit-1440.png)
  — vue documentaire complète viewport 1440×2200.

---

## 7. Dettes restantes

| Dette | Sévérité | Plan |
|---|---|---|
| `TabAnalytics` reste inline dans `Site360.jsx` (1634 LoC) | Bas | Refacto possible vers un composant dédié (sprint refacto, hors P0) |
| 4 modals (`BacsWizard`, `IntakeWizard`, `SegModal`, autres) restent inline | Info | Pas de bug, juste de la cohérence — possible polish |
| Registry uniquement « enabled » à la livraison P0 | Info | Mécanisme `status: 'hidden'` prêt pour futur découplage module |
| `dataQuality.score < 50` bandeau partiel non testé dans la spec | Bas | Couvert indirectement par les tests Playwright (smoke `length > 200`) |

Aucune dette doctrinale (aucun jargon EN, aucun calcul métier FE
ajouté, aucune route morte, aucun `href="#"`).

---

## 8. GO / NO-GO reprise P3 Énergie

**GO P3.3 Énergie** — sprint Site360 P0 livré sans impact sur la brique
Énergie :

- Aucune modification des routes Énergie ni du LoadCurveTab.
- Aucune modification du contrat `/api/energy/*`.
- Source-guards Énergie (71/71) restent verts.
- Le branchement Site360 vers Énergie via `SITE360_CANONICAL_ROUTES.consommation`
  (`/consommations/courbe`) facilite la cohérence pour futures itérations.

La branche `claude/energie-p3-3-tarification-hors-horaires` est prête à
être reprise (créée depuis `052e078f`, inchangée).
