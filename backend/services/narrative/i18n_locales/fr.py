"""Catalogue FR — Phase 9.C narrative-sol2.

Locale par défaut. Toutes les clés canoniques narrative en français,
extraites des constantes existantes des modules :

- sentence_composer.SENTENCE_STABLE_TEMPLATES
- sentence_composer composers (DT_drift / MAJOR_ANOMALY / AUDIT_DEADLINE / PURCHASE_WINDOW)
- persona_context.PERSONA_ROLE_LABEL + PERSONA_ROLE_LABEL_FEMININE

Convention placeholder : `{name}` interpolé via `i18n.t()`.
"""

CATALOG: dict[str, str] = {
    # ─── Phrases stables (silence Option 3.C avec action implicite Phase 8.C) ──
    # Phase 11.A — sourçage §7 systématique (audit personas P0-1)
    "stable.grand_groupe": (
        "Votre patrimoine tient sa trajectoire cette semaine — "
        "score conformité maintenu, aucune nouvelle dérive détectée. "
        "Focus prochain comité : préparer les déclarations OPERAT annuelles "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    "stable.eti_tertiaire": (
        "Votre parc tient sa trajectoire cette semaine — "
        "score conformité maintenu, aucune nouvelle dérive détectée. "
        "Focus prochain comité : préparer les déclarations OPERAT annuelles "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    "stable.industrie": (
        "Votre groupe industriel tient sa trajectoire cette semaine — "
        "émissions scope 1-2-3 alignées sur la trajectoire CSRD. "
        "Focus prochain comité : préparer le reporting CBAM trimestriel "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    "stable.commerce": (
        "Votre activité tient le cap cette semaine — pas de surcoût détecté, "
        "consommation alignée sur votre profil. "
        "Focus prochain mois : vérifier la facture S+2 vs profil "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    "stable.erp": (
        "Votre établissement tient sa trajectoire cette semaine — "
        "service public maintenu, pas d'écart sur la conformité. "
        "Focus prochain conseil : préparer l'audit énergétique annuel "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    "stable.unknown": (
        "Votre périmètre tient le cap cette semaine — pas de signal saillant. "
        "Focus suggéré : vérifier les prochaines échéances réglementaires "
        "(source synthèse hebdo PROMEOS, confiance haute)"
    ),
    # ─── DT_drift composers (Phase 1 événementielle) ───────────────────────
    "composer.dt_drift.grand_groupe": (
        "{sites_count} {sites_word} de votre patrimoine {verb} basculé en dérive "
        "du jalon Décret Tertiaire -40 % cette semaine {source_suffix}"
    ),
    "composer.dt_drift.eti_tertiaire": (
        "{sites_count} {sites_word} de votre parc {verb} basculé en dérive "
        "du jalon Décret Tertiaire -40 % cette semaine {source_suffix}"
    ),
    "composer.dt_drift.commerce": (
        "Votre {activity} consomme {magnitude} vs la moyenne des {activity}s "
        "de votre région cette semaine {source_suffix}"
    ),
    "composer.dt_drift.erp": (
        "Votre établissement a basculé en dérive du jalon Décret Tertiaire -40 % cette semaine {source_suffix}"
    ),
    "composer.dt_drift.unknown": ("Votre périmètre s'éloigne de la trajectoire 2030 cette semaine {source_suffix}"),
    # ─── MAJOR_ANOMALY composers ───────────────────────────────────────────
    "composer.major_anomaly.grand_groupe": (
        "Anomalie majeure détectée sur votre patrimoine cette semaine : {title} {source_suffix}"
    ),
    "composer.major_anomaly.eti_tertiaire": (
        "Anomalie majeure détectée sur votre parc cette semaine : {title} {source_suffix}"
    ),
    "composer.major_anomaly.commerce": ("Anomalie détectée cette semaine, à vérifier : {title} {source_suffix}"),
    "composer.major_anomaly.erp": (
        "Anomalie majeure détectée sur votre établissement cette semaine : {title} {source_suffix}"
    ),
    # ─── AUDIT_DEADLINE composers ──────────────────────────────────────────
    "composer.audit_deadline.grand_groupe": (
        "Échéance réglementaire imminente sur votre patrimoine : {title} {source_suffix}"
    ),
    "composer.audit_deadline.eti_tertiaire": (
        "Échéance réglementaire imminente sur votre parc : {title} {source_suffix}"
    ),
    "composer.audit_deadline.commerce": ("Échéance imminente, à traiter rapidement : {title} {source_suffix}"),
    "composer.audit_deadline.erp": (
        "Échéance réglementaire imminente sur votre établissement : {title} {source_suffix}"
    ),
    # ─── PURCHASE_WINDOW composers ─────────────────────────────────────────
    "composer.purchase_window.grand_groupe": "Fenêtre achat ouverte sur votre patrimoine : {title} {source_suffix}",
    "composer.purchase_window.eti_tertiaire": "Fenêtre achat ouverte sur votre parc : {title} {source_suffix}",
    "composer.purchase_window.commerce": "Bonne fenêtre pour renégocier votre contrat : {title} {source_suffix}",
    "composer.purchase_window.erp": "Fenêtre achat ouverte sur votre établissement : {title} {source_suffix}",
    # ─── Source / confiance suffix ─────────────────────────────────────────
    "source_suffix": "(source {source}, confiance {confidence})",
    "confidence.high": "haute",
    "confidence.medium": "moyenne",
    "confidence.low": "à confirmer",
    # ─── Persona role labels ───────────────────────────────────────────────
    "role.dg.default": "DG",
    "role.cfo.default": "DAF",
    "role.cfo.grand_groupe": "Directeur Financier",
    "role.cfo.feminine.grand_groupe": "Directrice Financière",
    "role.director_erp.default": "directeur d'établissement",
    "role.director_erp.feminine": "directrice d'établissement",
    "role.owner_commerce.default": "propriétaire",
    "role.energy_manager.default": "Energy Manager",
    "role.asset_manager.default": "Asset Manager",
    "role.energy_buyer.default": "acheteur énergie",
    "role.energy_buyer.feminine": "acheteuse énergie",
    "role.csr_manager.default": "responsable RSE",
    # ─── Persona mention pattern ───────────────────────────────────────────
    "persona.mention": "Pour {first_name}, {role_label} : {focus_text}",
}


__all__ = ["CATALOG"]
