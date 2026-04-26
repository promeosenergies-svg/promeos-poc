# ADR-002 — Chantier α moteur d'événements proactif

**Statut** : Proposé
**Date** : 2026-04-26
**Sprint** : S2 (semaines 4-5)
**Personnes impliquées** : Amine (founder), Claude architect-helios

## Contexte

Test doctrinal T6 (J vs J+1) FAIL universel sur 7 piliers (Sprint 0 audit). Principe 6 "Le produit pousse, ne tire pas" et principe 7 "Le patrimoine vit, le produit suit" restent partiels sans ce moteur.

Backend mature 6/7 piliers contient déjà les détecteurs : `bill_intelligence/engine.py` (anomalies factures), `services/ems/signature_service.py` (dérives baseline CUSUM), `regops/scoring.py` (échéances DT/BACS/APER), `cost_simulator_2026.py` (fenêtres EPEX), agent **SENTINEL-REG** (cf `memory/agent_veille_reglementaire.md` 17 mécanismes), `flex_nebco_service.py` (fenêtres NEBCO). Mais aucune orchestration commune, aucune persistance d'événement, aucune priorisation par impact, aucune distribution dans les week-cards de l'ADR-001.

**Inventaire Sprint 0bis** : `notification_service.py` couvre 65% (5 briques compliance/consumption/billing/contract/action) — utiliser comme socle. **Lacune vraie : scheduler backend (0%) à construire.**

Watchlist frontend `models/dashboardEssentials.buildWatchlist` est un anti-pattern §8.1 (logique métier frontend) — à migrer backend.

## Décision

### Architecture

**Event bus in-process Python** (pas Redis pour démo juillet — éviter dépendance infra). Pattern publisher/subscriber via `backend/events/event_bus.py` (asyncio queue).

**Scheduler APScheduler** (pas Celery — overkill démo). Cron-style :
- Détecteurs lourds (signature CUSUM, scoring RegOps) : toutes les 6h
- Détecteurs marché (EPEX, NEBCO) : toutes les heures pendant fenêtre J-1 9h30 → J 22h
- SENTINEL-REG poll sources veille : 2x/jour (matin/soir)
- Email digest Marie : daily 7h45 Europe/Paris
- Détecteurs anomalies factures : à l'ingestion R6X / PHOTO

Migration Redis + Celery prévue post-démo (ADR ultérieur).

### Modèle données

Nouvelle table `events` :
```
events (
  id uuid PK,
  org_id uuid FK NOT NULL,  -- org-scoping mandatory
  site_id uuid FK NULL,
  pillar enum,  -- bill_intel | regops | ems | achat | flex | patrimoine | sentinel
  type enum,  -- anomaly_invoice | baseline_drift | regulatory_deadline | epex_window | nebco_window | regulatory_change | contract_renewal | data_quality
  severity enum,  -- info | watch | major | critical
  impact_eur decimal NULL,
  urgency_days int NULL,
  confidence enum,  -- high | medium | low
  card_type enum,  -- watch | todo | good_news | drift (pour SolWeekCards ADR-001)
  title text,  -- déjà transformé acronymes (cf ADR-004)
  body text,  -- narrative 1-2 lignes
  cta_route varchar NULL,  -- deep-link vers page Sol pertinente
  payload jsonb,  -- data détecteur
  detected_at timestamp,
  expires_at timestamp NULL,
  status enum,  -- new | seen | snoozed_until | dismissed | resolved
  status_changed_at timestamp,
  user_id uuid NULL  -- qui a marqué seen/snooze/dismiss
)
```
Index : `(org_id, status, severity, detected_at desc)`, `(org_id, expires_at)` pour cleanup.

### Priorisation par impact

Score canonique calculé backend (jamais frontend) :
```
score = ln(1 + impact_eur) * severity_weight * urgency_factor * confidence_factor
severity_weight = { critical: 4, major: 2, watch: 1, info: 0.5 }
urgency_factor = max(0.5, min(3, 30 / urgency_days))
confidence_factor = { high: 1.0, medium: 0.7, low: 0.4 }
```
SoT formule dans `backend/services/events/event_prioritizer.py`. Test source-guard interdit toute reformulation frontend.

### Endpoint contrat

`GET /api/events/upcoming?org_id=X&persona=daily|comex&page_key=cockpit_daily|patrimoine|...&horizon_days=7`
Réponse :
```
{
  briefing_narrative: string,  -- 2-3 lignes synthèse top events
  cards: [{ type, title, body, cta, impact_eur, urgency_days, severity, source }] (exactement 3),
  total_events_pending: int,
  next_refresh_at: timestamp,
  provenance: { source, confidence, updated_at }
}
```

`POST /api/events/{event_id}/status` — body `{ status: seen|snoozed|dismissed, snooze_until? }` org-scoping enforced.

### Détecteurs minimaux S2

