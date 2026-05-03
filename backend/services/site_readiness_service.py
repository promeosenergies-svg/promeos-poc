"""Site readiness service — `is_site_production_ready` (matrice v1 §9.2).

Sprint C-2 Phase 1.4 — comble Section 9 audit Phase B.

Algorithme `is_site_production_ready` : 7 checks pour évaluer si un site a
suffisamment de données pour être considéré 'production-ready' (compliance +
calculs réglementaires fonctionnels).

Source : matrice v1 §9.2 + doctrine PROMEOS Sol §9.

7 checks :
    1. Hiérarchie complète Org → EJ → Portefeuille → Site
    2. Champs P0 site complets (8 champs)
    3. Au moins 1 bâtiment avec surface non nulle + sous-catégorie OPERAT déclarée
    4. Au moins 1 compteur déclaré
    5. Au moins 1 contrat actif lié à un DeliveryPoint du site
    6. Compliance score calculable (V2 wrapper Phase 5 — NON_APPLICABLE accepté)
    7. Cabs 2030 calculable SI DT assujetti (sinon non requis = passe par défaut)

Adaptations MVP vs matrice v1 §9.2 :
- Check 3 : `Batiment.surface_m2` (proxy SDP) car `surface_de_plancher_sdp_m2`
  pas dans le modèle actuel + fallback sur `Site.operat_sous_categorie_id`
  car `Batiment.categorie_operat_batiment` n'existe pas.
- Check 5 : query `ContractDeliveryPoint` (table N:N) car `DeliveryPoint.contracts`
  n'est pas une relation directe.
"""

from __future__ import annotations

import logging
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Optional

from sqlalchemy.orm import Session


_logger = logging.getLogger(__name__)


# Champs P0 absolus Site (matrice v1 §9.1)
# Note : adaptations vs matrice — utilisation des noms réels du modèle Site Phase 3.
P0_SITE_FIELDS = [
    "nom",  # vs matrice "nom_site"
    "adresse",
    "code_postal",
    "ville",  # vs matrice "commune"
    "tertiaire_area_m2",  # vs matrice "surface_tertiaire_totale_m2"
    "altitude_m",
    "operat_sous_categorie_id",
    # "mode_propriete" : pas dans le modèle Site actuel — reportable
]


@dataclass
class SiteReadinessCheck:
    """Résultat d'un check production-ready individuel."""

    name: str
    passed: bool
    message: Optional[str] = None
    details: Optional[dict] = None


@dataclass
class SiteReadinessResult:
    """Résultat global production-ready : 7 checks + agrégats."""

    site_id: int
    production_ready: bool
    completion_pct: float
    checks: list[SiteReadinessCheck] = field(default_factory=list)
    champs_p0_manquants: list[str] = field(default_factory=list)
    next_action_recommended: Optional[str] = None
    computed_at: str = ""

    def to_dict(self) -> dict:
        return {
            "site_id": self.site_id,
            "production_ready": self.production_ready,
            "completion_pct": self.completion_pct,
            "checks": [asdict(c) for c in self.checks],
            "champs_p0_manquants": self.champs_p0_manquants,
            "next_action_recommended": self.next_action_recommended,
            "computed_at": self.computed_at,
        }


def _check_hierarchy(site) -> SiteReadinessCheck:
    """Check 1 — Hiérarchie complète Org → EJ → Portefeuille → Site."""
    has_pf = site.portefeuille is not None
    has_ej = has_pf and site.portefeuille.entite_juridique is not None
    has_org = has_ej and site.portefeuille.entite_juridique.organisation_id is not None
    passed = has_pf and has_ej and has_org
    return SiteReadinessCheck(
        name="hierarchie_complete",
        passed=passed,
        message=None if passed else "Hiérarchie Org → EJ → Portefeuille → Site incomplète",
        details={
            "has_portefeuille": has_pf,
            "has_entite_juridique": has_ej,
            "has_organisation": has_org,
        },
    )


