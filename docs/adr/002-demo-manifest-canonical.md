# ADR-002: Demo Manifest Canonical — Source unique de verite pour le mode demo

**Date**: 2026-02-14
**Statut**: Accepted
**Auteurs**: Equipe PROMEOS

---

## Contexte

PROMEOS possede un mode demo qui genere 120 sites realistes avec conformite, consommations, factures et actions. Ce mode est active via DemoBanner (frontend) qui appelle `/demo/seed-pack` (backend). Apres le seed, le frontend doit savoir:

- Quel pack a ete seede (small/medium/large)
- Combien de sites, dans quelle org
- Quel siteId utiliser par defaut pour les pages site-level
- Si le seed est en cours ou termine

Sans source de verite unique, chaque page interrogeait le backend differemment, causant des incoherences (mauvais orgId, sites count = 0, pages vides).

---

## Probleme

Comment garantir que toutes les pages frontend affichent des donnees coherentes apres un seed demo, sans hardcoder d'IDs et sans polling excessif?

---

## Options envisagees

### Option A: Polling status endpoint

- (+) Simple a implementer
- (-) Latence (delai entre fin du seed et detection)
- (-) Charge serveur (polling toutes les 2s)
- (-) Pas de donnees structurees sur le pack seede

### Option B: WebSocket push

- (+) Temps reel
- (-) Complexite infra (ASGI WebSocket + gestion connexions)
- (-) Surdimensionne pour un evenement rare (seed = 1 fois par session)

### Option C: Manifest canonical + applyDemoScope (retenu)

- (+) Source unique de verite: le backend renvoie un manifest JSON complet apres le seed
- (+) Le frontend applique le scope atomiquement via `applyDemoScope()`
- (+) Silent polling (`/demo/status-pack`) uniquement pendant le seed, puis arret
- (+) Le manifest est aussi disponible via `/demo/manifest` (GET idempotent)

---

## Decision

**Option C retenue.** Architecture en 3 etapes:

### 1. Backend: Seed orchestrator + manifest

Le `demo_seed/orchestrator.py` genere les donnees et retourne un manifest:

```json
{
  "status": "done",
  "pack": "medium",
  "org_id": 3,
  "org_nom": "Groupe Casino",
  "sites_count": 36,
  "default_site_id": 42,
  "default_site_name": "Casino Confluence",
  "seeded_at": "2026-02-14T10:30:00Z"
}
```

Le `demo_state.py` persiste l'etat du seed en memoire (status: idle/seeding/done/error) et expose le manifest via `/demo/status-pack` et `/demo/manifest`.

### 2. Frontend: DemoContext + DemoBanner

- `DemoContext` stocke le mode demo (enabled/disabled) et le manifest courant
- `DemoBanner` affiche le selecteur de pack, lance le seed, poll `/demo/status-pack` (silent, pas de toast d'erreur), et appelle `applyDemoScope()` quand `status === "done"`
- `/demo/status-pack` est dans `SILENT_URLS` pour ne pas declencher de logs d'erreur pendant le polling

### 3. ScopeContext: applyDemoScope()

Quand le manifest arrive, `applyDemoScope({ orgId, orgNom })` est appele:
- Enregistre l'org dynamiquement dans `demoOrgs` (persiste localStorage)
- Switch le scope atomiquement (`setScope` + `saveScope`)
- Declenche le `useEffect` de fetch sites pour le nouvel orgId
- Toutes les pages se re-rendent avec les bonnes donnees

---

## Consequences

### Positives

- **Coherence garantie**: apres `applyDemoScope()`, orgId/sitesCount/siteIds sont corrects partout
- **Zero hardcoding**: les IDs viennent du manifest, pas du code
- **Silent polling**: pas de bruit dans les logs/toasts pendant le seed
- **Idempotent**: `/demo/manifest` peut etre appele a tout moment pour retrouver l'etat

### Negatives

- L'etat demo est en memoire serveur (`demo_state.py`): perdu au redemarrage. Acceptable pour un POC.
- Le manifest est lie a un seul pack a la fois (pas de multi-pack simultane)

### Risques acceptes

- Si le serveur redemarre pendant un seed, l'etat passe a "idle" et le frontend doit re-seeder. Mitigation: le seed est idempotent (parametre `reset=true`).
