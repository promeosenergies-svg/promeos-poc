"""
PROMEOS RegOps — Règle DPE Tertiaire (décret 2024-1040)

Évalue l'obligation de Diagnostic de Performance Énergétique pour le tertiaire.

Règles générées :
  - DPE_SCOPE       : hors scope si tertiaire_area_m2 < seuil (1000 m²)
  - DPE_REALIZATION : manque d'attestation VALIDE → AT_RISK avec deadline
  - DPE_VALIDITY    : attestation VALIDE mais émise > 10 ans → NON_COMPLIANT

Non inclus dans le score composite A.2 (regs.yaml scoring.weights exclut DPE).
Les findings remontent dans le cockpit et /api/compliance/bundle.
"""

from datetime import date

from ..schemas import Finding


def _years_before(ref: date, years: int) -> date:
    """Retourne ref - N années, avec fallback 28/02 pour les 29/02."""
    try:
        return ref.replace(year=ref.year - years)
    except ValueError:
        return ref.replace(year=ref.year - years, day=28)


_DPE_EVIDENCE_TYPES = {"ATTESTATION_DPE"}


def _parse_deadline(raw) -> date | None:
    if not raw:
        return None
    if isinstance(raw, date):
        return raw
    try:
        return date.fromisoformat(str(raw))
    except (ValueError, TypeError):
        return None


def _find_valid_dpe_evidence(evidences: list):
    """Retourne l'Evidence DPE VALIDE la plus récente, ou None."""
    valid = []
    for e in evidences:
        if not e.type or not e.statut:
            continue
        type_str = str(e.type)
        statut_str = str(e.statut)
        if any(t in type_str for t in _DPE_EVIDENCE_TYPES) and "VALIDE" in statut_str:
            valid.append(e)
    if not valid:
        return None
    # Prend le plus récent selon created_at si dispo
    return max(valid, key=lambda e: getattr(e, "created_at", None) or date.min)


def evaluate(site, batiments: list, evidences: list, config: dict) -> list[Finding]:
    findings: list[Finding] = []

    scope_threshold = config.get("scope_threshold_m2", 1000)
    deadlines = config.get("deadlines", {}) or {}
    validite_annees = int(config.get("validite_annees", 10))
    penalties = config.get("penalties", {}) or {}

    surface = getattr(site, "tertiaire_area_m2", None)

    # ── Scope ────────────────────────────────────────────────────────────────
    if surface is None:
        findings.append(
            Finding(
                regulation="DPE_TERTIAIRE",
                rule_id="DPE_SCOPE_UNKNOWN",
                status="UNKNOWN",
                severity="LOW",
                confidence="LOW",
                legal_deadline=None,
                trigger_condition="tertiaire_area_m2 absent",
                config_params_used={"scope_threshold_m2": scope_threshold},
                inputs_used=[],
                missing_inputs=["tertiaire_area_m2"],
                explanation="Surface tertiaire non renseignée — impossible de déterminer l'applicabilité du DPE tertiaire.",
                category="obligation",
            )
        )
        return findings

    if surface < scope_threshold:
        findings.append(
            Finding(
                regulation="DPE_TERTIAIRE",
                rule_id="DPE_OUT_OF_SCOPE",
                status="OUT_OF_SCOPE",
                severity="LOW",
                confidence="HIGH",
                legal_deadline=None,
                trigger_condition=f"tertiaire_area_m2 ({surface:.0f}) < seuil ({scope_threshold})",
                config_params_used={"scope_threshold_m2": scope_threshold},
                inputs_used=["tertiaire_area_m2"],
                missing_inputs=[],
                explanation=f"Site hors scope DPE tertiaire ({surface:.0f} m² < {scope_threshold} m²).",
                category="obligation",
            )
        )
        return findings

    # ── In-scope : check réalisation + validité ─────────────────────────────
    deadline_realization = _parse_deadline(deadlines.get("batiments_1000m2"))
    deadline_affichage = _parse_deadline(deadlines.get("affichage_public"))
    evidence = _find_valid_dpe_evidence(evidences)

    if evidence is None:
        # Pas de DPE valide
        today = date.today()
        past_deadline = deadline_realization is not None and today > deadline_realization
        status = "NON_COMPLIANT" if past_deadline else "AT_RISK"
        severity = "CRITICAL" if past_deadline else "HIGH"
        penalty = penalties.get("non_realisation_pm")

        findings.append(
            Finding(
                regulation="DPE_TERTIAIRE",
                rule_id="DPE_REALIZATION_MISSING",
                status=status,
                severity=severity,
                confidence="HIGH",
                legal_deadline=deadline_realization,
                trigger_condition=f"Aucune ATTESTATION_DPE VALIDE (surface {surface:.0f} m² ≥ {scope_threshold} m²)",
                config_params_used={
                    "scope_threshold_m2": scope_threshold,
                    "deadline": deadline_realization.isoformat() if deadline_realization else None,
                },
                inputs_used=["tertiaire_area_m2", "evidences"],
                missing_inputs=["attestation_dpe"],
                explanation=(
                    "DPE tertiaire obligatoire (décret 2024-1040) — aucune attestation valide trouvée. "
                    f"Échéance : {deadline_realization.isoformat() if deadline_realization else 'non définie'}."
                ),
                category="obligation",
                estimated_penalty_eur=float(penalty) if penalty else None,
                penalty_source="regs.yaml",
                penalty_basis=f"non_realisation_pm: {penalty} EUR" if penalty else None,
            )
        )
        return findings

    # ── DPE présent : check validité (10 ans) ───────────────────────────────
    emission = getattr(evidence, "created_at", None)
    if hasattr(emission, "date"):
        emission = emission.date()

    if emission is not None:
        age_limit = _years_before(date.today(), validite_annees)
        if emission < age_limit:
            findings.append(
                Finding(
                    regulation="DPE_TERTIAIRE",
                    rule_id="DPE_EXPIRED",
                    status="NON_COMPLIANT",
                    severity="HIGH",
                    confidence="HIGH",
                    legal_deadline=None,
                    trigger_condition=f"DPE émis le {emission.isoformat()} (> {validite_annees} ans)",
                    config_params_used={"validite_annees": validite_annees},
                    inputs_used=["attestation_dpe.created_at"],
                    missing_inputs=[],
                    explanation=f"Le DPE a plus de {validite_annees} ans — renouvellement obligatoire.",
                    category="obligation",
                    estimated_penalty_eur=float(penalties.get("non_realisation_pm", 0)) or None,
                    penalty_source="regs.yaml",
                )
            )
            return findings

    findings.append(
        Finding(
            regulation="DPE_TERTIAIRE",
            rule_id="DPE_COMPLIANT",
            status="COMPLIANT",
            severity="LOW",
            confidence="HIGH",
            legal_deadline=deadline_affichage,
            trigger_condition="ATTESTATION_DPE VALIDE présente et dans les délais",
            config_params_used={"validite_annees": validite_annees},
            inputs_used=["attestation_dpe"],
            missing_inputs=[],
            explanation="DPE tertiaire valide — obligation décret 2024-1040 remplie.",
            category="obligation",
        )
    )
    return findings
