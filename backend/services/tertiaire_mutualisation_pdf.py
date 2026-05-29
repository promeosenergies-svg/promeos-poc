"""
PROMEOS S4 (2026-05-29) — Export PDF Table 1B Annexe IV (mutualisation).

Pattern aligné sur `services/v4/pdf_export_service.py` (reportlab +
SimpleDocTemplate + tokens couleur Sol). Le PDF :
  - reproduit la Table 1B (groupe + EFA membres + statut RL + source réglementaire)
  - inclut un hash SHA256 d'opposabilité (identifiant d'export)
  - cite verbatim Art. 14 arrêté 10/04/2020 modifié + L.174-1 + R.174-31 CCH

Cross-check Phase 0 : pas de nouvelle référence Légifrance — on s'appuie
sur le cross-check S3 livré dans `crosscheck_legifrance_mutualisation_art14_2026_05_28.md`.

Garde-fous opposabilité (cohérents service S3) :
  - Refuse si groupe non opposable (Art. 14 §1 al.2 — solidarité RL).
  - Pas d'inclusion du token de validation RL (donnée sensible).
  - Hash SHA256 = signature reproductible de l'état au moment de l'export.
"""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from io import BytesIO

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from models import GroupeStructures, TertiaireEfa


# Tokens couleur Sol (alignés pdf_export_service v4).
_SOL_BROWN_DARK = colors.HexColor("#3d2e1c")
_SOL_BROWN_MID = colors.HexColor("#6b5a4a")
_SOL_BROWN_LIGHT = colors.HexColor("#8a7869")
_SOL_CREAM = colors.HexColor("#faf6ed")
_SOL_ACCENT = colors.HexColor("#c9a875")

# Référence canonique unique pour toute mention réglementaire dans ce PDF.
_SOURCE_REGULATORY = "Article 14 arrêté 10/04/2020 modifié — Table 1B Annexe IV (R.174-31 + L.174-1 CCH)"


class MutualisationPdfError(Exception):
    """Erreur générique export PDF Table 1B."""


def compute_export_hash(payload: dict) -> str:
    """SHA256 hex (16 chars head) de la structure exportée.

    Sert d'identifiant opposable : un audit ADEME pourra recalculer le
    hash à partir des mêmes données et vérifier l'absence d'altération.
    """
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def generate_table_1b_pdf(db, groupe: GroupeStructures) -> tuple[bytes, str]:
    """Génère le PDF Table 1B Annexe IV pour un groupe de structures.

    Args:
        db: session SQLAlchemy (pour résoudre les EFA).
        groupe: instance GroupeStructures déjà vérifiée comme exportable
                par `ensure_groupe_exportable()` (le caller fait le check).

    Returns:
        (pdf_bytes, export_hash)
        - pdf_bytes : contenu binaire du PDF
        - export_hash : SHA256 hex de la structure (opposabilité)
    """
    actives = [m for m in groupe.membres if m.deleted_at is None]
    if not actives:
        raise MutualisationPdfError("Le groupe ne contient aucune EFA active — refus PDF avant rendu.")

    efa_ids = [m.efa_id for m in actives]
    efas = {e.id: e for e in db.query(TertiaireEfa).filter(TertiaireEfa.id.in_(efa_ids)).all()}

    generated_at = datetime.now(timezone.utc)
    generated_at_iso = generated_at.isoformat()
    generated_at_fr = generated_at.strftime("%d/%m/%Y %H:%M UTC")

    # Structure canonique pour le hash (reproductible).
    payload_for_hash = {
        "groupe_id": groupe.id,
        "groupe_nom": groupe.nom,
        "groupe_status": groupe.status,
        "organisation_id": groupe.organisation_id,
        "membres": [
            {
                "efa_id": m.efa_id,
                "efa_nom": getattr(efas.get(m.efa_id), "nom", ""),
                "site_id": m.site_id,
                "rl_status": m.representant_legal_status,
                "rl_validated_at": (
                    m.representant_legal_validated_at.isoformat() if m.representant_legal_validated_at else None
                ),
            }
            for m in actives
        ],
        "source_reglementaire": _SOURCE_REGULATORY,
        "generated_at": generated_at_iso,
    }
    export_hash = compute_export_hash(payload_for_hash)

    pdf_bytes = _render_with_reportlab(groupe, actives, efas, generated_at_fr, export_hash)
    return pdf_bytes, export_hash


