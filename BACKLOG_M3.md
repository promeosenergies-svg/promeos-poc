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

### M3-METHOD-DOC — Doc méthode « audit avant fix »  ✅ LIVRÉ (M2-5.9)

- **Livré** : `docs/dev/methode_audit_avant_fix.md` rédigé (bonus M2-5.9),
  référencé dans CLAUDE.md §Workflow méthodologique. Sibling de
  `methode_walkthrough_navigateur.md`.
- **Objet (rappel)** : formaliser la Phase 0/1 read-only → STOP gate → phases
  → DoD → commit atomique → source-guard. ROI documenté (M2-5.9, M2-5.8.A).

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
| ~~M3-METHOD-DOC~~ | ✅ | — | livré M2-5.9 |

**Effort cumulé M3 restant : ~15 j/h** (4 sprints — M3-METHOD-DOC soldé M2-5.9).

Ordre recommandé : M3-DEBT (débloque une baseline saine) → M3-JWT-USER-UUID →
M3-SEED-MIGRATION → M3-LINK-EVENT-DOCTRINE.

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

### M3-LEGACY-TOUCHES — Registre des exceptions doctrine « no legacy »  🟢 P3 · ~0 h

- **Origine** : M2-5.8.A.bis.
- **Objet** : tenir un registre des composants legacy touchés par les sprints
  M2-5+ — pour matérialiser les frontières doctrine et planifier d'éventuelles
  refontes ciblées.
- **Pourquoi** : la discipline « aucun composant legacy modifié » a tenu 10
  sprints (M2-5.0 → .8.A). M2-5.8.A.bis l'a rompue une fois, de façon assumée
  et justifiée — ce type d'exception doit être tracé, pas dilué.
- **Exceptions enregistrées** :
  - **M2-5.8.A.bis — `frontend/src/pages/LoginPage.jsx`** : ajout d'un state
    probe DEMO_MODE + d'un bouton « Connexion démo HELIOS » conditionnel + d'un
    handler. Périmètre strict : aucune modification du flux email/password
    existant, aucun refactoring. Justifié par l'Option B (le walkthrough Phase 0
    a prouvé que le prompt inline était inatteignable derrière `RequireAuth`).
- **DoD** : registre tenu à jour ; section « Exceptions doctrine » ajoutée à
  `docs/sprints/M2-5_FRONTEND_PLAN.md` §13 lors d'un prochain passage doc.

**Effort cumulé M2-5 → M3 : ~9-11 h** (8 items courts).

---

## 6. Items issus de M2-6 (sécu Cat 1 + CFO mode MV3)

Tracés par le bilan global post-clôture M2-6.B (commit `9a7c8984` +
`.bis-backlog`). Pattern doctrine : chaque commit M2-6 a mentionné une
promesse `M3-*` dans son message ; ce bloc matérialise les 4 entrées
promises et ferme l'écart inter-sprints détecté par la self-review fin
de phase.

### M3-PDF-WEASYPRINT-MIGRATION — Fidélité PDF Sol via HTML→PDF  🟢 P2 · ~1 j/h

