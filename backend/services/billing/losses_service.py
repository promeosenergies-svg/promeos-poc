"""Bill-Intel pertes & récupérations — source de vérité unique.

Sprint 2 Vague B ét7' (27/04/2026). Factorise les calculs auparavant
inline dans `narrative_generator._build_bill_intel` (lignes 1160-1162) et
ajoute 2 nouveaux indicateurs réclamés par l'audit personas Vague A :

- **payback_avg_days** (CFO) : délai moyen détection→résolution sur les
  insights resolved. Permet la formule "récupère X k€ en Y mois" attendue
  par le CFO Jean-Marc CODIR Q3.
- **recovery_rate_pct** (Marie + CFO) : ratio reclaims YTD / pertes totales
  YTD. Mesure l'efficacité du processus de contestation.

Règle d'or chiffres (memory feedback 27/04) :
  - Fiable : un seul service, calculs déterministes, lecture DB pure
  - Vérifiable : provenance exposée (source + confidence + sample_size +
    methodology). Test pytest reproductibilité.
  - Simple : valeurs pré-formatées FR via `_fmt_eur_short`. Confiance
    dégradée explicitement quand échantillon faible (<5 insights resolved).

Doctrine §8.1 : aucun calcul métier frontend — tout passe par ce service.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from models import EntiteJuridique, Portefeuille, Site, not_deleted
from models.billing_models import BillingInsight
from models.enums import InsightStatus

# Seuil minimum d'échantillon pour produire une moyenne payback fiable.
# En-dessous, on retourne la valeur mais on dégrade la confiance MEDIUM → LOW.
_MIN_SAMPLE_FOR_PAYBACK_HIGH = 10
_MIN_SAMPLE_FOR_PAYBACK_MEDIUM = 3

# Confidence levels — mêmes valeurs que `services.data_provenance` mais
# importées localement pour ne pas créer de cycle d'import.
_CONFIDENCE_HIGH = "high"
_CONFIDENCE_MEDIUM = "medium"
_CONFIDENCE_LOW = "low"


@dataclass(frozen=True)
class LossesProvenance:
    """Métadonnées de fiabilité d'une mesure de pertes — règle d'or chiffres."""

    source: str
    confidence: str  # high | medium | low
    sample_size: int  # nombre d'insights agrégés pour la statistique
    computed_at: datetime
    methodology: str  # 1 phrase explicative pour tooltip non-sachant


@dataclass(frozen=True)
class BillingLossesSummary:
    """Synthèse pertes/récupérations Bill-Intel pour un scope organisation.

    Tous les chiffres sont en EUR (montants) ou jours (délais). Les
    formats d'affichage (`26 k€`, `« 14 mois »`) sont à la charge du
    consommateur — ce DTO porte des nombres bruts avec leur provenance.
    """

    # ── Volumes ──
    nb_open: int
    nb_ack: int
    nb_resolved: int
    nb_total_ytd: int  # open + ack + resolved sur l'année courante

    # ── Montants en EUR ──
    perte_open_eur: float  # cumul des pertes des insights status=open
    contestation_eur: float  # cumul des pertes des insights status=ack
    reclaim_ytd_eur: float  # cumul des pertes des insights resolved YTD

    # ── Indicateurs nouveaux Sprint 2 ét7' ──
    payback_avg_days: Optional[float]  # délai moyen détection→résolution
    recovery_rate_pct: Optional[float]  # reclaim_ytd / (reclaim_ytd + perte_open)

    # ── Provenance (règle d'or chiffres) ──
    losses_provenance: LossesProvenance
    payback_provenance: LossesProvenance
    recovery_provenance: LossesProvenance


# ── Helpers internes ─────────────────────────────────────────────────


def _scope_billing_insights(db: Session, org_id: int) -> list[BillingInsight]:
    """Charge tous les BillingInsight d'une org (jointure 3 niveaux)."""
    return (
        not_deleted(db.query(BillingInsight), BillingInsight)
        .join(Site, Site.id == BillingInsight.site_id)
        .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
        .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
        .filter(EntiteJuridique.organisation_id == org_id)
        .all()
    )


