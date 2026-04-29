"""
PROMEOS — Dashboard Essentials service (migration JS → Python).

Phase 1.4.d du sprint refonte cockpit dual sol2 (29/04/2026). Migration
de `frontend/src/models/dashboardEssentials.js` (717 lignes) vers backend
Python pour respecter la règle d'or CLAUDE.md #1 :
zero business logic in frontend.

NOTE — migration progressive (stratégie « SoT d'abord ») :
    Le fichier JS frontend/src/models/dashboardEssentials.js reste temporairement
    en place comme couche de compatibilité legacy. Les 4 pages importeuses
    (Cockpit.jsx, ConformitePage.jsx, CommandCenter.jsx, billingHealthModel.js)
    seront migrées pour consommer l'endpoint /api/cockpit/essentials en
    Phase 1.4.d.bis (session dédiée). La suppression du JS interviendra
    uniquement après validation de la bascule frontend complète.

Constantes canoniques (portées depuis frontend/src/lib/constants.js) :
    RISK_THRESHOLDS        — seuils risque EUR (org: crit 50 000 / warn 10 000)
    COVERAGE_THRESHOLDS    — seuils couverture données %
    CONFORMITY_THRESHOLDS  — seuils conformité %
    MATURITY_THRESHOLDS    — seuils maturité %
    READINESS_WEIGHTS      — poids score maturité (data 0.3 / conformity 0.4 / actions 0.3)
    SEVERITY_RANK          — ordre tri sévérité (critical=0 … low=5)
    COMPLIANCE_SCORE_THRESHOLDS — seuils score unifié (ok=80 / warn=50)

Exports :
    WatchItem               — item liste de surveillance
    ConsistencyIssue        — item d'inconsistance données
    ConsistencyResult       — {ok, issues}
    SiteItem                — résumé site (worst/best)
    TopSites                — {worst, best}
    Opportunity             — opportunité actionnable
    BriefingItem            — item briefing du jour
    TodayAction             — action à traiter aujourd'hui
    ExecBullet              — bullet résumé exécutif
    ExecKpi                 — KPI décideur
    HealthState             — état de santé agrégé
    DashboardEssentials     — résultat agrégé complet

    build_watchlist()       — liste surveillance (max 5, triée par sévérité)
    check_consistency()     — détection inconsistances données
    build_top_sites()       — worst 5 / best 5 sites
    build_opportunities()   — opportunités (max 3, isExpert uniquement)
    build_briefing()        — briefing du jour (max 3)
    build_today_actions()   — actions à traiter (max 5, dédupliquées)
    build_executive_summary() — résumé exécutif (max 3 bullets)
    build_executive_kpis()  — 4 tuiles KPI décideur
    build_dashboard_essentials() — agrégateur principal
    compute_health_state()  — état de santé unifié

Compatibilité : accepte les clés camelCase legacy (nonConformes, aRisque,
risqueTotal, couvertureDonnees, compliance_score, compliance_confidence)
en plus des clés snake_case. Cela garantit la tolérance de migration avec
les payloads existants retournés par KpiService.
"""

from dataclasses import dataclass, field
from typing import Optional

# ── Constantes canoniques (portées depuis frontend/src/lib/constants.js) ─────
# Ces seuils sont la référence pour tous les calculs de dashboard.
# Ne PAS dupliquer dans d'autres modules — importer depuis ici.

RISK_THRESHOLDS_ORG_CRIT = 50_000  # EUR
RISK_THRESHOLDS_ORG_WARN = 10_000  # EUR
RISK_THRESHOLDS_SITE_CRIT = 10_000  # EUR
RISK_THRESHOLDS_SITE_WARN = 3_000  # EUR

COVERAGE_SUSPICIOUS = 30  # % — 100% conforme + < 30% couverture = suspect
COVERAGE_WARN = 50  # % — en dessous → statut warn sur tuile KPI
COVERAGE_OPPORTUNITY = 80  # % — en dessous → item opportunité / briefing

CONFORMITY_POSITIVE = 80  # % — score >= 80 + 0 NC → bullet positive
CONFORMITY_WARN = 50  # % — score >= 50 → warn, < 50 → negative

MATURITY_CRIT = 40  # % — score < 40 → crit
MATURITY_WARN = 70  # % — score < 70 → warn, >= 70 → ok

READINESS_WEIGHT_DATA = 0.3
READINESS_WEIGHT_CONFORMITY = 0.4
READINESS_WEIGHT_ACTIONS = 0.3

COMPLIANCE_SCORE_OK = 80  # % — >= 80 → ok (vert)
COMPLIANCE_SCORE_WARN = 50  # % — >= 50 → warn (ambre), < 50 → crit (rouge)

# Ordre de tri par sévérité (inférieur = plus urgent)
SEVERITY_RANK: dict[str, int] = {
    "critical": 0,
    "high": 1,
    "warn": 2,
    "medium": 3,
    "info": 4,
    "low": 5,
}


# ── Dataclasses ───────────────────────────────────────────────────────────────


