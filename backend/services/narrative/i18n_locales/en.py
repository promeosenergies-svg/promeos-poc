"""Catalogue EN — Phase 9.C narrative-sol2 squelette.

Locale anglaise : traductions partielles du catalogue FR. Les clés non
traduites tombent automatiquement sur le fallback FR via `i18n.t()`.

## État Phase 9.C

Squelette MVP : ~30% des clés traduites (les plus saillantes pour démo
internationale CFO US/UK). V2 livre les ~70% restantes après panel UK.

## Convention traduction EN

- Tone CFO US/UK : direct, factuel (vs FR pédagogique-expert)
- "Patrimoine" → "portfolio" (immobilier institutionnel US)
- "Décret Tertiaire" → "French Tertiary Decree -40%" (préservé brand)
- "DAF" → "CFO" (sigle US standard)
- Format chiffres : virgule milliers + point décimal (anglo-saxon) — à
  câbler dans `formatters.py` V2 si EN locale activée

Ref : audit final ticket BL-5 + sprint narrative-sol2 Phase 9.C V2.
"""

CATALOG: dict[str, str] = {
    # ─── Phrases stables (skeleton EN) ─────────────────────────────────────
    "stable.grand_groupe": (
        "Your portfolio is on track this week — "
        "compliance score maintained, no new drift detected. "
        "Next committee focus: prepare annual OPERAT declarations"
    ),
    "stable.eti_tertiaire": (
        "Your real estate portfolio is on track this week — "
        "compliance score maintained, no new drift detected. "
        "Next committee focus: prepare annual OPERAT declarations"
    ),
    "stable.commerce": (
        "Your business is on track this week — no overcharge detected, "
        "consumption aligned with your profile. "
        "Next month focus: check S+2 invoice vs profile"
    ),
    "stable.erp": (
        "Your facility is on track this week — "
        "public service maintained, no compliance gap. "
        "Next council focus: prepare annual energy audit"
    ),
    "stable.unknown": (
        "Your perimeter is on track this week — no notable signal. "
        "Suggested focus: review upcoming regulatory deadlines"
    ),
    # ─── Source / confidence suffix (EN) ───────────────────────────────────
    "source_suffix": "(source: {source}, confidence: {confidence})",
    "confidence.high": "high",
    "confidence.medium": "medium",
    "confidence.low": "to be confirmed",
    # ─── Persona role labels EN ────────────────────────────────────────────
    "role.dg.default": "CEO",
    "role.cfo.default": "CFO",
    "role.cfo.grand_groupe": "Chief Financial Officer",
    "role.cfo.feminine.grand_groupe": "Chief Financial Officer",  # épicène EN
    "role.director_erp.default": "facility director",
    "role.director_erp.feminine": "facility director",  # épicène EN
    "role.owner_commerce.default": "owner",
    "role.energy_manager.default": "Energy Manager",
    "role.asset_manager.default": "Asset Manager",
    "role.energy_buyer.default": "energy buyer",
    "role.energy_buyer.feminine": "energy buyer",  # épicène EN
    "role.csr_manager.default": "CSR manager",
    # ─── Persona mention pattern EN ────────────────────────────────────────
    "persona.mention": "For {first_name}, {role_label}: {focus_text}",
    # ─── Phase 10.B — Composers événementiels traduits (P1-2 audit Phase 9) ──
    # DT_drift composers (Phase 1 événementielle)
    "composer.dt_drift.grand_groupe": (
        "{sites_count} {sites_word} of your portfolio {verb} drifted off-track "
        "from the French Tertiary Decree -40% target this week {source_suffix}"
    ),
    "composer.dt_drift.eti_tertiaire": (
        "{sites_count} {sites_word} of your real estate portfolio {verb} drifted "
        "off-track from the French Tertiary Decree -40% target this week {source_suffix}"
    ),
    "composer.dt_drift.commerce": (
        "Your {activity} consumes {magnitude} vs the regional {activity} average this week {source_suffix}"
    ),
    "composer.dt_drift.erp": (
        "Your facility has drifted off-track from the French Tertiary Decree -40% target this week {source_suffix}"
    ),
    "composer.dt_drift.unknown": ("Your perimeter is drifting from the 2030 trajectory this week {source_suffix}"),
    # MAJOR_ANOMALY composers
    "composer.major_anomaly.grand_groupe": (
        "Major anomaly detected on your portfolio this week: {title} {source_suffix}"
    ),
    "composer.major_anomaly.eti_tertiaire": (
        "Major anomaly detected on your real estate portfolio this week: {title} {source_suffix}"
    ),
    "composer.major_anomaly.commerce": "Anomaly detected this week, please review: {title} {source_suffix}",
    "composer.major_anomaly.erp": ("Major anomaly detected on your facility this week: {title} {source_suffix}"),
    # AUDIT_DEADLINE composers
    "composer.audit_deadline.grand_groupe": ("Imminent regulatory deadline on your portfolio: {title} {source_suffix}"),
    "composer.audit_deadline.eti_tertiaire": (
        "Imminent regulatory deadline on your real estate portfolio: {title} {source_suffix}"
    ),
    "composer.audit_deadline.commerce": "Imminent deadline, prompt action required: {title} {source_suffix}",
    "composer.audit_deadline.erp": ("Imminent regulatory deadline on your facility: {title} {source_suffix}"),
    # PURCHASE_WINDOW composers
    "composer.purchase_window.grand_groupe": "Purchase window open on your portfolio: {title} {source_suffix}",
    "composer.purchase_window.eti_tertiaire": (
        "Purchase window open on your real estate portfolio: {title} {source_suffix}"
    ),
    "composer.purchase_window.commerce": "Good window to renegotiate your contract: {title} {source_suffix}",
    "composer.purchase_window.erp": "Purchase window open on your facility: {title} {source_suffix}",
}


__all__ = ["CATALOG"]
