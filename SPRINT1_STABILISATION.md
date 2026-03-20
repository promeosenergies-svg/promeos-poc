# Sprint 1 — Refactoring structurel PROMEOS

**Date :** 2026-03-17
**Branche :** `ux/cockpit-v3`
**Commit :** `3b9d070`

---

## 1. Résumé exécutif

Sprint 1 focalisé sur 4 chantiers de refactoring structurel :

| Chantier | Avant | Après | Statut |
|----------|-------|-------|--------|
| patrimoine.py | 3129 lignes monolithe | 7 modules (staging, sites, compteurs, contracts, billing, helpers) | OK |
| ConformitePage.jsx | 1560 lignes | 786 lignes + 5 composants extraits | OK |
| PII | Emails en clair dans audit logs | Emails masqués (3 chars + ***) | OK |
| Tests E2E | 6 specs existantes | +1 spec (5 tests chaîne transverse) | OK |

**Risque** : Faible — aucune modification de logique métier, 61 routes patrimoine préservées.

---

## 2. Détail des refactorings

### A. patrimoine.py → routes/patrimoine/

| Fichier | Lignes | Contenu |
|---------|--------|---------|
| `__init__.py` | 98 | Routeur principal, inclut les sous-routeurs |
| `_helpers.py` | 651 | Fonctions partagées (_get_org_id, _serialize_site, etc.) |
| `staging.py` | 884 | Import, staging, mapping, demo_load, portfolio_sync |
| `sites.py` | 937 | CRUD sites, KPIs, anomalies, snapshot, complétude |
| `compteurs.py` | 134 | CRUD compteurs, move, detach |
| `contracts.py` | 205 | CRUD contrats énergie |
| `billing.py` | 505 | Payment rules, réconciliation |

L'ancien `patrimoine.py` est conservé comme backup (`patrimoine_legacy.py` non nécessaire car git).

### B. ConformitePage.jsx → composants conformité

| Composant | Lignes | Rôle |
|-----------|--------|------|
| `ComplianceSummaryBanner.jsx` | 236 | Bandeau hero 3 états (vert/orange/rouge) + top urgences |
| `ComplianceScoreHeader.jsx` | 126 | Score + breakdown barres + confiance |
| `FindingAuditDrawer.jsx` | 188 | Drawer détail finding avec identité, paramètres, preuves |
| `DevBadges.jsx` | 61 | Badges API/scope pour mode Expert |
| `conformiteUtils.js` | 215 | Utilitaires purs (scope, parsing, formatage) |
| `index.js` | 15 | Barrel re-exports |

### C. PII — Quick wins

| Fichier | Changement |
|---------|-----------|
| `routes/admin_users.py:179` | `email` → `email_masked` (3 chars + ***) dans log_audit create_user |
| `routes/auth.py:305` | `target_email` → `target_email_masked` dans log_audit impersonate |

**Cartographie PII complète :**

| Champ | Modèle | Stockage | Exposition API | Risque |
|-------|--------|----------|---------------|--------|
| email | User | SQLite | /api/admin/users, /api/auth/me | Admin-only, acceptable |
| hashed_password | User | SQLite bcrypt | Jamais exposé | OK |
| nom, prenom | User | SQLite | /api/admin/users | Admin-only |
| contact_email | TertiaireEfa | SQLite | /api/tertiaire/efa/* | Fonctionnel |
| recipient_emails | NotificationDigest | SQLite | /api/notifications/prefs | User-scoped |

**Points restants (Sprint 2+)** :
- Politique de rétention des audit logs
- Chiffrement at-rest des emails (si réglementaire)
- Export RGPD (droit d'accès/suppression)

### D. Tests E2E

`e2e/e7-sprint1-chain.spec.js` — 5 tests :
1. T1: Quick-create site → apparaît dans le registre
2. T2: Patrimoine → Conformité link fonctionne
3. T3: Cockpit charge sans crash (ActionDrawerProvider)
4. T4: Actions & Suivi charge et liste les actions
5. T5: Billing charge sans régression

---

## 3. Tests exécutés

| Suite | Résultat |
|-------|----------|
| Backend (31 tests) | **31 passed** |
| Frontend build (Vite) | **OK (24.8s)** |
| Lint (ruff + ESLint + Prettier) | **OK** |

---

## 4. Régressions potentielles

| Risque | Probabilité | Vérification |
|--------|------------|-------------|
| Import patrimoine cassé | Très faible | 61 routes chargées, tests OK |
| ConformitePage layout shift | Faible | Build OK, composants identiques visuellement |
| Audit log format change | Nulle | Masquage email = changement intentionnel |

---

## 5. TODO Sprint 2

| # | Action | Effort | Priorité |
|---|--------|--------|----------|
| 1 | CI/CD pipeline (lint + test + build) | M | Haute |
| 2 | Connecteur Enedis (structure OAuth) | M | Haute |
| 3 | Connecteur Météo-France / Open-Meteo | S | Moyenne |
| 4 | Schémas Pydantic stricts sur routes patrimoine | M | Moyenne |
| 5 | KPI formels : documenter formules de score | M | Moyenne |
| 6 | Rate limiting global | S | Moyenne |
| 7 | RGPD : export/suppression données utilisateur | M | Basse |
| 8 | Refactorer Cockpit.jsx (800+ lignes) | M | Basse |
| 9 | Badge UI désynchronisé patrimoine-conformité | S | Basse |
| 10 | Auto-provision EFA/BACS à la création site | M | Basse |
