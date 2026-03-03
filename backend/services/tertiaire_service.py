"""
PROMEOS V40 — Service Tertiaire / OPERAT
qualify_efa, run_controls, precheck_declaration, generate_operat_pack
"""
import hashlib
import json
import logging
import os
import zipfile
from datetime import date, datetime, timezone
from pathlib import Path

from sqlalchemy.orm import Session

from models import (
    TertiaireEfa, TertiaireEfaBuilding, TertiaireResponsibility,
    TertiairePerimeterEvent, TertiaireDeclaration,
    TertiaireProofArtifact, TertiaireDataQualityIssue,
    EfaStatut, DeclarationStatus,
    DataQualityIssueSeverity, DataQualityIssueStatus,
    Site, Batiment,  # V42
)

logger = logging.getLogger(__name__)


# ── Qualification ────────────────────────────────────────────────────────────

def qualify_efa(db: Session, efa_id: int) -> dict:
    """Retourne le statut de qualification d'une EFA (completude donnees)."""
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        return {"status": "not_found", "explanation": "EFA introuvable"}

    if efa.statut == EfaStatut.CLOSED:
        return {"status": "closed", "explanation": "EFA fermée", "efa_id": efa_id}

    buildings = db.query(TertiaireEfaBuilding).filter(
        TertiaireEfaBuilding.efa_id == efa_id
    ).all()
    responsibilities = db.query(TertiaireResponsibility).filter(
        TertiaireResponsibility.efa_id == efa_id
    ).all()

    checks = {
        "has_buildings": len(buildings) > 0,
        "has_surfaces": all(b.surface_m2 and b.surface_m2 > 0 for b in buildings) if buildings else False,
        "has_usages": all(b.usage_label for b in buildings) if buildings else False,
        "has_responsibilities": len(responsibilities) > 0,
        "has_reporting_period": efa.reporting_start is not None,
    }

    total = len(checks)
    ok_count = sum(1 for v in checks.values() if v)
    pct = round(ok_count / total * 100) if total > 0 else 0

    if pct == 100:
        qualification = "complete"
        explanation = "Toutes les données EFA sont renseignées"
    elif pct >= 60:
        qualification = "partielle"
        missing = [k for k, v in checks.items() if not v]
        explanation = f"Données partielles — manquant : {', '.join(missing)}"
    else:
        qualification = "insuffisante"
        missing = [k for k, v in checks.items() if not v]
        explanation = f"Données insuffisantes — manquant : {', '.join(missing)}"

    return {
        "status": qualification,
        "efa_id": efa_id,
        "completeness_pct": pct,
        "checks": checks,
        "explanation": explanation,
    }


# ── Controles qualite V2 ─────────────────────────────────────────────────────

# V45: proof_required structuré — type, label_fr, owner_role, deadline_hint, doc_domain
def _proof(proof_type, label_fr, owner_role="proprietaire", deadline_hint="Avant dépôt"):
    """Helper pour construire un proof_required structuré V45."""
    return {
        "type": proof_type,
        "label_fr": label_fr,
        "owner_role": owner_role,
        "deadline_hint": deadline_hint,
        "doc_domain": "conformite/tertiaire-operat",
    }


