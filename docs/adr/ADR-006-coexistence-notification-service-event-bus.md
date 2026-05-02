# ADR-006 — Coexistence `notification_service` ↔ `event_bus`

**Statut** : Accepté
**Date** : 2026-05-02
**Sprint** : Sprint α-fin Phase 1.B (post-audit Phase 0)
**Personnes impliquées** : Amine (founder), Claude architect-helios

## Contexte

L'audit Phase 0 du chantier α moteur événements (`docs/audits/sprint_alpha_phase0_audit_20260502.md`) a révélé que **trois systèmes événements coexistent** sur la branche `claude/refonte-sol2` :

1. **`backend/services/event_bus/`** (chantier α — 9 détecteurs, ~1 771 LOC) : signaux internes typés `SolEventCard` (doctrine v1.1 §10), exposés depuis Phase 1.A via `GET /api/v1/events/upcoming` (commit `a3b48f07`).
2. **`backend/services/notification_service.py`** (521 LOC, 5 briques) : notifications in-app `build_from_compliance` / `_billing` / `_purchase` / `_consumption` / `_actions` consommées par 7 fichiers (`routes/notifications.py`, `routes/action_center.py`, `services/navigation_badges_service.py`, `services/action_workflow_service.py`, `scripts/seed_data.py`, et 2 tests).
3. **`backend/watchers/` + `routes/watchers_route.py`** (161 LOC) : veille SENTINEL-REG sources externes (CRE / Légifrance / RTE / RSS) avec persistance `RegSourceEvent` + pipeline `WatcherEventStatus` (NEW → REVIEWED → APPLIED \| DISMISSED). **Hors scope de cet ADR** — système clairement distinct (signaux externes vs internes).

L'audit a identifié un **recouvrement fonctionnel partiel** entre les deux premiers systèmes sur 4 briques :

| Brique notification_service | Détecteur event_bus équivalent |
|---|---|
| `build_from_compliance` | `compliance_deadline_detector` |
| `build_from_billing` | `billing_anomaly_detector` |
| `build_from_consumption` | `consumption_drift_detector` |
| `build_from_actions` | `action_overdue_detector` |

L'audit Q3 a tranché : `(a)` parallèle court terme + `(b)` migration moyen terme post-démo. Cet ADR formalise la décision, ses justifications et les critères de bascule.

## Décision

**Court terme (Sprint α-fin)** — coexistence stricte des deux systèmes en parallèle :

- `event_bus/*` reste **strictement intact** (réutilisation pure depuis la couche query Phase 1.A — cf. `events_query_service.py`).
- `notification_service.py` reste **strictement intact** — aucune modification, aucune migration prématurée vers les détecteurs.
- Source-guard `SG_EVENTS_05` (cf. `tests/test_events_source_guards.py`) interdit toute mutation de `event_bus/*` depuis la couche query, garantissant l'isolation.
- Documentation (cet ADR) explicite la frontière sémantique pour éviter le drift et empêcher les agents/contributeurs futurs de fusionner les deux systèmes par opportunité.

**Frontière sémantique acceptée** :

| Système | Rôle | Périmètre signaux | Persistance |
|---|---|---|---|
| `event_bus/` | Moteur de détection multi-pillar (P6 « produit pousse ») | Signaux factuels typés `SolEventCard` (9 EventTypes doctrine §10) | Stateless (détection à la volée) — store snapshot append-only `event_history_snapshot.py` Phase 9.D pour replay narrative |
| `notification_service.py` | Couche présentation in-app (badges rail, action center) | Notifications utilisateur structurées par persona | Cache déduplication via `_hash_inputs()` |

Les deux systèmes consomment partiellement les mêmes services backend SoT (`compute_portfolio_compliance`, `bill_intelligence_service`, etc.), ce qui rend le drift sémantique **possible mais surveillable** — chaque évolution d'un service SoT doit être validée côté event_bus ET notification_service.

**Moyen terme (post-démo investisseur juillet)** — migration tracée via cet ADR :

Migration des 4 briques `notification_service` recouvrantes vers détecteurs `event_bus`, avec `notification_service` recentré sur sa fonction de **couche présentation** (consommation `compute_events()` + transformation badges/action center). Plan détaillé en §Plan migration ci-dessous.

## Justification

**3 raisons (par ordre de priorité décroissante)** :

