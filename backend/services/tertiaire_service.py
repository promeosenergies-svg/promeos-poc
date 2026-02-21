"""
PROMEOS V40 — Service Tertiaire / OPERAT
qualify_efa, run_controls, precheck_declaration, generate_operat_pack
"""
import hashlib
import json
import logging
import os
import zipfile
from datetime import date, datetime
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


# ── Controles qualite ────────────────────────────────────────────────────────

# Codes d'issues (deterministes, traces)
CONTROL_RULES = [
    {
        "code": "TERTIAIRE_NO_BUILDING",
        "severity": "critical",
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
        "check": lambda efa, buildings, resps, events: any(
            not b.surface_m2 or b.surface_m2 <= 0 for b in buildings
        ) if buildings else False,
        "message_fr": "Surface manquante ou nulle sur un ou plusieurs bâtiments",
        "impact_fr": "La surface totale EFA ne peut pas être calculée correctement",
        "action_fr": "Renseigner la surface (m²) de chaque bâtiment associé",
        "proof_required": None,
        "proof_owner": None,
    },
    {
        "code": "TERTIAIRE_MISSING_USAGE",
        "severity": "medium",
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
        "check": lambda efa, buildings, resps, events: len(resps) == 0,
        "message_fr": "Aucun responsable défini pour l'EFA",
        "impact_fr": "Le rôle de l'assujetti n'est pas clair (propriétaire, locataire, mandataire)",
        "action_fr": "Définir au moins un responsable avec son rôle",
        "proof_required": "Bail ou titre de propriété",
        "proof_owner": "À CLARIFIER",
    },
    {
        "code": "TERTIAIRE_NO_REPORTING_PERIOD",
        "severity": "medium",
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
        "check": lambda efa, buildings, resps, events: (
            sum(b.surface_m2 or 0 for b in buildings) < 1000
        ) if buildings and all(b.surface_m2 for b in buildings) else False,
        "message_fr": "Surface totale EFA inférieure au seuil d'assujettissement (1000 m²)",
        "impact_fr": "L'EFA pourrait ne pas être assujettie au Décret tertiaire",
        "action_fr": "Vérifier les surfaces. Si < 1000 m², l'EFA n'est peut-être pas assujettie",
        "proof_required": "Attestation de surface — À CLARIFIER (source exacte)",
        "proof_owner": "À CLARIFIER",
    },
]


def run_controls(db: Session, efa_id: int, year: int = None) -> list[dict]:
    """Execute les controles de completude/coherence sur une EFA.
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
            issue_data = {
                "efa_id": efa_id,
                "year": year,
                "code": rule["code"],
                "severity": rule["severity"],
                "message_fr": rule["message_fr"],
                "impact_fr": rule["impact_fr"],
                "action_fr": rule["action_fr"],
                "proof_required_json": json.dumps(
                    {"label": rule["proof_required"], "owner": rule["proof_owner"]}
                ) if rule["proof_required"] else None,
                "proof_owner_role": rule["proof_owner"],
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
        "generated_at": datetime.utcnow().isoformat(),
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
<p style="margin-top: 24px; color: #666;">Généré le {datetime.utcnow().strftime('%d/%m/%Y à %H:%M')} par PROMEOS</p>
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
                "updated_at": datetime.utcnow().isoformat(),
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

def get_tertiaire_dashboard(db: Session, org_id: int = None) -> dict:
    """KPIs agrégés pour le dashboard tertiaire."""
    query = db.query(TertiaireEfa).filter(TertiaireEfa.deleted_at.is_(None))
    if org_id:
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


# ── Site Signals V42 ────────────────────────────────────────────────────────

def compute_site_signals(db: Session, org_id: int = None) -> dict:
    """Qualifie chaque site du patrimoine vis-à-vis du Décret tertiaire.

    Heuristique V1:
    - surface_tertiaire_m2 >= 1000 → assujetti_probable
    - surface_tertiaire_m2 < 1000 mais données incomplètes → a_verifier
    - surface_tertiaire_m2 < 1000 et données complètes → non_concerne

    Un site "couvert" = a déjà au moins une EFA active/draft liée via building_id.
    """
    sites = db.query(Site).filter(
        Site.actif.is_(True),
        Site.deleted_at.is_(None),
    ).order_by(Site.nom).all()

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

        signals.append({
            "site_id": site.id,
            "site_nom": site.nom,
            "ville": site.ville,
            "surface_tertiaire_m2": surface_tertiaire,
            "nb_batiments": len(bats),
            "signal": signal,
            "data_complete": data_complete,
            "is_covered": is_covered,
            "efa_ids": efa_ids,
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
    }
