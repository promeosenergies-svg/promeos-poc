# Investigation P0-V1 + P0-V2 pré-push Sprint 1 Vague B

> **Date** : 2026-04-24
> **HEAD avant investigation** : `9fa1e77d`
> **HEAD après investigation** : voir §Commits
> **Durée réelle** : ~15 min (budget 20-30 min)

## P0-V1 — Modal onboarding "Navigation par module"

### Diagnostic

**Cas retenu : C1** — Script Playwright ne dismisse pas le modal avant capture.

### Preuves

**Composant** : `frontend/src/components/OnboardingOverlay.jsx`
- L4 : `const ONBOARDING_KEY = 'promeos_onboarding_done'`
- L29-35 : `useEffect` lit `localStorage.getItem(ONBOARDING_KEY)` — si absent → `setVisible(true)`
- L37-44 : `dismiss()` persiste `localStorage.setItem(ONBOARDING_KEY, 'true')`

→ Le mécanisme seen-flag **fonctionne correctement en usage réel**. Au premier login, modal affiché ; une fois cliqué "Passer le tour" ou "Commencer" → flag persisté → plus jamais ré-affiché.

**Script capture** : `tools/playwright/audit-agent.mjs:271-273`
- Chaque session Playwright = nouveau browser context = `localStorage` vide
- Le script seed uniquement `promeos_token` (JWT auth)
- **Pas de pre-seed du flag `promeos_onboarding_done`** → modal visible sur 7/7 captures

### Fix appliqué

`tools/playwright/audit-agent.mjs` : ajout d'une ligne dans le `page.evaluate` auth pour pre-seed le flag onboarding.

```js
localStorage.setItem('promeos_onboarding_done', 'true');
```

Cohérent avec la constante `ONBOARDING_KEY` de `OnboardingOverlay.jsx:4`. Commentaire inline référence le composant pour éviter la récidive si la key change.

### Re-capture effectuée

`tools/playwright/captures/sprint1-vague-b-postfix/2026-04-24-14-22/` — 6 PNG sans modal onboarding. **Vérification visuelle** : `01-cockpit.png` confirme absence modal, premier fold pleinement visible (panel + hero + KPIs + week-cards + courbe charge).

---

## P0-V2 — Routes `/achat-energie` vs `/assistant-achat` identiques

### Diagnostic

**Cas retenu : C3 + C1 hybride** — la route `/achat-assistant` existe comme redirect vers `/achat-energie?tab=assistant` mais **AchatSol ne consomme pas le query param**. Le script capture visite 2 fois la même URL effective.

### Preuves

**Routes** : `frontend/src/App.jsx`
- L497 : `<Route path="/achat-energie" element={<PurchasePage />} />` (alias AchatSol)
- L513-514 : `<Route path="/achat-assistant" element={<Navigate to="/achat-energie?tab=assistant" replace />} />`

**NavRegistry** : `frontend/src/layout/NavRegistry.js`
- Un seul item `{ to: '/achat-energie', label: "Scénarios d'achat", … }`
- **`/achat-assistant` n'est PAS dans NavRegistry** — c'est juste un legacy URL alias

**Composant AchatSol** : `frontend/src/pages/AchatSol.jsx`
- Aucun `useSearchParams` (pas de consommation `?tab=`)
- Commentaire explicite L14-16 : "l'AchatPage legacy gère ses propres drawers ScenarioDrawer via la route"
- Les week-cards font `navigate('/achat-energie?tab=assistant')` → no-op visuel sur AchatSol Sol (seul AchatPage legacy réagissait)

**Script capture** : `tools/playwright/audit-agent.mjs:55-56`
- Entrée 16 : `/achat-energie`
- Entrée 17 : `/achat-assistant` → redirect → `/achat-energie?tab=assistant` → AchatSol ignore le tab → rend identique à entrée 16

→ 2 captures identiques **attendues** tant que le URL state tab n'est pas implémenté dans AchatSol.

### Fix appliqué

**Option α choisie** : retrait de l'entrée `17-assistant-achat` du script audit-agent (doublon capture tant que AchatSol n'implémente pas `?tab=assistant`). Commentaire inline référence le backlog Vague D.

**Pourquoi pas Option β** (créer `AssistantAchatSol.jsx` dédiée) : hors scope Sprint 1 Vague B (câblage pages Sol = Vague C/D Sprint 2). L'audit fresh §6 avait déjà identifié ce gap URL state dans le tableau des pages problématiques.

**Pourquoi pas fix NavRegistry** : aucune entrée NavRegistry n'est concernée. Pas de divergence SSOT nav vs routes. Rien à modifier côté registry.

### Lien backlog

Le backlog existant `docs/backlog/vague_d_progress_bars_dt_bacs_aper.md` et l'audit fresh documentent déjà la dette URL state. Pas besoin de nouveau doc — commentaire inline dans `audit-agent.mjs` suffit pour pointer la raison.

Si Sprint 2 Vague D/C ajoute le `?tab=assistant` dans AchatSol, re-ajouter l'entrée `17-assistant-achat` au script capture avec la même numérotation (cohérence rapports visuels).

---

## Commits

```text
<hash F6a> chore(audit-captures): pre-seed onboarding seen-flag + drop achat-assistant doublon
```

1 seul commit atomique (script tool uniquement, pas de code prod). Contenu :
- Fix script pre-seed `promeos_onboarding_done` (P0-V1 C1)
- Retrait entrée `17-assistant-achat` du script (P0-V2 C3 Option α)
- Aucun code frontend prod modifié

## Recommandations push Sprint 1 Vague B

- [x] **Push safe maintenant** — tous P0 fixés ou proprement reportés
  - P0-V1 : script capture fixé + captures re-faites
  - P0-V2 : doublon retiré du script + commentaire backlog
  - P0-V3 `/conformite/tertiaire` sticky/grouping : **hors scope** ce mini-prompt, ticket Sprint 2 Vague C
- [ ] Push bloqué — arbitrage user requis → N/A

```bash
git push -u origin claude/nav-sol-parity-sprint-1-vague-b
```

## Captures à conserver

- `tools/playwright/captures/sprint1-vague-b-postfix/2026-04-24-14-22/` — 6 PNG sans modal ✅
- Ancien dossier `sprint1-vague-b-final/2026-04-24-13-01/` — 7 PNG avec modal (peut être supprimé ou conservé comme historique du bug détecté)

## Non-couvert (hors scope mini-prompt)

- **P0-V3** : `/conformite/tertiaire` liste EFA scroll infini sans sticky/grouping → Sprint 2 Vague C (câblage pages Sol)
- **AchatSol URL state `?tab=assistant`** : Sprint 2 Vague D (URL state pages problématiques, déjà identifié audit fresh §6)