@dataclass
class WatchItem:
    """Item de la liste de surveillance (max 5, triée par sévérité)."""

    id: str
    label: str
    severity: str  # 'critical' | 'high' | 'warn' | 'medium' | 'info'
    path: str
    cta: str

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "severity": self.severity, "path": self.path, "cta": self.cta}


@dataclass
class ConsistencyIssue:
    """Issue d'inconsistance données."""

    code: str
    label: str

    def to_dict(self) -> dict:
        return {"code": self.code, "label": self.label}


@dataclass
class ConsistencyResult:
    """Résultat de check_consistency."""

    ok: bool
    issues: list[ConsistencyIssue] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {"ok": self.ok, "issues": [i.to_dict() for i in self.issues]}


@dataclass
class SiteItem:
    """Résumé d'un site (worst ou best)."""

    id: int
    nom: str
    ville: Optional[str]
    statut_conformite: Optional[str]
    risque_eur: Optional[float] = None
    conso_kwh_an: Optional[float] = None

    def to_dict(self) -> dict:
        d = {"id": self.id, "nom": self.nom, "ville": self.ville, "statut_conformite": self.statut_conformite}
        if self.risque_eur is not None:
            d["risque_eur"] = self.risque_eur
        if self.conso_kwh_an is not None:
            d["conso_kwh_an"] = self.conso_kwh_an
        return d


@dataclass
class TopSites:
    """Paires worst/best (5 chacun)."""

    worst: list[SiteItem] = field(default_factory=list)
    best: list[SiteItem] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "worst": [s.to_dict() for s in self.worst],
            "best": [s.to_dict() for s in self.best],
        }


@dataclass
class Opportunity:
    """Opportunité actionnable (max 3, isExpert uniquement)."""

    id: str
    label: str
    sub: str
    path: str
    cta: str

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "sub": self.sub, "path": self.path, "cta": self.cta}


@dataclass
class BriefingItem:
    """Item du briefing du jour (max 3)."""

    id: str
    label: str
    severity: str
    path: str

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "severity": self.severity, "path": self.path}


@dataclass
class TodayAction:
    """Action à traiter aujourd'hui (max 5, dédupliquée)."""

    id: str
    label: str
    severity: str
    path: str
    cta: str
    type: str  # 'watchlist' | 'opportunity'

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "label": self.label,
            "severity": self.severity,
            "path": self.path,
            "cta": self.cta,
            "type": self.type,
        }


@dataclass
class ExecBullet:
    """Bullet du résumé exécutif (max 3)."""

    id: str
    type: str  # 'positive' | 'negative' | 'warn' | 'opportunity'
    label: str
    sub: Optional[str] = None
    path: Optional[str] = None

    def to_dict(self) -> dict:
        d = {"id": self.id, "type": self.type, "label": self.label}
        if self.sub is not None:
            d["sub"] = self.sub
        if self.path is not None:
            d["path"] = self.path
        return d


@dataclass
class ExecKpi:
    """Tuile KPI décideur (4 tuiles dans la vue exécutive)."""

    id: str
    accent_key: str
    label: str
    value: str
    raw_value: Optional[float]
    sub_short: str
    sub: str
    status: str  # 'ok' | 'warn' | 'crit' | 'neutral'
    message_ctx: dict = field(default_factory=dict)
    path: Optional[str] = None
    explain: Optional[str] = None

    def to_dict(self) -> dict:
        d = {
            "id": self.id,
            "accentKey": self.accent_key,
            "label": self.label,
            "value": self.value,
            "rawValue": self.raw_value,
            "subShort": self.sub_short,
            "sub": self.sub,
            "status": self.status,
            "messageCtx": self.message_ctx,
        }
        if self.path is not None:
            d["path"] = self.path
        if self.explain is not None:
            d["explain"] = self.explain
        return d


@dataclass
class HealthReason:
    """Raison d'un état de santé dégradé."""

    id: str
    label: str
    severity: str
    link: str

    def to_dict(self) -> dict:
        return {"id": self.id, "label": self.label, "severity": self.severity, "link": self.link}


@dataclass
class HealthCta:
    """CTA dans le banner d'état de santé."""

    label: str
    to: str

    def to_dict(self) -> dict:
        return {"label": self.label, "to": self.to}


@dataclass
class HealthState:
    """État de santé agrégé du dashboard."""

    level: str  # 'GREEN' | 'AMBER' | 'RED'
    title: str
    subtitle: str
    reasons: list[HealthReason]
    all_reason_count: int
    primary_cta: HealthCta
    secondary_cta: Optional[HealthCta] = None

    def to_dict(self) -> dict:
        d = {
            "level": self.level,
            "title": self.title,
            "subtitle": self.subtitle,
            "reasons": [r.to_dict() for r in self.reasons],
            "allReasonCount": self.all_reason_count,
            "primaryCta": self.primary_cta.to_dict(),
        }
        if self.secondary_cta is not None:
            d["secondaryCta"] = self.secondary_cta.to_dict()
        return d


