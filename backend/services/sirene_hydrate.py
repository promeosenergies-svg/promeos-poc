"""
PROMEOS - Hydratation per-SIREN depuis l'API recherche-entreprises.api.gouv.fr
vers les tables locales sirene_*.

Objectif : permettre le flow onboarding_from_sirene sans import CSV complet 2.6 GB.
Cas d'usage : demo, pilote, test utilisateur, onboarding single-tenant.

Pour l'import mensuel complet, utiliser sirene_import.py (CSV INSEE).
"""

import logging
from datetime import datetime, timezone

import httpx
from sqlalchemy.orm import Session

from models.sirene import SireneUniteLegale, SireneEtablissement

logger = logging.getLogger(__name__)

_API_BASE = "https://recherche-entreprises.api.gouv.fr/search"
_TIMEOUT = 10.0


def hydrate_siren_from_api(db: Session, siren: str) -> dict:
    """Charge une entreprise + tous ses etablissements depuis l'API gouv.

    Retourne un dict :
      {
        "siren": "552032534",
        "ul_inserted": bool,
        "etablissements_inserted": int,
        "etablissements_total": int,
      }

    Si l'entreprise existe deja en base, met a jour les champs.
    """
    siren = (siren or "").strip().replace(" ", "")
    if len(siren) != 9 or not siren.isdigit():
        raise ValueError(f"SIREN invalide : {siren}")

    try:
        resp = httpx.get(
            _API_BASE,
            params={"q": siren, "per_page": 5},
            timeout=_TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        raise RuntimeError(f"API gouv indisponible : {e}") from e

    results = data.get("results", [])
    ent = next((r for r in results if r.get("siren") == siren), None)
    if ent is None:
        raise LookupError(f"SIREN {siren} introuvable dans l'API gouv")
    now = datetime.now(timezone.utc)

    # ── Unite Legale ──
    ul = db.query(SireneUniteLegale).filter(SireneUniteLegale.siren == siren).first()
    ul_inserted = False
    if not ul:
        ul = SireneUniteLegale(siren=siren, snapshot_date=now)
        db.add(ul)
        ul_inserted = True

    ul.denomination = ent.get("nom_complet") or ent.get("nom_raison_sociale")
    ul.sigle = ent.get("sigle")
    ul.nom_unite_legale = ent.get("nom")
    ul.prenom1 = (ent.get("prenom_1") or ent.get("prenoms", "").split(" ")[0]) or None
    ul.categorie_juridique = ent.get("nature_juridique")
    ul.activite_principale = ent.get("activite_principale")
    ul.nomenclature_activite = ent.get("nomenclature_activite_principale", "NAFRev2")
    ul.categorie_entreprise = ent.get("categorie_entreprise")
    ul.etat_administratif = ent.get("etat_administratif", "A")
    ul.statut_diffusion = "O"
    ul.tranche_effectifs = ent.get("tranche_effectif_salarie")
    ul.date_creation = ent.get("date_creation")
    ul.date_dernier_traitement = ent.get("date_mise_a_jour_rne")
    ul.caractere_employeur = "O" if ent.get("caractere_employeur") else "N"
    ul.economie_sociale_solidaire = "O" if ent.get("economie_sociale_solidaire") else "N"
    ul.snapshot_date = now

    siege_obj = ent.get("siege", {}) or {}
    if siege_obj.get("nic"):
        ul.nic_siege = siege_obj["nic"]

    db.flush()

    # ── Etablissements (matching + siege) ──
    etabs_payload = list(ent.get("matching_etablissements") or [])
    if siege_obj and not any(e.get("siret") == siege_obj.get("siret") for e in etabs_payload):
        etabs_payload.append(siege_obj)

    valid_sirets = [
        (e.get("siret") or "").strip()
        for e in etabs_payload
        if (e.get("siret") or "").strip().isdigit() and len((e.get("siret") or "").strip()) == 14
    ]
    existing_by_siret = (
        {s.siret: s for s in db.query(SireneEtablissement).filter(SireneEtablissement.siret.in_(valid_sirets)).all()}
        if valid_sirets
        else {}
    )

    etab_inserted = 0
    for e in etabs_payload:
        siret = (e.get("siret") or "").strip()
        if len(siret) != 14 or not siret.isdigit():
            continue

        existing = existing_by_siret.get(siret)
        if not existing:
            existing = SireneEtablissement(
                siret=siret,
                siren=siren,
                nic=siret[9:],
                snapshot_date=now,
            )
            db.add(existing)
            existing_by_siret[siret] = existing
            etab_inserted += 1

        existing.enseigne = e.get("enseigne") or (e.get("liste_enseignes") or [None])[0]
        existing.denomination_usuelle = e.get("denomination_usuelle")
        existing.activite_principale = e.get("activite_principale")
        existing.etat_administratif = e.get("etat_administratif", "A")
        existing.statut_diffusion = "O"
        existing.etablissement_siege = bool(e.get("est_siege") or e.get("siret") == siege_obj.get("siret"))
        existing.numero_voie = str(e.get("numero_voie") or "") or None
        existing.type_voie = e.get("type_voie")
        existing.libelle_voie = e.get("libelle_voie")
        existing.complement_adresse = e.get("complement_adresse")
        existing.code_postal = e.get("code_postal")
        existing.libelle_commune = e.get("libelle_commune")
        existing.code_commune = e.get("commune")
        existing.date_creation = e.get("date_creation")
        existing.date_dernier_traitement = ent.get("date_mise_a_jour_rne")
        existing.snapshot_date = now

    db.commit()
    logger.info(
        "hydrate_siren_from_api: siren=%s ul_inserted=%s etab_inserted=%d total=%d",
        siren,
        ul_inserted,
        etab_inserted,
        len(etabs_payload),
    )

    return {
        "siren": siren,
        "ul_inserted": ul_inserted,
        "etablissements_inserted": etab_inserted,
        "etablissements_total": len(etabs_payload),
    }
