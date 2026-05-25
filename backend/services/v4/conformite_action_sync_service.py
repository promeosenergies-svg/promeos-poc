"""PROMEOS — Boucle Conformité → Centre d'Action (fondations P0-5).

Conformité P0 2026-05-23 — pose les fondations de la boucle "DATA_MISSING
réglementaire → ActionCenterItem". P1 livrera l'endpoint d'écriture, P0 livre
le service lecteur idempotent + le contrat.

Phase actuelle (P0) :
- Service `plan_remediation_actions_for_org(db, org_id)` **READ-ONLY** : calcule
  ce que devraient être les ActionCenterItem à créer/mettre à jour à partir
  des `RuleApplicability` de status `DATA_MISSING`.
- Retourne un `RemediationPlan` (dataclass immutable + dict sérialisable JSON).
- N'écrit RIEN en base.

Phase suivante (P1) :
- Endpoint `POST /api/conformite/sync-remediation-actions` qui consomme ce
  service et crée/met à jour les items via `ActionCenterItemRepository`.
- Idempotency-Key obligatoire (cf. ADR-025 §1.4 IS6).
- Audit trail `action_event_log` event_type=`item_created_from_rule`.

Doctrine respectée :
- Aucun nouveau menu (la création se fait depuis Conformité existant via CTA).
- Aucune nouvelle route exposée dans ce sprint (service interne uniquement).
- Aucun écran ajouté.
- Réutilise `RuleApplicability` (P0-B remediation enrichi) et `Kind` /
  `Domain` existants.

Référence : `docs/dev/conformite_action_sync_contract.md`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy.orm import Session

from models.v4.enums import Domain, Kind
from regulatory.applicability_service import compute_applicability
from regulatory.applicability_types import ApplicabilityStatus, RuleApplicability, RuleCode


# ─── Dataclasses résultat ────────────────────────────────────────────────────


@dataclass(frozen=True)
class ActionItemDraft:
    """Draft d'`ActionCenterItem` à créer/mettre à jour pour une remédiation.

    Pas d'`id` (sera attribué par le repository en P1). `external_ref` sert de
    clé d'idempotency : `rule_code:scope_level:scope_id:reason_code` → stable
    sur les ré-exécutions du même calcul.
    """

    external_ref: str  # clé idempotency stable
    organisation_id: int
    kind: str  # Kind enum value (EVIDENCE_REQUEST ou ACTION)
    domain: str  # Domain enum value (CONFORMITE)
    title_fr: str  # libellé FR utilisateur
    description_fr: str  # explication courte FR
    rule_code: str  # DT / BACS / APER / SME / BEGES
    reason_code: str  # ex DT.DATA_MISSING.SURFACE
    scope_level: str  # site / batiment / organisation / entite_juridique
    scope_id: Optional[int]
    remediation_field: Optional[str]  # ex "site.tertiaire_area_m2"
    cta_label_fr: str  # ex "Compléter la surface"
    # Action Center V4 P0 fix (2026-05-25) — source_url canonique pointant
    # vers la page hub /conformite filtrée sur la règle. Sera persisté dans
    # `ActionCenterItem.source_url` quand le P1 endpoint sera livré pour
    # permettre au drawer V4 de rendre « Voir la source » sans parser
    # description (audit deep §6 P0-4, contrat figé ici pour P1).
    source_url: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RemediationPlan:
    """Plan de remédiation calculé pour une organisation.

    Le plan est purement lecteur (read-only) en P0 — il décrit ce qu'il
    *faudrait* créer comme ActionCenterItem sans les créer.
    """

    org_id: int
    items_to_create: list[ActionItemDraft] = field(default_factory=list)
    summary: dict[str, int] = field(default_factory=dict)
    computed_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "org_id": self.org_id,
            "items_to_create": [d.to_dict() for d in self.items_to_create],
            "summary": dict(self.summary),
            "computed_at": self.computed_at,
        }


# ─── Helpers FR ─────────────────────────────────────────────────────────────


_KIND_BY_REASON_PREFIX: dict[str, str] = {
    # Toutes les DATA_MISSING génèrent un EVIDENCE_REQUEST (par définition :
    # "demande de donnée à fournir pour évaluer la règle").
    # Les APPLICABLE génèreront ACTION ou DEADLINE plus tard (hors P0-5).
}


def _kind_for_entry(entry: RuleApplicability) -> str:
    """Détermine le kind ActionCenterItem pour une entrée d'applicabilité.

    Doctrine P0-5 : pour l'instant on ne planifie QUE les DATA_MISSING
    (boucle minimale "complète tes données réglementaires"). Les APPLICABLE
    (échéances DT 2030, etc.) seront planifiés en P1+ avec leur propre logique
    (DEADLINE / ACTION).
    """
    if entry.status == ApplicabilityStatus.DATA_MISSING:
        return Kind.EVIDENCE_REQUEST.value
    # Cas non géré P0-5 — ne devrait pas arriver vu le filtre upstream.
    return Kind.ACTION.value


def _title_fr_for_entry(entry: RuleApplicability, remediation: dict[str, Any]) -> str:
    """Compose le titre FR de l'ActionCenterItem.

    Pattern : "<règle FR> — <libellé champ> manquant" (ou variante CTA).
    """
    rule_labels = {
        "DT": "Décret Tertiaire",
        "BACS": "Régulation chauffage (BACS)",
        "APER": "EnR parking / toiture (APER)",
        "SME": "Audit énergétique (SMÉ)",
        "BEGES": "Bilan GES réglementaire",
    }
    rule_fr = rule_labels.get(entry.rule_code.value, entry.rule_code.value)
    label = remediation.get("remediation_label_fr") or "donnée"
    return f"{rule_fr} — {label} à compléter"


def _description_fr_for_entry(entry: RuleApplicability, remediation: dict[str, Any]) -> str:
    """Compose la description FR : hint + scope label."""
    hint = remediation.get("remediation_hint_fr") or entry.reason_human
    scope_lbl = entry.scope_label or f"{entry.scope_level} #{entry.scope_id}"
    return f"{hint} ({scope_lbl})"


def _external_ref(entry: RuleApplicability) -> str:
    """Clé d'idempotency stable pour cette remédiation.

    Pattern : `<rule_code>:<scope_level>:<scope_id>:<reason_code>`.
    Garantit qu'un nouvel appel sur le même contexte produit la même clé →
    le repository P1 pourra faire `upsert` au lieu de créer des doublons.
    """
    return f"{entry.rule_code.value}:{entry.scope_level}:{entry.scope_id or 0}:{entry.reason_code}"


def _source_url(entry: RuleApplicability) -> str:
    """Action Center V4 P0 fix (2026-05-25) — URL canonique de retour vers
    la source côté hub /conformite. Permet au drawer V4 d'afficher
    « Voir la source » → page Conformité filtrée sur la règle (audit deep
    §6 P0-4). Si un scope_id site existe, on l'inclut pour préciser le
    périmètre ; sinon on retombe sur la page règle générique."""
    rule = entry.rule_code.value
    if entry.scope_level == "site" and entry.scope_id:
        return f"/conformite?regulation={rule}&site={entry.scope_id}"
    return f"/conformite?regulation={rule}"


# ─── API publique ───────────────────────────────────────────────────────────


def plan_remediation_actions_for_org(
    db: Session,
    org_id: int,
    *,
    site_ids: Optional[list[int]] = None,
) -> RemediationPlan:
    """Calcule le plan de remédiation pour une organisation (READ-ONLY P0-5).

    Args:
        db: session SQLAlchemy
        org_id: organisation cible (org-scoping appliqué par compute_applicability)
        site_ids: filtre optionnel (sinon tous les sites de l'org)

    Returns:
        `RemediationPlan` avec :
        - `items_to_create` : liste d'`ActionItemDraft` (kind=EVIDENCE_REQUEST,
          domain=CONFORMITE) à créer pour chaque DATA_MISSING détecté
        - `summary` : compteurs `{total, by_rule[X], by_level[Y]}`

    Boucle Conformité → Centre d'Action — fondations P0-5 :
    - **N'écrit RIEN** en base. Pour créer effectivement les items, P1 livrera
      l'endpoint `POST /api/conformite/sync-remediation-actions`.
    - Idempotent : 2 appels successifs sans changement réglementaire donnent
      le même plan (même `external_ref` pour chaque draft).
    - Réutilise `RuleApplicability.to_dict()` enrichi P0-B.

    Doctrine :
    - Aucun nouveau menu, aucun nouvel endpoint exposé dans ce sprint.
    - Le service est destiné à être consommé par un endpoint admin/cron en P1.
    """
    applicability_by_rule: dict[RuleCode, list[RuleApplicability]] = compute_applicability(
        db, org_id, site_ids=site_ids
    )

    items: list[ActionItemDraft] = []
    by_rule: dict[str, int] = {}
    by_level: dict[str, int] = {}

    for rule_code, entries in applicability_by_rule.items():
        for entry in entries:
            if entry.status != ApplicabilityStatus.DATA_MISSING:
                continue

            # Enrichissement P0-B : to_dict() injecte remediation_* + affected_site_ids
            payload = entry.to_dict()
            remediation_keys = {
                "remediation_field",
                "remediation_label_fr",
                "remediation_hint_fr",
                "cta_label_fr",
            }
            remediation = {k: payload.get(k) for k in remediation_keys if payload.get(k)}

            if not remediation:
                # Code DATA_MISSING non mappé dans remediation.py → on skip
                # (source-guard test_data_missing_remediation_source_guards.py
                # garantit qu'il n'y en a pas en production).
                continue

            draft = ActionItemDraft(
                external_ref=_external_ref(entry),
                organisation_id=org_id,
                kind=_kind_for_entry(entry),
                domain=Domain.CONFORMITE.value,
                title_fr=_title_fr_for_entry(entry, remediation),
                description_fr=_description_fr_for_entry(entry, remediation),
                rule_code=rule_code.value,
                reason_code=entry.reason_code,
                scope_level=entry.scope_level,
                scope_id=entry.scope_id,
                remediation_field=remediation.get("remediation_field"),
                cta_label_fr=remediation.get("cta_label_fr") or "Compléter",
                source_url=_source_url(entry),
            )
            items.append(draft)
            by_rule[rule_code.value] = by_rule.get(rule_code.value, 0) + 1
            by_level[entry.scope_level] = by_level.get(entry.scope_level, 0) + 1

    return RemediationPlan(
        org_id=org_id,
        items_to_create=items,
        summary={
            "total": len(items),
            **{f"by_rule_{k}": v for k, v in by_rule.items()},
            **{f"by_level_{k}": v for k, v in by_level.items()},
        },
        computed_at=datetime.now(timezone.utc).isoformat(),
    )
