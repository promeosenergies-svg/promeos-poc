"""
PROMEOS V50 — Génération de templates de preuves OPERAT dans la Mémobox (KB)

Fonction principale :
  generate_proof_templates(efa_id, year, issue_code, proof_types, action_id?)
    → Crée des docs KB "draft" pré-remplis pour chaque proof_type demandé
    → Dedup : si un doc KB existe déjà pour (efa_id, year, proof_type), skip
    → Optionnel : auto-link vers une action via kb.link_doc_to_action (V48)
"""

import hashlib
from datetime import datetime, timezone

from services.tertiaire_proof_catalog import PROOF_TYPES


# ── Template renderer ────────────────────────────────────────────────────────


def render_template_md(proof_type: str, context: dict) -> tuple:
    """Génère (filename, content_md, display_name) pour un type de preuve.

    Args:
        proof_type: clé dans PROOF_TYPES
        context: {efa_id, efa_nom, year, issue_code, org_name?}

    Returns:
        (filename, content_md, display_name)
    """
    pt = PROOF_TYPES.get(proof_type)
    if not pt:
        raise ValueError(f"Type de preuve inconnu : {proof_type}")

    efa_id = context.get("efa_id", "?")
    efa_nom = context.get("efa_nom", "EFA")
    year = context.get("year", datetime.now(timezone.utc).year)
    issue_code = context.get("issue_code", "")
    org_name = context.get("org_name", "Organisation")

    title = pt["title_fr"]
    description = pt["description_fr"]
    examples = pt["examples_fr"]

    display_name = f"{title} — {efa_nom} ({year})"
    filename = f"preuve_{proof_type}_efa{efa_id}_{year}.md"

    examples_md = "\n".join(f"- {ex}" for ex in examples)

    content_md = f"""# {title}

**EFA** : {efa_nom} (ID {efa_id})
**Année** : {year}
**Organisation** : {org_name}
{f"**Issue** : {issue_code}" if issue_code else ""}

---

## Description

{description}

## Pièces attendues

{examples_md}

## Instructions

1. Remplacez ce contenu par la preuve réelle (PDF, scan, attestation).
2. Passez le document en statut « review » puis « validated » une fois vérifié.
3. Ce document sera automatiquement lié à l'EFA et à l'anomalie associée.

---

*Modèle généré automatiquement par PROMEOS V50 — {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")}*
"""

    return filename, content_md, display_name


# ── Template generation engine ───────────────────────────────────────────────


def generate_proof_templates(
    efa_id: int,
    year: int,
    issue_code: str,
    proof_types: list,
    action_id: int = None,
    efa_nom: str = "EFA",
    org_name: str = "Organisation",
) -> dict:
    """Génère des templates de preuves dans la Mémobox (KB store).

    Returns:
        {
          "created": [...],
          "skipped": [...],
          "errors": [...],
          "total_created": int,
          "total_skipped": int,
        }
    """
    from app.kb.store import KBStore

    kb = KBStore()

    context = {
        "efa_id": efa_id,
        "efa_nom": efa_nom,
        "year": year,
        "issue_code": issue_code,
        "org_name": org_name,
    }

    created = []
    skipped = []
    errors = []

    for pt in proof_types:
        if pt not in PROOF_TYPES:
            errors.append(
                {
                    "proof_type": pt,
                    "error": f"Type de preuve inconnu : {pt}",
                }
            )
            continue

        # Deterministic doc_id for dedup
        doc_id = f"operat_template:{efa_id}:{year}:{pt}"

        # Check dedup: if doc already exists in KB, skip
        existing = kb.get_doc(doc_id) if hasattr(kb, "get_doc") else None
        if existing:
            skipped.append(
                {
                    "proof_type": pt,
                    "doc_id": doc_id,
                    "reason": "Modèle déjà existant dans la Mémobox",
                }
            )
            continue

        try:
            filename, content_md, display_name = render_template_md(pt, context)

            content_hash = hashlib.sha256(content_md.encode("utf-8")).hexdigest()[:16]

            doc = {
                "doc_id": doc_id,
                "title": display_name,
                "source_type": "md",
                "source_path": f"templates/{filename}",
                "content_hash": content_hash,
                "updated_at": datetime.now(timezone.utc).isoformat(),
                "status": "draft",
                "display_name": display_name,
                "meta": {
                    "proof_type": pt,
                    "efa_id": efa_id,
                    "year": year,
                    "issue_code": issue_code,
                    "template_kind": PROOF_TYPES[pt]["template_kind"],
                    "version": "v50",
                },
                "nb_sections": 1,
                "nb_chunks": 1,
            }

            kb.upsert_doc(doc)

            # Auto-link to action if provided (V48 proof link)
            link_result = None
            if action_id:
                link_result = kb.link_doc_to_action(
                    action_id=action_id,
                    kb_doc_id=doc_id,
                    proof_type=pt,
                )

            created.append(
                {
                    "proof_type": pt,
                    "doc_id": doc_id,
                    "display_name": display_name,
                    "filename": filename,
                    "status": "draft",
                    "action_link": link_result,
                }
            )

        except Exception as exc:
            errors.append(
                {
                    "proof_type": pt,
                    "error": str(exc),
                }
            )

    return {
        "efa_id": efa_id,
        "year": year,
        "issue_code": issue_code,
        "created": created,
        "skipped": skipped,
        "errors": errors,
        "total_created": len(created),
        "total_skipped": len(skipped),
    }
