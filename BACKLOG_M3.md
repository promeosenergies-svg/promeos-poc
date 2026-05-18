# Backlog M3 — PROMEOS

> Créé : Sprint M2-4.7 (closure documentaire Sprint M2-4 — 2026-05-18).
> Source de vérité des chantiers ouverts post-M2-4. `SECURITY.md` §5 y renvoie.
> Mise à jour : à chaque closure de sprint M3.

---

## 1. Sprints M3 planifiés

### M3-DEBT — Résorption de la dette de tests baseline  🔴 P0 · ~6 j/h

- **Objet** : 164 tests pré-existants en échec, hérités de la branche `refonte-sol2`
  (documentés en M2-4.1.ter, `docs/test-debt/baseline_m2-4-1-ter_failures.txt`).
- **Pourquoi P0** : la règle de non-régression M2-4 est *« 0 NEW failures »* et non
  *« 0 total »* — un compromis acceptable pour livrer le Centre d'Action V4, mais
  une baseline rouge masque les vraies régressions futures. À solder en début M3.
- **Méthode** : triage par cause racine (DB locked / fixtures obsolètes / refonte
  UI / dérive de données), puis lots de correctifs atomiques. Cf. sprint
  `M3-METHOD-DOC` pour la méthode « audit avant fix ».
- **DoD** : baseline `docs/test-debt/` ramenée à 0, ou chaque échec résiduel
  requalifié `xfail` documenté avec ticket de sortie.

### M3-JWT-USER-UUID — Dette JWT `user_id` int ↔ V4 `actor_id` UUID  🟡 P1 · ~2,5 j/h

- **Objet** : résoudre la dette de typage résiduelle décrite dans `SECURITY.md` §5.1.
  Le JWT porte `user_id: int` ; `action_event_log.actor_id`, `evidences.uploaded_by`,
  `action_blockers.added_by` sont des `UUID`.
- **État actuel** : pas de bug — M2-4.4 dérive un `actor_id` UUID5 déterministe et
  trace le `user_id` int réel dans `event_payload.actor_user_id`. Dette de cohérence
  de schéma, pas de sécurité.
- **Options** (parallèles à ADR-009) : A — table de correspondance `users` int→UUID ;
  B — JWT en `user_id: UUID` ; **D (reco)** — migrer `actor_id`/`uploaded_by`/`added_by`
  UUID→Integer FK `users.id`, par symétrie exacte avec la résolution `organisation_id`.
- **DoD** : ADR-009-bis (ou amendement) actant l'option ; migration + maj models +
  adaptation tests M2-4.4 ; `event_payload.actor_user_id` devient redondant → retiré.

### M3-SEED-MIGRATION — Migration data legacy → V4  🟡 P1 · ~5 j/h

- **Objet** : exécuter le manuel de bascule ADR-026 — migrer les **173 rows**
  cardinales (`action_items` 35 + `bill_anomaly` 52 + `anomaly` KB 86) du legacy
  vers les 8 tables V4.
- **Prérequis** : 14 endpoints V4 routés (✅ livré M2-4.4), seed V4 idempotent
  (✅ livré M2-4.1.bis). La migration réelle de données restait hors scope M2-4.
- **Garde-fous ADR-026** : 9 invariants I1-I9, backup hors Git (I9), receipt
  sanitizé, STOP GATE J+14. Cutover prévu Mois 4 dans la doctrine V4.
- **DoD** : 173 rows migrées + vérifiées (counts + checksums), legacy conservé
  12 mois (rétention RGPD), receipt committé.

### M3-LINK-EVENT-DOCTRINE — event_type `link_created`  🟢 P2 · ~1,5 j/h

- **Objet** : `PATCH /items/{id}` (edit cosmétique) et `POST /items/{id}/links`
  n'émettent pas d'audit event — aucun des 16 `event_type` doctrine (SG-6) ne les
  couvre (cf. `SECURITY.md` §5.3).
- **Travail** : amender ADR-029 pour ajouter `link_created` (et arbitrer si l'edit
  cosmétique mérite un event), étendre la whitelist SG-6 à 17 valeurs, câbler
  l'émission dans `backend/routes/v4/action_center.py`.
- **DoD** : ADR-029 amendé, SG-6 mis à jour, tests d'émission verts.

### M3-METHOD-DOC — Doc méthode « audit avant fix »  🟢 P3 · ~1 j/h

- **Objet** : formaliser la méthode appliquée tout le Sprint M2-4 (Phase 0/1
  read-only → STOP gate → phases numérotées → DoD → commit atomique → source-guard).
- **Pourquoi** : la méthode a évité plusieurs faux départs en M2-4 (renommage
  `obs_logging/`, dette baseline classée environnementale). La capitaliser comme
  doc réutilisable pour les sprints suivants.
- **DoD** : `docs/dev/methode_audit_avant_fix.md` rédigé, référencé dans CLAUDE.md.

---

## 2. Différés M2-5 / M2-6 (hors M3 — rappel)

Ces chantiers ont une fenêtre dédiée dans la doctrine V4 ; listés ici pour vue
d'ensemble seulement (détail : `SECURITY.md` §5.2 et §5.3).

| Chantier | Fenêtre | Détail |
| --- | --- | --- |
| ActionLink cibles polymorphes (site/building/meter/invoice/contract) | M2-5 | `link_target_validator` lève 501 en attendant |
| Evidence formats DOCX/XLSX/ZIP/CSV | M2-5 | M2-4 = PDF/JPG/PNG (magic bytes) |
| Scope hiérarchique V4 (ENTITÉ/PORTEFEUILLE/SITE) | M2-6 | hook `_apply_scope()` prêt |
| `write_event()` Pydantic strict (16 schemas v1) | M2-6 | IE7 |
| Rétention 90j evidence enforce Python | M2-6 | IE6 |
| Rôle V4 `auditor` distinct | M2-6 | actuellement `auditeur` legacy → `viewer` |
| Endpoint admin `closed → reopened` | M2-6 | si besoin confirmé (IL3) |

---

## 3. Long terme (hors Mois 2-3)

- Scan antivirus (ClamAV) + chiffrement at-rest + backend S3 pour les evidences.
- Migration storage rate limiting in-memory → Redis (multi-instance).
- Refresh tokens + révocation.
- 2FA pour rôles admin.
- OAuth2 SSO (Google, Azure AD).
- Password rotation policy.

---

## 4. Priorisation M3

| Sprint | Priorité | Effort | Dépendance |
| --- | --- | --- | --- |
| M3-DEBT | 🔴 P0 | ~6 j/h | aucune — à solder en premier |
| M3-JWT-USER-UUID | 🟡 P1 | ~2,5 j/h | aucune |
| M3-SEED-MIGRATION | 🟡 P1 | ~5 j/h | ADR-026 (backup + STOP GATE) |
| M3-LINK-EVENT-DOCTRINE | 🟢 P2 | ~1,5 j/h | amendement ADR-029 |
| M3-METHOD-DOC | 🟢 P3 | ~1 j/h | aucune |

**Effort cumulé M3 estimé : ~16 j/h** (5 sprints).

Ordre recommandé : M3-DEBT (débloque une baseline saine) → M3-JWT-USER-UUID →
M3-SEED-MIGRATION → M3-LINK-EVENT-DOCTRINE → M3-METHOD-DOC.
