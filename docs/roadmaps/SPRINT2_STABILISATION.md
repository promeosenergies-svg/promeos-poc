# Sprint 2 — Contrats, qualité et documentation PROMEOS

**Date :** 2026-03-17
**Branche :** `ux/cockpit-v3`
**Commit :** `e7676d5`

---

## 1. Résumé exécutif

| Chantier | Livré | Risque |
|----------|-------|--------|
| CI/CD renforcé | Alembic check ajouté au pipeline | Nul |
| Schemas Pydantic | 3 schemas stricts sur routes critiques | Faible |
| Contrat erreur API | APIError standard + handler global | Faible |
| KPI formels | 7 KPI documentés avec formules exactes | Nul |
| Tests invariants | 7 tests transverses | Nul |

**Non traité (hors scope)** : connecteurs Enedis/Météo, refonte Cockpit.jsx, RGPD complet.

---

## 2. Fichiers modifiés

| Fichier | Rôle | Risque |
|---------|------|--------|
| `.github/workflows/quality-gate.yml` | +Alembic check step | Nul |
| `backend/schemas/error.py` | Contrat APIError | Nul |
| `backend/schemas/patrimoine_schemas.py` | Schemas Pydantic stricts | Faible |
| `backend/schemas/__init__.py` | Exports schemas | Nul |
| `backend/middleware/error_handler.py` | Handler erreurs global | Faible |
| `backend/main.py` | Enregistrement handler | Faible |
| `backend/routes/sites.py` | Schema sur quick-create | Faible |
| `backend/routes/patrimoine/_helpers.py` | Contraintes ContractCreateRequest | Faible |
| `backend/tests/test_invariants.py` | 7 tests transverses | Nul |
| `docs/KPI_FORMELS.md` | Documentation KPI | Nul |

---

## 3. Détail

### A. CI/CD
- Step `Alembic check (schema drift)` ajouté au job backend
- Bloque le pipeline si les modèles et la DB divergent

### B. Schemas Pydantic stricts
- `QuickCreateSiteRequest` : validation nom (strip, non vide), code_postal (5 chars), ville
- `SiteUpdateRequest` : SIRET (14 digits), surface (bounds), champs optionnels typés
- `ContractCreateRequest` : energy_type enum, dates ISO, prix avec bounds

### C. Contrat erreur API
```json
{
  "code": "NOT_FOUND",
  "message": "Site 999 non trouvé",
  "hint": "Vérifiez l'identifiant",
  "correlation_id": "a1b2c3d4"
}
```
- 3 handlers : HTTPException, RequestValidationError, Exception générique
- correlation_id pour traçabilité

### D. KPI formels
Documentés dans `docs/KPI_FORMELS.md` :
1. compliance_score_composite : DT×0.45 + BACS×0.30 + APER×0.25 − penalty
2. risque_financier_euro : 7500€ × NC + 3750€ × AR
3. completude : 8 checks binaires, score = filled/8 × 100
4. patrimoine_kpis : 18 KPI (status counts, surface, contrats)
5. cockpit stats : agrégation org
6. BACS status : evidence-based priority
7. Limites connues documentées

### E. Tests invariants
7 tests dans `test_invariants.py` :
1. Quick-create → bâtiment auto-créé
2. Site archivé → exclu des queries
3. Contrat + site invalide → erreur
4. Erreur 404 → format APIError
5. Erreur validation → format APIError
6. Pas d'EFA orpheline
7. Complétude → structure valide

---

## 4. Tests exécutés

| Suite | Résultat |
|-------|----------|
| Backend (38 tests) | **38 passed** (11.5s) |
| Frontend build | **OK** (28.3s) |
| Lint (ruff) | **OK** |

---

## 5. Régressions potentielles

| Risque | Probabilité | Vérification |
|--------|------------|-------------|
| Handler erreur change format réponse | Faible | Seules les erreurs changent, pas les succès |
| Schema strict rejette payload valide | Très faible | Schemas appliqués sur 2 routes seulement |

---

## 6. TODO Sprint 3

| # | Action | Effort | Priorité |
|---|--------|--------|----------|
| 1 | Connecteur Enedis (structure OAuth) | M | Haute |
| 2 | Connecteur Météo-France / Open-Meteo | S | Moyenne |
| 3 | Rate limiting global | S | Moyenne |
| 4 | Schemas Pydantic sur routes billing/conformité | M | Moyenne |
| 5 | RGPD : export/suppression données utilisateur | M | Basse |
| 6 | Refactorer Cockpit.jsx | M | Basse |
| 7 | Badge UI désynchronisé patrimoine-conformité | S | Basse |
| 8 | Merge ux/cockpit-v3 → main | S | Haute |
