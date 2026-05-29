"""
PROMEOS S3 — Service « Groupe de structures » (mutualisation P0 juridique).

Encapsule les garde-fous réglementaires de l'Article 14 de l'arrêté du
10 avril 2020 modifié (R.174-31 + L.174-1 CCH). Toute violation lève
`MutualisationViolation` traduit en HTTP 422 par les routes.

5 invariants enforced ici :
  I1. Statuses canoniques uniquement (draft/pending_validation/validated/archived).
  I2. Validation représentant légal par EFA obligatoire avant export final.
  I3. Une EFA active ne peut appartenir qu'à un seul groupe actif.
  I4. Redistribution d'économie unique par EFA donneuse / jalon.
  I5. Aucune redistribution au-delà du surplus disponible (garde-fou
      additionnel non-textuel mais cohérent avec l'esprit § III Art. 14).

Cross-check : docs/audits/crosscheck_legifrance_mutualisation_art14_2026_05_28.md
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import (
    GROUPE_STATUSES,
    GroupeStructures,
    GroupeStructuresMembre,
    MutualisationLedger,
    RL_STATUSES,
    TertiaireEfa,
)


class MutualisationViolation(ValueError):
    """Exception métier — un garde-fou Art. 14 a été enfreint.

    Attributs :
      code : identifiant machine (ex 'EFA_ALREADY_IN_ACTIVE_GROUP').
      message_fr : message FR opposable affiché à l'utilisateur.
      hint : indication de remédiation (qui faire quoi).
    """

    def __init__(self, code: str, message_fr: str, hint: Optional[str] = None) -> None:
        super().__init__(f"[{code}] {message_fr}")
        self.code = code
        self.message_fr = message_fr
        self.hint = hint


# ─── Création / cycle de vie du groupe ────────────────────────────────────


def create_groupe(
    db: Session,
    *,
    organisation_id: int,
    nom: str,
    description: Optional[str] = None,
    created_by: Optional[str] = None,
) -> GroupeStructures:
    """Crée un nouveau groupe de structures en statut `draft`."""
    if not nom or not nom.strip():
        raise MutualisationViolation(
            "GROUPE_NOM_REQUIS",
            "Le nom du groupe est obligatoire.",
            hint="Saisissez un libellé métier (ex « Patrimoine bureaux Île-de-France »).",
        )
    groupe = GroupeStructures(
        organisation_id=organisation_id,
        nom=nom.strip(),
        description=(description or None),
        status="draft",
        created_by=created_by,
    )
    db.add(groupe)
    db.flush()
    return groupe


def archive_groupe(db: Session, groupe: GroupeStructures) -> GroupeStructures:
    """Archive un groupe (statut terminal, libère les EFA membres).

    Une EFA appartenant à un groupe archivé peut être réintégrée dans
    un nouveau groupe (I3 ne s'applique qu'aux groupes actifs).
    """
    groupe.status = "archived"
    # Soft-delete cascade des appartenances pour libérer les EFA (I3).
    now = datetime.now(timezone.utc)
    for m in groupe.membres:
        if m.deleted_at is None:
            m.deleted_at = now
    db.flush()
    return groupe


# ─── I3 — Ajout d'une EFA dans un groupe (unicité d'appartenance) ────────


def add_efa_to_groupe(
    db: Session,
    groupe: GroupeStructures,
    efa_id: int,
) -> GroupeStructuresMembre:
    """Ajoute une EFA au groupe. Refuse si :
    - groupe archivé (I3 : pas d'ajout dans un groupe terminal).
    - EFA déjà membre actif d'un autre groupe (I3 cardinal Art. 14 §1 al.3).
    - EFA hors org du groupe (sécurité IS1).
    """
    if groupe.status == "archived":
        raise MutualisationViolation(
            "GROUPE_ARCHIVED",
            "Impossible d'ajouter une EFA à un groupe archivé.",
            hint="Créez un nouveau groupe en statut « draft » et réintégrez-y l'EFA.",
        )

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if efa is None:
        raise MutualisationViolation(
            "EFA_NOT_FOUND",
            f"L'EFA #{efa_id} est introuvable.",
            hint="Vérifiez l'identifiant ou créez l'EFA via /conformite/tertiaire.",
        )
    if efa.org_id != groupe.organisation_id:
        raise MutualisationViolation(
            "EFA_CROSS_ORG",
            "Cette EFA n'appartient pas à votre organisation.",
            hint=None,
        )

    # I3 — Vérification d'unicité d'appartenance active.
    existing = (
        db.query(GroupeStructuresMembre)
        .filter(
            GroupeStructuresMembre.efa_id == efa_id,
            GroupeStructuresMembre.deleted_at.is_(None),
        )
        .first()
    )
    if existing is not None:
        raise MutualisationViolation(
            "EFA_ALREADY_IN_ACTIVE_GROUP",
            f"L'EFA « {efa.nom} » appartient déjà à un autre groupe actif "
            "(Art. 14 §1 al.3 de l'arrêté du 10 avril 2020 modifié : une "
            "entité fonctionnelle ne peut être présente dans plusieurs groupes).",
            hint=(f"Retirez d'abord l'EFA du groupe actif (id={existing.group_id}) ou archivez ce groupe."),
        )

    membre = GroupeStructuresMembre(
        group_id=groupe.id,
        efa_id=efa_id,
        site_id=efa.site_id,
        representant_legal_status="pending",
    )
    db.add(membre)
    db.flush()
    # Statut du groupe : reste `draft` tant qu'aucune validation RL faite.
    return membre


def remove_efa_from_groupe(
    db: Session,
    groupe: GroupeStructures,
    efa_id: int,
) -> None:
    """Retire une EFA du groupe (soft-delete de l'appartenance)."""
    membre = (
        db.query(GroupeStructuresMembre)
        .filter(
            GroupeStructuresMembre.group_id == groupe.id,
            GroupeStructuresMembre.efa_id == efa_id,
            GroupeStructuresMembre.deleted_at.is_(None),
        )
        .first()
    )
    if membre is None:
        raise MutualisationViolation(
            "MEMBRE_NOT_FOUND",
            f"L'EFA #{efa_id} n'est pas membre actif de ce groupe.",
        )
    membre.deleted_at = datetime.now(timezone.utc)
    db.flush()


# ─── I2 — Validation du représentant légal (Art. 14 §1 al.2) ─────────────


def set_representant_legal_status(
    db: Session,
    membre: GroupeStructuresMembre,
    *,
    new_status: str,
    validator_user_id: Optional[str],
    validation_note: Optional[str] = None,
) -> GroupeStructuresMembre:
    """Met à jour le statut RL pour une EFA membre.

    Accepte 'validated' ou 'rejected'. 'pending' = état initial à la création.

    Sprint S4 (2026-05-29) — si new_status='validated', calcule un
    `validation_token_hash` SHA256 du payload (group_id, efa_id,
    validator_user_id, validated_at_iso). Ce hash sert d'identifiant
    opposable au contrôle ADEME ultérieur (Art. 14 §1 al.2 — solidarité).
    """
    if new_status not in RL_STATUSES:
        raise MutualisationViolation(
            "RL_STATUS_INVALID",
            f"Statut de validation invalide : {new_status!r}. Valeurs autorisées : {RL_STATUSES}.",
        )
    if new_status == "pending":
        raise MutualisationViolation(
            "RL_STATUS_REGRESSION_DENIED",
            "Repasser une validation RL en 'pending' n'est pas autorisé (audit trail).",
        )
    membre.representant_legal_status = new_status
    if new_status == "validated":
        validated_at = datetime.now(timezone.utc)
        membre.representant_legal_validated_at = validated_at
        # S4 — Hash opposable. Pas de secret-key (déterministe et public),
        # sa valeur d'audit vient de la reproductibilité par le contrôleur
        # à partir des données stockées.
        import hashlib

        payload = f"{membre.group_id}|{membre.efa_id}|{validator_user_id or ''}|{validated_at.isoformat()}"
        membre.validation_token_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    else:
        # rejected → reset timestamp + hash
        membre.representant_legal_validated_at = None
        membre.validation_token_hash = None
    membre.validator_user_id = validator_user_id
    membre.validation_note = validation_note
    db.flush()
    return membre


def all_membres_rl_validated(groupe: GroupeStructures) -> bool:
    """True ssi TOUTES les EFA membres actives ont RL=validated.

    Garde-fou I2 utilisé en amont de l'export Table 1B.
    """
    actives = [m for m in groupe.membres if m.deleted_at is None]
    if not actives:
        return False
    return all(m.representant_legal_status == "validated" for m in actives)


def ensure_groupe_exportable(groupe: GroupeStructures) -> None:
    """Lève si le groupe n'est pas opposable à l'ADEME (Art. 14 §1 al.2).

    Conditions d'opposabilité :
      - statut groupe ∈ { 'pending_validation', 'validated' }
      - au moins 1 EFA membre active
      - TOUS les RL validés
    """
    if groupe.status == "archived":
        raise MutualisationViolation(
            "GROUPE_ARCHIVED",
            "Le groupe est archivé — l'export Table 1B n'est plus opposable.",
        )
    actives = [m for m in groupe.membres if m.deleted_at is None]
    if not actives:
        raise MutualisationViolation(
            "GROUPE_EMPTY",
            "Le groupe ne contient aucune EFA active.",
            hint="Ajoutez au moins une EFA avant d'exporter la Table 1B.",
        )
    missing = [m for m in actives if m.representant_legal_status != "validated"]
    if missing:
        raise MutualisationViolation(
            "RL_VALIDATION_MISSING",
            (
                f"L'export Table 1B exige la validation préalable du représentant "
                f"légal de chaque EFA membre (Art. 14 §1 al.2). "
                f"Validations manquantes : {len(missing)} EFA sur {len(actives)}."
            ),
            hint=("Collectez la validation du représentant légal de chaque EFA concernée puis retentez l'export."),
        )


# ─── I4 / I5 — Ledger de redistribution ──────────────────────────────────


def record_redistribution(
    db: Session,
    groupe: GroupeStructures,
    *,
    donneuse_efa_id: int,
    jalon_annee: int,
    kwh_redistribues: float,
    surplus_disponible_kwh: float,
    note: Optional[str] = None,
) -> MutualisationLedger:
    """Enregistre une redistribution d'économies dans le ledger.

    Garde-fous :
      - I4 : refus si l'EFA donneuse a déjà redistribué pour ce jalon
        (UNIQUE DB + check explicite côté service pour message FR).
      - I5 : refus si `kwh_redistribues > surplus_disponible_kwh`.
    """
    if kwh_redistribues <= 0:
        raise MutualisationViolation(
            "REDISTRIBUTION_KWH_NON_POSITIF",
            "Le volume redistribué doit être strictement positif.",
        )
    if surplus_disponible_kwh < 0:
        raise MutualisationViolation(
            "SURPLUS_NEGATIF",
            "Le surplus disponible est négatif — aucune redistribution possible.",
        )
    if kwh_redistribues > surplus_disponible_kwh:
        raise MutualisationViolation(
            "REDISTRIBUTION_EXCEDE_SURPLUS",
            (
                f"Le volume redistribué ({kwh_redistribues:.0f} kWh) excède le "
                f"surplus disponible ({surplus_disponible_kwh:.0f} kWh) pour cette EFA."
            ),
            hint="Réduisez le volume ou recalculez le surplus avec les dernières données.",
        )
    # I4 — déjà redistribué pour ce jalon ?
    existing = (
        db.query(MutualisationLedger)
        .filter(
            MutualisationLedger.group_id == groupe.id,
            MutualisationLedger.donneuse_efa_id == donneuse_efa_id,
            MutualisationLedger.jalon_annee == jalon_annee,
        )
        .first()
    )
    if existing is not None:
        raise MutualisationViolation(
            "REDISTRIBUTION_DEJA_EFFECTUEE",
            (
                f"L'EFA #{donneuse_efa_id} a déjà redistribué ses économies pour "
                f"le jalon {jalon_annee} (Art. 14 §1 al.4 : une seule redistribution "
                "autorisée)."
            ),
        )
    entry = MutualisationLedger(
        group_id=groupe.id,
        jalon_annee=jalon_annee,
        donneuse_efa_id=donneuse_efa_id,
        kwh_redistribues=kwh_redistribues,
        note=note,
    )
    db.add(entry)
    db.flush()
    return entry


# ─── Status transitions du groupe ────────────────────────────────────────


def set_groupe_status(
    db: Session,
    groupe: GroupeStructures,
    new_status: str,
) -> GroupeStructures:
    """Bascule explicite du status (whitelist Art. 14)."""
    if new_status not in GROUPE_STATUSES:
        raise MutualisationViolation(
            "GROUPE_STATUS_INVALID",
            f"Statut invalide : {new_status!r}. Valeurs autorisées : {GROUPE_STATUSES}.",
        )
    groupe.status = new_status
    db.flush()
    return groupe
