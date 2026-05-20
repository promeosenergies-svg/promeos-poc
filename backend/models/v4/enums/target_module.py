"""M2-4.4 — TargetModule : enum strict des cibles polymorphes d'un ActionLink.

7 valeurs. Seule `action_center_item` a un repository V4 org-scopé et est
vérifiable dans ce sprint (M2-4.4). Les 6 autres lèvent 501 NOT_IMPLEMENTED
via `link_target_validator` — différées M2-5/M2-6 (cf. SECURITY.md §5.4).

Note DB-vs-API : `ActionLink.target_module` reste `String(40)` au niveau DB
(aucune migration). La rigueur enum est portée à la couche API/Pydantic.
"""

from enum import Enum


class TargetModule(str, Enum):
    """Modules cibles d'un lien ActionCenterItem → autre entité."""

    ACTION_CENTER_ITEM = "action_center_item"  # implémenté (repo V4 org-scopé)
    SITE = "site"  # 501 — différé M2-5
    BUILDING = "building"  # 501 — différé M2-5
    METER = "meter"  # 501 — différé M2-5
    INVOICE = "invoice"  # 501 — différé M2-5
    CONTRACT = "contract"  # 501 — différé M2-5
    REGULATORY_OBLIGATION = "regulatory_obligation"  # 501 — différé M2-6
