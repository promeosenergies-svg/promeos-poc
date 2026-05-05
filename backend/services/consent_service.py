"""
PROMEOS — Service consentement RGPD effectif (Sprint C-4 Phase 4.5, ADR-007 + Option B).

Retourne le consentement effectif d'un DeliveryPoint en respectant l'override local
(`consentement_dataconnect_local` / `consentement_grdf_local`). Si `_local` est null,
remonte au global Org. **Pas de propagation physique** (Option B archi-helios) —
override local préservé sans risque RGPD d'écrasement silencieux.

Architecture (ADR-007 Phase 4.5 implémentation) :

- Hiérarchie : `DP._local IF NOT NULL ELSE Org._global`
- Court-circuit ELD locales (cardinal différenciateur PROMEOS Sprint C-3 Phase 3.6) :
  cascade GRDF cible UNIQUEMENT `grd_code='GRDF'`. Les 20 ELD locales (Régaz Bordeaux,
  GreenAlp Grenoble, R-GDS Strasbourg, Vialis Colmar, etc.) ont leur propre process
  consentement local distinct.
- Lecture seule : aucune écriture DB. La cascade physique sur `_local` est interdite
  (cf. source-guard `test_consent_no_direct_propagation_source_guards.py`).

Cas d'usage cardinaux :

- `services/data_ingestion/consent_gate.py` (Sprint C-5+) — gate ingestion Enedis/GRDF
- `coherence_globale.yaml` invariant 3 `CONSENTEMENT_INGESTION_COHERENCE` (Sprint C-4 P4.1)
- Cockpit RGPD UI (Sprint C-5+) — affichage statut effectif PRM/PCE
"""

from __future__ import annotations

from typing import Literal, Optional


ConsentType = Literal["dataconnect", "grdf"]


def get_effective_consent(dp, type_: ConsentType) -> Optional[bool]:
    """Retourne le consentement effectif pour un DP donné.

    Hiérarchie :
    1. `DP.consentement_<type>_local` si non-null → priorité absolue (ADR-007 override)
    2. Sinon, remonte à `Organisation.consentement_<type>_global` via FK chain
       Site → Portefeuille → EntiteJuridique → Organisation
    3. Si aucun défini → None (statut "pas encore choisi", distinct de False explicite)

    Args:
        dp: instance DeliveryPoint
        type_: "dataconnect" (Enedis) ou "grdf" (ADICT GRDF)

    Returns:
        bool | None — consentement effectif (True/False) ou None si non défini.

    Note Phase 4.5 : **lecture seule**. La logique de propagation physique a été
    explicitement rejetée (Option A → A2/B Phase 4.5) car elle écrase silencieusement
    les overrides locaux RGPD-protégés (violation ADR-007).
    """
    if type_ not in ("dataconnect", "grdf"):
        raise ValueError(f"type_ inconnu: {type_!r} (attendu 'dataconnect' ou 'grdf')")

    local_attr = f"consentement_{type_}_local"
    local = getattr(dp, local_attr, None)
    if local is not None:
        return local  # Override local prioritaire (ADR-007)

    # Remonter au global Org via FK chain
    org = _get_org_from_dp(dp)
    if org is None:
        return None
    global_attr = f"consentement_{type_}_global"
    return getattr(org, global_attr, None)


def is_consent_active(dp, type_: ConsentType) -> bool:
    """True si le consentement effectif est explicitement True.

    Distinction cardinale vs `get_effective_consent() == True` :
    - `is_consent_active` retourne False si consentement = None (pas explicitement consenti)
    - Cohérent avec doctrine RGPD CNIL : pas de consentement = pas autorisé
    """
    return get_effective_consent(dp, type_) is True


def _get_org_from_dp(dp):
    """Remonte la chaîne FK DP → Site → Portefeuille → EntiteJuridique → Organisation.

    Returns:
        Organisation | None si chaîne FK incomplète (defensive).
    """
    site = getattr(dp, "site", None)
    if site is None:
        return None
    portefeuille = getattr(site, "portefeuille", None)
    if portefeuille is None:
        return None
    ej = getattr(portefeuille, "entite_juridique", None)
    if ej is None:
        return None
    return getattr(ej, "organisation", None)
