"""PROMEOS V4 Centre d'Action — package isolation Q13-B (Sprint M2-2).

Sous-package isolé pour éviter collision avec `backend/models/*.py` legacy
(ex. `backend/models/enums.py` legacy avec 40+ enums non-V4 ; `backend/models/action_item.py`
ActionItem legacy supprimé Mois 5 par L8).

Sprint M2-2 livre :
- v4/enums/   : 9 enums Python V4 (cohérent L7 §3 + décisions D1-D5)
- v4/<table>.py : 8 SQLAlchemy V4 models (commit 2/5)

Sprints suivants Mois 2 :
- Sprint M2-3 : OrgScopingMiddleware + @org_scoped + repositories org-scopés (IS11)
- Sprint M2-4 : 12 endpoints /api/action-center/*
- Sprint M2-5 : LifecycleStateMachine (IL1-IL11)
- Sprint M2-6 : EvidenceStorage + 16 schemas Pydantic + magic bytes IE9

Cardinal Q13-B : aucun import legacy depuis ce sous-package.
Cardinal IS1 : tous les models ont organisation_id NOT NULL.
"""

from models.v4.action_blockers import ActionBlocker
from models.v4.action_center_items import ActionCenterItem
from models.v4.action_event_log import ActionEventLog
from models.v4.action_links import ActionLink
from models.v4.action_scenarios import ActionScenario
from models.v4.duplicate_groups import DuplicateGroup
from models.v4.evidences import Evidence
from models.v4.recurrence_groups import RecurrenceGroup

# 8 V4 SQLAlchemy models — re-export pour migration Alembic + imports application
__all__ = [
    "ActionBlocker",
    "ActionCenterItem",
    "ActionEventLog",
    "ActionLink",
    "ActionScenario",
    "DuplicateGroup",
    "Evidence",
    "RecurrenceGroup",
]