@dataclass
class DashboardEssentials:
    """Résultat agrégé complet du dashboard — retourné par build_dashboard_essentials."""

    kpis: dict
    watchlist: list[WatchItem]
    briefing: list[BriefingItem]
    top_sites: TopSites
    opportunities: list[Opportunity]
    today_actions: list[TodayAction]
    executive_summary: list[ExecBullet]
    executive_kpis: list[ExecKpi]
    consistency: ConsistencyResult
    health_state: HealthState

    def to_dict(self) -> dict:
        return {
            "kpis": self.kpis,
            "watchlist": [w.to_dict() for w in self.watchlist],
            "briefing": [b.to_dict() for b in self.briefing],
            "topSites": self.top_sites.to_dict(),
            "opportunities": [o.to_dict() for o in self.opportunities],
            "todayActions": [a.to_dict() for a in self.today_actions],
            "executiveSummary": [b.to_dict() for b in self.executive_summary],
            "executiveKpis": [k.to_dict() for k in self.executive_kpis],
            "consistency": self.consistency.to_dict(),
            "healthState": self.health_state.to_dict(),
        }


# ── Helpers internes ──────────────────────────────────────────────────────────


def _plural_fr(n: int, singular: str, plural: str) -> str:
    """Retourne singular si n==1, plural sinon."""
    return singular if n == 1 else plural


def _format_percent_fr(pct: float) -> str:
    """Format pourcent FR : '42 %' (espace fine insécable)."""
    return f"{round(pct)} %"


def _get_risk_status(amount: float) -> str:
    """Calcule le statut de risque à partir du montant EUR."""
    if amount > RISK_THRESHOLDS_ORG_CRIT:
        return "crit"
    if amount > RISK_THRESHOLDS_ORG_WARN:
        return "warn"
    return "ok"


def _severity_sort_key(item: dict) -> int:
    return SEVERITY_RANK.get(item.get("severity", "info"), 99)


# ── build_watchlist ───────────────────────────────────────────────────────────


def build_watchlist(kpis: dict, sites: list[dict] | None = None) -> list[WatchItem]:
    """
    Construit la liste de surveillance triée par sévérité (max 5).

    Args:
        kpis: dict avec nonConformes, aRisque, couvertureDonnees, total
        sites: liste de dicts site (clé conso_kwh_an)

    Returns:
        list[WatchItem] max 5, triée critical → high → warn → medium
    """
    if sites is None:
        sites = []

    items: list[WatchItem] = []

    # 1. Non-conformes — critical
    nc = kpis.get("nonConformes", kpis.get("non_conformes", 0)) or 0
    if nc > 0:
        items.append(
            WatchItem(
                id="non_conformes",
                label=f"{nc} site{_plural_fr(nc, '', 's')} non conforme{_plural_fr(nc, '', 's')} — actions requises",
                severity="critical",
                path="/conformite",
                cta="Voir conformité",
            )
        )

    # 2. Sites à risque — high
    ar = kpis.get("aRisque", kpis.get("a_risque", 0)) or 0
    if ar > 0:
        items.append(
            WatchItem(
                id="a_risque",
                label=f"{ar} site{_plural_fr(ar, '', 's')} à risque réglementaire",
                severity="high",
                path="/actions",
                cta="Plan d'action",
            )
        )

    # 3. Sites sans données de consommation — warn
    sites_without_data = [s for s in sites if not (s.get("conso_kwh_an") or 0)]
    if sites_without_data:
        n = len(sites_without_data)
        items.append(
            WatchItem(
                id="no_conso_data",
                label=f"Données manquantes sur {n} site{_plural_fr(n, '', 's')}",
                severity="warn",
                path="/consommations/import",
                cta="Importer",
            )
        )

    # 4. Couverture données basse — medium (si total >= 3 et #3 absent)
    couverture = kpis.get("couvertureDonnees", kpis.get("couverture_donnees", 0)) or 0
    total = kpis.get("total", 0) or 0
    if couverture < COVERAGE_WARN and total >= 3 and not sites_without_data:
        items.append(
            WatchItem(
                id="low_coverage",
                label=f"Couverture données insuffisante : {_format_percent_fr(couverture)}",
                severity="medium",
                path="/consommations/import",
                cta="Compléter",
            )
        )

    # Trier par sévérité, cap à 5
    items.sort(key=lambda w: SEVERITY_RANK.get(w.severity, 99))
    return items[:5]


# ── check_consistency ─────────────────────────────────────────────────────────


def check_consistency(kpis: dict) -> ConsistencyResult:
    """
    Détecte les incohérences de données dans le dashboard.

    Args:
        kpis: dict avec conformes, total, couvertureDonnees

    Returns:
        ConsistencyResult { ok, issues }
    """
    issues: list[ConsistencyIssue] = []
    total = kpis.get("total", 0) or 0
    conformes = kpis.get("conformes", 0) or 0
    couverture = kpis.get("couvertureDonnees", kpis.get("couverture_donnees", 0)) or 0

    # Cas 1 : 100% conformes + < 30% couverture → suspect
    conforme_rate = conformes / total if total > 0 else 0
    if conforme_rate == 1 and couverture < COVERAGE_SUSPICIOUS and total > 0:
        issues.append(
            ConsistencyIssue(
                code="all_conformes_low_data",
                label="Conformité complète détectée mais peu de données — vérifiez les imports",
            )
        )

    # Cas 2 : Zéro donnée de consommation
    if couverture == 0 and total > 0:
        issues.append(
            ConsistencyIssue(
                code="no_data_coverage",
                label="Aucun site n'a de données de consommation — importez des relevés",
            )
        )

    return ConsistencyResult(ok=len(issues) == 0, issues=issues)