# Codes d'issues (deterministes, traces) — V2 enrichi
CONTROL_RULES = [
    {
        "code": "TERTIAIRE_NO_BUILDING",
        "severity": "critical",
        "title_fr": "Aucun bâtiment",
        "check": lambda efa, buildings, resps, events: len(buildings) == 0,
        "message_fr": "Aucun bâtiment associé à l'EFA",
        "impact_fr": "Impossible de calculer la surface assujettie",
        "action_fr": "Associer au moins un bâtiment avec sa surface et son usage",
        "proof_required": None,
        "proof_owner": None,
    },
    {
        "code": "TERTIAIRE_MISSING_SURFACE",
        "severity": "high",
        "title_fr": "Surface manquante",
        "check": lambda efa, buildings, resps, events: any(
            not b.surface_m2 or b.surface_m2 <= 0 for b in buildings
        ) if buildings else False,
        "message_fr": "Surface manquante ou nulle sur un ou plusieurs bâtiments",
        "impact_fr": "La surface totale EFA ne peut pas être calculée correctement",
        "action_fr": "Renseigner la surface (m²) de chaque bâtiment associé",
        "proof_required": _proof("preuve_surface_usage", "Preuve de surface (plan, DPE, géomètre)", "mandataire", "À fournir pour compléter le patrimoine"),
        "proof_owner": "mandataire",
    },
    {
        "code": "TERTIAIRE_MISSING_USAGE",
        "severity": "medium",
        "title_fr": "Usage non renseigné",
        "check": lambda efa, buildings, resps, events: any(
            not b.usage_label for b in buildings
        ) if buildings else False,
        "message_fr": "Catégorie d'usage non renseignée sur un ou plusieurs bâtiments",
        "impact_fr": "La catégorie d'activité OPERAT ne peut pas être déterminée",
        "action_fr": "Renseigner la catégorie d'usage (bureaux, commerce, enseignement, etc.)",
        "proof_required": None,
        "proof_owner": None,
    },
    {
        "code": "TERTIAIRE_NO_RESPONSIBILITY",
        "severity": "high",
        "title_fr": "Responsable absent",
        "check": lambda efa, buildings, resps, events: len(resps) == 0,
        "message_fr": "Aucun responsable défini pour l'EFA",
        "impact_fr": "Le rôle de l'assujetti n'est pas clair (propriétaire, locataire, mandataire)",
        "action_fr": "Définir au moins un responsable avec son rôle",
        "proof_required": _proof("bail_titre_propriete", "Bail ou titre de propriété", "proprietaire", "À conserver en cas d'audit"),
        "proof_owner": "proprietaire",
    },
    {
        "code": "TERTIAIRE_NO_REPORTING_PERIOD",
        "severity": "medium",
        "title_fr": "Période reporting absente",
        "check": lambda efa, buildings, resps, events: efa.reporting_start is None,
        "message_fr": "Période de reporting non définie",
        "impact_fr": "Impossible de calculer les trajectoires de réduction",
        "action_fr": "Définir la date de début du reporting (année de référence)",
        "proof_required": None,
        "proof_owner": None,
    },
    {
        "code": "TERTIAIRE_SURFACE_COHERENCE",
        "severity": "medium",
        "title_fr": "Surface < seuil",
        "check": lambda efa, buildings, resps, events: (
            sum(b.surface_m2 or 0 for b in buildings) < 1000
        ) if buildings and all(b.surface_m2 for b in buildings) else False,
        "message_fr": "Surface totale EFA inférieure au seuil d'assujettissement (1 000 m²)",
        "impact_fr": "L'EFA pourrait ne pas être assujettie au Décret tertiaire",
        "action_fr": "Vérifier les surfaces. Si < 1 000 m², l'EFA n'est peut-être pas assujettie",
        "proof_required": _proof("justificatif_exemption", "Justificatif d'exemption ou d'exclusion", "proprietaire", "À conserver en cas d'audit"),
        "proof_owner": "proprietaire",
    },
    # V45: nouvelles règles
    {
        "code": "TERTIAIRE_RESP_NO_EMAIL",
        "severity": "low",
        "title_fr": "Email responsable manquant",
        "check": lambda efa, buildings, resps, events: (
            len(resps) > 0 and any(not r.contact_email for r in resps)
        ),
        "message_fr": "Email de contact non renseigné pour un ou plusieurs responsables",
        "impact_fr": "Impossible de contacter le responsable en cas d'audit ou de relance",
        "action_fr": "Renseigner l'email de contact de chaque responsable",
        "proof_required": None,
        "proof_owner": None,
    },
    {
        "code": "TERTIAIRE_PERIMETER_EVENT_PROOF",
        "severity": "high",
        "title_fr": "Preuve modulation requise",
        "check": lambda efa, buildings, resps, events: len(events) > 0,
        "message_fr": "Événement de périmètre déclaré — preuve de modulation requise",
        "impact_fr": "Sans justificatif, la modulation ne sera pas acceptée par OPERAT",
        "action_fr": "Déposer le dossier de modulation (vacance, travaux, changement d'usage)",
        "proof_required": _proof("dossier_modulation", "Dossier de modulation (vacance, travaux, changement d'usage)", "proprietaire", "À joindre au dépôt si modulation demandée"),
        "proof_owner": "proprietaire",
    },
]