Réutilisation services existants — wrappers publishers vers event bus :
1. `bill_intel.invoice_anomaly_detector` (existe `engine.py`) → events type `anomaly_invoice`
2. `ems.baseline_drift_detector` (existe `signature_service.py` CUSUM) → events `baseline_drift`
3. `regops.deadline_scanner` (à créer, lit `RegAssessment` + `regulatory_calendar` skill) → events `regulatory_deadline` (DT 2030, BACS 2027, APER, Audit SMÉ 11/10/2026)
4. `achat.epex_window_detector` (wrap `cost_simulator_2026.py`) → events `epex_window`
5. `flex.nebco_window_detector` (wrap `flex_nebco_service.py`) → events `nebco_window`
6. `sentinel_reg.regulatory_change_detector` (wrap agent SENTINEL-REG, poll 28 sources veille KB `reference_sources_veille_kb.md`) → events `regulatory_change`
7. `achat.contract_renewal_detector` (lit `Contract.renewal_date - 90j`) → events `contract_renewal`

### Notifications hors-app

Module `backend/services/notifications/` (existe — étendre, ne pas reconstruire) :
- **Email digest matinal Marie 7h45** : SMTP relay (provider `Postmark` — fallback `SES`). Template HTML densifié reproduisant structure week-cards. Opt-in par user via `User.notification_preferences`
- **SMS critique Jean-Marc** : provider `Twilio`. Trigger : event `severity=critical AND impact_eur > seuil_user (default 5000€)`. Quota max 3/semaine pour éviter fatigue
- **Webhook Teams/Slack optionnel** : Phase 2 post-démo (signalé mais non bloquant)

Persistance des envois : table `notification_log` (event_id FK, channel, sent_at, delivery_status). RGPD : opt-in explicite, désinscription un clic.

### Migration watchlist frontend

`models/dashboardEssentials.buildWatchlist` (frontend) → supprimé S2.5, remplacé par hook `useEvents(pageKey, persona)` qui appelle `/api/events/upcoming`. Test source-guard `test_no_buildWatchlist_in_frontend`.

## Conséquences

- **Positives** : test T6 (J vs J+1) PASS sur 7 piliers, principe 6+7 incarnés, pattern Sprint 0 #5 résolu (logique frontend migrée)
- **Négatives / risques** : APScheduler in-process = SPOF si backend redémarre — events à re-détecter au boot via `replay_missed_runs=True`. Twilio coût ~0.08€/SMS — quota strict obligatoire
- **Migration** : S2.1 event bus + table + 3 détecteurs (bill, ems, regops) → S2.2 endpoint /api/events/upcoming + suppression buildWatchlist → S2.3 détecteurs achat+flex+sentinel + email digest → S2.4 SMS critique

## Alternatives considérées

1. **Redis Streams + Celery dès S2** — rejeté : surdimensionné pour démo juillet, impose ops Redis sur démo investisseur. Migration prévue post-démo
2. **Polling frontend toutes les 30s** — rejeté : viole §8.1, charge serveur, latence push
3. **WebSocket push temps réel** — différé : intéressant mais hors scope démo. Roadmap S7+ pour cockpit live

## Tests / validation

- T6 (J vs J+1) automatisé via `tests/doctrine/test_t6_day_j_evolution.py` : snapshot week-cards J, mock `now()` à J+1, assert ≥1 card a changé d'état/priorité
- Test source-guard `test_no_buildWatchlist_frontend`
- Test event_prioritizer formule canonique invariante
- Test org-scoping leak : event org_A ne fuit jamais vers org_B (lié `security-auditor`)
- Tests détecteurs unitaires : mock RegAssessment/Contract/Anomaly → assert event publié

## Doctrine compliance §11.3

- **Principes respectés** : 6 (produit pousse), 7 (patrimoine vit), 4 (densité — week-cards toujours pleines), 10 (transformation — events typés non bruts)
- **Anti-patterns évités** : §6.4 page identique J vs J+1, §6.5 logique frontend (buildWatchlist)
- **Personas servis** : Marie (digest 7h45), Jean-Marc (SMS critique seuil €), investisseur (démo "le produit s'écrit chaque jour")

## Référence cross-ADR

ADR-001 (week-cards alimentées par /api/events/upcoming), ADR-003 (events filtrés par archetype), ADR-004 (titres events transformés via dictionnaire). Memory : `agent_veille_reglementaire.md`, `reference_sources_veille_kb.md`, `reference_flex_index_2026.md`, `reference_regulatory_landscape_2026_2050.md`. Doctrine §9.3 chantier α.

## Délégations sortantes

- Implémentation S2 : `implementer` (chaîné `test-engineer` + `code-reviewer` + `qa-guardian` pre-merge)
- Validation détecteurs métier : `regulatory-expert` (RegOps), `bill-intelligence` (factures), `ems-expert` (CUSUM dérives)
- Validation org-scoping events : `security-auditor`
- Validation infra événementielle : `data-connector` (sources externes 28 KB)