def _as_utc(dt: Optional[datetime]) -> Optional[datetime]:
    """Normalise un datetime en UTC-aware (compat SQLAlchemy naive storage).

    Convention PROMEOS : `TimestampMixin.created_at/updated_at` sont
    insérés en `datetime.now(timezone.utc)` mais relus naive par
    SQLAlchemy. On présume UTC implicite.
    """
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt


def _payback_days(insight: BillingInsight) -> Optional[int]:
    """Délai détection→résolution en jours (None si non résolu ou dates absentes)."""
    if insight.insight_status != InsightStatus.RESOLVED:
        return None
    created = _as_utc(getattr(insight, "created_at", None))
    updated = _as_utc(getattr(insight, "updated_at", None))
    if created is None or updated is None:
        return None
    delta = updated - created
    return max(0, delta.days)


def _confidence_for_sample(sample_size: int) -> str:
    """Mappe la taille d'échantillon vers un niveau de confiance.

    Cohérent avec règle d'or chiffres (memory feedback) : un calcul sur
    moins de 3 points n'est pas une statistique exploitable.
    """
    if sample_size >= _MIN_SAMPLE_FOR_PAYBACK_HIGH:
        return _CONFIDENCE_HIGH
    if sample_size >= _MIN_SAMPLE_FOR_PAYBACK_MEDIUM:
        return _CONFIDENCE_MEDIUM
    return _CONFIDENCE_LOW


# ── API publique ─────────────────────────────────────────────────────


