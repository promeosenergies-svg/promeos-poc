# ADR-003: Quality Gate — Strategie de tests et validation continue

**Date**: 2026-02-16
**Statut**: Accepted
**Auteurs**: Equipe PROMEOS

---

## Contexte

PROMEOS est un POC avec 66+ endpoints backend, 30+ pages frontend, et 4 moteurs de regles de conformite. Le rythme de developpement est eleve (sprints courts, features en parallele). Sans filet de securite, les regressions sont frequentes:

- Un changement de scope casse 5 pages silencieusement
- Un refactoring de route casse le frontend sans alerte
- Une regle de conformite modifiee produit des scores incoherents

---

## Probleme

Comment maintenir la confiance dans le code avec un rythme de livraison eleve, sans ralentir le developpement avec une CI lourde?

---

## Options envisagees

### Option A: Tests E2E uniquement (Cypress/Playwright)

- (+) Teste le systeme entier
- (-) Lent (minutes), fragile (selectors), couteux a maintenir
- (-) Mauvais feedback loop (trop lent pour le dev quotidien)

### Option B: Tests unitaires classiques (Jest/Pytest)

- (+) Rapide, isole
- (-) Ne detecte pas les regressions d'integration (scope + API + rendu)
- (-) Necessite des mocks lourds pour les composants React

### Option C: Strategie pyramidale adaptee au POC (retenu)

- (+) Source guards (< 1s): verifient la structure du code sans rendu
- (+) Tests unitaires (< 5s): logique metier, services, moteurs de regles
- (+) Tests d'integration (< 10s): API endpoints avec TestClient
- (+) Performance budgets: assertions sur les temps de reponse
- (+) E2E smoke (optionnel): 3 tests Playwright pour le happy path

---

## Decision

**Option C retenue.** Pyramide de tests a 4 niveaux:

### Niveau 1: Source Guards (frontend, ~200 tests)

Tests Vitest qui lisent le source code (`readFileSync`) et verifient des invariants structurels:

```javascript
const src = readFileSync('DevPanel.jsx', 'utf8');
expect(src).toContain('useScope');
expect(src).toContain('getLastRequests');
```

**Avantages**: ultra-rapide (pas de rendu DOM), detecte les suppressions accidentelles d'imports, de composants ou de features. Agit comme un "contrat" sur la structure du code.

### Niveau 2: Tests unitaires (backend, ~770 tests)

Pytest avec `TestClient` FastAPI. Chaque route a son fichier de test:

```python
def test_compliance_summary_returns_200():
    resp = client.get("/compliance/summary", headers={"X-Org-Id": "1"})
    assert resp.status_code == 200
    assert "total_sites" in resp.json()
```

Couvrent: routes, services, moteurs de regles, IAM (61 tests), compliance, KB.

### Niveau 3: Performance Budgets

Fichier `perf_config.py` avec seuils configurables:

```python
PERF_THRESHOLDS = {
    "slow_request_ms": 300,
    "test_cockpit_ms": 500,
    "test_sites_list_ms": 300,
}
```

Le middleware backend log un `slow_request` warning si un endpoint depasse le seuil. Les tests de perf verifient que les endpoints critiques respectent leur budget.

### Niveau 4: Pre-commit hooks

Husky + lint-staged:
- `.jsx`: ESLint --fix + Prettier --write
- `.py`: Ruff check --fix + Ruff format

ESLint: `--max-warnings=174` (ratchet descendant, objectif 0).

### Pipeline CI

```
PR / push
  ├── frontend: ESLint + Prettier + Vite build + Vitest (1076 tests)
  ├── backend: Ruff + Pytest (770+ tests)
  └── e2e (optionnel): Playwright smoke (3 tests)
```

---

## Consequences

### Positives

- **Feedback < 30s** en local (vitest + pytest)
- **1076 tests frontend + 770+ tests backend** = filet de securite dense
- Les source guards detectent les regressions structurelles (import manquant, composant supprime) en < 1s
- Les perf budgets previennent les degradations de performance
- Le ratchet ESLint force l'amelioration progressive de la qualite

### Negatives

- Les source guards testent la structure, pas le comportement (un composant peut etre present mais bugge)
- Les tests backend utilisent une DB SQLite en memoire: pas de test de migration reelle
- Les E2E sont optionnels (pas bloqueants en CI pour le POC)

### Risques acceptes

- Le ratchet ESLint a 174 warnings est temporaire. Chaque sprint doit reduire ce nombre.
- Les tests de perf dependent de la machine: les seuils sont calibres pour le dev local, pas pour la CI.