# ── build_top_sites ───────────────────────────────────────────────────────────


def build_top_sites(sites: list[dict] | None = None) -> TopSites:
    """
    Retourne worst 5 (non-conformes, triés par risque_eur DESC)
    et best 5 (conformes, triés par conso_kwh_an ASC).

    Args:
        sites: liste de dicts site avec statut_conformite, risque_eur, conso_kwh_an

    Returns:
        TopSites { worst, best }
    """
    if not sites:
        return TopSites(worst=[], best=[])

    # worst : non-conformes triés par risque_eur DESC
    worst_raw = sorted(
        [s for s in sites if s.get("statut_conformite") != "conforme"],
        key=lambda s: -(s.get("risque_eur") or 0),
    )[:5]
    worst = [
        SiteItem(
            id=s["id"],
            nom=s.get("nom", ""),
            ville=s.get("ville"),
            statut_conformite=s.get("statut_conformite"),
            risque_eur=float(s.get("risque_eur") or 0),
        )
        for s in worst_raw
    ]

    # best : conformes triés par conso_kwh_an ASC (nuls en dernier)
    best_raw = sorted(
        [s for s in sites if s.get("statut_conformite") == "conforme"],
        key=lambda s: s.get("conso_kwh_an") or 0,
    )[:5]
    best = [
        SiteItem(
            id=s["id"],
            nom=s.get("nom", ""),
            ville=s.get("ville"),
            statut_conformite=s.get("statut_conformite"),
            conso_kwh_an=float(s.get("conso_kwh_an") or 0),
        )
        for s in best_raw
    ]

    return TopSites(worst=worst, best=best)


# ── build_opportunities ───────────────────────────────────────────────────────


def build_opportunities(
    kpis: dict,
    sites: list[dict] | None = None,
    *,
    is_expert: bool = False,
) -> list[Opportunity]:
    """
    Construit jusqu'à 3 opportunités actionnables (uniquement si is_expert=True).

    Args:
        kpis: dict avec couvertureDonnees, total, nonConformes, risqueTotal
        sites: non utilisé V1 (réservé extension)
        is_expert: bool — retourne [] si False

    Returns:
        list[Opportunity] max 3
    """
    if not is_expert:
        return []

    items: list[Opportunity] = []
    couverture = kpis.get("couvertureDonnees", kpis.get("couverture_donnees", 0)) or 0
    total = kpis.get("total", 0) or 0
    nc = kpis.get("nonConformes", kpis.get("non_conformes", 0)) or 0
    risque_total = kpis.get("risqueTotal", kpis.get("risque_total", 0)) or 0

    # 1. Couverture données incomplète
    if couverture < COVERAGE_OPPORTUNITY and total > 0:
        missing_sites = total - round(couverture * total / 100)
        items.append(
            Opportunity(
                id="complete_data",
                label="Compléter les données de consommation",
                sub=(
                    f"{_format_percent_fr(couverture)} couvert — "
                    f"{missing_sites} site{_plural_fr(missing_sites, '', 's')} sans données"
                ),
                path="/consommations/explorer",
                cta="Explorer",
            )
        )

    # 2. Non-conformes présents
    if nc > 0:
        items.append(
            Opportunity(
                id="reduce_risk",
                label="Réduire le risque Décret Tertiaire",
                sub=f"{nc} site{_plural_fr(nc, '', 's')} en retard — plan d'actions disponible",
                path="/actions",
                cta="Plan d'action",
            )
        )

    # 3. Risque financier élevé
    if risque_total > RISK_THRESHOLDS_ORG_WARN:
        k_eur = round(risque_total / 1000)
        items.append(
            Opportunity(
                id="optimize_subscriptions",
                label="Optimiser les abonnements énergie",
                sub=f"Risque estimé : {k_eur} k€ — audit des contrats recommandé",
                path="/performance",
                cta="Analyser",
            )
        )

    return items[:3]


# ── build_briefing ────────────────────────────────────────────────────────────


