"""
PROMEOS — Schemas pydantic RGPD consentement (Sprint C-7 Phase 7.3, ADR-019).

Validation stricte CNIL : `cgu_version` requis si consentement_* set
(article 7 RGPD — preuve de consentement informé incluant version CGU acceptée).
"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, model_validator


class OrganisationConsentementPatch(BaseModel):
    """Schema PATCH consentement org-niveau (ADR-019).

    Si `consentement_dataconnect_global` ou `consentement_grdf_global` set (True/False),
    `cgu_version` est OBLIGATOIRE (CNIL preuve d'origine forte).
    """

    consentement_dataconnect_global: Optional[bool] = None
    consentement_grdf_global: Optional[bool] = None
    cgu_version: Optional[str] = Field(
        None,
        max_length=20,
        description="Version CGU acceptée (ex: '1.0', '2.1.0'). Requis si consentement_* set.",
    )

    @model_validator(mode="after")
    def validate_cgu_required_if_consent_set(self) -> "OrganisationConsentementPatch":
        """ADR-019 : si consentement_*_global set, cgu_version obligatoire (CNIL article 7).

        Sprint C-8 Phase 8.1 — D-Sprint-C7-CGU-Referentiel-Central-001 fix :
        validation contre référentiel central `services.cgu_service.is_valid_cgu_version()`
        (cardinal CNIL — version arbitraire rejetée).
        """
        from services.cgu_service import is_valid_cgu_version

        consent_set = self.consentement_dataconnect_global is not None or self.consentement_grdf_global is not None
        if consent_set and not self.cgu_version:
            raise ValueError(
                "cgu_version requis si consentement_*_global modifié (RGPD CNIL article 7 — preuve d'origine forte)"
            )
        if self.cgu_version and not is_valid_cgu_version(self.cgu_version):
            raise ValueError(
                f"cgu_version='{self.cgu_version}' inconnue du référentiel central "
                "(backend/config/cgu_referentiel.yaml). CNIL preuve d'origine forte exige version vérifiable."
            )
        return self

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "OrganisationConsentementPatch":
        """Au moins 1 champ doit être set (sinon PATCH vide non sensé)."""
        if (
            self.consentement_dataconnect_global is None
            and self.consentement_grdf_global is None
            and not self.cgu_version
        ):
            raise ValueError("Au moins un champ consentement_* ou cgu_version requis (PATCH vide rejeté)")
        return self


class DeliveryPointConsentementLocalPatch(BaseModel):
    """Schema PATCH consentement override local DP (ADR-019 + ADR-007 Option B archi-helios).

    Override local préservé (lecture seule via `get_effective_consent`) — Phase 4.5 doctrine.
    """

    consentement_dataconnect_local: Optional[bool] = None
    consentement_grdf_local: Optional[bool] = None
    cgu_version: Optional[str] = Field(
        None,
        max_length=20,
        description="Version CGU acceptée pour override local.",
    )

    @model_validator(mode="after")
    def validate_cgu_required_if_consent_set(self) -> "DeliveryPointConsentementLocalPatch":
        """Sprint C-8 Phase 8.1 — validation référentiel central CGU (cohérent OrganisationConsentementPatch)."""
        from services.cgu_service import is_valid_cgu_version

        consent_set = self.consentement_dataconnect_local is not None or self.consentement_grdf_local is not None
        if consent_set and not self.cgu_version:
            raise ValueError("cgu_version requis si consentement_*_local modifié (CNIL article 7)")
        if self.cgu_version and not is_valid_cgu_version(self.cgu_version):
            raise ValueError(
                f"cgu_version='{self.cgu_version}' inconnue du référentiel central "
                "(backend/config/cgu_referentiel.yaml)."
            )
        return self

    @model_validator(mode="after")
    def validate_at_least_one_field(self) -> "DeliveryPointConsentementLocalPatch":
        if (
            self.consentement_dataconnect_local is None
            and self.consentement_grdf_local is None
            and not self.cgu_version
        ):
            raise ValueError("Au moins un champ consentement_*_local ou cgu_version requis")
        return self
