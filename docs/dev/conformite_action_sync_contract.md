# Boucle Conformité → Centre d'Action — contrat & fondations

> **Sprint** : Conformité P0 (2026-05-23) — fondations livrées (service lecteur).
> **Sprint suivant** : P1 — endpoint d'écriture + idempotency-Key + audit trail.
> **Service** : `backend/services/v4/conformite_action_sync_service.py`
> **Référence audit** : `docs/audits/audit_brique_conformite_deep_readonly_2026_05_23.md` §7 et §11 item 6.

---

## 1. Pourquoi cette boucle

Post-P0-B patrimoine, le frontend reçoit pour chaque règle réglementaire en
`DATA_MISSING` un payload enrichi avec `remediation_field`, `remediation_label_fr`,
`cta_label_fr` et `affected_site_ids`. Le composant `CadreApplicable` (Cockpit
Stratégique) permet à l'utilisateur de cliquer "Compléter la surface" et arrive
sur Patrimoine filtré (`?incomplete=DT`).

**Trou identifié par l'audit Conformité P0** : aucune automatisation côté
backend ne crée d'`ActionCenterItem` à partir de ces `DATA_MISSING`. Le DAF
qui veut "voir toutes les actions à faire" dans le Centre d'Action ne les
trouve pas — il doit créer manuellement chaque tâche.

La boucle Conformité → Centre d'Action ferme ce trou : à partir de la
photographie réglementaire (`compute_applicability`), on génère un plan
d'`ActionItemDraft` qui peut être créé / mis à jour idempotently dans le
Centre d'Action.

---

## 2. Doctrine respectée (rappel amendement 2026-05-23)

- Pas de nouveau menu, pas de nouvel onglet principal.
- Pas de nouvelle route exposée dans ce sprint (P0).
- Pas de nouvelle brique ACC / PMO / Flex / Partner Hub.
- `/conformite` reste le hub unique pour le périmètre DT/BACS/APER/SMÉ/BEGES.
- Le Centre d'Action V4 existant reçoit les items via les endpoints déjà en place
  (`POST /api/v4/action-center/items`) — aucune nouvelle surface utilisateur.

---

## 3. Découpage P0 vs P1

### Phase P0 (livré 2026-05-23) — `plan_remediation_actions_for_org`

**READ-ONLY** : calcule ce que devraient être les items à créer/mettre à jour.
N'écrit RIEN en base.

```python
from services.v4.conformite_action_sync_service import plan_remediation_actions_for_org

plan = plan_remediation_actions_for_org(db, org_id=42)
# plan.items_to_create -> list[ActionItemDraft]
# plan.summary -> {"total": 7, "by_rule_DT": 3, "by_level_site": 5, ...}
# plan.computed_at -> ISO timestamp
```

**Garanties** :
- **Idempotent** : 2 appels successifs sans changement réglementaire produisent
  le même plan avec les mêmes `external_ref`.
- **JSON-sérialisable** : `plan.to_dict()` est prêt à exposer via API ou logger.
- **Pas d'écriture** : aucun `ActionCenterItem` ni event log créé.