- **Origine** : M2-6.B.pdf (commit `9a7c8984`) — Phase 1 audit cardinal Q22=C.
- **Contexte actuel** : WeasyPrint indisponible en MV3 (Cairo + Pango absents
  de l'env brew), ReportLab 4.4.10 retenu en fallback. Le PDF actuel est
  conforme Q20=C minimaliste mais ne porte pas la signature typo Fraunces +
  tokens Sol exacts.
- **Pré-requis** : installer Cairo + Pango + GDK-Pixbuf + shared-mime-info
  sur env pilote/prod (`apt-get` Ubuntu / `brew` macOS), puis `pip install
  weasyprint`.
- **Acceptation** : `python -c "from weasyprint import HTML; HTML(string='<h1>x</h1>').write_pdf()"`
  retourne bytes PDF valides ; `pdf_export_service.py` bascule branche
  WeasyPrint et tests existants restent verts.
- **Tests à pin** : `test_pdf_contains_total_47500_and_completude_phrase`
  reste vert + nouveau `test_pdf_uses_weasyprint_when_available`.
- **DoD** : install deps + adapter `pdf_export_service.py` pour réactiver
  branche WeasyPrint + retirer le fallback ReportLab si non souhaité +
  re-mesurer fidélité Sol vs ReportLab actuel.

### M3-CFO-SEMANTIC-CONVERGENCE — Counts vs sums € périmètre unifié ?  🟢 P2 · 0-3 j/h

- **Origine** : M2-6.B.backend (commit `992b5c79`) — Surprise #5 audit Phase 1.
- **Contexte actuel** : Dissociation cardinale actée MV3 — `counts_*` filtrent
  `lifecycle_state != closed` (urgence opérationnelle Marie), `sums_eur_*`
  incluent TOUS items closed inclus (portfolio CFO Jean-Marc). Cette
  dissociation peut surprendre un user habitué aux dashboards « tout-en-un ».
- **Décision** : recueil retour pilote 2 mois HELIOS/MERIDIAN, arbitrer
  post-pilote selon retour usage réel.
- **3 options post-pilote** :
  - **A — Convergence** (~0.5 j/h) : si pilote attend une sémantique unique,
    fusionner counts/sums sur même périmètre. Modifier filtre repo
    `ActionCenterItemRepository.get_summary()`.
  - **B — Filtre UI** (~2-3 j/h) : toggle « Vue urgence » vs « Vue portfolio »
    persisté en préférence user + tests E2E.
  - **C — Statu quo** (0 j/h) : si pilote confirme la dissociation comme valeur
    métier (probable — workflow CFO réel).
- **Refs** : [`docs/produit/semantique_cfo_sums_counts.md`](docs/produit/semantique_cfo_sums_counts.md)
  (doc cardinale pitch + dialogue Marie/Jean-Marc).
- **DoD** : arbitrage Amine post-collecte feedback pilote, exécution de
  l'option retenue + tests pin maintenus.

### M3-IMPACT-PERIOD-BASIS — Schéma enrichi `impact_period` débloque «€/an»  🟢 P2 · ~1.5-2 j/h

- **Origine** : M2-6.B.frontend (commit `470afd5c`) — Q16 audit Amine corrigé.
- **Contexte actuel** : MV3 affiche `47 500 €` sans suffixe « €/an » car les
  impacts seedés sont hétérogènes (anomalie facture trimestrielle / sanction
  OPERAT one-shot / gain pluri-annuel contrat / optim annuel). Afficher
  « €/an » sur les 4 mentirait sur 3.
- **Travail** : enrichir le schéma `ActionCenterItem` :
  - `impact_period: Enum["annuel", "mensuel", "one_shot", "duree_contrat"]`
  - `impact_basis: Text` (justification métier sourcée — ex. « décret 2014-1393
    art. 5 : 15 €/m² × seuil »)
- **Conséquences UI** : suffixe période contextuel par item (`/an`, `/mois`,
  « évité », etc.) côté colonne Référentiel + NarrativeBar. Format
  `47 500 €/an` débloqué pour items annuels confirmés.
- **Tests à pin** : nouveau `test_period_displayed_when_set` + maintien
  `test_helios_use_case_a_total_47500` + `test_sum_includes_closed_items_cfo_semantics`.
- **DoD** : migration Alembic 2 colonnes + seed Use Case A update + helper
  format adapté côté FE (`formatEurosWithPeriod`) + tests verts.

### M3-PERF-COCKPIT-JOUR-BASELINE-551MS — P95 breach observé live  🟢 P2 · ~0.5-2 j/h

- **Origine** : M2-6.A.3 (commit `9158ef18`) — Smoke Cas 2 découverte live.
- **Contexte actuel** : Endpoint `GET /api/cockpit/jour` mesuré **P95=551.89 ms**
  en smoke M2-6.A.3 (> budget MV3 P95=500 ms). Breach non re-confirmable
  post-restart (`uvicorn --reload` clear store in-memory — limitation MV3
  documentée [`RUNBOOK_OBSERVABILITY.md`](docs/deploy/RUNBOOK_OBSERVABILITY.md)).
- **Travail M3+** : collecte 7+ jours post-stabilisation pilote, re-confirmer
  breach persistant ou résorbé. Si persistant :
  1. Profiling endpoint (cProfile + SQLAlchemy `echo=True` slow queries log)
  2. Identifier hot path (calculs lourds ? slow query ? N+1 ?)
  3. Optimisation ciblée (index DB / cache résultat / refactor calcul)
  4. Re-mesure post-fix via `/health/metrics` 7 jours
- **Acceptation** : P95 `/api/cockpit/jour` retombe sous budget 500 ms OU
  `ENDPOINT_OVERRIDES` ajusté à 700 ms si valeur de référence métier acceptée.
- **Refs** : [`docs/deploy/RUNBOOK_OBSERVABILITY.md`](docs/deploy/RUNBOOK_OBSERVABILITY.md)
  § « Procédure ajustement budgets post-pilote ».
- **DoD** : breach résorbé OU budget overridé documenté.

### M3-BE-SQLITE-LOCK-INVESTIGATION — Lock SQLite après long usage session  🟡 P1 · ~0.5-1 j/h

- **Objet** : BE `python -m backend.main` devient hung (HTTP 000 timeout sur
  `curl /api/v4/action-center/summary` ou `/api/health`) après une longue
  session d'usage continu (>2-3h, ~12 commits enchaînés M2-6). Symptôme
  observé empiriquement en clôture M2-6.C.1-reduit (commit `6af61f58`),
  re-observé en validation pré-M2-6.C.2 (commit `8737d9b6`).
- **Origine** : Session M2-6 enchaînée (commits `e6f90423` → `8737d9b6`,
  ~12 commits avec backend reload uvicorn à chaque touch backend). Probable
  cause racine : WAL mode SQLite désactivé OU connection pool SQLAlchemy
  mal configuré OU transaction non-commitée bloquante (test seed → endpoint
  write → autre thread).
- **Symptômes observés** :
  - `curl http://127.0.0.1:8001/api/health` retourne `000` (timeout 10s)
  - Process `python main.py` toujours visible dans `ps aux` + port :8001 occupé
  - Aucune erreur log récente, pas de crash apparent
  - Restart manuel résout systématiquement (`kill -TERM <PID> && python main.py`)
  - Tient au moins ~30 min post-restart sans hang (test pré-M2-6.C.2 OK)
- **Risque pilote** : Pilote externe HELIOS/MERIDIAN à 2 mois. Un BE qui hang
  sous charge prolongée = risque opérationnel direct sur le pilote.
  **Priorité P1** (pas P0 — workaround restart fonctionnel ; pas P2/P3 — risque
  confiance pilote pendant démo).
- **Pistes d'investigation M3+** :
  1. Vérifier `PRAGMA journal_mode=WAL` actif (vs `DELETE` par défaut SQLite —
     WAL permet lecteurs concurrents pendant écriture)
  2. Auditer transactions SQLAlchemy non-commitées (`session.commit()` manquants
     dans seeds, tests, ou middleware error handlers)
  3. Vérifier connection pool size + timeout
     (`create_engine(pool_size=N, pool_timeout=T, pool_pre_ping=True)`)
  4. Logger les queries actives au moment du hung (`echo=True` SQLAlchemy debug
     puis `SELECT * FROM sqlite_master` pour identifier locks)
  5. Considérer migration PostgreSQL (cf. ADR `DATABASE_URL` postgresql commenté
     dans `backend/.env.example`) qui résout structurellement le single-writer
     SQLite — déjà candidat M3+ pour scale pilote
- **DoD** :
  - Cause racine identifiée (WAL / pool / transaction non-commit)
  - Fix implémenté (PRAGMA WAL, config pool, ou correction session leak)
  - Test pytest qui reproduit le hung pré-fix + valide post-fix (long-running
    fixture session continue + assert response time stable)
  - BE stable sur session continue >4h sans restart manuel
- **Workaround MV3** : restart manuel BE en cas de hang (`kill -TERM <PID>` +
  relance `python main.py`). ~5 secondes interruption.
- **Refs** :
  - M2-6.C.1-reduit bilan (commit `6af61f58`, validation Playwright initialement
    différée par hang BE)
  - Pré-M2-6.C.2 validation (commit `<bumped>`, restart confirmé fonctionnel)
  - [`docs/deploy/RUNBOOK_OBSERVABILITY.md`](docs/deploy/RUNBOOK_OBSERVABILITY.md)
    § « En cas d'incident — Cas 1 Latency spike soudain »
  - [`backend/.env.example`](backend/.env.example) (DATABASE_URL postgresql
    commenté — résolution structurelle candidate)

### M3-DRAWER-BREADCRUMB-PATRIMOINE-BE — Snapshots patrimoniaux pour DrawerBreadcrumb  🟢 P2 · ~1-1.5 j/h

- **Objet** : `DrawerBreadcrumb` patrimonial (organisation › site › bâtiment ›
  compteur) a été livré côté FE en M2-6.C.3 (commit 4/4) en mode MV3-ready :
  composant complet + 6 tests, mais **silencieux** car le BE
  `ActionCenterItemResponse` n'expose pas les snapshots de nom patrimoniaux
  (uniquement `organisation_id` Integer).
- **Origine** : M2-6.C.3 commit 4/4 (DrawerBreadcrumb) — STOP gate Phase 4.1
  cardinal a confirmé l'absence des champs côté BE schema. Garde-fou Amine
  immutable « aucun changement payload » a empêché l'extension dans M2-6.C.3
  (à raison — c'est un changement structurel qui mérite son sprint M3+ dédié).
- **Activation FE** : aucune (déjà prête). Dès que le BE expose les 4 champs,
  le breadcrumb s'affiche automatiquement.
- **Pistes BE M3+** :
  1. Étendre `ActionCenterItemResponse` Pydantic avec 4 champs
     optionnels snapshot : `organisation_name`, `site_name`, `building_name`,
     `meter_id` (déjà supporté côté FE).
  2. Source : pattern « UUID isolé + snapshot label » ADR-029 §3.4 (même que
     `owner_id` + `owner_display_name` M2-5.11.E). Snapshot au POST/PATCH item.
  3. Alternative : enrichir endpoint GET item par join runtime (plus coûteux,
     préfère snapshots pour cohérence pattern V4).
- **⚠ Sécu cardinale pré-activation (P1 audit M2-6.C.3)** :
  Le format PDL Enedis (`PRM-XXXXXXXX`, 14 chiffres) est classé donnée
  personnelle RGPD FR en contexte résidentiel + donnée sensible commerciale
  B2B (identifie une installation précise). DrawerBreadcrumb actuel affiche
  `meter_id` BRUT dans le DOM — récupérable par extensions navigateur, RUM
  (Sentry/DataDog), captures partagées. Combiné à org+site+building, chaîne
  d'identification complète (CWE-359 RGPD).
  **AVANT activation BE M3+, implémenter une couche de masquage côté FE** :
    a. Option A (simple) : afficher derniers 4 chiffres seulement
       (`••••••5678` pour `PRM-12345678`)
    b. Option B (référence) : remplacer par libellé fonctionnel
       (`Compteur #<short-id>` non-PDL dérivé d'un hash stable)
    c. Option C (CFO-friendly) : afficher uniquement nom site/bâtiment,
       omettre `meter_id` du breadcrumb visuel
  L'arbitrage A/B/C dépend de la valeur opérationnelle du compteur dans
  le contexte UX (CFO Marie a-t-elle besoin de l'identifiant en clair ?).
- **DoD** :
  - 4 champs snapshot exposés (Pydantic schema + repo mapping)
  - Seed `helios_use_case_a` populate ces 4 champs sur les 9 items
  - **NOUVEAU** : DrawerBreadcrumb FE intègre couche de masquage `meter_id`
    selon option A/B/C arbitrée (cf. P1 sécu ci-dessus)
  - Test contract BE schema : `assert organisation_name in response.json()`
  - Test FE : assertion que le `meter_id` brut n'apparaît jamais dans le DOM
    (uniquement la version masquée)
  - Test Playwright étape 11 valide breadcrumb visible avec ≥2 segments
- **Refs** :
  - M2-6.C.3 commit 4/4 (DrawerBreadcrumb FE livré silencieux MV3)
  - [`DrawerBreadcrumb.jsx`](frontend/src/pages/action-center-v4/components/drawer/DrawerBreadcrumb.jsx) FE composant
  - [`DrawerBreadcrumb.test.jsx`](frontend/src/pages/action-center-v4/__tests__/DrawerBreadcrumb.test.jsx) 6 tests
  - ADR-029 §3.4 pattern UUID isolé + snapshot label
  - Surprise #6 du prompt M2-6.C.3 (anticipée et matérialisée)

### M3-ROLE-LABELS-SOT-EXTRACTION — Extraire SoT mapping role→libellé FR  🟢 P2 · ~30 min

- **Objet** : `ROLE_LABELS_V4` dans `constants/narrative.js` (M2-6.C.3 commit
  2/4 split) est la **5ème copie** du même mapping rôle → libellé persona FR.
  Les 4 autres copies vivent dans `AppShell.jsx`, `AdminRolesPage.jsx`,
  `AdminAssignmentsPage.jsx`, `AdminUsersPage.jsx`. De plus, `energy_manager`
  est traduit divergence : `'Responsable Énergie'` dans AppShell/Admin vs
  `'Resp. Énergie'` dans `ROLE_LABELS_V4`. Le seuil documenté de 3 duplications
  (cf. comment narrative.js:138) est dépassé.
- **Origine** : Audit code-reviewer M2-6.C.3 P1 — la 5ème copie a été révélée
  par le split constants.js. Les 4 premières existaient déjà avant (dette
  pré-M2-6.C.3), mais leur visibilité a augmenté avec la nouvelle structure.
- **Action** :
  1. Créer `frontend/src/utils/roleLabels.js` exportant la SoT unique
  2. Arbitrer `energy_manager` → un seul libellé (recommandation :
     `'Responsable Énergie'` cohérent avec les 4 surfaces existantes ; ou
     `'Resp. Énergie'` plus court si contrainte d'espace narrative)
  3. Importer cette SoT dans les 5 surfaces (AppShell + 3 Admin + V4 NarrativeBar)
  4. Supprimer `ROLE_LABELS_V4` de `constants/narrative.js`
- **DoD** :
  - 1 fichier `utils/roleLabels.js` exporte `ROLE_LABELS` unique
  - 0 duplication du mapping role→libellé dans frontend/src/
  - `energy_manager` traduit en une seule valeur cohérente
  - Tests AppShell + Admin pages + NarrativeBar restent verts (alignement
    libellé requis)
- **Refs** :
  - M2-6.C.3 commit 2/4 (split constants exposait la dette)
  - [`narrative.js:138`](frontend/src/pages/action-center-v4/constants/narrative.js#L138) comment dette
  - [`AppShell.jsx:51-62`](frontend/src/layout/AppShell.jsx#L51-L62) SoT de référence proposée

### M3-CLEANUP-NAMING-MICRO — Batch micro-cleanup audit 3-agents M2-6.C.3  🟢 P2 · ~2-3 h

- **Objet** : 6 P2 résiduels listés par l'audit 3-agents code-reviewer post-
  M2-6.C.3 (commit `07bfb3a8`). Tous légitimes mais non-bloquants pilote.
  Non traités M2-6.C.3 (discipline atomic — sprint architecture + audit-fix
  P1 seulement). Bundle de petits cleanup à grouper en sprint dédié M3+
  pour ne pas polluer l'audit-global d'un sprint mêlé.
- **Origine** : Audit code-reviewer post-M2-6.C.3 (commit `07bfb3a8`
  mentionne explicitement le ticket comme bundle de regroupement).
- **Liste exhaustive** :
  1. `DrawerBreadcrumb.jsx` L48 — `key={index}` sur boucle segments (anti-
     pattern React, faible risque MV3 car segments statiques). Remplacer
     par `key={segment}` ou `key={`seg-${index}-${segment}`}`.
  2. `NarrativeBar.jsx` L56 — addition `sumsByPriority.P0 + .P1` en
     frontend. Borderline règle d'or « zéro calcul métier FE » : c'est
     présenté comme affichage mais si définition « décisions » évolue
     (ex. ajouter P2 à risque) le calcul FE dériverait silencieusement.
     Demander BE d'exposer `sums_eur_decisions` (= P0+P1) dans
     `ActionCenterSummaryResponse` à côté de `sums_eur_total`.
  3. `ImpactSection.test.jsx` L22 — shadow-override `emptyImpact` local
     (objet payload riche) vs `v4Mocks.js` (wrapper hook). Renommer la
     fixture locale en `EMPTY_IMPACT_PAYLOAD` ou `noImpactPayload` pour
     éliminer la confusion sémantique.
  4. `v4Mocks.js` L91/L116 — naming incohérent `setupV4HooksDefault` vs
     `setupHooksV4Mock`. Harmoniser en M3 vers `setupV4HooksDefault` +
     `setupV4HooksMock` (même préfixe + même position du `V4`).
  5. `components/narrative/ListFilterBar.jsx` — mal classé : `ListFilterBar`
     filtre la table items (kind chips + lifecycle dropdown + reset), pas
     un composant narratif. Déplacer vers `components/items/ListFilterBar.jsx`
     (co-localisation avec ItemsTable, KindCell). 1 consommateur direct +
     1 test à ajuster — risque faible.
  6. `DrawerBreadcrumb.jsx` — composant jamais affiché en MV3 (BE n'expose
     pas les champs patrimoniaux). Pattern doctrine §6.6 OK, mais charge
     cognitive pour reviewer. Lien explicite vers `M3-DRAWER-BREADCRUMB-
     PATRIMOINE-BE` déjà présent dans `ItemDetailDrawer` L155-158. Informatif.
- **DoD** :
  - 6 P2 traités en 1 commit atomique `chore(v4,cleanup): M3-CLEANUP-NAMING-
    MICRO — batch 6 P2 audit M2-6.C.3`
  - 0 régression baseline (Vitest 5289+2 maintenue)
  - Aucun nouveau scope produit
- **Refs** :
  - Audit 3-agents post-M2-6.C.3 (commit `07bfb3a8`)
  - Pattern P2-cleanup batch inauguré M2-6.C.P2-cleanup (commit `32c1a6cd`)

### M3-DOC-METHODE-FAMILY — Capitaliser amendements doctrine post-M2-6  🟢 P2 · ~1-1,5 h

- **Objet** : 4 amendements doctrine `docs/dev/methode_*.md` détectés par
  l'audit-global M2-6 Check 4 (cohérence 4 doctrines). Non bloquants merge,
  capitalisables post-merge en sprint dédié.
- **Origine** : Audit-global pré-merge M2-6 (Check 4 verdict ⚠ P2). Mention
  initiale `M3-DOC-METHODE-FAMILY` dans commit M2-6.0 (`e6f90423`) —
  « Capitalisation doctrine self-review PR avant merge ».
- **Amendements à apporter** :
  1. `methode_audit_avant_fix.md` — capitaliser **5 occurrences Phase 1
     audit M2-6** (ROI cumulé ~30-40h économisées). Section « Empirique
     M2-6 » à ajouter avec les 5 cas validés : /summary backend, V4Modal
     M2-6.C.1, owner_id M2-6.C.2, ROLE_LABELS split M2-6.C.3 commit 2/4,
     DrawerBreadcrumb M2-6.C.3 commit 4/4.
  2. `methode_self_review_pr.md` — capitaliser **5 occurrences `.bis`
     immédiat M2-6** : M2-6.B.frontend.bis (47,5 k€), M2-6.B.bis-backlog
     (traçabilité), M2-6.C.1-reduit.bis (Playwright), M2-6.C.3 audit-fix
     batch (PRM + ROLE_LABELS), audit-global.bis-backlog (ce commit).
  3. `methode_self_review_pr.md` — nouvelle section « Pattern MV3-ready
     silencieux » (inauguré M2-6.C.3 commit 4/4 DrawerBreadcrumb).
     Critères : composant FE complet + tests + Playwright, mais silencieux
     tant que BE n'expose pas la donnée. Active automatiquement dès BE
     M3+. Doctrine §6.6 anti-bruit respectée.
  4. Nouvelle doctrine candidate `methode_audit_3_agents.md` — capitaliser
     pattern **audit 3-agents post-livraison** (inauguré M2-6.C.2 +
     reproduit M2-6.C.3). Lancement parallèle code-reviewer + security +
     qa-guardian, convergence verdict, matrice décision (GO / batch fix
     P1 / STOP). Inclut le format synthèse cumulée et la matrice 5.3.
- **DoD** :
  - 3 fichiers `methode_*.md` amendés + 1 nouveau fichier
  - Cross-références entre les 4 doctrines (actuellement
    `methode_walkthrough_navigateur.md` n'en a aucune)
  - Index `docs/dev/README.md` ou équivalent à jour si applicable
- **Refs** :
  - Audit-global M2-6 Check 4 (ce commit)
  - M2-6.0 commit `e6f90423` (mention initiale M3-DOC-METHODE-FAMILY)
  - M2-6.B.bis-backlog commit `f3307069` (section "Bilan global post sous-
    phase composée" capitalisée — base de la doctrine famille)

**Effort cumulé M2-6 → M3 : ~9-17 j/h** (9 items, fourchette large car
M3-CFO-SEMANTIC dépend de l'arbitrage pilote, M3-BE-SQLITE-LOCK dépend de
la repro, M3-DRAWER-BREADCRUMB inclut désormais layer masquage PDL,
M3-CLEANUP-NAMING-MICRO + M3-DOC-METHODE-FAMILY ajoutés par audit-global).
