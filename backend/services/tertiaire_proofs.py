"""
PROMEOS V45 — Catalogue de preuves OPERAT + helpers statut preuves

PROOF_CATALOG : catalogue minimal des preuves attendues pour le Décret tertiaire.
get_expected_proofs_for_efa : preuves attendues selon contexte EFA.
list_proofs_status : compteurs expected/deposited/validated par EFA+year.
"""

import json
import logging

from sqlalchemy.orm import Session

from models import (
    TertiaireEfa,
    TertiaireEfaBuilding,
    TertiaireResponsibility,
    TertiairePerimeterEvent,
    TertiaireProofArtifact,
    EfaStatut,
)

logger = logging.getLogger(__name__)

# ── Catalogue de preuves OPERAT (V1 robuste) ─────────────────────────────────

PROOF_CATALOG = {
    "attestation_operat": {
        "type": "attestation_operat",
        "label_fr": "Attestation OPERAT / récépissé de dépôt",
        "owner_role": "proprietaire",
        "exemple_fichiers": ["PDF attestation", "Récépissé ADEME"],
        "deadline_hint": "Avant échéance annuelle OPERAT",
        "kb_domain": "conformite/tertiaire-operat",
        "description_fr": "Attestation officielle de dépôt sur la plateforme OPERAT ou récépissé ADEME.",
    },
    "dossier_modulation": {
        "type": "dossier_modulation",
        "label_fr": "Dossier de modulation (vacance, travaux, changement d'usage)",
        "owner_role": "proprietaire",
        "exemple_fichiers": ["PDF dossier modulation", "Justificatifs travaux"],
        "deadline_hint": "À joindre au dépôt si modulation demandée",
        "kb_domain": "conformite/tertiaire-operat",
        "description_fr": "Justificatif de modulation : vacance partielle, travaux lourds, changement d'activité.",
    },
    "justificatif_exemption": {
        "type": "justificatif_exemption",
        "label_fr": "Justificatif d'exemption ou d'exclusion",
        "owner_role": "proprietaire",
        "exemple_fichiers": ["PDF justificatif", "Attestation surface < seuil"],
        "deadline_hint": "À conserver en cas d'audit",
        "kb_domain": "conformite/tertiaire-operat",
        "description_fr": "Preuve que le bâtiment n'est pas assujetti (surface < 1000 m², usage exclu, etc.).",
    },
    "justificatif_multi_occupation": {
        "type": "justificatif_multi_occupation",
        "label_fr": "Justificatif multi-occupation (répartition, parties communes)",
        "owner_role": "proprietaire",
        "exemple_fichiers": ["PDF répartition charges", "XLSX surfaces par occupant"],
        "deadline_hint": "Avant dépôt si multi-occupation",
        "kb_domain": "conformite/tertiaire-operat",
        "description_fr": "Répartition des surfaces et charges entre occupants pour un bâtiment partagé.",
    },
    "preuve_surface_usage": {
        "type": "preuve_surface_usage",
        "label_fr": "Preuve de surface / usage (si patrimoine incomplet)",
        "owner_role": "mandataire",
        "exemple_fichiers": ["PDF plan cadastral", "Attestation géomètre", "DPE"],
        "deadline_hint": "À fournir pour compléter le patrimoine",
        "kb_domain": "conformite/tertiaire-operat",
        "description_fr": "Justificatif de surface tertiaire ou catégorie d'usage en cas d'incohérence patrimoine.",
    },
    "bail_titre_propriete": {
        "type": "bail_titre_propriete",
        "label_fr": "Bail ou titre de propriété",
        "owner_role": "proprietaire",
        "exemple_fichiers": ["PDF bail commercial", "Titre de propriété"],
        "deadline_hint": "À conserver en cas d'audit",
        "kb_domain": "conformite/tertiaire-operat",
        "description_fr": "Bail commercial ou titre de propriété identifiant le rôle de l'assujetti.",
    },
}