**Tests verrous** : `backend/tests/services/test_conformite_action_sync_service.py` (10 tests, couvrant les 5 statuts cardinaux, l'idempotency, l'absence d'écriture, et la sérialisation).

### Phase P1 (à livrer) — endpoint d'écriture

```
POST /api/conformite/sync-remediation-actions
Headers:
  X-Org-Id: 42
  Idempotency-Key: 2026-05-23T10:00:00Z   (cf. ADR-025 §1.4 IS6)
Response:
  200 OK
  {
    "created": [...],
    "updated": [...],
    "skipped_existing": [...],
    "summary": {...}
  }
```

**Comportement attendu** :
1. Appelle `plan_remediation_actions_for_org(db, org_id)` (le service P0).
2. Pour chaque `ActionItemDraft` :
   - Cherche l'`ActionCenterItem` existant par `external_ref` + `organisation_id`.
   - Si trouvé et OPEN/IN_PROGRESS → mise à jour cosmétique (title, description) + skip création.
   - Si trouvé et CLOSED → skip (idempotency : un item résolu n'est pas recréé).
   - Sinon → création via `ActionCenterItemRepository.create(...)`.
3. Pour chaque création : écrit `action_event_log` event_type=`item_created_from_rule`
   avec payload `{rule_code, reason_code, scope_level, scope_id}`.
4. Réponse JSON : compteurs séparés `created` / `updated` / `skipped`.

**Sécurité** :
- Org-scoping cardinal via `resolve_org_id`.
- `Idempotency-Key` obligatoire (header) — la 2e requête avec la même clé
  retourne la 1re réponse (idem `POST /items` actuel).
- Rate limit `QUOTA_WRITE_V4` partagé avec les autres POST V4.

**Tests à prévoir P1** :
- création initiale (N items créés)
- 2e appel idempotency-Key → même réponse, zéro nouvelle ligne
- nouvelle DATA_MISSING apparue → 1 nouvel item créé, autres skip
- DATA_MISSING résolue (ex : surface saisie) → item existant clôturé automatiquement (ou pas, à arbitrer P1)
- multi-org : l'endpoint refuse cross-org via 404

---

## 4. Mapping règle → ActionItemDraft

| Réglementation | `kind` | `domain` | Exemple `title_fr` |
|---|---|---|---|
| DT.DATA_MISSING.* | `EVIDENCE_REQUEST` | `CONFORMITE` | "Décret Tertiaire — Surface tertiaire à compléter" |
| BACS.DATA_MISSING.CVC_POWER | `EVIDENCE_REQUEST` | `CONFORMITE` | "Régulation chauffage (BACS) — Puissance CVC à compléter" |
| APER.DATA_MISSING.* | `EVIDENCE_REQUEST` | `CONFORMITE` | "EnR parking / toiture (APER) — Surface de parking à compléter" |
| SME.DATA_MISSING.* | `EVIDENCE_REQUEST` | `CONFORMITE` | "Audit énergétique (SMÉ) — Effectif de l'organisation à compléter" |
| BEGES.DATA_MISSING.EFFECTIF | `EVIDENCE_REQUEST` | `CONFORMITE` | "Bilan GES réglementaire — Effectif de l'organisation à compléter" |

Tous les drafts sont `kind=EVIDENCE_REQUEST` (par définition : "demande de donnée
à fournir") et `domain=CONFORMITE`. Le validator `validate_evidence_required_for_closure`
(P0-1) refuse leur clôture en RESOLVED sans preuve vérifiée → la boucle est
auto-cohérente (créer un item ⇒ exiger une preuve avant de le clôturer).

---

## 5. Clé d'idempotency `external_ref`

**Pattern** : `{rule_code}:{scope_level}:{scope_id}:{reason_code}`

Exemples :
- `DT:site:42:DT.DATA_MISSING.SURFACE`
- `BACS:site:42:BACS.DATA_MISSING.CVC_POWER`
- `SME:organisation:7:SME.DATA_MISSING.EFFECTIF`

**Garanties** :
- Stable entre 2 appels (testé : `test_plan_external_ref_is_stable`)
- Unique par (rule, scope, reason) → permet UPSERT côté P1
- Reflète le contexte métier → debugging clair (`SELECT * FROM action_center_items WHERE external_ref LIKE 'DT:%'`)

---

## 6. Hors scope P0-5 (et hors scope P1 explicite)

- **APPLICABLE deadlines** : DT 2030, APER 2026/2028, SMÉ 11/10/2026 → ne génèrent pas
  encore d'items DEADLINE/ACTION. P1+ pour ces kinds.
- **NOT_APPLICABLE / UNKNOWN** : ne génèrent rien (rien à faire pour l'utilisateur).
- **ACC / PMO / Flex / Partner Hub** : hors scope total (cf. amendement
  2026-05-23 doctrine navigation).

---

## 7. Migration douce (pas de big bang)

P0 livre le service en lecture seule → on peut tester la qualité du plan sans
risquer de polluer le Centre d'Action avec des dizaines d'items générés
inopinément. P1 livre l'endpoint d'écriture quand le plan est jugé fiable
sur un panel d'organisations réelles.

Pendant la phase intermédiaire :
- Un admin peut lancer `python -c "from services.v4.conformite_action_sync_service import plan_remediation_actions_for_org; ..."` pour inspecter le plan d'une organisation.
- Aucun item n'est créé automatiquement.
- L'utilisateur final continue à créer ses items via le CTA "Compléter la surface" du CadreApplicable (P0-B).

---

## 8. Critères d'acceptation P1 (rappel pour le sprint suivant)

- [x] Endpoint `POST /api/conformite/sync-remediation-actions` exposé.
- [x] Header `Idempotency-Key` validé UUID (400 `IDEMPOTENCY_KEY_INVALID` sinon) ;
      idempotence métier par signature `(org_id, kind, domain, title)` côté serveur.
- [x] Org-scoping via `populate_org_context` (V4) + `require_v4_role(USER, ADMIN)`.
- [x] Tests : création initiale + replay idempotent + NOT_APPLICABLE = 0 + Idempotency-Key
      invalide + item clos non re-créé + audit event log (`tests/test_conformite_sync_remediation_actions.py` — 7 tests).
- [x] Audit trail écrit pour chaque création : `ActionEventLog(event_type=created,
      event_payload.source="regulatory_rule", rule_code, reason_code, scope_level,
      remediation_field)`. Le whitelist `EventType` (16 valeurs strictes) ne permet pas
      d'ajouter `item_created_from_rule` sans migration DDL — on encode l'origine
      réglementaire dans `event_payload.source` à la place.
- [x] UI : bouton "Créer les actions à traiter" dans le header `/conformite` (à côté
      de "Réévaluer"). Toast récap `{created, skipped_existing, skipped_resolved}`.
- [x] Aucun nouvel écran, aucun nouveau menu, aucune nouvelle brique.

---

## 9. Conformité P1 — closure 2026-05-23

Sprint Conformité P1 livré sur `claude/conformite-p1` :

| Chantier | Livrables | Tests verts |
|---|---|---|
| **C1** — Endpoint sync | `backend/routes/conformite_sync.py` + `main.py` include | 7 |
| **C2** — UI bouton synchroniser | `ConformitePage.jsx` (header actions) + `services/api/conformite.js::syncConformiteRemediationActions` | n/a (E2E manuel) |
| **C3** — UI Org/EJ minimal SMÉ/BEGES | `components/conformite/SmeBegesProfileCard.jsx` + extension schemas `OrganisationUpdate`/`EntiteJuridiqueUpdate` + serializers `_org_to_dict`/`_entite_to_dict` | 8 |
| **C4** — APER gate roof manquant | `tests/regulatory/test_rule_aper.py` (3 nouveaux tests : parking < seuil + roof NULL → DATA_MISSING.ROOF_AREA) | 14 (3 nouveaux) |
| **C5** — Cleanup legacy | 6 endpoints CEE Pipeline V69 → 410 Gone + 2 doublons BACS regops → 410 Gone (`compliance.py`, `bacs.py`) | 9 |
| **C6** — Evidence P1 | `services/v4/evidence_validity_service.py` (validité par règle : DT 1 an, BACS 3 ans, SMÉ ISO 50001 3 ans, audit énergétique 4 ans, BEGES 3 ans, défaut 90 j) + `GET /evidences/{id}/download` dans `routes/v4/action_center.py` | 25 (19 validity + 6 download) |
| **Total** | — | **63 tests backend** |

**Doctrine respectée** : `/conformite` reste le hub unique. Aucun menu ACC / PMO /
Flex / Partner Hub créé. Tous les boutons et formulaires sont des sections de
`/conformite`. Aucune route `/acc`. Frontend strict display-only + appels REST
(zero business logic). Aucune migration DDL nécessaire (Alembic neutre).