def _build_proof_links(efa_id, rule, year=None):
    """V45: Construit les deep-links Mémobox pour une issue avec proof_required."""
    proof = rule.get("proof_required")
    if not proof:
        return []
    efa_hint = f"efa_id={efa_id}"
    params = (
        f"/kb?context=proof"
        f"&domain={proof['doc_domain'].replace('/', '%2F')}"
        f"&status=draft"
        f"&hint={proof['label_fr'][:80].replace(' ', '+')}"
        f"&proof_type={proof['type']}"
        f"&efa_id={efa_id}"
    )
    if year:
        params += f"&year={year}"
    return [params]


def run_controls(db: Session, efa_id: int, year: int = None) -> list[dict]:
    """Execute les controles de completude/coherence sur une EFA.
    V45: enrichi avec proof_required structuré + proof_links deep-link Mémobox.
    Retourne la liste des issues detectees.
    """
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        return []

    buildings = db.query(TertiaireEfaBuilding).filter(
        TertiaireEfaBuilding.efa_id == efa_id
    ).all()
    resps = db.query(TertiaireResponsibility).filter(
        TertiaireResponsibility.efa_id == efa_id
    ).all()
    events = db.query(TertiairePerimeterEvent).filter(
        TertiairePerimeterEvent.efa_id == efa_id
    ).all()

    issues = []
    for rule in CONTROL_RULES:
        try:
            triggered = rule["check"](efa, buildings, resps, events)
        except Exception:
            triggered = False

        if triggered:
            proof_req = rule.get("proof_required")
            proof_links = _build_proof_links(efa_id, rule, year)

            issue_data = {
                "efa_id": efa_id,
                "year": year,
                "code": rule["code"],
                "severity": rule["severity"],
                "title_fr": rule.get("title_fr", rule["code"]),
                "message_fr": rule["message_fr"],
                "impact_fr": rule["impact_fr"],
                "action_fr": rule["action_fr"],
                # V45: structured proof_required
                "proof_required": proof_req,
                "proof_links": proof_links,
                # Legacy V1 fields (backward compat)
                "proof_required_json": json.dumps(proof_req) if proof_req else None,
                "proof_owner_role": rule.get("proof_owner"),
            }
            issues.append(issue_data)

    # Persist issues (upsert by code + efa_id)
    for issue_data in issues:
        existing = db.query(TertiaireDataQualityIssue).filter(
            TertiaireDataQualityIssue.efa_id == efa_id,
            TertiaireDataQualityIssue.code == issue_data["code"],
            TertiaireDataQualityIssue.status == DataQualityIssueStatus.OPEN,
        ).first()
        if not existing:
            db.add(TertiaireDataQualityIssue(
                efa_id=issue_data["efa_id"],
                year=issue_data["year"],
                code=issue_data["code"],
                severity=DataQualityIssueSeverity(issue_data["severity"]),
                message_fr=issue_data["message_fr"],
                impact_fr=issue_data["impact_fr"],
                action_fr=issue_data["action_fr"],
                status=DataQualityIssueStatus.OPEN,
                proof_required_json=issue_data["proof_required_json"],
                proof_owner_role=issue_data["proof_owner_role"],
            ))
    db.commit()

    return issues


# ── Precheck declaration ──────────────────────────────────────────────────────

