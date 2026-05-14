# PROMEOS V4 · Annexe Risques Consolidés Mois 2-6

> Version : v1.0 · 2026-05-14
> Source : ADR-025/026/027/028/029 sections Risques + L8 + L9
> Statut : Référence opérationnelle Mois 2-6
> Audience : opérateur projet (Amine) + équipe backend Mois 2

---

## 0. Mode d'emploi

Cette annexe consolide **tous les risques** identifiés dans les 10 livrables Mois 1 en un seul tableau opérationnel. Elle complète L9 §6 (qui ne liste que les 6 risques Mois 2 majeurs).

**Comment utiliser** :

1. **Sprint planning** : avant chaque sprint M2-X, lire les risques applicables
2. **Daily check** : surveiller les indicateurs early-warning du jour
3. **Si incident** : appliquer le Plan B documenté
4. **Post-mortem** : ajouter de nouveaux risques observés (versionner v1.0 → v1.1)

**Légende criticité** :
- **P0** : bloquant pour la prod / sécurité / RGPD (action immédiate)
- **P1** : crédibilité ou intégrité menacée (action sous 48h)
- **P2** : optimisation / dette technique (planifier)

---

## 1. Risques P0 (12)

### R0-1 · IDOR cross-org via décorateur oublié (IS1)

| Champ | Détail |
|---|---|
| Source | ADR-027 §10 M1 + IS1 |
| Sprint | M2-3 (sécurité) · M2-4 (routes) |
| Probabilité | Moyenne |
| Impact | Très élevé (fuite data + RGPD + perte confiance) |
| Indicateur early-warning | CI : source-guard `test_all_aci_routes_have_org_scoped_decorator` échoue · logs : routes 200 sur cross-org tests |
| Plan B | Désactiver feature flag de la route fautive · audit IDOR matrix 288 forcé · hotfix décorateur + tests |
| Mitigation préventive | 50 source-guards CI + IDOR matrix 288 cellules tests automatisés |

### R0-2 · Privilege escalation via correct-kind (IS5)

| Champ | Détail |
|---|---|
| Source | ADR-027 §10 M2 + IS5 |
| Sprint | M2-3 + M2-4 |
| Probabilité | Faible |
| Impact | Très élevé (admin compromis) |
| Indicateur early-warning | `security_audit_log` : events `privilege.escalation.attempt` répétés |
| Plan B | Désactiver endpoint `/correct-kind` · audit immédiat · rotation JWT secret |
| Mitigation préventive | `admin_only_with_fresh_token` + token <5min obligatoire |

### R0-3 · Logs leak PII RGPD (IS7 + IS8)

| Champ | Détail |
|---|---|
| Source | ADR-027 §10 M7 + ADR-029 §10 |
| Sprint | M2-3 + M2-6 |
| Probabilité | Moyenne |
| Impact | Très élevé (RGPD CNIL · amende potentielle) |
| Indicateur early-warning | source-guard `test_logs_no_body` échoue · audit log contient emails/tokens |
| Plan B | Purge immédiate des logs concernés · notification CNIL si <72h |
| Mitigation préventive | structlog sanitization + IP anonymisée /24 /48 + source-guards |

### R0-4 · Backup commit accidentel dans Git (IS10 + I9)

| Champ | Détail |
|---|---|
| Source | ADR-026 I9 + ADR-027 IS10 |
| Sprint | M2-1 (gitignore setup) |
| Probabilité | Moyenne (négligence humaine) |
| Impact | Très élevé (data clients dans repo public) |
| Indicateur early-warning | gitleaks CI échoue · `git status` montre `.backup` ou `*.sql` |
| Plan B | `git filter-branch` immédiat + force push + rotation tous secrets exposés |
| Mitigation préventive | `.gitignore` strict + source-guard `test_gitignore_excludes_backups` |

### R0-5 · Backup pré-cutover corrompu (I5)