1. **Risque démo juillet > risque drift court terme**. Migration des 4 briques `notification_service` casserait potentiellement `navigation_badges_service`, `action_center`, `action_workflow_service`, `seed_data`. Pré-démo investisseur, le coût d'une régression silencieuse sur les badges rail (signal critique CFO/Marie) excède largement le coût du doublon contrôlé. La migration nécessite un cycle audit + tests + observation pilote → minimum 3 jours dev + 1 semaine observation.

2. **ADR-002 prévoit la migration phase 3 ultérieure**. Le chantier α a déjà livré ~85% (audit Phase 0 §1) sans toucher `notification_service`. Forcer la migration maintenant viole le principe de non-régression Sprint Doctrine P0 (baseline tests intangible). L'audit consolidé Sprint 2 Vague C confirme que les deux systèmes coexistent sans incident depuis ét11 (commit `c30c5624` HEAD `claude/refonte-sol2`).

3. **Frontière sémantique réelle, pas artificielle**. `event_bus.SolEventCard` répond aux 6 questions doctrine §10 (fait / périmètre / impact / action / source / confiance) — c'est un **fait observé** typé. `notification_service` produit une **notification utilisateur** dérivée (avec déduplication, persona, route deep-link UI). Les deux concepts diffèrent : un fait `event_bus` peut produire 0, 1 ou plusieurs notifications selon le persona destinataire (ex: même `compliance_deadline` → notif différente DAF vs Energy Manager). Une fusion prématurée perdrait cette nuance.

## Critères déclencheurs migration

La bascule de la coexistence vers la migration des 4 briques `notification_service` recouvrantes se déclenche si **≥ 1** des conditions suivantes est rencontrée post-démo :

1. **Drift sémantique détecté** : un service SoT évolue (ex: `compute_portfolio_compliance` change de seuil) et la couverture diverge entre `event_bus.compliance_deadline_detector` et `notification_service.build_from_compliance` (audit révèle un site flaggé non-conforme côté détecteur mais pas côté notif, ou inversement).
2. **Audit régulatoire industrialisation** (SMÉ tier 3, CSRD, DPO) exige un trail unique « qui a vu quoi quand » → une seule SoT events persistée requise. Phase 1.B+ table DB `events` (cf. ADR-002 §modèle données) bloque par construction.
3. **Tier3 consommateur additionnel** (mobile native, BI client, Zapier, webhook Teams/Slack) requiert un contrat REST cohérent → endpoint Phase 1.A `/api/v1/events/upcoming` devient SoT, `notification_service` doit l'alimenter ou être recentré présentation.
4. **Coût maintenance double** dépasse 2 jours/sprint sur 3 sprints consécutifs (mesuré via tickets « cohérence event_bus ↔ notification_service » dans tracker).
5. **Décision produit** : si la stratégie passe au push notif hors-app (email digest Marie 7h45 — Phase 2.E ADR-002), un seul moteur de détection doit nourrir email digest + badges in-app + endpoint REST → migration mécanique.

## Plan migration (hors scope α — post-démo)

5 étapes, ~7-10 jours dev cumulés. Branche dédiée `claude/sprint-merge-notif-event-bus`.

| Étape | Sujet | Durée | Dépendances |
|---|---|---:|---|
| **M1** | ADR-007 stratégie migration détaillée (mapping brique-par-brique notif → détecteur, contrats préservés `navigation_badges_service` + `action_center`, plan rollback) | 0.5 j | – |
| **M2** | Refacto `navigation_badges_service` pour consommer `compute_events()` au lieu de `notification_service.sync_notifications` (préserver schéma `NavBadgesResponse` et SG_NAV_*). Tests cumulés `test_navigation_badges*.py` doivent rester verts. | 2.0 j | M1 |
| **M3** | Refacto `action_center` + `action_workflow_service` même approche, préserver schéma `ActionCenterResponse`. | 2.0 j | M2 |
| **M4** | Suppression `notification_service.build_from_*` × 4 + dépréciation `sync_notifications` (orchestrateur). Garder `_count_summary` + `_get_thresholds` si utilisés ailleurs. | 1.5 j | M3 |
| **M5** | Tests non-régression complets (~6 027 baseline) + observation pilote 5j + bascule production. | 2.0 j | M4 |

**Critère de succès migration** : tests pytest baseline ≥ 6 027 maintenue, `navigation_badges_service` produit le même `NavBadgesResponse` qu'avant (golden snapshot test), et `notification_service.build_from_*` × 4 supprimées.

## Conséquences

