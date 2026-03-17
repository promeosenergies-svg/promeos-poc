"""
PROMEOS - Patrimoine package.
Assembles all sub-module routers into a single router
with prefix "/api/patrimoine".

Re-exports helpers/schemas for backward compatibility with code that does:
    from routes.patrimoine import _get_org_id, _serialize_contract, ...
"""

from fastapi import APIRouter

from routes.patrimoine.staging import router as staging_router
from routes.patrimoine.sites import router as sites_router
from routes.patrimoine.compteurs import router as compteurs_router
from routes.patrimoine.contracts import router as contracts_router
from routes.patrimoine.billing import router as billing_router

router = APIRouter(prefix="/api/patrimoine", tags=["Patrimoine"])

router.include_router(staging_router)
router.include_router(sites_router)
router.include_router(compteurs_router)
router.include_router(contracts_router)
router.include_router(billing_router)

# ── Backward-compatible re-exports ──────────────────────────────────────────
# External code (tests, services, other routes) imports these directly from
# "routes.patrimoine".  Re-exporting from _helpers keeps them working.

from routes.patrimoine._helpers import (  # noqa: F401, E402
    # Helpers / utils
    _get_org_id,
    _check_batch_org,
    _check_site_belongs_to_org,
    _check_portfolio_belongs_to_org,
    _load_site_with_org_check,
    _load_compteur_with_org_check,
    _load_contract_with_org_check,
    _normalize_compteur_type,
    _parse_excel_to_staging,
    _worst_compliance_status,
    _serialize_site,
    _build_sites_query,
    _serialize_compteur,
    _serialize_contract,
    _serialize_payment_rule,
    _resolve_payment_rule,
    _compute_site_completeness,
    # Pydantic schemas
    FixRequest,
    BulkFixRequest,
    ActivateRequest,
    InvoiceImportRequest,
    UpdateFieldRequest,
    SiteUpdateRequest,
    SiteMergeRequest,
    CompteurMoveRequest,
    CompteurUpdateRequest,
    ContractCreateRequest,
    ContractUpdateRequest,
    PaymentRuleCreateRequest,
    PaymentRuleBulkApplyRequest,
    ReconciliationFixRequest,
    MappingPreviewRequest,
    SubMeterCreateRequest,
    # Response models
    RegulatoryImpact,
    BusinessImpact,
    AnomalyResponse,
    SiteAnomaliesResponse,
    OrgAnomaliesSiteItem,
    OrgAnomaliesResponse,
    PortfolioSitesAtRisk,
    PortfolioSitesHealth,
    PortfolioTrend,
    PortfolioFrameworkItem,
    PortfolioTopSiteItem,
    PortfolioSummaryResponse,
)

# Re-export route functions that tests import by name
from routes.patrimoine.billing import (  # noqa: F401, E402
    apply_reconciliation_fix,
    get_reconciliation_fix_history,
    get_reconciliation_evidence,
    get_reconciliation_evidence_csv,
    get_portfolio_evidence_csv,
    get_site_reconciliation,
    get_portfolio_reconciliation,
    get_reconciliation_evidence_summary,
)

from routes.patrimoine.staging import (  # noqa: F401, E402
    staging_import,
)

# Re-export match_staging_to_existing (tests import it from routes.patrimoine)
from services.patrimoine_service import match_staging_to_existing  # noqa: F401, E402
