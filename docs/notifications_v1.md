# PROMEOS - Notifications & Alert Center V1 (Sprint 10.2)

## Objectif

Centre d'alertes in-app (pas d'email V1) qui detecte l'urgent depuis 5 briques
et alimente le cockpit + badges sidebar.

## Architecture

### Sources (5 briques)

| Source | Criteres de generation | Severites |
|--------|----------------------|-----------|
| **Compliance** | NOK severity>=high → CRITICAL, UNKNOWN → WARN, deadline <=30j → CRITICAL | CRITICAL, WARN |
| **Billing** | loss_eur >= 5000 → CRITICAL, >= 1000 → WARN | CRITICAL, WARN, INFO |
| **Purchase** | renewal <=30j → CRITICAL, <=60j → WARN, <=90j → INFO | CRITICAL, WARN, INFO |
| **Consumption** | data_gap → WARN, loss >= 5000 → CRITICAL, >= 1000 → WARN | CRITICAL, WARN |
| **Action Hub** | overdue >14j → CRITICAL, overdue → WARN, BLOCKED → WARN | CRITICAL, WARN |

### Modeles

- **NotificationEvent**: alerte persiste avec severity, deeplink, evidence, workflow (NEW→READ→DISMISSED)
- **NotificationBatch**: log de chaque run de sync
- **NotificationPreference**: preferences org (badges, snooze, seuils)

### Dedup

Unicite par `(org_id, source_type, source_id, source_key)`.
Le `inputs_hash` (SHA-256) detecte les changements de contenu.
Un resync ne duplique jamais — il update si le contenu change, skip sinon.
Le statut READ/DISMISSED est preserve lors d'un resync.

## API Endpoints

| Methode | Path | Description |
|---------|------|-------------|
| POST | `/api/notifications/sync?org_id=` | Sync alertes depuis 5 briques |
| GET | `/api/notifications/list?org_id=&severity=&status=&source_type=&site_id=` | Liste filtrable |
| GET | `/api/notifications/summary?org_id=` | Counts par severity/status + new_critical/new_warn |
| PATCH | `/api/notifications/{id}` | Workflow: `{"status": "read"}` ou `{"status": "dismissed"}` |
| GET | `/api/notifications/preferences?org_id=` | Preferences org |
| PUT | `/api/notifications/preferences?org_id=` | Mettre a jour preferences |
| GET | `/api/notifications/batches?org_id=` | Historique syncs |

## Dashboard 2 Minutes

Le champ `alerts` est ajoute au retour de `/api/dashboard/2min`:

```json
{
  "alerts": {
    "new_critical": 3,
    "new_warn": 5,
    "new_total": 10,
    "total": 15,
    "top_alert": {
      "id": 1,
      "title": "Non-conformite BACS...",
      "severity": "critical",
      "deeplink_path": "/conformite?site_id=1",
      "source_type": "compliance"
    }
  }
}
```

## Frontend

- **Page**: `/notifications` (Alertes)
- **Sidebar**: Bell icon avec badge rouge (new_critical + new_warn)
- **UI**: 3 severity cards + table filtrable + actions rapides (Voir, Marquer lu, Ignorer)
- **Deep links**: chaque alerte a un bouton "Voir" qui navigue vers la page source

## Seuils par defaut

```json
{
  "critical_due_days": 30,
  "warn_due_days": 60
}
```

Configurables via PUT `/api/notifications/preferences`.

## Seed Demo

Le seed genere automatiquement les notifications depuis les donnees existantes,
puis applique une distribution demo:
- 70% NEW
- 20% READ
- 10% DISMISSED

## Tests

22 tests dans 8 classes (test_notifications.py):
- TestSyncIdempotent (2): double sync = 0 doublons + batch cree
- TestSeverityMapping (3): compliance high=CRITICAL, contract 30j/60j
- TestPatchStatus (4): READ, DISMISSED, invalid, 404
- TestPreserveWorkflow (1): resync preserve READ
- TestDashboard2MinAlerts (2): alerts present + top_alert
- TestFilterEndpoints (6): list all, severity, source, summary, batches, empty
- TestSyncEndpoint (2): sync via API + returns summary
- TestPreferences (2): get defaults + put preferences

## Limites V1

- Pas d'email / webhook (V2)
- Pas de digest periodique (V2)
- Pas de SLA / escalation (V2)
- Pas de push notifications (V2)
- Snooze global uniquement (pas par alerte)

## Fichiers modifies/crees

| Fichier | Action |
|---------|--------|
| `backend/models/enums.py` | +3 enums (NotificationSeverity, NotificationStatus, NotificationSourceType) |
| `backend/models/notification.py` | **Creer** (NotificationEvent, NotificationBatch, NotificationPreference) |
| `backend/models/__init__.py` | Register 3 models + 3 enums |
| `backend/services/notification_service.py` | **Creer** (build_from_* + sync_notifications) |
| `backend/routes/notifications.py` | **Creer** (7 endpoints) |
| `backend/routes/__init__.py` | Register notifications_router |
| `backend/main.py` | Register notifications_router |
| `backend/routes/dashboard_2min.py` | +_notifications_summary helper |
| `backend/scripts/seed_data.py` | +sync_notifications_demo |
| `backend/tests/test_notifications.py` | **Creer** (22 tests) |
| `frontend/src/services/api.js` | +6 fonctions notifications |
| `frontend/src/pages/NotificationsPage.jsx` | **Creer** |
| `frontend/src/App.jsx` | +route /notifications + alias /alertes |
| `frontend/src/layout/Sidebar.jsx` | +Bell icon + badge dynamique |
| `frontend/src/layout/Breadcrumb.jsx` | +notifications + alertes labels |
| `docs/notifications_v1.md` | **Creer** |