def compute_billing_losses_summary(
    db: Session,
    org_id: int,
    *,
    insights: Optional[list[BillingInsight]] = None,
) -> BillingLossesSummary:
    """Source de vérité unique pour les pertes/récupérations Bill-Intel d'une org.

    Remplace les calculs inline `sum((i.estimated_loss_eur or 0.0) for ...)`
    auparavant dispersés. Cette fonction est déterministe : même DB → même
    output (testé via `test_losses_service.py::test_reproducibility`).

    Parameters
    ----------
    db : Session
        Session SQLAlchemy active.
    org_id : int
        Identifiant org pour le scope multi-tenant.
    insights : list[BillingInsight], optional
        Liste pré-chargée par le caller. Si fournie, évite une 2ᵉ query SQL
        (caller comme `narrative_generator._build_bill_intel` charge déjà
        la liste pour produire les week-cards). Si None, query interne.

    Returns
    -------
    BillingLossesSummary
        Toutes les agrégations + provenance pour 3 mesures (losses, payback,
        recovery rate). Les valeurs `None` signalent "donnée non
        calculable" (ex. payback sans insight resolved).
    """
    now = datetime.now(timezone.utc)
    if insights is None:
        insights = _scope_billing_insights(db, org_id)

    open_insights = [i for i in insights if i.insight_status == InsightStatus.OPEN]
    ack_insights = [i for i in insights if i.insight_status == InsightStatus.ACK]
    resolved_insights = [i for i in insights if i.insight_status == InsightStatus.RESOLVED]

    # ── Année en cours pour ratio YTD (memory feedback : "depuis le 1ᵉʳ janvier") ──
    year_start = datetime(now.year, 1, 1, tzinfo=timezone.utc)
    resolved_ytd = [
        i
        for i in resolved_insights
        if (updated := _as_utc(getattr(i, "updated_at", None))) is not None and updated >= year_start
    ]

    # ── Montants ──
    perte_open_eur = sum((i.estimated_loss_eur or 0.0) for i in open_insights)
    contestation_eur = sum((i.estimated_loss_eur or 0.0) for i in ack_insights)
    reclaim_ytd_eur = sum((i.estimated_loss_eur or 0.0) for i in resolved_ytd)

    # ── Payback moyen (jours) ──
    payback_samples = [d for d in (_payback_days(i) for i in resolved_ytd) if d is not None]
    payback_avg_days: Optional[float] = sum(payback_samples) / len(payback_samples) if payback_samples else None

    # ── Recovery rate (%) — récupéré sur le total détecté actionnable ──
    # Dénominateur = reclaim YTD + open + ack (toutes les anomalies
    # détectées hors faux positifs). Inclure ack reflète "succès du
    # processus complet" plutôt que "succès des seules récupérations
    # déjà closes" — recommandation /simplify ét7' P2.
    perte_jouable_eur = reclaim_ytd_eur + perte_open_eur + contestation_eur
    recovery_rate_pct: Optional[float] = 100.0 * reclaim_ytd_eur / perte_jouable_eur if perte_jouable_eur > 0 else None

    # ── Provenances (règle d'or chiffres) ──
    losses_provenance = LossesProvenance(
        source="Bill-Intel shadow billing v4.2",
        confidence=_confidence_for_sample(len(insights)),
        sample_size=len(insights),
        computed_at=now,
        methodology=(
            "Cumul des estimated_loss_eur par statut workflow "
            "(open/ack/resolved). Reclaims YTD : insights résolus depuis le 1ᵉʳ janvier."
        ),
    )

    payback_provenance = LossesProvenance(
        source="Bill-Intel reclaims YTD",
        confidence=_confidence_for_sample(len(payback_samples)),
        sample_size=len(payback_samples),
        computed_at=now,
        methodology=(
            "Moyenne arithmétique du délai entre la détection (created_at) "
            "et la résolution (updated_at) des insights status=resolved YTD. "
            "Confiance HIGH ≥10 échantillons, MEDIUM ≥3, LOW sinon."
        ),
    )

    recovery_provenance = LossesProvenance(
        source="Bill-Intel reclaims YTD",
        confidence=_confidence_for_sample(len(resolved_ytd) + len(open_insights) + len(ack_insights)),
        sample_size=len(resolved_ytd) + len(open_insights) + len(ack_insights),
        computed_at=now,
        methodology=(
            "Reclaim YTD divisé par la somme reclaim YTD + pertes ouvertes "
            "+ contestations en cours. Indique le taux de succès du processus "
            "de contestation, hors faux positifs. None si aucune anomalie "
            "n'a été remontée (dénominateur zéro)."
        ),
    )

    return BillingLossesSummary(
        nb_open=len(open_insights),
        nb_ack=len(ack_insights),
        nb_resolved=len(resolved_insights),
        nb_total_ytd=len(open_insights) + len(ack_insights) + len(resolved_ytd),
        perte_open_eur=perte_open_eur,
        contestation_eur=contestation_eur,
        reclaim_ytd_eur=reclaim_ytd_eur,
        payback_avg_days=payback_avg_days,
        recovery_rate_pct=recovery_rate_pct,
        losses_provenance=losses_provenance,
        payback_provenance=payback_provenance,
        recovery_provenance=recovery_provenance,
    )


def fmt_payback_human(payback_avg_days: Optional[float]) -> str:
    """Format compact human-friendly d'un délai payback.

    Exemples : 14 jours / 1 jour / 1.5 mois / 4 mois / 2.0 ans / —.
    Les bornes 30 / 365 jours décident l'unité. Memory feedback chiffres :
    "ordre de grandeur intuitif" + accord singulier/pluriel correct.
    """
    if payback_avg_days is None or payback_avg_days <= 0:
        return "—"
    if payback_avg_days < 30:
        n = round(payback_avg_days)
        return f"{n} jour{'s' if n > 1 else ''}"
    months = payback_avg_days / 30
    if months < 12:
        # < 2 mois : 1 décimale (1.5 mois)
        if months < 2:
            return f"{months:.1f} mois"
        return f"{round(months)} mois"
    years = months / 12
    return f"{years:.1f} an{'s' if years >= 2 else ''}"


def fmt_recovery_rate(recovery_rate_pct: Optional[float]) -> str:
    """Format pourcentage compact (1 décimale si <10%, entier sinon)."""
    if recovery_rate_pct is None:
        return "—"
    if recovery_rate_pct < 10:
        return f"{recovery_rate_pct:.1f} %"
    return f"{round(recovery_rate_pct)} %"