| Champ | Détail |
|---|---|
| Source | ADR-026 §10 + I5 |
| Sprint | Mois 4 J-1 |
| Probabilité | Faible |
| Impact | Très élevé (rollback impossible si cutover échoue) |
| Indicateur early-warning | checksums SHA256 ne matchent pas · restore test J-1 échoue |
| Plan B | **Cutover REPORTÉ.** Investigation backup. Refaire triple artefact + restore test sur 2e environnement |
| Mitigation préventive | Triple artefact (binaire + SQL + JSON) + restore test J-1 obligatoire |

### R0-6 · Suppression legacy prématurée Mois 5 (I6)

| Champ | Détail |
|---|---|
| Source | ADR-026 I6 + L8 §1.1 |
| Sprint | Mois 5 J+14 |
| Probabilité | Faible |
| Impact | Très élevé (perte data legacy si V4 instable) |
| Indicateur early-warning | Pression deadline sans STOP GATE 8/8 validé |
| Plan B | **REFUSER suppression** tant que STOP GATE n'est pas 8/8 ✅. Reporter d'1 mois si nécessaire |
| Mitigation préventive | Checklist STOP GATE binaire manuelle + validation Amine explicite |

### R0-7 · Auto-close récurrence P0/P1 sans preuve (IL7)

| Champ | Détail |
|---|---|
| Source | ADR-028 §12 + IL7 |
| Sprint | M2-5 |
| Probabilité | Moyenne |
| Impact | Élevé (risque conformité enterré silencieusement) |
| Indicateur early-warning | logs : events `auto_close.recurrence.completed` sur items P0/P1 sans `evidence_id` |
| Plan B | Rollback transitions auto-close fautives · investigation cause · audit `regulatory_applicability_service` |
| Mitigation préventive | IL7 check obligatoire `has_evidence OR has_justification` avant auto-close |

### R0-8 · `expired` clôture risque actif (IL4)

| Champ | Détail |
|---|---|
| Source | ADR-028 §12 + IL4 |
| Sprint | M2-5 |
| Probabilité | Moyenne (erreur humaine) |
| Impact | Très élevé (RGPD + conformité enterrée) |
| Indicateur early-warning | logs : `expired` closure_reason sur item `domain=conformite, priority=P0/P1` |
| Plan B | Réouvrir item (admin + fresh token + justification) · audit cause · escalade |
| Mitigation préventive | `verify_closure_reason_valid` IL4 check + tests unit |

### R0-9 · Magic bytes MIME contourné (IE9)

| Champ | Détail |
|---|---|
| Source | ADR-029 §12 + IE9 |
| Sprint | M2-6 |
| Probabilité | Faible |
| Impact | Très élevé (upload malware sous PDF déguisé) |
| Indicateur early-warning | source-guard `test_IE9_magic_bytes_reject_exe_renamed_pdf` échoue · evidences à mime suspects |
| Plan B | Désactiver endpoint upload · scan antivirus des evidences uploadées · rotation users si compromis |
| Mitigation préventive | `python-magic` + double-check manuel signatures + libmagic à jour |

### R0-10 · Purge silencieuse RGPD (IE5)

| Champ | Détail |
|---|---|
| Source | ADR-029 §12 + IE5 |
| Sprint | Mois 4 J+1 (activation prod) |
| Probabilité | Faible |
| Impact | Très élevé (preuves légales supprimées) |
| Indicateur early-warning | `RETENTION_PURGE_ENABLED=True` activé sans dry-run préalable |
| Plan B | Désactiver purge immédiatement · restore depuis backup si <12 mois · audit cause |
| Mitigation préventive | Triple garde-fou (feature flag + dry-run + trace) + activation procédure stricte L9 §1.1 |

### R0-11 · Réouverture admin abusée (IL3 + IL11)

| Champ | Détail |
|---|---|
| Source | ADR-028 §12 + IL3 + IL11 |
| Sprint | M2-5 |
| Probabilité | Faible |
| Impact | Élevé (intégrité statistiques + audit RGPD) |
| Indicateur early-warning | `action_event_log` : events `reopened` fréquents par même admin · justifications vides ou copy-paste |
| Plan B | Audit RGPD admin · révoquer privilèges si abus · alerte direction |
| Mitigation préventive | Admin role + fresh token (<5min) + justification min 10 chars obligatoire |

### R0-12 · RGPD art. 17 droit à l'oubli non implémenté

