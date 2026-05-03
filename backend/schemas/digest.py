"""Pydantic schemas digest dispatch — Phase 2.D Sprint α-push.

DispatchRequest (body endpoint) + DigestRunSummary (response + service
return). Tous les compteurs sont des int >= 0. correlation_id permet le
tracing cross-services (logs API + email_provider + GHA Actions).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, Field


class DispatchRequest(BaseModel):
    """Body POST /api/v1/digest/dispatch — tous champs optionnels.

    `dry_run=True` rend les templates et compte les destinataires SANS
    appeler email_provider (utile pour tests E2E + smoke production).

    `user_filter` restreint le dispatch à un sous-ensemble d'IDs users
    (utile pour tests staging + replay sélectif).
    """

    dry_run: bool = False
    user_filter: Optional[List[int]] = Field(
        None,
        description="Si fourni, dispatch uniquement à ces user_ids (test/replay)",
    )


class DigestRunSummary(BaseModel):
    """Réponse endpoint + retour service.

    Compteurs structurés pour observability GHA Actions :
    - sent : envois Brevo réussis (success=True)
    - skipped_no_opt_in : users sans digest_daily_enabled=True (filtre amont,
      ces users ne sont pas itérés — compteur reste 0 en pratique mais
      gardé pour traçabilité future si on change la stratégie de filtre)
    - skipped_no_events : users opt-in mais 0 events à pousser
    - failed : envois Brevo échoués (silent fail email_provider)
    - dry_run : mirror du flag d'entrée
    - correlation_id : trace ID pour cross-log
    """

    sent: int = 0
    skipped_no_opt_in: int = 0
    skipped_no_events: int = 0
    failed: int = 0
    dry_run: bool = False
    correlation_id: str