def precheck_declaration(db: Session, efa_id: int, year: int) -> dict:
    """Pre-verification avant generation du pack export.
    Retourne la checklist + statut (pret / incomplet / a_risque).
    """
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        return {"status": "not_found", "checklist": []}

    # Run controls first
    issues = run_controls(db, efa_id, year)

    buildings = db.query(TertiaireEfaBuilding).filter(
        TertiaireEfaBuilding.efa_id == efa_id
    ).all()
    resps = db.query(TertiaireResponsibility).filter(
        TertiaireResponsibility.efa_id == efa_id
    ).all()
    proofs = db.query(TertiaireProofArtifact).filter(
        TertiaireProofArtifact.efa_id == efa_id
    ).all()

    total_surface = sum(b.surface_m2 or 0 for b in buildings)

    checklist = [
        {
            "label": "Bâtiment(s) associé(s)",
            "ok": len(buildings) > 0,
            "detail": f"{len(buildings)} bâtiment(s)" if buildings else "Aucun",
        },
        {
            "label": "Surface totale renseignée",
            "ok": total_surface > 0,
            "detail": f"{int(total_surface)} m²" if total_surface > 0 else "Non renseignée",
        },
        {
            "label": "Catégorie(s) d'usage",
            "ok": all(b.usage_label for b in buildings) if buildings else False,
            "detail": ", ".join(set(b.usage_label for b in buildings if b.usage_label)) or "Non renseigné",
        },
        {
            "label": "Responsable(s) défini(s)",
            "ok": len(resps) > 0,
            "detail": f"{len(resps)} responsable(s)" if resps else "Aucun",
        },
        {
            "label": "Période de reporting",
            "ok": efa.reporting_start is not None,
            "detail": str(efa.reporting_start) if efa.reporting_start else "Non définie",
        },
        {
            "label": "Preuve(s) documentaire(s)",
            "ok": len(proofs) > 0,
            "detail": f"{len(proofs)} preuve(s)" if proofs else "Aucune",
        },
    ]

    ok_count = sum(1 for c in checklist if c["ok"])
    total = len(checklist)

    critical_issues = [i for i in issues if i["severity"] == "critical"]
    high_issues = [i for i in issues if i["severity"] == "high"]

    if critical_issues:
        status = "bloque"
    elif ok_count < total or high_issues:
        status = "incomplet"
    else:
        status = "pret"

    # Update or create declaration record
    decl = db.query(TertiaireDeclaration).filter(
        TertiaireDeclaration.efa_id == efa_id,
        TertiaireDeclaration.year == year,
    ).first()
    if not decl:
        decl = TertiaireDeclaration(
            efa_id=efa_id,
            year=year,
            status=DeclarationStatus.DRAFT,
        )
        db.add(decl)

    decl.checklist_json = json.dumps(checklist, ensure_ascii=False)
    if status == "pret":
        decl.status = DeclarationStatus.PRECHECKED
    db.commit()

    return {
        "status": status,
        "efa_id": efa_id,
        "year": year,
        "declaration_status": decl.status.value if decl.status else "draft",
        "checklist": checklist,
        "ok_count": ok_count,
        "total": total,
        "issues_count": len(issues),
        "critical_count": len(critical_issues),
    }


# ── Export pack (SIMULE) ─────────────────────────────────────────────────────