def build_briefing(
    kpis: dict,
    watchlist: list[WatchItem] | None = None,
    alerts_count: int = 0,
) -> list[BriefingItem]:
    """
    Dérive jusqu'à 3 items prioritaires pour le "Briefing du jour".
    Ordre de sévérité : critical → high → warn.

    Args:
        kpis: dict avec nonConformes, aRisque, couvertureDonnees, total
        watchlist: non utilisé V1 (réservé extension)
        alerts_count: nombre d'alertes actives

    Returns:
        list[BriefingItem] max 3
    """
    bullets: list[BriefingItem] = []
    nc = kpis.get("nonConformes", kpis.get("non_conformes", 0)) or 0
    ar = kpis.get("aRisque", kpis.get("a_risque", 0)) or 0
    couverture = kpis.get("couvertureDonnees", kpis.get("couverture_donnees", 0)) or 0
    total = kpis.get("total", 0) or 0

    # 1. Non-conformes → critical
    if nc > 0:
        bullets.append(
            BriefingItem(
                id="non_conformes",
                label=f"{nc} site{_plural_fr(nc, '', 's')} à mettre en conformité",
                severity="critical",
                path="/conformite",
            )
        )

    # 2. Sites à risque → high
    if ar > 0:
        bullets.append(
            BriefingItem(
                id="a_risque",
                label=f"{ar} site{_plural_fr(ar, '', 's')} à risque Décret Tertiaire",
                severity="high",
                path="/actions",
            )
        )

    # 3. Alertes actives → high ou warn
    if alerts_count > 0:
        bullets.append(
            BriefingItem(
                id="alertes_actives",
                label=(
                    f"{alerts_count} alerte{_plural_fr(alerts_count, '', 's')} "
                    f"active{_plural_fr(alerts_count, '', 's')}"
                ),
                severity="high" if alerts_count > 5 else "warn",
                path="/notifications",
            )
        )

    # 4. Couverture données basse → warn
    if couverture < COVERAGE_OPPORTUNITY and total > 0:
        missing = total - round(couverture * total / 100)
        bullets.append(
            BriefingItem(
                id="coverage",
                label=f"{missing} site{_plural_fr(missing, '', 's')} sans données de consommation",
                severity="warn",
                path="/consommations/import",
            )
        )

    return bullets[:3]


# ── build_today_actions ───────────────────────────────────────────────────────


def build_today_actions(
    kpis: dict,
    watchlist: list[WatchItem] | None = None,
    opportunities: list[Opportunity] | None = None,
) -> list[TodayAction]:
    """
    Construit le top-5 "À traiter aujourd'hui" — dédupliqué watchlist + opportunities.
    Trié par sévérité : critical → high → warn → medium → info.

    Args:
        kpis: non utilisé V1 (réservé extension)
        watchlist: items déjà triés par sévérité
        opportunities: items transformés en type 'opportunity' à sévérité 'info'

    Returns:
        list[TodayAction] max 5
    """
    if watchlist is None:
        watchlist = []
    if opportunities is None:
        opportunities = []

    seen: set[str] = set()
    items: list[TodayAction] = []

    # Watchlist en premier (priorité critique)
    for w in watchlist:
        if w.id not in seen:
            seen.add(w.id)
            items.append(
                TodayAction(
                    id=w.id,
                    label=w.label,
                    severity=w.severity,
                    path=w.path,
                    cta=w.cta,
                    type="watchlist",
                )
            )

    # Opportunities (priorité basse)
    for o in opportunities:
        if o.id not in seen:
            seen.add(o.id)
            items.append(
                TodayAction(
                    id=o.id,
                    label=o.label,
                    severity="info",
                    path=o.path,
                    cta=o.cta,
                    type="opportunity",
                )
            )

    # Trier par sévérité, cap à 5
    items.sort(key=lambda a: SEVERITY_RANK.get(a.severity, 99))
    return items[:5]


# ── build_executive_summary ───────────────────────────────────────────────────


