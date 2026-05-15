"""PROMEOS V4 Centre d'Action — package isolation Q13-B (Sprint M2-2).

Sous-package isolé pour éviter collision avec `backend/models/*.py` legacy
(ex. `backend/models/enums.py` legacy avec 40+ enums non-V4 ; `backend/models/action_item.py`
ActionItem legacy supprimé Mois 5 par L8).

Sprint M2-2 livre :
- v4/enums/   : 9 enums Python V4 (cohérent L7 §3 + décisions D1-D5)
- v4/<table>.py : 8 SQLAlchemy V4 models (Sprint M2-2 commit 2/5)

Sprints suivants Mois 2 :
- v4/services/ : Sprint M2-3 (lifecycle, evidence, event_log) — cf. backend/services/
- v4/repositories/ : Sprint M2-3 (pattern repository org-scopé IS11)
- v4/routes/ : Sprint M2-4 (12 endpoints /api/action-center/*)

Cardinal Q13-B : aucun import legacy depuis ce sous-package.
Cardinal IS1 : tous les models ont organisation_id NOT NULL.
"""