def generate_operat_pack(db: Session, efa_id: int, year: int) -> dict:
    """Genere un pack d'export OPERAT simule (zip + attestation HTML + JSON recap).
    IMPORTANT: Ce pack est une SIMULATION, pas une soumission reelle OPERAT.
    """
    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        return {"status": "not_found"}

    buildings = db.query(TertiaireEfaBuilding).filter(
        TertiaireEfaBuilding.efa_id == efa_id
    ).all()
    resps = db.query(TertiaireResponsibility).filter(
        TertiaireResponsibility.efa_id == efa_id
    ).all()
    events = db.query(TertiairePerimeterEvent).filter(
        TertiairePerimeterEvent.efa_id == efa_id
    ).all()

    total_surface = sum(b.surface_m2 or 0 for b in buildings)
    usages = list(set(b.usage_label for b in buildings if b.usage_label))

    # JSON recap
    recap = {
        "_simulation": True,
        "_avertissement": "Ce dossier est une SIMULATION PROMEOS. Il ne constitue pas une soumission officielle OPERAT.",
        "efa_id": efa_id,
        "efa_nom": efa.nom,
        "year": year,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "surface_totale_m2": total_surface,
        "usages": usages,
        "nb_batiments": len(buildings),
        "nb_responsables": len(resps),
        "nb_evenements_perimetre": len(events),
        "responsables": [
            {"role": r.role.value if r.role else None, "entity": r.entity_value}
            for r in resps
        ],
    }

    # HTML attestation
    html_attestation = f"""<!DOCTYPE html>
<html lang="fr">
<head><meta charset="utf-8"><title>Attestation OPERAT (simulation) — {efa.nom}</title></head>
<body style="font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px;">
<div style="background: #fef3c7; border: 2px solid #f59e0b; padding: 16px; border-radius: 8px; margin-bottom: 24px;">
<strong>⚠ SIMULATION</strong> — Ce document est généré par PROMEOS à titre indicatif.
Il ne constitue pas une soumission officielle sur la plateforme OPERAT.
</div>
<h1>Attestation Décret tertiaire — Année {year}</h1>
<h2>EFA : {efa.nom}</h2>
<table style="border-collapse: collapse; width: 100%;">
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Surface totale</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{int(total_surface)} m²</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Catégories d'usage</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{', '.join(usages) or 'Non renseigné'}</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Nombre de bâtiments</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{len(buildings)}</td></tr>
<tr><td style="padding: 8px; border: 1px solid #ddd;"><strong>Responsables</strong></td><td style="padding: 8px; border: 1px solid #ddd;">{len(resps)}</td></tr>
</table>
<p style="margin-top: 24px; color: #666;">Généré le {datetime.now(timezone.utc).strftime('%d/%m/%Y à %H:%M')} par PROMEOS</p>
</body></html>"""

    # Write files
    export_dir = Path(__file__).resolve().parent.parent / "data" / "tertiaire_exports"
    export_dir.mkdir(parents=True, exist_ok=True)

    pack_name = f"operat_pack_efa{efa_id}_{year}"
    pack_dir = export_dir / pack_name
    pack_dir.mkdir(parents=True, exist_ok=True)

    recap_path = pack_dir / "recap.json"
    recap_path.write_text(json.dumps(recap, ensure_ascii=False, indent=2), encoding="utf-8")

    html_path = pack_dir / "attestation_simulation.html"
    html_path.write_text(html_attestation, encoding="utf-8")

    # Create zip
    zip_path = export_dir / f"{pack_name}.zip"
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.write(recap_path, "recap.json")
        zf.write(html_path, "attestation_simulation.html")

    # Update declaration
    decl = db.query(TertiaireDeclaration).filter(
        TertiaireDeclaration.efa_id == efa_id,
        TertiaireDeclaration.year == year,
    ).first()
    if decl:
        decl.status = DeclarationStatus.EXPORTED
        decl.exported_pack_path = str(zip_path)
        db.commit()

    # ── V40: Register pack as KB document + proof artifact ───────────────────
    kb_doc_id = None
    kb_display_name = None
    kb_open_url = None
    try:
        # SHA256 checksum du zip
        sha256 = hashlib.sha256(zip_path.read_bytes()).hexdigest()
        kb_doc_id = f"generated_operat_{sha256[:12]}"

        from app.kb.store import KBStore
        kb_store = KBStore()

        # Dedup : si même hash, on ne recrée pas
        # V40.1: human-friendly display name (never shows hash to user)
        kb_display_name = f"Pack OPERAT \u2014 {efa.nom} \u2014 {year}"

        existing = kb_store.get_doc(kb_doc_id)
        if not existing or existing.get("content_hash") != sha256:
            kb_store.upsert_doc({
                "doc_id": kb_doc_id,
                "title": f"Pack OPERAT — {efa.nom} — {year}",
                "display_name": kb_display_name,
                "source_type": "pdf",
                "source_path": str(zip_path),
                "content_hash": sha256,
                "nb_sections": 2,
                "nb_chunks": 0,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "meta": {
                    "efa_id": efa_id,
                    "efa_nom": efa.nom,
                    "year": year,
                    "surface_m2": total_surface,
                    "simulation": True,
                    "generated_type": "operat_export",
                },
                "status": "review",
            })
            # Set domain on the KB doc
            try:
                kb_store.db.conn.cursor().execute(
                    "UPDATE kb_docs SET domain = ? WHERE doc_id = ?",
                    ("conformite/tertiaire-operat", kb_doc_id),
                )
                kb_store.db.conn.commit()
            except Exception:
                pass  # domain column may not exist yet

        # Create proof artifact (bridge Tertiaire ↔ KB)
        existing_artifact = db.query(TertiaireProofArtifact).filter(
            TertiaireProofArtifact.efa_id == efa_id,
            TertiaireProofArtifact.type == "operat_export_pack",
            TertiaireProofArtifact.kb_doc_id == kb_doc_id,
        ).first()
        if not existing_artifact:
            artifact = TertiaireProofArtifact(
                efa_id=efa_id,
                type="operat_export_pack",
                file_path=str(zip_path),
                kb_doc_id=kb_doc_id,
                owner_role=efa.role_assujetti,
                tags_json=json.dumps({"year": year, "efa_id": efa_id}),
            )
            db.add(artifact)
            db.commit()

        # Deep-link vers la Mémobox avec contexte preuve
        kb_open_url = (
            f"/kb?context=proof"
            f"&domain=conformite%2Ftertiaire-operat"
            f"&status=review"
            f"&hint=Pack+OPERAT+%E2%80%94+{efa.nom}+%E2%80%94+{year}"
        )

    except Exception as exc:
        logger.warning("V40: KB doc creation failed for pack %s: %s", pack_name, exc)
        # Non-bloquant : l'export fonctionne même si KB échoue

    return {
        "status": "exported",
        "simulation": True,
        "efa_id": efa_id,
        "year": year,
        "zip_path": str(zip_path),
        "recap": recap,
        "kb_doc_id": kb_doc_id,
        "kb_doc_display_name": kb_display_name if kb_doc_id else None,
        "kb_open_url": kb_open_url,
    }


