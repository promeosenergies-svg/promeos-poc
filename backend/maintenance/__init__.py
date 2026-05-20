"""
PROMEOS V4 · Maintenance jobs (purge mensuelle · ADR-029 IE5).

Scaffold Sprint M2-1. Implémentation Sprint M2-6 (avec feature flag OFF par défaut).

Invariant cardinal :
- IE5 : aucune purge silencieuse — triple garde-fou
        (1) Feature flag `RETENTION_PURGE_ENABLED` (env)
        (2) Dry-run mode `RETENTION_PURGE_DRY_RUN_FIRST` (env)
        (3) Trace `security_audit_log` avec correlation_id

Modules planifiés Sprint M2-6 :
- retention_purge.py : `monthly_retention_purge()` APScheduler cron
                       (1er du mois 2h UTC · off-peak)

Calendrier activation :
  Mois 2-3 : RETENTION_PURGE_ENABLED=False · trace 'skipped'
  Mois 4 J-7 : RETENTION_PURGE_ENABLED=True + DRY_RUN_FIRST=True · counts only
  Mois 4 J+1 : RETENTION_PURGE_DRY_RUN_FIRST=False · purge réelle
  Mois 5+ : régime cruise mensuel

Source : docs/dev/L6_ADR-029_evidence_audit_trail.md §12 (commit 15711df4).
"""
