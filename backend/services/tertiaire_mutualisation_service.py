"""
PROMEOS — Simulateur de mutualisation Decret Tertiaire.

Principe : un assujetti avec N sites peut compenser les sites en retard
avec les sites en avance. La verification de l'atteinte des objectifs
est evaluee au niveau du « groupe de structures » constitue.

STATUT REGLEMENTAIRE (au 2026-05-28, verifie Legifrance) :
- La mutualisation patrimoniale est explicitement prevue par l'Article
  R.174-31 du Code de la construction et de l'habitation (modalite
  d'application de l'Article L.111-10-3, fondement legal trajectoire).
- L'Article 14 de l'arrete du 10 avril 2020 modifie precise les
  modalites de mutualisation : constitution d'un « groupe de structures »
  saisi via la plateforme OPERAT, avec validation du representant legal
  de chaque entite fonctionnelle integree au perimetre. Donnees attendues :
  Table 1B de l'Annexe IV de l'arrete.
- Regles d'unicite (Art. 14) : une entite fonctionnelle ne peut
  appartenir qu'a UN seul groupe ; les consommations economisees ne
  peuvent etre redistribuees qu'UNE seule fois.
- L'arrete du 1er aout 2025 (NOR ATDL2430864A) apporte les precisions
  sur la mutualisation multi-sites et l'attestation numerique OPERAT
  (obligatoire apres 1er juillet 2026).
- A la date du sprint, le module OPERAT « Mutualisation des resultats
  a l'echelle d'un patrimoine » est en cours de deploiement progressif
  par l'ADEME. Tant qu'il n'est pas pleinement operationnel, chaque
  site reste a declarer individuellement et la compensation est
  constatee lors du controle decennal (echeances 2030/2040/2050).
- PROMEOS anticipe le calcul de la position consolidee pour preparer
  la trajectoire patrimoniale en amont du depot, en s'appuyant sur les
  regles d'unicite citees plus haut.

Sources officielles uniquement (Legifrance) :
- Article L.111-10-3 du Code de la construction et de l'habitation —
  fondement legal de l'obligation de reduction.
- Article R.174-31 du meme code — modalite d'application mutualisation.
- Decret n°2019-771 du 23/07/2019 — calcul objectif au niveau patrimoine.
- Arrete du 10 avril 2020 modifie, Article 14 — modalites mutualisation
  via OPERAT + groupes de structures + Table 1B Annexe IV.
- Arrete du 1er aout 2025 — precisions mutualisation 2026+.

Aucune reference a un editeur tiers n'est exposee dans les messages
rendus a l'utilisateur (doctrine PROMEOS : zero mention concurrent UI,
cf. feedback_promeos_zero_concurrent_ui).
"""

import logging
from dataclasses import dataclass, field, asdict
from typing import Optional

from sqlalchemy.orm import Session

logger = logging.getLogger("promeos.tertiaire.mutualisation")

# Constantes importees depuis sources canoniques
from config.emission_factors import BASE_PENALTY_EURO
from services.operat_trajectory import TARGETS as _OT_TARGETS

DISCLAIMER_MUTUALISATION = (
    "Simulation patrimoniale — le module OPERAT « Mutualisation des "
    "résultats à l'échelle d'un patrimoine » est en cours de déploiement "
    "progressif. En attendant, chaque entité fonctionnelle (EFA) reste "
    "à déclarer individuellement et la compensation est constatée lors "
    "du contrôle décennal. PROMEOS calcule la position consolidée pour "
    "préparer votre groupe de structures avant dépôt OPERAT. "
    "Sources : Art. R.174-31 du Code de la construction et de "
    "l'habitation et Article 14 de l'arrêté du 10 avril 2020 modifié "
    "(constitution du groupe de structures + Table 1B de l'Annexe IV)."
)

# Conversion : operat_trajectory stocke le *reste* (0.60 = garder 60% = -40%)
# On veut la *reduction* (0.40 = reduire de 40%)
JALON_REDUCTIONS = {yr: round(1 - factor, 2) for yr, factor in _OT_TARGETS.items()}


@dataclass
class SiteMutualisationDetail:
    site_id: int
    site_nom: str
    efa_id: int
    efa_nom: str
    reference_kwh: float
    actuelle_kwh: float
    objectif_kwh: float
    ecart_kwh: float  # + = deficit, - = surplus
    statut: str  # "surplus" | "deficit" | "conforme"