# ── Dashboard KPIs ───────────────────────────────────────────────────────────

def get_tertiaire_dashboard(db: Session, org_id: int = None, site_id: int = None) -> dict:
    """KPIs agrégés pour le dashboard tertiaire."""
    query = db.query(TertiaireEfa).filter(TertiaireEfa.deleted_at.is_(None))
    if site_id:
        query = query.filter(TertiaireEfa.site_id == site_id)
    elif org_id:
        query = query.filter(TertiaireEfa.org_id == org_id)

    efas = query.all()
    total = len(efas)
    active = sum(1 for e in efas if e.statut == EfaStatut.ACTIVE)
    draft = sum(1 for e in efas if e.statut == EfaStatut.DRAFT)
    closed = sum(1 for e in efas if e.statut == EfaStatut.CLOSED)

    # Count open issues
    efa_ids = [e.id for e in efas]
    open_issues = 0
    critical_issues = 0
    if efa_ids:
        issues = db.query(TertiaireDataQualityIssue).filter(
            TertiaireDataQualityIssue.efa_id.in_(efa_ids),
            TertiaireDataQualityIssue.status == DataQualityIssueStatus.OPEN,
        ).all()
        open_issues = len(issues)
        critical_issues = sum(
            1 for i in issues if i.severity == DataQualityIssueSeverity.CRITICAL
        )

    return {
        "total_efa": total,
        "active": active,
        "draft": draft,
        "closed": closed,
        "open_issues": open_issues,
        "critical_issues": critical_issues,
    }


# ── Site Signals V42 + Explainability V43 ──────────────────────────────────

# Labels FR pour les types de site
_TYPE_LABELS_FR = {
    "magasin": "Magasin",
    "usine": "Usine",
    "bureau": "Bureau",
    "entrepot": "Entrepôt",
    "commerce": "Commerce",
    "copropriete": "Copropriété",
    "logement_social": "Logement social",
    "collectivite": "Collectivité",
    "hotel": "Hôtel",
    "sante": "Santé",
    "enseignement": "Enseignement",
}


def _format_surface(val):
    """Format surface with French locale-like thousands separator."""
    if val is None:
        return "non renseignée"
    return f"{int(round(val)):,}".replace(",", "\u202f") + " m²"