| Champ | Détail |
|---|---|
| Source | ADR-029 §10.2 |
| Sprint | M2-6 |
| Probabilité | Élevé si manqué (oubli pendant sprints) |
| Impact | Très élevé (violation RGPD CNIL) |
| Indicateur early-warning | DoD Mois 2 critère #20 non coché : "Endpoint art. 17 anonymisation présent" |
| Plan B | Sprint extra urgent Mois 3 · pas de cutover Mois 4 sans cet endpoint |
| Mitigation préventive | DoD binaire fin Mois 2 obligatoire avant cutover Mois 4 |

---

## 2. Risques P1 (15)

### R1-1 · Cutover Mois 4 J0 dégrade performance > 2× budgets

| Champ | Détail |
|---|---|
| Source | ADR-025 §10 + ADR-026 §6 |
| Sprint | Mois 4 J0 |
| Probabilité | Moyenne |
| Impact | Élevé (UX dégradée + risque rollback) |
| Indicateur early-warning | J+0 smoke tests : latence p95 > 2× budget ADR-025 §9 |
| Plan B | **Rollback déclenché** (ADR-026 §6) · investigation indexes manquants · re-cutover après fix |
| Mitigation préventive | Dry-run staging J-7 avec benchmark perfs (Q25-A) |

### R1-2 · HELIOS seeds non-idempotents

| Champ | Détail |
|---|---|
| Source | ADR-026 §10 + Q20-A |
| Sprint | M2-7 |
| Probabilité | Faible |
| Impact | Moyen (démo perturbée + tests instables) |
| Indicateur early-warning | Test `test_run_3_times_same_state` échoue |
| Plan B | Fix `regen_seeds_v4.py` · re-seed obligatoire dans CI avant chaque test |
| Mitigation préventive | Test idempotence à 3 obligatoire avant merge M2-7 |

### R1-3 · Pattern repository contourné (IS11)

| Champ | Détail |
|---|---|
| Source | ADR-027 §10 + IS11 |
| Sprint | M2-4 |
| Probabilité | Moyenne (négligence dev) |
| Impact | Élevé (faille IDOR potentielle) |
| Indicateur early-warning | source-guard `test_no_direct_db_in_routes` échoue · PR contient `db.query()` direct |
| Plan B | Refactor PR obligatoire avant merge · review architecture |
| Mitigation préventive | Source-guard CI bloquante + pattern documenté L7 §11 |

### R1-4 · 288 IDOR tests trop longs à écrire manuellement

| Champ | Détail |
|---|---|
| Source | L9 §6 |
| Sprint | M2-4 + M2-8 |
| Probabilité | Élevé |
| Impact | Moyen (retard sprint M2-8) |
| Indicateur early-warning | Sprint M2-4 fini avec <30 IDOR tests · auto-génération non démarrée |
| Plan B | Pytest parametrize auto-génération · skip extension si nécessaire (mais 288 = DoD Mois 2 obligatoire) |
| Mitigation préventive | Auto-génération depuis Sprint M2-4 · matrice CSV en source |

### R1-5 · Sprint M2-2 (schéma DB) déborde > 3 jours

| Champ | Détail |
|---|---|
| Source | L9 §6 |
| Sprint | M2-2 |
| Probabilité | Moyenne |
| Impact | Élevé (cascade sur M2-3 à M2-8) |
| Indicateur early-warning | Day 2 Sprint M2-2 : <50% des CHECK constraints implémentées |
| Plan B | Buffer 1 jour entre M2-2 et M2-3 (déjà prévu L9) · découper M2-2 en sous-tâches priorisées |
| Mitigation préventive | Ne pas démarrer M2-3 sans M2-2 acceptance complète |

### R1-6 · JWT replay token volé

| Champ | Détail |
|---|---|
| Source | ADR-027 §10 M4 |
| Sprint | M2-3 |
| Probabilité | Faible |
| Impact | Élevé (compromission session) |
| Indicateur early-warning | `security_audit_log` : auth events depuis IPs anormales |
| Plan B | Rotation JWT secret immédiate · invalidation sessions concernées · audit logs |
| Mitigation préventive | Rotation 1h access token + 30j refresh + revocation list |