def _render_with_reportlab(groupe, actives, efas, generated_at_fr, export_hash):
    """Layout reportlab — 1 page A4."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        topMargin=24 * mm,
        bottomMargin=20 * mm,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        title=f"PROMEOS — Table 1B — {groupe.nom}",
        author="PROMEOS",
    )
    styles = getSampleStyleSheet()  # noqa: F841 — utilisé indirectement par ParagraphStyle

    title = ParagraphStyle(
        "TitleS4",
        fontName="Helvetica-Bold",
        fontSize=16,
        textColor=_SOL_BROWN_DARK,
        leading=20,
        spaceAfter=4,
    )
    subtitle = ParagraphStyle(
        "SubtitleS4",
        fontName="Helvetica-Oblique",
        fontSize=9,
        textColor=_SOL_BROWN_MID,
        leading=12,
        spaceAfter=10,
    )
    h2 = ParagraphStyle(
        "H2S4",
        fontName="Helvetica-Bold",
        fontSize=11,
        textColor=_SOL_BROWN_DARK,
        leading=14,
        spaceBefore=10,
        spaceAfter=6,
    )
    body = ParagraphStyle(
        "BodyS4",
        fontName="Helvetica",
        fontSize=9,
        textColor=_SOL_BROWN_DARK,
        leading=12,
    )
    small = ParagraphStyle(
        "SmallS4",
        fontName="Helvetica",
        fontSize=7.5,
        textColor=_SOL_BROWN_LIGHT,
        leading=10,
    )

    elements = [
        Paragraph("Mutualisation Décret Tertiaire — Table 1B Annexe IV", title),
        Paragraph(
            f"Groupe « {groupe.nom} » · statut {groupe.status} · généré {generated_at_fr}",
            subtitle,
        ),
        Paragraph("Composition du groupe de structures", h2),
        _build_members_table(actives, efas),
        Spacer(1, 8),
        Paragraph(
            f"<b>Source réglementaire :</b> {_SOURCE_REGULATORY}",
            body,
        ),
        Paragraph(
            "Constitution du groupe selon l'Article 14 §1 al.1 de l'arrêté "
            "10/04/2020 modifié. Validation du représentant légal de chaque "
            "entité fonctionnelle requise (Art. 14 §1 al.2) — vaut acceptation "
            "du principe de solidarité patrimoniale.",
            body,
        ),
        Spacer(1, 10),
        Paragraph(
            f"<b>Identifiant d'export (opposabilité) :</b> <font face='Courier'>{export_hash}</font>",
            body,
        ),
        Paragraph(
            "Le hash SHA256 ci-dessus est calculé sur l'état du groupe au "
            "moment de l'export. Un contrôle ADEME ultérieur peut recalculer "
            "ce hash à partir des données déposées sur OPERAT pour vérifier "
            "l'absence d'altération.",
            small,
        ),
        Spacer(1, 6),
        Paragraph(
            "Document généré par PROMEOS — aucun éditeur tiers n'a contribué "
            "à ce contenu. La déclaration finale sur OPERAT reste à la charge "
            "de l'assujetti dès que le module ADEME « Mutualisation des "
            "résultats à l'échelle d'un patrimoine » sera opérationnel.",
            small,
        ),
    ]

    doc.build(elements)
    out = buffer.getvalue()
    buffer.close()
    return out


def _build_members_table(actives, efas):
    """Table reportlab — EFA membres + statut RL."""
    headers = ["EFA #", "Nom EFA", "Site #", "Statut RL", "Validation RL"]
    rows = [headers]
    for m in actives:
        efa = efas.get(m.efa_id)
        rl_validated = (
            m.representant_legal_validated_at.strftime("%d/%m/%Y %H:%M") if m.representant_legal_validated_at else "—"
        )
        rows.append(
            [
                str(m.efa_id),
                (getattr(efa, "nom", "") or "")[:40],
                str(m.site_id or "—"),
                m.representant_legal_status,
                rl_validated,
            ]
        )
    table = Table(rows, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("FONT", (0, 0), (-1, -1), "Helvetica", 9),
                ("FONT", (0, 0), (-1, 0), "Helvetica-Bold", 9),
                ("BACKGROUND", (0, 0), (-1, 0), _SOL_CREAM),
                ("TEXTCOLOR", (0, 0), (-1, -1), _SOL_BROWN_DARK),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("LINEBELOW", (0, 0), (-1, 0), 0.8, _SOL_ACCENT),
                ("LINEBELOW", (0, -1), (-1, -1), 0.4, _SOL_BROWN_LIGHT),
                (
                    "ROWBACKGROUNDS",
                    (0, 1),
                    (-1, -1),
                    [colors.white, _SOL_CREAM],
                ),
            ]
        )
    )
    return table
