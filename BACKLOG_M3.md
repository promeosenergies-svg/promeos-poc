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

---

## 5. Items issus du sprint M2-5 (frontend Centre d'Action V4)

> Dettes légères détectées pendant M2-5 (9 sous-sprints, frontend MV3). Distinctes
> des 5 sprints M3 de la §1 : ce sont des chantiers courts (≤ 1 j/h), à insérer
> opportunément. Cf. `docs/sprints/M2-5_FRONTEND_PLAN.md` §13.

### M3-MATRIX-CONTRACT-TEST — Synchro matrice lifecycle BE/FE  🟢 P2 · ~1 h

- **Origine** : M2-5.4.
- **Objet** : test contractuel garantissant la synchro entre la matrice backend
  `backend/services/v4/lifecycle_validator.py` (`_ALLOWED_TRANSITIONS`) et la
  matrice frontend `frontend/src/pages/action-center-v4/utils/lifecycleTransitions.js`.
- **Pourquoi** : la duplication contrôlée BE/FE est délibérée (pas de partage de
  code en MV3) mais une dérive silencieuse est possible si une seule des deux
  matrices est modifiée.
- **DoD** : un test backend qui sérialise la matrice en JSON + un test frontend
  qui assert l'égalité (ou un fixture partagé), verts.

### M3-MODAL-STACK-MGMT — Escape ne ferme que la modal du dessus  🟢 P2 · ~2-3 h

- **Origine** : M2-5.5.
- **Objet** : gérer une pile de modals dans `src/ui/Modal.jsx` pour qu'`Escape`
  ne ferme que la modal au sommet, pas la modal **et** le drawer parent.
- **Pourquoi** : les 5 modals M2-5.4/.5/.6 sont montées dans le `Drawer` détail →
  `Escape` double-ferme. Acceptable en MV3 mais UX dégradée pour le pilote.
- **DoD** : `src/ui/Modal.jsx` gère le stack ; touche à un composant legacy →
  mini-sprint dédié hors scope M2-5, tests de non-régression du legacy verts.

### M3-LINT-CLEANUP — Résorber les warnings ESLint legacy  🟢 P3 · ~2 h

- **Origine** : M2-5.1.
- **Objet** : ramener `npm run lint` (`eslint src --max-warnings=15`) au vert —
  ~33 warnings legacy pré-existants dépassent le seuil.
- **Pourquoi** : `npm run lint` full-repo est rouge (pré-existant, hors scope
  M2-5). Le `lint-staged` par fichier passe (seuil 174), mais le full-repo non.
- **DoD** : warnings legacy résorbés (imports morts, deps de hooks), `npm run
  lint` vert, seuil `--max-warnings` resserré.

### M3-FRONTEND-POLISH-ACTOR-NAME — Enrichir l'acteur des events  🟢 P2 · ~1-2 h

- **Origine** : M2-5.3.A.
- **Objet** : `action_event_log` porte `actor_id` + `actor_role` + `actor_name`,
  mais `actor_name` n'est pas toujours renseigné côté écriture runtime (le seed
  M2-5.7, lui, le renseigne). `EventItem` retombe sur « Système » par défaut.
- **Pourquoi** : enrichir l'écriture backend (M2-4.4) pour joindre `user.name`
  côté serveur sur tout event utilisateur → timeline plus lisible.
- **DoD** : `actor_name` systématiquement renseigné côté backend, 1-2 tests.

### M3-PATTERN-DOC-UI-WRITE — Documenter le pattern UI write V4  🟢 P3 · ~30 min

- **Origine** : M2-5.6 (fin de la réplication 3×).
- **Objet** : documenter le pattern UI write V4 (cf. `M2-5_FRONTEND_PLAN.md`
  §13.3) dans `docs/frontend/PATTERN_UI_WRITE_V4.md`.
- **Pourquoi** : 5 modals respectent le pattern sans document explicite — un dev
  ajoutant une 6ᵉ modal en M3 doit rétro-lire 3 modals pour le deviner.
- **DoD** : `docs/frontend/PATTERN_UI_WRITE_V4.md` rédigé, référencé dans CLAUDE.md.

### M3-FORBID-EXTRA-PATTERN — Capitaliser le piège Pydantic `extra="forbid"`  🟢 P3 · ~10 min

- **Origine** : M2-5.6 (piège `resolution_comment` ≠ `resolution_note`).
- **Objet** : capitaliser dans `MEMORY.md` le piège Pydantic `extra="forbid"` —
  tout champ inconnu d'un payload PATCH/POST = 422 muet ; vérifier le schéma
  exact avant tout write côté frontend.
- **Pourquoi** : 3 sprints write consécutifs (M2-5.4/.5/.6) ont rencontré cette
  surprise. La documenter pour ne pas la re-mordre.
- **DoD** : 1 entrée `feedback` ajoutée dans la mémoire projet.

### M3-USE-CASE-B-C — Étendre le seed à 2-3 scénarios métier  🟢 P3 · ~2 h

- **Origine** : M2-5.7.
- **Objet** : étendre `backend/seeds/use_case_a_seed.py` à 2-3 Use Cases (B =
  audit BACS multi-sites ; C = renégociation contrat post-ARENH).
- **Pourquoi** : le pilote voudra tester d'autres scénarios. Use Case A suffit
  pour la 1ʳᵉ démo, B/C sont utiles ensuite.
- **DoD** : seeds B/C livrés, idempotents, sur le pattern déclaratif M2-5.7.

**Effort cumulé M2-5 → M3 : ~9-11 h** (7 items courts).
