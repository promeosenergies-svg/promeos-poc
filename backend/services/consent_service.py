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


def get_effective_consent_with_audit(dp, type_: ConsentType) -> dict:
    """Sprint C-5 Phase 5.3 (ADR-007 ext) — Helper RGPD avec audit trail complet.

    Retourne un dict avec :

    - `active` : bool | None — consentement effectif (cf. `get_effective_consent`)
    - `by_user_id` : int | None — qui a donné le consentement (FK users.id, NULL si user supprimé)
    - `cgu_version` : str | None — version CGU au moment du consentement
    - `at` : datetime | None — timestamp dernier changement
    - `scope` : "local" | "global" | "none" — d'où vient la valeur effective

    Hiérarchie identique à `get_effective_consent` :
    1. DP._local prioritaire si non-null → scope="local"
    2. Org._global fallback → scope="global"
    3. Aucun défini → scope="none" + tous les champs null

    Cas d'usage cardinaux :
    - Audit RGPD officiel ("prouver que tel utilisateur a accepté tel jour la version X")
    - Cockpit RGPD UI Sprint C-5+ — affichage trace complète par PRM/PCE
    - Export RGPD droit d'accès personnel (article 15 RGPD)
    """
    if type_ not in ("dataconnect", "grdf"):
        raise ValueError(f"type_ inconnu: {type_!r} (attendu 'dataconnect' ou 'grdf')")

    local_active_attr = f"consentement_{type_}_local"
    local_by_attr = f"consentement_{type_}_local_by"
    local_cgu_attr = f"consentement_{type_}_local_cgu_version"
    local_at_attr = f"consentement_{type_}_local_at"

    local = getattr(dp, local_active_attr, None)
    if local is not None:
        return {
            "active": local,
            "by_user_id": getattr(dp, local_by_attr, None),
            "cgu_version": getattr(dp, local_cgu_attr, None),
            "at": getattr(dp, local_at_attr, None),
            "scope": "local",
        }

    org = _get_org_from_dp(dp)
    if org is None:
        return {
            "active": None,
            "by_user_id": None,
            "cgu_version": None,
            "at": None,
            "scope": "none",
        }

    global_active_attr = f"consentement_{type_}_global"
    global_by_attr = f"consentement_{type_}_by"
    global_cgu_attr = f"consentement_{type_}_cgu_version"
    global_at_attr = f"consentement_{type_}_at"

    global_val = getattr(org, global_active_attr, None)
    if global_val is None:
        return {
            "active": None,
            "by_user_id": None,
            "cgu_version": None,
            "at": None,
            "scope": "none",
        }

    return {
        "active": global_val,
        "by_user_id": getattr(org, global_by_attr, None),
        "cgu_version": getattr(org, global_cgu_attr, None),
        "at": getattr(org, global_at_attr, None),
        "scope": "global",
    }