def _check_p0_site_fields(site) -> tuple[SiteReadinessCheck, list[str]]:
    """Check 2 — Champs P0 site complets."""
    missing = []
    for f in P0_SITE_FIELDS:
        val = getattr(site, f, None)
        if val in (None, "", 0):
            missing.append(f)
    passed = len(missing) == 0
    return (
        SiteReadinessCheck(
            name="champs_p0_site_complets",
            passed=passed,
            message=None if passed else f"Champs P0 manquants : {', '.join(missing)}",
            details={"missing": missing, "total_p0": len(P0_SITE_FIELDS)},
        ),
        missing,
    )


def _check_batiments_p0(site) -> SiteReadinessCheck:
    """Check 3 — Au moins 1 bâtiment avec surface > 0 + sous-cat OPERAT déclarée."""
    batiments = list(site.batiments) if site.batiments else []
    nb_batiments = len(batiments)
    sous_cat_declared = bool(site.operat_sous_categorie_id)

    has_valid_batiment = any((b.surface_m2 or 0) > 0 for b in batiments)
    passed = nb_batiments > 0 and has_valid_batiment and sous_cat_declared

    if not nb_batiments:
        msg = "Aucun bâtiment déclaré sur le site"
    elif not has_valid_batiment:
        msg = "Aucun bâtiment avec surface non-nulle"
    elif not sous_cat_declared:
        msg = "Site.operat_sous_categorie_id manquant"
    else:
        msg = None

    return SiteReadinessCheck(
        name="batiments_p0_complets",
        passed=passed,
        message=msg,
        details={
            "nb_batiments": nb_batiments,
            "has_valid_surface": has_valid_batiment,
            "sous_cat_operat_declared": sous_cat_declared,
        },
    )


def _check_at_least_one_compteur(site) -> SiteReadinessCheck:
    """Check 4 — Au moins 1 compteur déclaré."""
    # Site.compteurs est lazy='dynamic' → utiliser .count() ou itérer
    compteurs = list(site.compteurs)
    nb = len(compteurs)
    passed = nb > 0
    return SiteReadinessCheck(
        name="au_moins_un_compteur",
        passed=passed,
        message=None if passed else "Aucun compteur déclaré sur le site",
        details={"nb_compteurs": nb},
    )


def _check_at_least_one_contrat(db: Session, site) -> SiteReadinessCheck:
    """Check 5 — Au moins 1 contrat actif lié à un DeliveryPoint du site.

    Adaptation MVP : query `ContractDeliveryPoint` (table N:N) car
    `DeliveryPoint.contracts` n'est pas une relation directe.
    """
    try:
        from models.patrimoine import ContractDeliveryPoint, DeliveryPoint

        nb = (
            db.query(ContractDeliveryPoint)
            .join(
                DeliveryPoint,
                DeliveryPoint.id == ContractDeliveryPoint.delivery_point_id,
            )
            .filter(DeliveryPoint.site_id == site.id)
            .count()
        )
        passed = nb > 0
        return SiteReadinessCheck(
            name="au_moins_un_contrat",
            passed=passed,
            message=None if passed else "Aucun contrat actif lié à un DeliveryPoint du site",
            details={"nb_contracts_lies": nb},
        )
    except Exception as e:
        _logger.warning("check au_moins_un_contrat failed: %s", e)
        return SiteReadinessCheck(
            name="au_moins_un_contrat",
            passed=False,
            message=f"Erreur lors du check contrat : {e}",
        )


def _check_compliance_calculable(db: Session, site) -> SiteReadinessCheck:
    """Check 6 — Compliance score calculable (V2 wrapper Phase 5).

    Accepte score=None / confidence='non_applicable' (cas légitime).
    """
    try:
        from services.compliance_score_service import compute_site_compliance_score

        result = compute_site_compliance_score(db, site.id)
        return SiteReadinessCheck(
            name="compliance_score_calculable",
            passed=True,
            details={
                "score": result.score,
                "confidence": result.confidence,
                "frameworks_evaluated": result.frameworks_evaluated,
            },
        )
    except Exception as e:
        return SiteReadinessCheck(
            name="compliance_score_calculable",
            passed=False,
            message=f"Compliance score non calculable : {e}",
            details={"error_type": type(e).__name__},
        )


