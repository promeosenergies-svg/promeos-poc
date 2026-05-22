# Runbook — Purge PII RGPD article 17 (M2-6.A.2)

> **Statut** : runbook légal. Sibling de `RUNBOOK_DEPLOY.md`. Établi M2-6.A.2.
>
> **Cible** : DPO PROMEOS + admins plateforme HELIOS / MERIDIAN.

## Origine

RGPD article 17 (droit à l'effacement) impose à PROMEOS d'honorer une demande
de purge PII dans un **délai de 1 mois** (extensible à 3 mois si demande
complexe, article 12 RGPD).

CNIL article 30 (registre des traitements) impose un journal historique des
purges effectuées. Ce journal NE DOIT PAS contenir de PII en clair (sinon on
re-crée ce qu'on a effacé).

## Vue d'ensemble

| Aspect | Implémentation M2-6.A.2 |
|---|---|
| Endpoint | `POST /api/admin/users/{user_id}/purge` |
| Auth | `require_platform_admin` STRICT (DG_OWNER / DSI_ADMIN ; pas de bypass DEMO_MODE) |
| Stratégie | Hybride : hard-clear User PII + anonymisation snapshots V4 + hard-delete UserOrgRole |
| Audit | Table `purge_log` (SHA256 hash user_id, jamais user_id en clair) |
| Whitelist | Emails terminant par `.demo` non purgeables (422) |
| Idempotency | 2e purge sur même user → 409 |
| Dry-run | `{"dry_run": true}` → preview report sans modifier la DB |

## Procédure complète

### 1. Réception de la demande

Canaux acceptés :

- Email à `rgpd@promeos.io` (à configurer en M2-6.A.3)
- Lettre recommandée (à l'adresse du siège)

**Délai légal** : 1 mois standard. Compter à partir de J0 = date de réception.

### 2. Vérification de l'identité du demandeur

L'admin DOIT vérifier que la demande émane bien de la personne dont les
données seront purgées (anti-impersonation) :

- Email de la demande = email du compte enregistré, **OU**
- Pièce d'identité scannée jointe à la demande

En cas de doute : demander une preuve supplémentaire avant toute action.

### 3. Pré-purge — Inventaire (dry-run)

```bash
ADMIN_TOKEN="<token DG_OWNER ou DSI_ADMIN>"
USER_ID=42

curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Demande RGPD reçue le 2026-05-22 (ticket RGPD-001)", "dry_run": true}' \
  https://api.promeos.io/api/admin/users/$USER_ID/purge
```

Réponse JSON :

```json
{
  "user_pii_cleared": true,
  "user_org_roles_deleted": 1,
  "event_logs_anonymized": 12,
  "action_items_owner_anonymized": 3,
  "purge_log_id": null,
  "dry_run": true
}
```

**Vérifier** les compteurs avant la purge effective :

- Si chiffres aberrants (ex: 10 000 events pour un user récent) → STOP, investiguer.
- Si compteurs cohérents → passer à l'étape 4.

### 4. Purge effective

```bash
curl -X POST \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"reason": "Demande RGPD article 17 — 2026-05-22 — ticket RGPD-001"}' \
  https://api.promeos.io/api/admin/users/$USER_ID/purge
```

Réponse JSON identique au dry-run, mais `dry_run: false` et `purge_log_id` posé.

### 5. Vérification post-purge

```bash
# 1. PII clearé en DB
sqlite3 backend/data/promeos.db \
  "SELECT email, nom, prenom, actif FROM users WHERE id = $USER_ID;"
# Attendu : email LIKE 'purged_%@purged.local', nom = 'Utilisateur supprimé', actif = 0

# 2. Audit log présent
sqlite3 backend/data/promeos.db \
  "SELECT id, user_id_hash, purged_at, reason FROM purge_log ORDER BY id DESC LIMIT 1;"

# 3. UserOrgRole supprimé
sqlite3 backend/data/promeos.db \
  "SELECT COUNT(*) FROM user_org_roles WHERE user_id = $USER_ID;"
# Attendu : 0
```

### 6. Réponse au demandeur

Modèle de réponse :

> Bonjour,
>
> Votre demande RGPD article 17 du **YYYY-MM-DD** (référence RGPD-XXX) a été
> honorée le **YYYY-MM-DD**. Vos données personnelles ont été anonymisées dans
> nos systèmes :
>
> - email, nom, prénom : effacés
> - mot de passe : invalidé (compte non re-authentifiable)
> - rôles dans les organisations : supprimés
> - traces d'activité (audit trail) : pseudonymisées (libellé « Utilisateur supprimé »)
>
> Conformément à CNIL article 30, un journal de cette opération est conservé
> (hash anonyme, sans contenu identifiable).
>
> Cordialement,
> DPO PROMEOS

## Codes d'erreur

| Code HTTP | Code métier | Cause | Action |
|---|---|---|---|
| 401 | (token) | JWT absent ou invalide | Re-générer token admin |
| 403 | (role) | Caller pas DG_OWNER / DSI_ADMIN | Escalade DPO |
| 404 | USER_NOT_FOUND | user_id inexistant | Vérifier l'id (typo ?) |
| 409 | USER_ALREADY_PURGED | Idempotency violée | Vérifier `purge_log` pour la date précédente |
| 422 | PROTECTED_DEMO_USER | Email `.demo` whitelisté | Ne pas purger les démos (données fictives) |
| 422 | (validation) | `reason` < 10 chars ou champ inconnu | Corriger le body |
| 500 | PURGE_INTERNAL_ERROR | Erreur cascade interne | Rollback effectué ; investiguer logs serveur |

## Cas particuliers

### Demo users (`.demo`)

Les comptes démo (suffixe `.demo`) ne sont pas purgeables (Q5=B M2-6.A.2). Ils
contiennent des données fictives, pas du PII réel. Retourne 422
`PROTECTED_DEMO_USER` avec message explicite.

Exemple protégé : `marie.dupont@helios.demo` (utilisé pour la narrative démo
HELIOS — préserver pour reproductibilité parcours pilote).

### User déjà purgé

Retourne 409 `USER_ALREADY_PURGED`. Vérifier dans `purge_log` :

```sql
SELECT id, purged_at, reason
FROM purge_log
WHERE user_id_hash = (
  SELECT lower(hex(sha256(CAST($USER_ID AS TEXT))))
)
ORDER BY purged_at DESC;
```

(Adapter selon DB cible — SQLite n'a pas `sha256` natif, utiliser le helper
Python `services.v4.pii_purge._hash_user_id(user_id)` si nécessaire.)

### Erreur cascade

Retourne 500 `PURGE_INTERNAL_ERROR`. La transaction est rollback-ée
automatiquement (atomicité garantie). Investiguer logs serveur (level=ERROR,
log_name `services.v4.pii_purge`), contacter dev avant retry.

## Délai légal CNIL

| Cas | Délai |
|---|---|
| Standard | **1 mois** depuis réception |
| Demande complexe (multi-orgs, audit poussé) | **3 mois max** (article 12 RGPD) |

Si le délai est prolongé, notifier le demandeur **avant l'expiration du 1er mois**.

## Anti-patterns

- ❌ Purger directement via SQL `DELETE` — bypass audit log + casse les checks
  d'intégrité V4 (CheckConstraints).
- ❌ Purger un demo `.demo` « parce qu'on veut tester » — utiliser un user de
  test dédié (`test+rgpd-{date}@example.com`).
- ❌ Re-créer un user avec la même email après purge — l'email purgée est
  `purged_<hash>@purged.local`, l'email d'origine est libérée pour réutilisation.
- ❌ Logger l'email purgé dans les logs serveur — déjà absent du logger
  `services.v4.pii_purge` (volontaire), mais à vérifier dans tout nouveau code.

## Doctrine référencée

- [`backend/services/v4/pii_purge.py`](../../backend/services/v4/pii_purge.py) — implémentation service
- [`backend/routes/admin_pii_purge.py`](../../backend/routes/admin_pii_purge.py) — endpoint admin
- [`backend/models/v4/purge_log.py`](../../backend/models/v4/purge_log.py) — modèle audit
- [`docs/dev/methode_self_review_pr.md`](../dev/methode_self_review_pr.md) — discipline cas trunk-based M2-6
- ADR-029 §3.4 — pattern V4 « UUID isolé + snapshot label » (base de la stratégie
  d'anonymisation : on anonymise les snapshots, pas les UUID5 opaques)