def build_executive_summary(
    kpis: dict,
    top_sites: TopSites | None = None,
) -> list[ExecBullet]:
    """
    Dérive 3 bullets exécutifs :
    - Un positif ("ce qui va")
    - Un négatif ("ce qui dérive")
    - Une opportunité

    Args:
        kpis: dict avec total, conformes, nonConformes, aRisque, risqueTotal,
              couvertureDonnees, compliance_score (optionnel), compliance_confidence (optionnel)
        top_sites: non utilisé V1 (réservé extension)

    Returns:
        list[ExecBullet] max 3
    """
    bullets: list[ExecBullet] = []

    total = kpis.get("total", 0) or 0
    conformes = kpis.get("conformes", 0) or 0
    nc = kpis.get("nonConformes", kpis.get("non_conformes", 0)) or 0
    ar = kpis.get("aRisque", kpis.get("a_risque", 0)) or 0
    risque_total = kpis.get("risqueTotal", kpis.get("risque_total", 0)) or 0
    couverture = kpis.get("couvertureDonnees", kpis.get("couverture_donnees", 0)) or 0

    # Score unifié backend (règle no-calc-in-front)
    cs_raw = kpis.get("compliance_score")
    pct_conf = round(cs_raw) if cs_raw is not None else 0

    # 1. Bullet positif / état global
    if total == 0:
        bullets.append(
            ExecBullet(
                id="no_sites",
                type="warn",
                label="Aucun site dans le périmètre",
                sub="Importez votre patrimoine pour démarrer",
            )
        )
    elif pct_conf >= CONFORMITY_POSITIVE and nc == 0 and ar == 0:
        bullets.append(
            ExecBullet(
                id="conforme_ok",
                type="positive",
                label=f"{_format_percent_fr(pct_conf)} des sites en conformité",
                sub=(
                    f"{conformes} site{_plural_fr(conformes, '', 's')} "
                    f"conforme{_plural_fr(conformes, '', 's')} (Décret Tertiaire + BACS)"
                ),
            )
        )
    elif total == 1:
        has_partial = conformes == 0 and (ar > 0 or nc > 0)
        bullets.append(
            ExecBullet(
                id="conforme_partial",
                type="warn" if has_partial else "negative",
                label=(
                    "Mise en conformité requise sur ce site"
                    if nc > 0
                    else "Ce site nécessite une attention réglementaire"
                ),
                sub=(
                    "Décret Tertiaire ou BACS à risque" if ar > 0 and nc == 0 else "Vérifiez le détail dans Conformité"
                ),
            )
        )
    else:
        nc_total = nc + ar
        bullets.append(
            ExecBullet(
                id="conforme_partial",
                type="warn" if pct_conf >= CONFORMITY_WARN else "negative",
                label=(
                    f"Aucun site pleinement conforme sur {total}"
                    if conformes == 0
                    else (
                        f"{conformes} sur {total} site{_plural_fr(total, '', 's')} "
                        f"pleinement conforme{_plural_fr(conformes, '', 's')}"
                    )
                ),
                sub=(
                    f"{nc} non conforme{_plural_fr(nc, '', 's')}, {ar} à risque"
                    if nc_total > 0
                    else f"{conformes} sur {total}"
                ),
            )
        )

    # 2. Bullet négatif / ce qui dérive
    if nc > 0:
        bullets.append(
            ExecBullet(
                id="non_conformes_exec",
                type="negative",
                label=(
                    f"{nc} site{_plural_fr(nc, '', 's')} nécessite{_plural_fr(nc, '', 'nt')} une mise en conformité"
                ),
                sub=f"Risque estimé : {round(risque_total / 1000)} k€" if risque_total > 0 else None,
                path="/conformite",
            )
        )
    elif ar > 0:
        bullets.append(
            ExecBullet(
                id="a_risque_exec",
                type="warn",
                label=(f"{ar} site{_plural_fr(ar, '', 's')} à surveiller (conformité réglementaire)"),
                sub=f"Risque estimé : {round(risque_total / 1000)} k€" if risque_total > 0 else None,
                path="/conformite",
            )
        )
    elif total > 0:
        bullets.append(
            ExecBullet(
                id="all_ok_exec",
                type="positive",
                label="Aucun écart réglementaire détecté",
                sub="Décret Tertiaire et BACS évalués — périmètre sous contrôle",
            )
        )

    # 3. Bullet opportunité / couverture ou coût
    if couverture < COVERAGE_OPPORTUNITY and total > 0:
        missing = total - round(couverture * total / 100)
        bullets.append(
            ExecBullet(
                id="coverage_exec",
                type="opportunity",
                label=f"{missing} site{_plural_fr(missing, '', 's')} sans données de consommation",
                sub="Importer les relevés pour affiner le score de maturité",
                path="/consommations/import",
            )
        )
    elif risque_total > RISK_THRESHOLDS_ORG_WARN:
        bullets.append(
            ExecBullet(
                id="cost_exec",
                type="opportunity",
                label=f"Optimisation potentielle sur {round(risque_total / 1000)} k€ de risque",
                sub="Audit des contrats et abonnements recommandé",
                path="/performance",
            )
        )

    return bullets[:3]


# ── build_executive_kpis ──────────────────────────────────────────────────────