### R1-7 · Énumération via 403/404 différenciés (M5 ADR-027)

| Champ | Détail |
|---|---|
| Source | ADR-027 §10 M5 + IS3 |
| Sprint | M2-3 + M2-4 |
| Probabilité | Moyenne |
| Impact | Élevé (cartographie data clients) |
| Indicateur early-warning | source-guard `test_cross_org_returns_404_not_403` échoue · pen-test détecte différence |
| Plan B | Hotfix retour 404 systématique · audit IDOR matrix |
| Mitigation préventive | IS3 + IDOR matrix tests obligatoires |

### R1-8 · Confusion merged_duplicate vs resolved_via_recurrence (IL5)

| Champ | Détail |
|---|---|
| Source | ADR-028 §12 + IL5 |
| Sprint | M2-5 |
| Probabilité | Élevé (UX) |
| Impact | Moyen (stats faussées + dette doctrinale) |
| Indicateur early-warning | Q&A : users confondent les 2 closure_reasons · stats ROI incohérentes |
| Plan B | UX guidelines + tooltip différenciation · formation interne |
| Mitigation préventive | Libellés FR distincts L7 §10 + IL5 garde-fou code |

### R1-9 · Coexistence Mois 2-3 cassée par dev qui supprime trop tôt

| Champ | Détail |
|---|---|
| Source | ADR-025 §10 + Q13-B |
| Sprint | M2-2 →  M2-8 |
| Probabilité | Faible (Q6-A explicite) |
| Impact | Très élevé (régression legacy) |
| Indicateur early-warning | PR contient `git rm legacy_models/` · L8 exécuté prématurément |
| Plan B | Refuser PR · rollback Git · rappel doctrine Q13-B |
| Mitigation préventive | L8 explicitement Mois 5 + L9 §9.2 décisions non-rejouables |

### R1-10 · Schemas Pydantic v1 cassés par évolution (IE7)

| Champ | Détail |
|---|---|
| Source | ADR-029 §12 + IE7 |
| Sprint | M2-6 + V4.1+ |
| Probabilité | Moyenne (V4.1+) |
| Impact | Élevé (events historiques non parsables) |
| Indicateur early-warning | Test `test_all_event_types_have_schema_v1` échoue · validation Pydantic erreurs |
| Plan B | Ajouter schemas v2 sans casser v1 · script migration v1 → v2 si nécessaire |
| Mitigation préventive | `schema_version` cardinal dans chaque payload (IE7) |

### R1-11 · `regulatory_applicability_service` produit evidences incohérentes (IE2)

| Champ | Détail |
|---|---|
| Source | Sprint Phase 3.5 + IE2 |
| Sprint | Coordination Phase 3.5 + M2-6 |
| Probabilité | Moyenne |
| Impact | Moyen (preuves system pas vérifiées humainement) |
| Indicateur early-warning | Evidences `uploaded_by=system` sans validation humaine · audit incohérence |
| Plan B | Validation humaine post-hoc obligatoire pour evidences system · review process |
| Mitigation préventive | Coordination Phase 3.5 → M2-6 · IE2 manual validation cardinal |

### R1-12 · `expires_at` calcul erroné (drift timezone)

| Champ | Détail |
|---|---|
| Source | ADR-029 + IE6 |
| Sprint | M2-6 |
| Probabilité | Faible |
| Impact | Moyen (preuves expirent à mauvais moment) |
| Indicateur early-warning | Test `test_IE6_expires_at_exactly_90_days` échoue · drift > 1h détecté |
| Plan B | Recalcul batch `expires_at` · audit timezone serveur |
| Mitigation préventive | UTC strict partout (cf. ADR-025) + tests timezone-aware |

### R1-13 · Performance budgets pas mesurés Mois 2

| Champ | Détail |
|---|---|
| Source | L9 §6 |
| Sprint | M2-8 |
| Probabilité | Moyenne |
| Impact | Élevé (régression silencieuse) |
| Indicateur early-warning | DoD Mois 2 critère #15 non coché · pas de benchmarks |
| Plan B | Sprint extra Mois 3 dédié perfs avant cutover Mois 4 |
| Mitigation préventive | Benchmarks dans CI dès M2-2 (suite à création tables) |

