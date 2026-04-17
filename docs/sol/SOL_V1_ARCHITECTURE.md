# Sol V1 — Architecture technique « Zéro Défaut »

**Scope** : 5 actions agentiques en 8 semaines, 5 lois non-négociables, LLM sandboxé, audit complet.
**Stack** : FastAPI + SQLAlchemy (backend) · React 18 + Vite (frontend) · SQLite→Postgres (DB) · Claude Haiku (LLM, rôles limités).

---

## 1. Les 5 lois en code

| Loi | Implémentation | Fichier |
|---|---|---|
| **L1 — Prévisualisation intégrale** | `ActionPlan.preview` obligatoire avant exécution ; `<SolActionPreview>` affiche le contenu final | `sol/planner.py` + `ui/sol/ActionPreview.jsx` |
| **L2 — Réversible ou différé** | `ActionPlan.grace_period_seconds` ≥ 900 (15 min) ; `SolPendingAction` table ; job `revert_or_execute` | `sol/scheduler.py` + `models/sol.py` |
| **L3 — Moteurs déterministes** | Chaque action = module Python isolé avec `dry_run()` / `execute(confirmation_token)` | `sol/engines/*.py` |
| **L4 — Audit complet** | `SolActionLog` append-only, RGPD-aware, exportable | `models/sol.py` + `routes/sol_audit.py` |
| **L5 — Refus explicite** | `ActionPlan.confidence_score` < seuil → `PlanRefused` avec `reason_fr` humain | `sol/validator.py` |

---

## 2. Arborescence fichiers à créer

### Backend
```
backend/
  sol/
    __init__.py
    intent.py               # classifie la demande utilisateur → IntentKind
    planner.py              # génère ActionPlan pour un intent reconnu
    validator.py            # valide ActionPlan contre les 5 lois
    scheduler.py            # cron + job queue pour grace_period + exécution différée
    audit.py                # wrapper SolActionLog (append-only)
    boundaries.py           # règles de refus (hors-domaine, légal, financier)
    llm_client.py           # wrapper Claude Haiku, 3 rôles stricts (CLASSIFY / EXPLAIN / SUMMARIZE)
    voice.py                # templates phrases + frenchifier (espaces fines, guillemets)
    context.py              # mémoire courte : scope, 3 dernières actions, horizon temporel

    engines/
      __init__.py
      invoice_dispute.py    # Action 1 — contestation facture
      exec_report.py        # Action 5 — rapport mensuel exécutif
      dt_action_plan.py     # Action 4 — plan d'action DT chiffré
      ao_builder.py         # Action 2 — appel d'offres fournisseurs
      operat_builder.py     # Action 3 — déclaration OPERAT

    prompts/
      v1/
        classify_intent.txt
        explain_plan.txt
        summarize_result.txt

  models/
    sol.py                  # SolActionLog, SolPendingAction, SolOrgPolicy, SolConfirmationToken

  routes/
    sol.py                  # /api/sol/ask · /api/sol/propose · /api/sol/confirm · /api/sol/cancel
    sol_audit.py            # /api/sol/audit/{org_id} · export CSV/PDF

  tests/
    sol/
      test_intent.py
      test_planner.py
      test_validator.py
      test_engines_invoice_dispute.py
      test_engines_exec_report.py
      test_engines_dt_action_plan.py
      test_engines_ao_builder.py
      test_engines_operat_builder.py
      test_scheduler_grace_period.py
      test_audit_immutable.py
      test_llm_fallback.py
      test_adversarial_prompts.py     # injections, jailbreak, prompts pourris
```

### Frontend
```
frontend/src/
  sol/
    SolCartouche.jsx        # status bar bas-droit, 5 états (repos/propose/pending/executing/done)
    SolHero.jsx             # carte héro "Sol propose une action" dans les pages
    SolActionPreview.jsx    # drawer de prévisualisation avant validation
    SolPendingBanner.jsx    # bannière pending dans le top de la page concernée
    SolHeadline.jsx         # phrase humaine au-dessus d'un KPI/chart
    SolAsk.jsx              # mode conversation (Cmd+K ou clic cartouche)
    SolJournal.jsx          # journal d'audit complet, filtrable, exportable
    api.js                  # client Sol : propose, confirm, cancel, ask, audit
    hooks/
      useSolProposals.js    # fetch propositions actives pour scope courant
      useSolPending.js      # fetch pending actions
    __tests__/
      SolActionPreview.test.jsx
      SolCartouche.test.jsx
      SolHeadline.test.jsx
      frenchifier.test.js
```

---

## 3. Schéma base de données

Voir prompt Sprint 1-2 pour détail des 4 tables : `sol_action_log`, `sol_pending_action`, `sol_confirmation_token`, `sol_org_policy`.

[... architecture complète fournie par Amine, voir conversation session 17/04/2026 ...]

---

Document source de vérité ingéré depuis la conversation Amine — version V1 à auditer avant Sprint 1-2.