def build_executive_kpis(
    kpis: dict,
    sites: list[dict] | None = None,
) -> list[ExecKpi]:
    """
    Construit 4 tuiles KPI pour la vue exécutive décideur.

    Args:
        kpis: dict avec total, conformes, nonConformes, aRisque, risqueTotal,
              couvertureDonnees, compliance_score, compliance_confidence
        sites: liste de dicts site (clé conso_kwh_an pour comptage couverture)

    Returns:
        list[ExecKpi] — 4 tuiles dans l'ordre : conformite, risque, maturite, couverture
    """
    if sites is None:
        sites = []

    total = kpis.get("total", 0) or 0
    conformes = kpis.get("conformes", 0) or 0
    nc = kpis.get("nonConformes", kpis.get("non_conformes", 0)) or 0
    ar = kpis.get("aRisque", kpis.get("a_risque", 0)) or 0
    risque_total = kpis.get("risqueTotal", kpis.get("risque_total", 0)) or 0
    couverture = kpis.get("couvertureDonnees", kpis.get("couverture_donnees", 0)) or 0
    compliance_confidence = kpis.get("compliance_confidence", "")

    # Score unifié backend (règle no-calc-in-front)
    cs_raw = kpis.get("compliance_score")
    compliance_score = round(cs_raw) if cs_raw is not None else None
    pct_conf = compliance_score if compliance_score is not None else 0

    # Score de maturité (readiness)
    actions_actives = round((conformes / total) * 60 + ((total - nc) / total) * 40) if total > 0 else 80
    readiness_score = (
        round(
            couverture * READINESS_WEIGHT_DATA
            + pct_conf * READINESS_WEIGHT_CONFORMITY
            + actions_actives * READINESS_WEIGHT_ACTIONS
        )
        if total > 0
        else 0
    )

    sites_with_data = sum(1 for s in sites if (s.get("conso_kwh_an") or 0) > 0)

    # Sous-label conformité
    def _conformite_sub() -> str:
        parts = [f"DT 45% · BACS 30% · APER 25%"]
        if nc > 0:
            parts.append(f"{nc} NC")
        if ar > 0:
            parts.append(f"{ar} à risque")
        if compliance_confidence == "low":
            parts.append("Données partielles")
        return (
            " · ".join(parts)
            if compliance_score is not None
            else (f"{conformes} sur {total} site{_plural_fr(total, '', 's')} conforme{_plural_fr(conformes, '', 's')}")
        )

    return [
        ExecKpi(
            id="conformite",
            accent_key="conformite",
            label="Conformité réglementaire",
            value=f"{pct_conf} / 100" if total > 0 else "—",
            raw_value=float(pct_conf),
            sub_short=(
                f"{nc} NC · {ar} à risque"
                if nc > 0
                else (f"{ar} site{_plural_fr(ar, '', 's')} à risque" if ar > 0 else f"{conformes}/{total} conformes")
            ),
            sub=_conformite_sub(),
            status=(
                "crit"
                if pct_conf < COMPLIANCE_SCORE_WARN
                else "warn"
                if pct_conf < COMPLIANCE_SCORE_OK
                else "ok"
                if total > 0
                else "neutral"
            ),
            message_ctx={"totalSites": total, "sitesAtRisk": ar, "sitesNonConformes": nc},
            path="/conformite",
            explain="compliance_score",
        ),
        ExecKpi(
            id="risque",
            accent_key="risque",
            label="Risque financier",
            value=f"{round(risque_total / 1000)} k€" if (total > 0 and risque_total > 0) else "—",
            raw_value=float(risque_total),
            sub_short=(f"{nc + ar} site{_plural_fr(nc + ar, '', 's')} concerné{_plural_fr(nc + ar, '', 's')}"),
            sub=(
                f"{nc + ar} site{_plural_fr(nc + ar, '', 's')} "
                f"concerné{_plural_fr(nc + ar, '', 's')} (périmètre sélectionné)"
            ),
            status=_get_risk_status(risque_total),
            message_ctx={"sitesAtRisk": nc + ar},
            path="/actions",
        ),
        ExecKpi(
            id="maturite",
            accent_key="maturite",
            label="Couverture opérationnelle",
            value=_format_percent_fr(readiness_score) if total > 0 else "—",
            raw_value=float(readiness_score),
            sub_short="Données + conformité + actions",
            sub="Score combiné données, conformité et actions",
            status=("crit" if readiness_score < MATURITY_CRIT else "warn" if readiness_score < MATURITY_WARN else "ok"),
            message_ctx={},
        ),
        ExecKpi(
            id="couverture",
            accent_key="neutral",
            label="Complétude données",
            value=_format_percent_fr(couverture) if total > 0 else "—",
            raw_value=float(couverture),
            sub_short=(
                f"{sites_with_data}/{total} site{_plural_fr(total, '', 's')} "
                f"couvert{_plural_fr(sites_with_data, '', 's')}"
            ),
            sub=(f"{sites_with_data}/{total} site{_plural_fr(total, '', 's')} avec données de consommation"),
            status=(
                "crit" if couverture is None or couverture <= 0 else "warn" if couverture < COVERAGE_WARN else "ok"
            ),
            message_ctx={},
            path="/consommations/import",
        ),
    ]


# ── build_dashboard_essentials ────────────────────────────────────────────────


def build_dashboard_essentials(
    sites: list[dict] | None = None,
    *,
    is_expert: bool = False,
    alerts_count: int = 0,
) -> DashboardEssentials:
    """
    Agrégateur principal — calcule tous les modèles dashboard à partir
    des sites bruts. Équivalent Python de buildDashboardEssentials() JS.

    Args:
        sites: liste de dicts site avec statut_conformite, risque_eur,
               conso_kwh_an, compliance_score (optionnel)
        is_expert: active les opportunités
        alerts_count: nombre d'alertes actives (pour health_state)

    Returns:
        DashboardEssentials — résultat agrégé complet
    """
    if sites is None:
        sites = []

    total = len(sites)
    conformes = sum(1 for s in sites if s.get("statut_conformite") == "conforme")
    nc = sum(1 for s in sites if s.get("statut_conformite") == "non_conforme")
    ar = sum(1 for s in sites if s.get("statut_conformite") == "a_risque")
    risque_total = sum(float(s.get("risque_eur") or 0) for s in sites)
    couverture = round(sum(1 for s in sites if (s.get("conso_kwh_an") or 0) > 0) / total * 100) if total > 0 else 0

    kpis = {
        "total": total,
        "conformes": conformes,
        "nonConformes": nc,
        "aRisque": ar,
        "risqueTotal": risque_total,
        "couvertureDonnees": couverture,
    }

    watchlist = build_watchlist(kpis, sites)
    top_sites = build_top_sites(sites)
    opportunities = build_opportunities(kpis, sites, is_expert=is_expert)
    briefing = build_briefing(kpis, watchlist, alerts_count=alerts_count)
    consistency = check_consistency(kpis)
    today_actions = build_today_actions(kpis, watchlist, opportunities)
    executive_summary = build_executive_summary(kpis, top_sites)
    executive_kpis = build_executive_kpis(kpis, sites)
    health_state = compute_health_state(
        kpis=kpis,
        watchlist=watchlist,
        briefing=briefing,
        consistency=consistency,
        alerts_count=alerts_count,
    )

    return DashboardEssentials(
        kpis=kpis,
        watchlist=watchlist,
        briefing=briefing,
        top_sites=top_sites,
        opportunities=opportunities,
        today_actions=today_actions,
        executive_summary=executive_summary,
        executive_kpis=executive_kpis,
        consistency=consistency,
        health_state=health_state,
    )