### R1-14 · CHECK constraint `chk_closure_consistency` mal implémentée

| Champ | Détail |
|---|---|
| Source | ADR-025 §2.1 + L8 §2.1 |
| Sprint | M2-2 |
| Probabilité | Moyenne |
| Impact | Élevé (données incohérentes en DB) |
| Indicateur early-warning | Test `test_chk_closure_consistency` échoue · INSERT incohérents passent |
| Plan B | Hotfix migration · audit data existante · purge si incohérences |
| Mitigation préventive | Tests unit CHECK constraints obligatoires Sprint M2-2 |

### R1-15 · Frontend optimistic UI réintroduit (IL10)

| Champ | Détail |
|---|---|
| Source | ADR-028 §12 + IL10 |
| Sprint | M2-5 + frontend Mois 3 |
| Probabilité | Moyenne (habitude dev FE) |
| Impact | Moyen (UX dégradée sur HTTP 409) |
| Indicateur early-warning | Code review : `setState` avant `await api.patch()` · tests e2e flacky |
| Plan B | Refactor FE wait-for-server · tests e2e renforcés |
| Mitigation préventive | IL10 source-guard frontend + tests e2e Playwright |

---

## 3. Risques P2 (10)

### R2-1 · Storage filesystem corruption disk

| Source | ADR-029 §12 |
| Sprint | M2-6 + ops Mois 4+ |
| Plan B | Restore depuis backup ADR-026 · migration S3 V4.1+ |

### R2-2 · APScheduler ne survit pas redémarrage app

| Source | ADR-025 + Q17 |
| Sprint | M2-1 (config) + M2-6 |
| Plan B | Migration Celery V4.1 si récurrent |

### R2-3 · pip-audit détecte CVE bloquante Mois 2-6

| Source | ADR-027 §10 |
| Sprint | Continu |
| Plan B | Upgrade dependency · workaround temporaire · waiver documenté |

### R2-4 · Documentation Sphinx/MkDocs incomplète fin Mois 2

| Source | L9 §8 critère #18 |
| Sprint | M2-8 |
| Plan B | Sprint extra Mois 3 doc · cutover Mois 4 maintenu |

### R2-5 · Brute force endpoints sensibles (M8 ADR-027)

| Source | ADR-027 §10 M8 |
| Sprint | M2-3 (rate limiter) |
| Plan B | Rate limiting renforcé · blacklist IPs |

### R2-6 · CSRF mutations (M6 ADR-027)

| Source | ADR-027 §10 M6 |
| Sprint | M2-3 |
| Plan B | CSRF token strict · Origin header check |

### R2-7 · Migration cron OS oubliée pour `regulatory_applicability_service`

| Source | Sprint Phase 3.5 |
| Sprint | Coordination Phase 3.5 |
| Plan B | Verification cron manuel · alertes monitoring |

### R2-8 · Dépendance `python-magic` cassée Mois 4+

| Source | ADR-029 §6 |
| Sprint | M2-6 + ops |
| Plan B | Fallback magic bytes manuel (signatures explicites) |

### R2-9 · `priority_explanation` JSONB volumineux dégrade perf

| Source | ADR-025 §10 + Q11-A |
| Sprint | M2-4 + perf monitoring |
| Plan B | Truncate explanation > 5 KB · lazy loading |

### R2-10 · Backup S3 V4.1+ non-implémenté quand pilots externes arrivent

| Source | ADR-029 §10 |
| Sprint | V4.1+ planning |
| Plan B | Migration S3 obligatoire avant pilots externes · sprint dédié |

---

## 4. Matrice criticité × sprint d'activation