def _check_cabs_si_dt(db: Session, site) -> SiteReadinessCheck:
    """Check 7 — Cabs 2030 calculable SI DT assujetti.

    Si site non DT-assujetti → check passe par défaut (non requis).
    """
    from services.compliance_score_service import _is_dt_assujetti

    if not _is_dt_assujetti(site):
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=True,
            message="Site non DT-assujetti, Cabs non requis",
            details={"dt_assujetti": False},
        )

    # Site DT-assujetti : Cabs doit être calculable
    if not site.code_postal or site.altitude_m is None:
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=False,
            message="Cabs 2030 non calculable (code_postal ou altitude_m manquants pour site DT-assujetti)",
            details={
                "dt_assujetti": True,
                "missing": [f for f in ("code_postal", "altitude_m") if getattr(site, f, None) in (None, "")],
            },
        )

    if not site.operat_sous_categorie_id:
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=False,
            message="Cabs 2030 non calculable : operat_sous_categorie_id manquant pour site DT-assujetti",
            details={"dt_assujetti": True},
        )

    surface = site.tertiaire_area_m2 or site.surface_m2 or 0
    if surface <= 0:
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=False,
            message="Cabs 2030 non calculable : surface tertiaire ou surface_m2 nulle",
            details={"dt_assujetti": True},
        )

    try:
        from regops.services.operat_cabs_service import (
            OperatNonAssujettiError,
            OperatSousCategorieIntrouvableError,
            OperatValeursAbsoluesService,
        )

        OperatValeursAbsoluesService().compute_cabs_2030(
            code_postal=site.code_postal,
            altitude_m=site.altitude_m,
            sous_categories_declared=[{"title": site.operat_sous_categorie_id, "surface_m2": surface}],
        )
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=True,
            details={"dt_assujetti": True},
        )
    except OperatNonAssujettiError as e:
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=False,
            message=f"Cabs 2030 non calculable : {e}",
            details={"dt_assujetti": True, "error_type": "OperatNonAssujettiError"},
        )
    except OperatSousCategorieIntrouvableError as e:
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=False,
            message=f"Cabs 2030 non calculable : sous-cat introuvable",
            details={"dt_assujetti": True, "error_type": "OperatSousCategorieIntrouvableError"},
        )
    except Exception as e:
        return SiteReadinessCheck(
            name="cabs_calculable_si_dt",
            passed=False,
            message=f"Cabs 2030 non calculable : {e}",
            details={"dt_assujetti": True, "error_type": type(e).__name__},
        )


def is_site_production_ready(db: Session, site_id: int) -> SiteReadinessResult:
    """7 checks production-ready Site (matrice v1 §9.2).

    Args:
        db: session SQLAlchemy
        site_id: identifiant du site à évaluer

    Returns:
        SiteReadinessResult avec :
        - production_ready : bool (True si tous les 7 checks passent)
        - completion_pct : pourcentage de checks réussis (0-100)
        - checks : liste détaillée des 7 SiteReadinessCheck
        - champs_p0_manquants : liste des champs P0 manquants (issu check 2)
        - next_action_recommended : message du 1er check rouge (ou None)

    Raises:
        ValueError: si site_id introuvable
    """
    from models import Site

    site = db.query(Site).filter(Site.id == site_id).first()
    if not site:
        raise ValueError(f"Site {site_id} introuvable")

    checks: list[SiteReadinessCheck] = []

    checks.append(_check_hierarchy(site))
    p0_check, p0_missing = _check_p0_site_fields(site)
    checks.append(p0_check)
    checks.append(_check_batiments_p0(site))
    checks.append(_check_at_least_one_compteur(site))
    checks.append(_check_at_least_one_contrat(db, site))
    checks.append(_check_compliance_calculable(db, site))
    checks.append(_check_cabs_si_dt(db, site))

    nb_passed = sum(1 for c in checks if c.passed)
    completion_pct = round(nb_passed / len(checks) * 100, 1)
    production_ready = all(c.passed for c in checks)

    # Recommandation = 1er check rouge
    next_action = None
    for c in checks:
        if not c.passed:
            next_action = c.message
            break

    return SiteReadinessResult(
        site_id=site_id,
        production_ready=production_ready,
        completion_pct=completion_pct,
        checks=checks,
        champs_p0_manquants=p0_missing,
        next_action_recommended=next_action,
        computed_at=datetime.utcnow().isoformat(),
    )
