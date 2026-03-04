"""
PROMEOS V50 — Catalogue de preuves OPERAT V2 + Mapping Issue → Preuves attendues

Source de vérité backend pour :
  - PROOF_TYPES : types de preuves avec titre FR, description, exemples de pièces
  - ISSUE_PROOF_MAPPING : issue_code → proof_types attendus + rationale + confidence

Confidence :
  - "high"  = mapping confirmé par textes réglementaires
  - "medium" = mapping déduit de la pratique courante
  - "low"   = V1 à confirmer — TODO vérification réglementaire
"""

# ── Types de preuves OPERAT ──────────────────────────────────────────────────

PROOF_TYPES = {
    "attestation_operat": {
        "proof_type": "attestation_operat",
        "title_fr": "Attestation OPERAT / récépissé de dépôt",
        "description_fr": (
            "Attestation officielle de dépôt annuel sur la plateforme OPERAT, "
            "ou récépissé ADEME confirmant la déclaration."
        ),
        "examples_fr": [
            "PDF attestation OPERAT",
            "Récépissé ADEME",
            "Capture écran confirmation dépôt",
        ],
        "template_kind": "attestation",
        "version": "v50",
    },
    "dossier_modulation": {
        "proof_type": "dossier_modulation",
        "title_fr": "Dossier de modulation",
        "description_fr": (
            "Justificatif de modulation de l'objectif : vacance partielle, "
            "travaux lourds, changement d'activité, force majeure."
        ),
        "examples_fr": [
            "PDF dossier modulation",
            "Justificatifs travaux (devis, factures)",
            "Attestation de vacance",
        ],
        "template_kind": "dossier",
        "version": "v50",
    },
    "justificatif_exemption": {
        "proof_type": "justificatif_exemption",
        "title_fr": "Justificatif d'exemption ou d'exclusion",
        "description_fr": (
            "Preuve que le bâtiment n'est pas assujetti au Décret tertiaire "
            "(surface < 1 000 m², usage exclu, bâtiment temporaire, etc.)."
        ),
        "examples_fr": [
            "PDF justificatif surface < seuil",
            "Attestation usage non tertiaire",
            "Plan cadastral avec surfaces",
        ],
        "template_kind": "justificatif",
        "version": "v50",
    },
    "justificatif_multi_occupation": {
        "proof_type": "justificatif_multi_occupation",
        "title_fr": "Justificatif multi-occupation",
        "description_fr": (
            "Répartition des surfaces et charges entre occupants "
            "pour un bâtiment partagé (parties communes, lots privatifs)."
        ),
        "examples_fr": [
            "PDF répartition charges",
            "XLSX surfaces par occupant",
            "Convention multi-occupation signée",
        ],
        "template_kind": "repartition",
        "version": "v50",
    },
    "preuve_surface_usage": {
        "proof_type": "preuve_surface_usage",
        "title_fr": "Preuve de surface / usage",
        "description_fr": (
            "Justificatif de surface tertiaire ou de catégorie d'usage "
            "en cas d'incohérence ou de données patrimoniales incomplètes."
        ),
        "examples_fr": [
            "PDF plan cadastral",
            "Attestation géomètre",
            "DPE avec surfaces",
        ],
        "template_kind": "justificatif",
        "version": "v50",
    },
    "bail_titre_propriete": {
        "proof_type": "bail_titre_propriete",
        "title_fr": "Bail ou titre de propriété",
        "description_fr": (
            "Bail commercial ou titre de propriété identifiant "
            "le rôle de l'assujetti (propriétaire, locataire, mandataire)."
        ),
        "examples_fr": [
            "PDF bail commercial",
            "Titre de propriété",
            "Acte notarié",
        ],
        "template_kind": "contrat",
        "version": "v50",
    },
}


# ── Mapping Issue → Preuves attendues ────────────────────────────────────────

ISSUE_PROOF_MAPPING = {
    "TERTIAIRE_NO_BUILDING": {
        "proof_types": [],
        "rationale_fr": "Aucune preuve spécifique — l'action est de compléter le patrimoine.",
        "confidence": "high",
    },
    "TERTIAIRE_MISSING_SURFACE": {
        "proof_types": ["preuve_surface_usage"],
        "rationale_fr": "Surface manquante : fournir un plan, DPE ou attestation géomètre.",
        "confidence": "high",
    },
    "TERTIAIRE_MISSING_USAGE": {
        "proof_types": [],
        "rationale_fr": "Pas de preuve documentaire requise — saisie directe dans PROMEOS.",
        "confidence": "high",
    },
    "TERTIAIRE_NO_RESPONSIBILITY": {
        "proof_types": ["bail_titre_propriete"],
        "rationale_fr": "Définir le responsable et fournir le bail ou titre de propriété.",
        "confidence": "medium",
    },
    "TERTIAIRE_NO_REPORTING_PERIOD": {
        "proof_types": [],
        "rationale_fr": "Pas de preuve documentaire requise — saisie directe.",
        "confidence": "high",
    },
    "TERTIAIRE_SURFACE_COHERENCE": {
        "proof_types": ["justificatif_exemption", "preuve_surface_usage"],
        "rationale_fr": (
            "Surface < 1 000 m² : vérifier l'assujettissement. "
            "Fournir un justificatif d'exemption ou une preuve de surface."
        ),
        "confidence": "medium",
    },
    "TERTIAIRE_RESP_NO_EMAIL": {
        "proof_types": [],
        "rationale_fr": "Pas de preuve documentaire requise — saisie directe.",
        "confidence": "high",
    },
    "TERTIAIRE_PERIMETER_EVENT_PROOF": {
        "proof_types": ["dossier_modulation"],
        "rationale_fr": (
            "Événement de périmètre déclaré : un dossier de modulation est "
            "obligatoire pour que la demande soit acceptée par OPERAT."
        ),
        "confidence": "high",
    },
}


# ── API functions ────────────────────────────────────────────────────────────


def get_proof_types() -> dict:
    """Retourne le catalogue complet des types de preuves OPERAT."""
    return {
        "proof_types": PROOF_TYPES,
        "version": "v50",
        "total": len(PROOF_TYPES),
    }


def get_issue_proof_mapping() -> dict:
    """Retourne le mapping complet issue_code → preuves attendues."""
    return {
        "issue_mapping": ISSUE_PROOF_MAPPING,
        "version": "v50",
        "total": len(ISSUE_PROOF_MAPPING),
    }


def get_proofs_for_issue(issue_code: str) -> dict:
    """Retourne les preuves attendues pour un code d'issue donné."""
    mapping = ISSUE_PROOF_MAPPING.get(issue_code)
    if not mapping:
        return {
            "issue_code": issue_code,
            "proof_types": [],
            "rationale_fr": "Code d'issue inconnu.",
            "confidence": "low",
            "details": [],
        }

    details = []
    for pt in mapping["proof_types"]:
        info = PROOF_TYPES.get(pt)
        if info:
            details.append(info)

    return {
        "issue_code": issue_code,
        "proof_types": mapping["proof_types"],
        "rationale_fr": mapping["rationale_fr"],
        "confidence": mapping["confidence"],
        "details": details,
    }