def _build_site_explanation(site, bats, surface_tertiaire, data_complete, is_covered, efa_ids):
    """V43: Build explainability payload for a single site signal."""
    has_batiments = len(bats) > 0
    all_surfaces_ok = has_batiments and all(b.surface_m2 and b.surface_m2 > 0 for b in bats)

    site_type_raw = site.type.value if site.type else None
    site_type_label = _TYPE_LABELS_FR.get(site_type_raw, site_type_raw) if site_type_raw else None

    # ── Rules applied ────────────────────────────────────────────────────
    rules = []

    # Rule 1: surface threshold
    rules.append({
        "code": "surface_threshold",
        "label_fr": "Surface totale ≥ 1\u202f000 m²",
        "value": surface_tertiaire,
        "threshold": 1000,
        "ok": bool(surface_tertiaire and surface_tertiaire >= 1000),
    })

    # Rule 2: buildings present
    rules.append({
        "code": "batiments_renseignes",
        "label_fr": "Au moins un bâtiment renseigné",
        "value": len(bats),
        "threshold": 1,
        "ok": has_batiments,
    })

    # Rule 3: all surfaces filled
    rules.append({
        "code": "surfaces_completes",
        "label_fr": "Surfaces renseignées pour tous les bâtiments",
        "value": sum(1 for b in bats if b.surface_m2 and b.surface_m2 > 0),
        "threshold": len(bats) if has_batiments else 1,
        "ok": all_surfaces_ok,
    })

    # ── Reasons FR ───────────────────────────────────────────────────────
    reasons = []

    if surface_tertiaire and surface_tertiaire >= 1000:
        reasons.append(f"Surface totale {_format_surface(surface_tertiaire)} ≥ 1\u202f000 m²")
    elif surface_tertiaire and surface_tertiaire > 0:
        reasons.append(f"Surface totale {_format_surface(surface_tertiaire)} < 1\u202f000 m²")
    else:
        reasons.append("Surface totale non renseignée")

    if site_type_label:
        reasons.append(f"Usage : {site_type_label}")
    else:
        reasons.append("Usage non renseigné — à vérifier")

    if not has_batiments:
        reasons.append("Aucun bâtiment renseigné dans le patrimoine")
    else:
        reasons.append(f"{len(bats)} bâtiment{'s' if len(bats) > 1 else ''} renseigné{'s' if len(bats) > 1 else ''}")

    if not all_surfaces_ok and has_batiments:
        missing_count = sum(1 for b in bats if not b.surface_m2 or b.surface_m2 <= 0)
        reasons.append(f"{missing_count} bâtiment{'s' if missing_count > 1 else ''} sans surface renseignée")

    if is_covered:
        reasons.append(f"EFA existante (n° {', '.join(str(i) for i in efa_ids[:3])})")
    else:
        reasons.append("Aucune EFA créée pour ce site")

    # ── Missing fields ───────────────────────────────────────────────────
    missing = []
    if not surface_tertiaire or surface_tertiaire <= 0:
        missing.append("surface")
    if not site_type_raw:
        missing.append("usage_site")
    if not has_batiments:
        missing.append("batiments")
    elif not all_surfaces_ok:
        missing.append("surface_batiment")
    if not site.naf_code:
        missing.append("code_naf")

    # ── Recommended next step + CTA ──────────────────────────────────────
    signal = (
        "assujetti_probable" if surface_tertiaire and surface_tertiaire >= 1000
        else "a_verifier" if not data_complete
        else "non_concerne"
    )

    if signal == "assujetti_probable" and not is_covered:
        next_step = "creer_efa"
        cta = {
            "label_fr": "Créer l'EFA",
            "to": f"/conformite/tertiaire/wizard?site_id={site.id}",
        }
    elif missing:
        next_step = "completer_patrimoine"
        cta = {
            "label_fr": "Compléter le patrimoine",
            "to": f"/patrimoine?site_id={site.id}",
        }
    else:
        next_step = "aucune_action"
        cta = None

    return {
        "signal_version": "V1",
        "rules_applied": rules,
        "reasons_fr": reasons,
        "missing_fields": missing,
        "recommended_next_step": next_step,
        "recommended_cta": cta,
    }