@dataclass
class MutualisationResult:
    org_id: int
    jalon_annee: int
    jalon_reduction_pct: float
    sites: list[SiteMutualisationDetail] = field(default_factory=list)
    ecart_total_kwh: float = 0.0
    conforme_mutualise: bool = False
    nb_sites_surplus: int = 0
    nb_sites_deficit: int = 0
    penalite_sans_mutualisation_eur: float = 0.0
    penalite_avec_mutualisation_eur: float = 0.0
    economie_mutualisation_eur: float = 0.0

    def to_dict(self) -> dict:
        d = asdict(self)
        d["simulation"] = True
        d["disclaimer"] = DISCLAIMER_MUTUALISATION
        d["portefeuille"] = {
            "ecart_total_kwh": self.ecart_total_kwh,
            "conforme_mutualise": self.conforme_mutualise,
            "nb_sites_surplus": self.nb_sites_surplus,
            "nb_sites_deficit": self.nb_sites_deficit,
            "penalite_sans_mutualisation_eur": self.penalite_sans_mutualisation_eur,
            "penalite_avec_mutualisation_eur": self.penalite_avec_mutualisation_eur,
            "economie_mutualisation_eur": self.economie_mutualisation_eur,
        }
        return d


def compute_mutualisation(
    db: Session,
    org_id: int,
    jalon: int = 2030,
) -> MutualisationResult:
    """Calcule la simulation de mutualisation pour un portefeuille.

    Args:
        db: session SQLAlchemy
        org_id: organisation
        jalon: annee cible (2030, 2040 ou 2050)

    Returns:
        MutualisationResult avec detail par site et synthese portefeuille
    """
    from models import Site, not_deleted
    from models.tertiaire import TertiaireEfa, TertiaireEfaConsumption

    reduction_pct = JALON_REDUCTIONS.get(jalon, 0.40)

    # Trouver toutes les EFA de l'org avec reference + conso recente
    efas = (
        db.query(TertiaireEfa)
        .filter(
            TertiaireEfa.org_id == org_id,
            TertiaireEfa.reference_year.isnot(None),
            TertiaireEfa.reference_year_kwh.isnot(None),
            not_deleted(TertiaireEfa),
        )
        .all()
    )

    sites_detail = []
    for efa in efas:
        # Conso la plus recente
        latest_conso = (
            db.query(TertiaireEfaConsumption)
            .filter(
                TertiaireEfaConsumption.efa_id == efa.id,
                TertiaireEfaConsumption.is_reference == False,
            )
            .order_by(TertiaireEfaConsumption.year.desc())
            .first()
        )
        if not latest_conso:
            continue

        ref_kwh = efa.reference_year_kwh
        actuelle_kwh = latest_conso.kwh_total
        objectif_kwh = round(ref_kwh * (1 - reduction_pct))
        ecart_kwh = round(actuelle_kwh - objectif_kwh)

        if ecart_kwh > 0:
            statut = "deficit"
        elif ecart_kwh < 0:
            statut = "surplus"
        else:
            statut = "conforme"

        # Nom du site
        site = db.query(Site).filter(Site.id == efa.site_id).first() if efa.site_id else None
        site_nom = site.nom if site else efa.nom

        sites_detail.append(
            SiteMutualisationDetail(
                site_id=efa.site_id or 0,
                site_nom=site_nom,
                efa_id=efa.id,
                efa_nom=efa.nom,
                reference_kwh=ref_kwh,
                actuelle_kwh=actuelle_kwh,
                objectif_kwh=objectif_kwh,
                ecart_kwh=ecart_kwh,
                statut=statut,
            )
        )

    # Synthese portefeuille
    nb_deficit = sum(1 for s in sites_detail if s.statut == "deficit")
    nb_surplus = sum(1 for s in sites_detail if s.statut == "surplus")
    ecart_total = sum(s.ecart_kwh for s in sites_detail)

    penalite_sans = BASE_PENALTY_EURO * nb_deficit
    penalite_avec = BASE_PENALTY_EURO if ecart_total > 0 else 0
    economie = penalite_sans - penalite_avec

    result = MutualisationResult(
        org_id=org_id,
        jalon_annee=jalon,
        jalon_reduction_pct=reduction_pct * 100,
        sites=sites_detail,
        ecart_total_kwh=round(ecart_total),
        conforme_mutualise=(ecart_total <= 0),
        nb_sites_surplus=nb_surplus,
        nb_sites_deficit=nb_deficit,
        penalite_sans_mutualisation_eur=penalite_sans,
        penalite_avec_mutualisation_eur=penalite_avec,
        economie_mutualisation_eur=economie,
    )

    logger.info(
        "mutualisation org=%d jalon=%d: %d sites, ecart_total=%d kWh, economie=%d EUR",
        org_id,
        jalon,
        len(sites_detail),
        ecart_total,
        economie,
    )
    return result
