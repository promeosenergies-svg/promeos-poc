"""
PROMEOS — Simulateur de modulation Decret Tertiaire.

Principe : un site peut demander un ajustement de son objectif s'il justifie
de contraintes techniques, architecturales ou de disproportion economique.

Deadline depot OPERAT : 30 septembre 2026.
Source : Decret n2019-771, art. 3 + Arrete du 10 avril 2020 (cas de modulation).
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("promeos.tertiaire.modulation")

# Facteur prudence : les gains par action ne s'additionnent pas toujours
INTERACTION_FACTOR = 0.85

# Jalon par defaut
DEFAULT_REDUCTION_PCT = 0.40  # -40% pour 2030


@dataclass
class ModulationAction:
    label: str
    cout_eur: float
    economie_annuelle_kwh: float
    economie_annuelle_eur: float
    duree_vie_ans: int
    tri_ans: float = 0.0  # calcule automatiquement


@dataclass
class ModulationConstraint:
    type: str  # "technique" | "architecturale" | "economique"
    description: str
    actions: list[ModulationAction] = field(default_factory=list)


@dataclass
class ModulationResult:
    efa_id: int
    efa_nom: str
    objectif_initial_kwh: float
    conso_actuelle_kwh: float
    economie_actions_kwh: float
    conso_apres_actions_kwh: float
    objectif_module_kwh: float
    delta_objectif_pct: float
    tri_moyen_ans: float
    cout_total_eur: float
    dossier_readiness_score: int  # 0-100
    criteres_remplis: list[str] = field(default_factory=list)
    criteres_manquants: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    actions_detail: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return asdict(self)


def simulate_modulation(
    db: Session,
    efa_id: int,
    contraintes: list[dict],
    jalon_reduction_pct: float = DEFAULT_REDUCTION_PCT,
) -> ModulationResult:
    """Simule un dossier de modulation pour une EFA.

    Args:
        db: session SQLAlchemy
        efa_id: identifiant de l'EFA
        contraintes: liste de contraintes avec actions
        jalon_reduction_pct: objectif de reduction (0.40 = -40%)

    Returns:
        ModulationResult avec objectif module, TRI, score readiness
    """
    from models.tertiaire import TertiaireEfa, TertiaireEfaConsumption, TertiaireEfaBuilding

    efa = db.query(TertiaireEfa).filter(TertiaireEfa.id == efa_id).first()
    if not efa:
        raise ValueError(f"EFA {efa_id} introuvable")

    ref_kwh = efa.reference_year_kwh or 0
    objectif_initial = round(ref_kwh * (1 - jalon_reduction_pct))

    # Conso actuelle (la plus recente non-reference)
    latest_conso = (
        db.query(TertiaireEfaConsumption)
        .filter(
            TertiaireEfaConsumption.efa_id == efa_id,
            TertiaireEfaConsumption.is_reference == False,
        )
        .order_by(TertiaireEfaConsumption.year.desc())
        .first()
    )
    conso_actuelle = latest_conso.kwh_total if latest_conso else 0

    # Parser et calculer les actions
    all_actions = []
    warnings = []
    for c in contraintes:
        for a in c.get("actions", []):
            eco_eur = a.get("economie_annuelle_eur", 0)
            cout = a.get("cout_eur", 0)
            tri = round(cout / eco_eur, 1) if eco_eur > 0 else 999
            action = ModulationAction(
                label=a.get("label", ""),
                cout_eur=cout,
                economie_annuelle_kwh=a.get("economie_annuelle_kwh", 0),
                economie_annuelle_eur=eco_eur,
                duree_vie_ans=a.get("duree_vie_ans", 0),
                tri_ans=tri,
            )
            all_actions.append(action)
            if tri > 15:
                warnings.append(f"Action '{action.label}' : TRI = {tri} ans > 15 ans")

    # Economies avec facteur interaction
    eco_brute = sum(a.economie_annuelle_kwh for a in all_actions)
    eco_ajustee = round(eco_brute * INTERACTION_FACTOR)
    cout_total = sum(a.cout_eur for a in all_actions)
    tri_moyen = (
        round(cout_total / sum(a.economie_annuelle_eur for a in all_actions if a.economie_annuelle_eur > 0), 1)
        if any(a.economie_annuelle_eur > 0 for a in all_actions)
        else 0
    )

    conso_apres = round(conso_actuelle - eco_ajustee)

    # Objectif module : si meme avec toutes les actions on ne peut pas atteindre
    if conso_apres > objectif_initial:
        objectif_module = conso_apres
    else:
        objectif_module = objectif_initial  # pas besoin de modulation

    delta_pct = round((objectif_module - objectif_initial) / objectif_initial * 100, 1) if objectif_initial > 0 else 0

    # Score readiness du dossier (6 criteres a ~16.7 pts chacun)
    criteres_remplis = []
    criteres_manquants = []

    # 1. Perimetre precis (EFA + surface)
    buildings = db.query(TertiaireEfaBuilding).filter_by(efa_id=efa_id).all()
    total_surface = sum(b.surface_m2 or 0 for b in buildings)
    if total_surface > 0:
        criteres_remplis.append("perimetre")
    else:
        criteres_manquants.append("perimetre")

    # 2. Donnees fiables (au moins 2 annees de conso)
    nb_consos = db.query(TertiaireEfaConsumption).filter_by(efa_id=efa_id).count()
    if nb_consos >= 2:
        criteres_remplis.append("donnees")
    else:
        criteres_manquants.append("donnees")

    # 3. Actions documentees
    if len(all_actions) > 0 and all(a.cout_eur > 0 and a.economie_annuelle_kwh > 0 for a in all_actions):
        criteres_remplis.append("actions")
    else:
        criteres_manquants.append("actions")

    # 4. Justification technique (au moins 1 contrainte avec description)
    has_justification = any(c.get("description", "").strip() for c in contraintes)
    if has_justification:
        criteres_remplis.append("technique")
    else:
        criteres_manquants.append("technique")

    # 5. TRI calcule pour toutes les actions
    if all_actions and all(a.tri_ans > 0 and a.tri_ans < 999 for a in all_actions):
        criteres_remplis.append("tri")
    else:
        criteres_manquants.append("tri")

    # 6. Coherence strategie globale (org avec plan)
    if efa.org_id:
        criteres_remplis.append("strategie_globale")
    else:
        criteres_manquants.append("strategie_globale")

    readiness_score = round(len(criteres_remplis) / 6 * 100)

    result = ModulationResult(
        efa_id=efa_id,
        efa_nom=efa.nom,
        objectif_initial_kwh=objectif_initial,
        conso_actuelle_kwh=conso_actuelle,
        economie_actions_kwh=eco_ajustee,
        conso_apres_actions_kwh=conso_apres,
        objectif_module_kwh=objectif_module,
        delta_objectif_pct=delta_pct,
        tri_moyen_ans=tri_moyen,
        cout_total_eur=cout_total,
        dossier_readiness_score=readiness_score,
        criteres_remplis=criteres_remplis,
        criteres_manquants=criteres_manquants,
        warnings=warnings,
        actions_detail=[asdict(a) for a in all_actions],
    )

    logger.info(
        "modulation efa=%d: objectif %d -> %d (+%.1f%%), readiness=%d/100",
        efa_id,
        objectif_initial,
        objectif_module,
        delta_pct,
        readiness_score,
    )
    return result
