# PROMEOS — Résumé Audit Sévère
**Date** : 19 mars 2026 | **Note actuelle** : 5,5/10 | **Atteignable à 90j** : 8/10

---

## Verdict en 3 lignes

La base architecturale est saine. La démo est crédible visuellement.
Mais 3 clics suffisent à exposer les vides : sécurité API inexistante, module ACC absent,
calculs achat en JavaScript non auditables. Ces 3 points bloquent toute vente B2B sérieuse.

---

## Scores par axe

| Axe | Note |
|-----|------|
| Produit / Logique | 6/10 |
| UX / UI | 6,5/10 |
| Front | 6/10 |
| Back / API | 5,5/10 |
| Données / Modèle métier | 6/10 |
| Règles métier / Conformité | 5/10 |
| Facturation / Achat | 4,5/10 |
| ACC / PMO / Settlement | **1/10** |
| Multi-sites / Navigation | 6/10 |
| Crédibilité marché | 5/10 |

---

## P0 — Bloquants (avant toute démo investisseur)

### 1. Zéro authentification stricte en production
285 endpoints utilisent `get_optional_auth` (lenient). Aucun n'utilise `get_current_user` (strict).
`AUTH_ENABLED=false` par défaut. `DEMO_MODE=true` → CORS wildcard `"*"`.
Un attaquant peut lire/écrire toutes les données sans token.
**Fichiers** : `backend/middleware/auth.py:25-26`, `backend/main.py:94-106`

### 2. Module ACC/PMO entièrement absent
`PMO_ACC` existe dans les enums. `PaymentRule` gère payeur/facturé.
Mais : zéro route `/api/acc/`, zéro page frontend, zéro settlement, zéro répartition entre participants.
L'ACC est le sujet n°1 des energy managers tertiaires en 2026.
**Localisation** : À créer entièrement.

### 3. Calcul des scénarios achat côté client (JS), non auditable
`frontend/src/domain/purchase/scoring.js` + `engine.js` = toute la logique.
Le backend persiste les résultats mais ne les recalcule pas.
Décision d'achat énergétique = plusieurs M€ — non défendable contractuellement.
**Fichiers** : `frontend/src/domain/purchase/scoring.js`, `backend/routes/purchase.py`

### 4. SECRET_KEY placeholder en .env
`SECRET_KEY=your-secret-key-change-in-production` → tous les JWT forgeable.
**Fichier** : `backend/.env`

---

## P1 — Crédibilité (avant premier pilote client)

| # | Problème | Localisation |
|---|----------|--------------|
| P1.1 | `_detect_framework()` fragile → score conformité peut silencieusement tomber à 50.0 | `compliance_score_service.py:366` |
| P1.2 | Shadow billing : prorata 30j hardcodé (erreur ±5% sur mois courts/longs) | `billing_shadow_v2.py` |
| P1.3 | APER : éligibilité sans calcul productible PV ni analyse ROI | `aper_service.py` |
| P1.4 | Consommation réelle absente en démo (confidence="none" sur 4/5 sites) | `consumption_unified_service.py` |
| P1.5 | Risque financier : 4 noms de champ différents dans le front | `normalizeRisk.jsx` |
| P1.6 | Achat gaz bloqué en dur (`ALLOWED_ENERGY_TYPES = {"elec"}`) | `purchase.py:48` |
| P1.7 | Aucun lien FK facture → action → ROI | `billing_models.py`, `action_item.py` |
| P1.8 | Export OPERAT non validé (format XSD ADEME non vérifié) | `operat.py`, TODO réglementaire |
| P1.9 | N+1 queries sur portfolio compliance (N sites × 3 frameworks) | `compliance_score_service.py:326` |

---

## P2 — Premium / Différenciation

| # | Problème |
|---|----------|
| P2.1 | Connecteurs (Enedis, MétéoFrance, PVGIS) déclarés mais ne produisent aucune donnée |
| P2.2 | KPI Catalog incomplet — formule/source/période manquantes pour plusieurs KPIs UI |
| P2.3 | CEE : modèle en DB mais zéro route, zéro page, zéro service actif |
| P2.4 | Cockpit sans tendance historique (ComplianceScoreHistory en DB, non exposé) |
| P2.5 | Flex (Sprint 21) non reliée au cockpit ni aux scénarios achat |
| P2.6 | Exports (PDF, CSV, OPERAT) non testés, qualité non garantie |

---

## Ruptures de logique dans la chaîne produit

```
Patrimoine ──✅──▶ Conformité ──⚠️──▶ Facturation ──❌──▶ Achat
                                                              │
                                    (calcul JS non auditable) │
                                                              ▼
                                    ACC/PMO ◀──❌── ABSENT ENTIER
                                                              │
                                                              ▼
                                    Flex ──❌──▶ non reliée au cockpit
                                                              │
                                                              ▼
                                    Actions ──❌──▶ ROI non mesuré
```

**8 ruptures identifiées** — les 3 premières briques sont cohérentes,
la chaîne se fragmente à partir de l'Achat.

---

## Plan d'action — Top 7 qui font le plus monter la note

| # | Action | Impact |
|---|--------|--------|
| 1 | Auth stricte (285 → 0 endpoints non protégés) | +0,8 pt |
| 2 | Module ACC V1 (settlement + répartition + page) | +0,7 pt |
| 3 | Calcul purchase côté serveur (scoring auditable) | +0,6 pt |
| 4 | MeterReading réelles en démo (confidence "high") | +0,5 pt |
| 5 | Champ `framework` explicite sur RegAssessment (supprimer _detect_framework) | +0,4 pt |
| 6 | FK `billing_insight_id` → ActionItem → ROI traçable | +0,4 pt |
| 7 | APER productible PVGIS + prorata shadow billing jours réels | +0,3 pt |

---

## Definition of Done — 8 conditions pour "solide et crédible"

1. `AUTH_ENABLED=true` par défaut, 0 endpoint mutation sans auth stricte
2. Chaîne complète reliée par FK : Patrimoine → Conformité → Facturation → Achat → ACC → Flex → Actions
3. Tous les KPIs du cockpit ont une formule dans `kpi_catalog.py`
4. Scoring achat calculé côté serveur (pas en JS)
5. Au moins 1 site démo avec MeterReading réelles, confidence ≥ "medium"
6. Export OPERAT validé XSD avant téléchargement
7. ACC V1 : settlement d'une période, répartition 2 participants, page dédiée
8. Cockpit < 2s sur 50 sites (N+1 résolu)

---

## Chiffres clés du repo

| Métrique | Valeur |
|----------|--------|
| Modèles backend | 60 |
| Routes (fichiers) | 59 |
| Services | 138 |
| Pages frontend | 40+ |
| Composants | 100+ |
| Tests backend | 222 fichiers (141 actifs) |
| Tests frontend | 47 fichiers (38 actifs) |
| Endpoints sans auth stricte | **285 / 285** |
| Pages ACC/PMO | **0 / 0** |
| Connecteurs actifs | **0 / 5** |