def compute_site_signals(db: Session, org_id: int = None, site_id: int = None) -> dict:
    """Qualifie chaque site du patrimoine vis-à-vis du Décret tertiaire.

    Heuristique V1 (V42) + Explainability V43:
    - surface_tertiaire_m2 >= 1000 → assujetti_probable
    - surface_tertiaire_m2 < 1000 mais données incomplètes → a_verifier
    - surface_tertiaire_m2 < 1000 et données complètes → non_concerne

    Un site "couvert" = a déjà au moins une EFA active/draft liée via building_id.
    """
    site_query = db.query(Site).filter(
        Site.actif.is_(True),
        Site.deleted_at.is_(None),
    )
    if site_id:
        site_query = site_query.filter(Site.id == site_id)
    sites = site_query.order_by(Site.nom).all()

    # Collect all EFA building associations to determine coverage
    covered_site_ids = set()
    efa_by_site = {}
    efas = db.query(TertiaireEfa).filter(
        TertiaireEfa.deleted_at.is_(None),
    ).all()
    for efa in efas:
        buildings = db.query(TertiaireEfaBuilding).filter(
            TertiaireEfaBuilding.efa_id == efa.id,
        ).all()
        for b in buildings:
            if b.building_id:
                bat = db.query(Batiment).filter(Batiment.id == b.building_id).first()
                if bat:
                    covered_site_ids.add(bat.site_id)
                    efa_by_site.setdefault(bat.site_id, []).append(efa.id)

    signals = []
    # V43: aggregate missing fields across all sites
    all_missing_fields = {}

    for site in sites:
        bats = db.query(Batiment).filter(
            Batiment.site_id == site.id,
            Batiment.deleted_at.is_(None),
        ).all()

        # Surface tertiaire: use site.tertiaire_area_m2 if set, else sum of building surfaces
        surface_tertiaire = site.tertiaire_area_m2
        sum_bat_surface = sum(b.surface_m2 or 0 for b in bats)
        if not surface_tertiaire:
            surface_tertiaire = sum_bat_surface

        # Data completeness
        has_batiments = len(bats) > 0
        all_surfaces_ok = has_batiments and all(b.surface_m2 and b.surface_m2 > 0 for b in bats)
        data_complete = has_batiments and all_surfaces_ok

        # Heuristic
        if surface_tertiaire and surface_tertiaire >= 1000:
            signal = "assujetti_probable"
        elif not data_complete:
            signal = "a_verifier"
        else:
            signal = "non_concerne"

        is_covered = site.id in covered_site_ids
        efa_ids = efa_by_site.get(site.id, [])

        # V43: explainability
        explain = _build_site_explanation(
            site, bats, surface_tertiaire, data_complete, is_covered, efa_ids,
        )

        # Track missing fields for summary
        for field in explain["missing_fields"]:
            all_missing_fields[field] = all_missing_fields.get(field, 0) + 1

        signals.append({
            # V42 fields (unchanged)
            "site_id": site.id,
            "site_nom": site.nom,
            "ville": site.ville,
            "surface_tertiaire_m2": surface_tertiaire,
            "nb_batiments": len(bats),
            "signal": signal,
            "data_complete": data_complete,
            "is_covered": is_covered,
            "efa_ids": efa_ids,
            # V43 fields
            **explain,
        })

    counts = {
        "assujetti_probable": sum(1 for s in signals if s["signal"] == "assujetti_probable"),
        "a_verifier": sum(1 for s in signals if s["signal"] == "a_verifier"),
        "non_concerne": sum(1 for s in signals if s["signal"] == "non_concerne"),
    }
    uncovered_probable = sum(
        1 for s in signals if s["signal"] == "assujetti_probable" and not s["is_covered"]
    )
    incomplete_data = sum(1 for s in signals if not s["data_complete"])

    return {
        "sites": signals,
        "total_sites": len(signals),
        "counts": counts,
        "uncovered_probable": uncovered_probable,
        "incomplete_data": incomplete_data,
        # V43: enriched summary
        "top_missing_fields": all_missing_fields,
    }