```
Sprint  P0           P1                      P2
─────────────────────────────────────────────────────────────
M2-1    R0-4         (préparation)           R2-1, R2-2, R2-3
M2-2    -            R1-5, R1-14             -
M2-3    R0-1, R0-2,  R1-3, R1-6, R1-7        R2-5, R2-6
        R0-3
M2-4    R0-1         R1-3, R1-4              -
M2-5    R0-7, R0-8,  R1-8, R1-15             -
        R0-11
M2-6    R0-9, R0-12  R1-10, R1-11, R1-12     R2-1, R2-8
M2-7    -            R1-2                    -
M2-8    -            R1-4, R1-13             R2-4
Mois 4  R0-5, R0-10  R1-1                    -
Mois 5  R0-6         -                       -
Mois 6+ -            -                       R2-10
```

---

## 5. Indicateurs early-warning cumulés (dashboard)

À monitorer **quotidiennement** Mois 2-6 :

| Indicateur | Source | Threshold critique | Action |
|---|---|---|---|
| Source-guards CI échoués | CI logs | ≥1 échec | Investigation immédiate · pas de merge |
| Tests pyramide non-verts | CI logs | <100% green | Hotfix avant merge |
| security_audit_log warnings | structlog | >10/jour | Audit pattern |
| IDOR matrix coverage | tests | <288 cellules | Sprint dédié extension |
| Performance budgets | benchmarks | >budget ADR-025 §9 | Audit indexes + queries |
| gitleaks alerts | CI logs | ≥1 secret détecté | Rotation immédiate · git filter-branch |
| pip-audit CVE | CI logs | ≥1 CVE high | Upgrade dependency |
| Backup checksums | `/backups/.../CHECKSUMS.sha256` | mismatch | **Cutover REPORTÉ** |
| Coexistence Mois 2-3 | grep legacy imports | ≥1 import legacy | Refuser merge |
| Dry-run staging | reports | échec | Cutover REPORTÉ |

---

## 6. Décisions cardinales Amine non-débattables (rappel)

Si pendant Mois 2-6 quelqu'un veut remettre en cause une de ces 11 décisions, **REFUSER** sans session Claude.ai cadrage dédiée + nouvel avenant doctrinal versionné :

| # | Décision | Référence |
|---|---|---|
| 1 | Q2-α table rase + triple backup obligatoire | Doctrine v0.3 §7 + ADR-026 |
| 2 | Q6-A Mois 1 docs only (TERMINÉ) | Doctrine v0.3 §0 |
| 3 | Q9-B recurrence_groups ≠ duplicate_groups | Doctrine v0.3 §6.3 |
| 4 | IL3 réouverture admin + fresh token + justification | ADR-028 §6.2 |
| 5 | IL4 expired interdit P0/P1 conformité/facturation | ADR-028 §4.2 |
| 6 | IL5 merged_duplicate interdit récurrence | ADR-028 §4.2 |
| 7 | IL7 auto-close P0/P1 exige preuve OU justification | ADR-028 §4.3 |
| 8 | IS11 pas d'accès DB direct (pattern repository) | ADR-027 §6 |
| 9 | IE9 magic bytes MIME validation | ADR-029 §6 |
| 10 | I9 backup hors Git + receipt sanitizé | ADR-026 §3 |
| 11 | Doctrine v0.3 (1er avenant versionné) | Doctrine §11 |

---

## 7. Procédure post-mortem (si incident)

Si un risque se matérialise malgré les mitigations :

1. **Stop the bleeding** : appliquer Plan B documenté
2. **Communication immédiate** : Slack équipe + (si critique) Amine
3. **Audit logs** : extraire tous events `security_audit_log` + `action_event_log` liés
4. **Root cause analysis** : comprendre pourquoi mitigation préventive a échoué
5. **Fix forward** : implémenter correctif + tests anti-régression
6. **Mise à jour de ce document** : ajouter le scénario réel observé en v1.1+
7. **Documentation** : ADR amendment si évolution doctrinale nécessaire

---

## 8. Versioning de cette annexe

| Version | Date | Auteur | Changements |
|---|---|---|---|
| v1.0 | 2026-05-14 | Amine + Claude | Initial · consolidation des 5 ADR + L8 + L9 |

**Politique** : mise à jour à chaque incident matérialisé ou nouveau risque identifié pendant les sprints Mois 2-6.

---

**Fin annexe.** Consultable à tout moment Mois 2-6. Distribuer à chaque nouveau dev qui rejoint le projet.