def get_expected_proofs_for_efa(db: Session, efa_id: int, year: int = None) -> list[dict]:
    """Retourne la liste des preuves attendues selon le contexte de l'EFA.

    Logique :
    - Toujours: attestation_operat + bail_titre_propriete
    - Si perimeter events existent: dossier_modulation
    - Si multi-occupation détectable: justificatif_multi_occupation
    - Si surfaces incohérentes / incomplètes: preuve_surface_usage
    """
    efa = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.id == efa_id,
            TertiaireEfa.deleted_at.is_(None),
        )
        .first()
    )
    if not efa:
        return []

    buildings = (
        db.query(TertiaireEfaBuilding)
        .filter(
            TertiaireEfaBuilding.efa_id == efa_id,
        )
        .all()
    )
    events = (
        db.query(TertiairePerimeterEvent)
        .filter(
            TertiairePerimeterEvent.efa_id == efa_id,
        )
        .all()
    )

    expected = []

    # Toujours attendu
    expected.append(PROOF_CATALOG["attestation_operat"])
    expected.append(PROOF_CATALOG["bail_titre_propriete"])

    # Si événements périmètre → dossier de modulation
    if len(events) > 0:
        expected.append(PROOF_CATALOG["dossier_modulation"])

    # Si surfaces manquantes ou nulles → preuve surface/usage
    has_missing_surface = any(not b.surface_m2 or b.surface_m2 <= 0 for b in buildings) if buildings else not buildings
    if has_missing_surface:
        expected.append(PROOF_CATALOG["preuve_surface_usage"])

    # Surface < 1000 → justificatif exemption potentiel
    total_surface = sum(b.surface_m2 or 0 for b in buildings)
    if buildings and total_surface < 1000:
        expected.append(PROOF_CATALOG["justificatif_exemption"])

    return expected


def list_proofs_status(db: Session, efa_id: int, year: int = None) -> dict:
    """Retourne les compteurs de preuves : expected, deposited, validated.

    Basé sur :
    - expected : get_expected_proofs_for_efa
    - deposited : TertiaireProofArtifact existants pour cette EFA
    - validated : ProofArtifact avec kb_doc_id dont le KB doc status = 'validated'
    """
    expected = get_expected_proofs_for_efa(db, efa_id, year)
    expected_types = [p["type"] for p in expected]

    # Deposited : proof artifacts existants
    artifacts = (
        db.query(TertiaireProofArtifact)
        .filter(
            TertiaireProofArtifact.efa_id == efa_id,
        )
        .all()
    )

    deposited = []
    validated = []

    for artifact in artifacts:
        entry = {
            "id": artifact.id,
            "type": artifact.type,
            "kb_doc_id": artifact.kb_doc_id,
            "file_path": artifact.file_path,
            "owner_role": artifact.owner_role.value if artifact.owner_role else None,
            "created_at": str(artifact.created_at) if artifact.created_at else None,
        }
        deposited.append(entry)

        # Check KB doc status for validation
        if artifact.kb_doc_id:
            try:
                from app.kb.store import KBStore

                kb_store = KBStore()
                doc = kb_store.get_doc(artifact.kb_doc_id)
                if doc and doc.get("status") == "validated":
                    validated.append(entry)
            except Exception:
                pass  # KB non disponible — non bloquant

    # Deposited types (for matching against expected)
    deposited_types = set(a.type for a in artifacts)

    # Missing = expected but not deposited
    missing = [p for p in expected if p["type"] not in deposited_types]

    return {
        "efa_id": efa_id,
        "year": year,
        "expected": expected,
        "expected_count": len(expected),
        "deposited": deposited,
        "deposited_count": len(deposited),
        "validated": validated,
        "validated_count": len(validated),
        "missing": missing,
        "missing_count": len(missing),
        "coverage_pct": round(len(deposited) / len(expected) * 100) if expected else 100,
    }