# ── compute_health_state ──────────────────────────────────────────────────────


def compute_health_state(
    kpis: dict,
    watchlist: list[WatchItem] | None = None,
    briefing: list[BriefingItem] | None = None,
    consistency: ConsistencyResult | None = None,
    alerts_count: int = 0,
) -> HealthState:
    """
    Calcule l'état de santé unifié à partir des signaux dashboard.
    Fonction pure — sans effets de bord, entièrement testable.

    Niveaux : GREEN → tout sous contrôle · AMBER → points d'attention · RED → actions requises

    Args:
        kpis: dict avec nonConformes, aRisque, conformes, total
        watchlist: items déjà triés par sévérité
        briefing: non utilisé dans la logique (conservé pour compatibilité signature JS)
        consistency: résultat check_consistency()
        alerts_count: nombre d'alertes critiques + warn

    Returns:
        HealthState
    """
    if watchlist is None:
        watchlist = []
    if consistency is None:
        consistency = ConsistencyResult(ok=True, issues=[])

    reasons: list[HealthReason] = []

    # Collecter les raisons depuis la watchlist (déjà triée par sévérité)
    for w in watchlist:
        reasons.append(HealthReason(id=w.id, label=w.label, severity=w.severity, link=w.path))

    # Ajouter les issues d'inconsistance (sévérité warn)
    if not consistency.ok:
        for issue in consistency.issues:
            reasons.append(
                HealthReason(
                    id=f"consistency-{issue.code}",
                    label=issue.label,
                    severity="warn",
                    link="/consommations/import",
                )
            )

    # Alertes actives — influencent le banner même sans watchlist items
    if alerts_count > 0:
        reasons.append(
            HealthReason(
                id="alerts-active",
                label=(
                    f"{alerts_count} alerte{_plural_fr(alerts_count, '', 's')} "
                    f"active{_plural_fr(alerts_count, '', 's')}"
                ),
                severity="high" if alerts_count > 5 else "medium",
                link="/notifications",
            )
        )

    # Conformité non évaluée (sites présents mais aucune valeur)
    nc = kpis.get("nonConformes", kpis.get("non_conformes", 0)) or 0
    ar = kpis.get("aRisque", kpis.get("a_risque", 0)) or 0
    conformes = kpis.get("conformes", 0) or 0
    total = kpis.get("total", 0) or 0

    if total > 0 and conformes == 0 and nc == 0 and ar == 0:
        reasons.append(
            HealthReason(
                id="conformite-unknown",
                label="Conformité non évaluée — lancer un scan",
                severity="warn",
                link="/conformite",
            )
        )

    # Déterminer le niveau
    has_critical = any(r.severity == "critical" for r in reasons) or nc > 0
    has_warn = any(r.severity in ("high", "warn", "medium") for r in reasons) or alerts_count > 0 or ar > 0

    if has_critical:
        level = "RED"
        title = "Actions requises"
        crit_count = sum(1 for r in reasons if r.severity == "critical")
        subtitle = (
            f"{crit_count} point{_plural_fr(crit_count, '', 's')} critique{_plural_fr(crit_count, '', 's')} "
            f"— intervention recommandée"
        )
    elif has_warn:
        level = "AMBER"
        title = "Points d'attention"
        subtitle = f"{len(reasons)} point{_plural_fr(len(reasons), '', 's')} à surveiller"
    else:
        level = "GREEN"
        title = "Tout est sous contrôle"
        subtitle = "Aucune action urgente — continuez la surveillance"

    # CTAs
    primary_cta = (
        HealthCta(label="Voir conformité", to="/conformite")
        if has_critical
        else HealthCta(label="Plan d'action", to="/actions")
        if has_warn
        else HealthCta(label="Explorer", to="/consommations/explorer")
    )

    secondary_cta = HealthCta(label=f"Voir les {len(reasons)} points", to="/anomalies") if len(reasons) > 3 else None

    return HealthState(
        level=level,
        title=title,
        subtitle=subtitle,
        reasons=reasons[:3],
        all_reason_count=len(reasons),
        primary_cta=primary_cta,
        secondary_cta=secondary_cta,
    )