- **Positives** : `event_bus/*` strictement protégé pendant Sprint α-fin (Phases 1.B → 2.F). Pas de big-bang risqué pré-démo. ADR formalisé permet aux contributeurs futurs (humains et agents) de comprendre la frontière sans la deviner.
- **Négatives / risques** : doublon contrôlé jusqu'à migration → 4 briques `notification_service` + 4 détecteurs equivalents `event_bus` peuvent diverger sur un changement de seuil amont si la double validation n'est pas appliquée. Mitigation : documentation cet ADR + critère déclencheur #1 + revue PR systématique sur tout fichier `services/compliance_*`, `services/billing_*`, `services/baseline_*`, `services/action_*`.
- **Migration** : tracée §Plan migration. Pas de date imposée — ADR active la migration sur déclencheur, pas sur calendrier. Évite la dette sprint forcée.

## Alternatives considérées

1. **Migrer immédiatement (option Q3 (c) de l'audit)** — rejeté : ~3 jours refacto pré-démo, risque casse `navigation_badges_service` + `action_center`. Coût/bénéfice défavorable Sprint α-fin.
2. **Conserver les 2 systèmes ad vitam aeternam** — rejeté : drift sémantique inévitable à long terme, complexification maintenance, audit régulatoire industrialisation impossible sans SoT unique.
3. **Migrer `notification_service` vers détecteurs `event_bus` mais conserver `notification_service` comme couche présentation** — c'est le plan migration §Plan migration. Préserve les contrats consommateurs (`NavBadgesResponse`, `ActionCenterResponse`) tout en unifiant la SoT détection.

## Tests / validation

Aucun test à créer pour cet ADR (commit doc pur). La validation court terme repose sur :

- Source-guard `SG_EVENTS_05` (`backend/tests/test_events_source_guards.py`) : `events_query_service` ne mute pas `event_bus/*`.
- Source-guards `SG_NAV_*` (`backend/tests/test_navigation_badges_source_guards.py`) : `navigation_badges_service` reste compatible `notification_service._count_summary` (mitigation couplage cross-module).
- Non-régression baseline pytest pré-démo.

La validation moyen terme (post-déclencheur) suit le plan §Plan migration M5.

## Doctrine compliance §11.3

- **Principes respectés** : 1 (cohérence cross-pillar par documentation explicite), 6 (le produit pousse — préservé via event_bus inchangé), 8.1 (zéro logique métier frontend — préservé), 13 (tout est lié — frontière documentée).
- **Anti-patterns évités** : §6.5 « refacto pré-démo non blindée », §6.4 « source de vérité dispersée sans cartographie ».
- **Personas servis** : Marie (badges rail intacts), CFO Jean-Marc (action center intact), Investisseur Sequoia (architecture documentée → réponse Q&A « comment ça scale ? »).

## Référence cross-ADR

- **ADR-001** — grammaire Sol §5 industrialisée (consommée par `event_bus` titres déjà narrativisés).
- **ADR-002** — chantier α moteur événements (architecture parente, §migration phase 3 ultérieure).
- **ADR-003** — chantier β multi-archetype (orthogonal, pas d'impact).
- **ADR-004** — chantier δ transformation acronymes (consommé par titres `event_bus`).
- **ADR-005** — ParameterStore tier-2 mitigation YAML (utilisé par détecteurs `event_bus` pour proxies CFO).

## Délégations sortantes

- Migration M2-M5 : `implementer` (chaîné `test-engineer` + `code-reviewer` + `qa-guardian` pre-merge).
- Validation cohérence détection cross-system : `bill-intelligence` (briques billing), `regulatory-expert` (briques compliance).
- Validation org-scoping multi-tenant lors migration : `security-auditor`.
- Suivi déclencheurs : ADR consultable + tracker tickets « cohérence event_bus ↔ notification_service ».

## Référence audit + commits

- Audit Phase 0 chantier α : `docs/audits/sprint_alpha_phase0_audit_20260502.md` (§3 Cartographie 3 sources, §5 Risques R1, §7 Q3).
- Phase 1.A endpoint REST : commit `a3b48f07` (`feat(alpha-fin): Phase 1.A — REST /api/v1/events/upcoming + query layer`).
- Sprint nav P1.2 navigation badges (consommateur `notification_service`) : commit `6c4cc362` (`feat(nav-p1): Phase 2.A — aggregate /api/v1/navigation/badges`).
- Source-guards `SG_EVENTS_*` (Phase 1.A) : `backend/tests/test_events_source_guards.py`.
- Source-guards `SG_NAV_*` (Phase 2.A nav) : `backend/tests/test_navigation_badges_source_guards.py`.
