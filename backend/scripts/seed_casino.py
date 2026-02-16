"""
PROMEOS - Seed: Groupe Casino (36 sites) + 3 obligations + superuser.
Called by POST /api/dev/reset_db and can be run standalone.
"""
import json
import random
from datetime import date, datetime

from sqlalchemy.orm import Session

from models import (
    Organisation, EntiteJuridique, Portefeuille, Site, Compteur,
    ComplianceFinding, ComplianceRunBatch,
    TypeSite, TypeCompteur, EnergyVector,
    ParkingType, OperatStatus, InsightStatus,
)


# ---------------------------------------------------------------------------
# Site definitions (36 sites: 12 Hypermarches + 12 Proximite + 12 Logistique)
# ---------------------------------------------------------------------------

_VILLES = [
    ("Paris", "75001", 48.8566, 2.3522), ("Lyon", "69001", 45.7640, 4.8357),
    ("Marseille", "13001", 43.2965, 5.3698), ("Toulouse", "31000", 43.6047, 1.4442),
    ("Bordeaux", "33000", 44.8378, -0.5792), ("Nantes", "44000", 47.2184, -1.5536),
    ("Lille", "59000", 50.6292, 3.0573), ("Strasbourg", "67000", 48.5734, 7.7521),
    ("Montpellier", "34000", 43.6108, 3.8767), ("Rennes", "35000", 48.1173, -1.6778),
    ("Nice", "06000", 43.7102, 7.2620), ("Grenoble", "38000", 45.1885, 5.7245),
]

_RUES = [
    "Avenue de la Republique", "Rue Victor Hugo", "Boulevard Gambetta",
    "Rue de la Liberte", "Avenue Jean Jaures", "Rue Pasteur",
    "Place de la Mairie", "Rue du Commerce", "Boulevard Haussmann",
    "Rue de Rivoli", "Avenue des Champs", "Rue Nationale",
]


def _build_sites():
    """Return 36 site dicts: 12 Hypermarches + 12 Proximite + 12 Logistique."""
    sites = []
    for i in range(36):
        ville_data = _VILLES[i % len(_VILLES)]
        ville, cp, lat, lon = ville_data
        group = i // 12  # 0=Hyper, 1=Proxi, 2=Logi

        if group == 0:
            prefix, site_type = "Hypermarche", TypeSite.COMMERCE
            surface = random.randint(3000, 12000)
        elif group == 1:
            prefix, site_type = "Casino Proxi", TypeSite.COMMERCE
            surface = random.randint(800, 2500)
        else:
            prefix, site_type = "Entrepot", TypeSite.ENTREPOT
            surface = random.randint(2000, 8000)

        sites.append({
            "nom": f"{prefix} {ville} #{i + 1:02d}",
            "type": site_type,
            "adresse": f"{random.randint(1, 200)} {_RUES[i % len(_RUES)]}",
            "code_postal": cp,
            "ville": ville,
            "region": ["IDF", "ARA", "PACA", "OCC", "NAQ", "PDL",
                        "HDF", "GE", "OCC", "BRE", "PACA", "ARA"][i % 12],
            "surface_m2": surface,
            "latitude": lat + random.uniform(-0.02, 0.02),
            "longitude": lon + random.uniform(-0.02, 0.02),
            "tertiaire_area_m2": surface if surface >= 1000 else None,
            # CVC power: realistic W/m2 estimates (30-80 W/m2)
            "cvc_power_kw": round(surface * random.uniform(0.03, 0.08), 1),
            # Parking: hypermarches have large parkings
            "parking_area_m2": random.randint(1500, 5000) if group == 0 else (
                random.randint(200, 1000) if group == 1 else random.randint(800, 3000)
            ),
            "parking_type": ParkingType.OUTDOOR if group == 0 else ParkingType.UNKNOWN,
            "roof_area_m2": round(surface * random.uniform(0.4, 0.8)),
            # NAF code: present on ~30/36 for DQ partial warnings
            "naf_code": "4711F" if i < 30 else None,
            # Annual energy
            "annual_kwh_total": random.randint(200000, 5000000),
        })
    return sites


# ---------------------------------------------------------------------------
# Compliance findings generator
# ---------------------------------------------------------------------------

def _generate_findings(db, sites, batch_id):
    """Create ComplianceFinding rows for BACS, Decret Tertiaire, APER."""
    findings = []

    for idx, site in enumerate(sites):
        # ---- BACS ----
        cvc = site.cvc_power_kw or 0
        if cvc and hasattr(site, "id"):
            pass  # use site object
        cvc_val = getattr(site, "cvc_power_kw", 0) or 0

        if cvc_val > 290:
            # High power: deadline 2025-01-01
            # 3 of first 10 high-power sites are NOK
            is_nok = idx < 3
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="bacs", rule_id="BACS_HIGH_DEADLINE",
                status="NOK" if is_nok else "OK",
                severity="critical" if is_nok else "low",
                deadline=date(2025, 1, 1),
                evidence="CVC > 290 kW, echeance 01/01/2025" + (
                    " — attestation BACS manquante" if is_nok else " — GTB classe A installee"),
                recommended_actions_json=json.dumps(
                    ["Installer un systeme GTB classe A ou B", "Obtenir attestation BACS"]
                ) if is_nok else None,
                run_batch_id=batch_id,
                insight_status=InsightStatus.OPEN if is_nok else InsightStatus.RESOLVED,
            ))
        elif cvc_val > 70:
            # Low power: deadline 2030
            is_unknown = idx % 4 == 0
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="bacs", rule_id="BACS_LOW_DEADLINE",
                status="UNKNOWN" if is_unknown else "OK",
                severity="high" if is_unknown else "low",
                deadline=date(2030, 1, 1),
                evidence="CVC 70-290 kW, echeance 01/01/2030" + (
                    " — donnees CVC incompletes" if is_unknown else " — conforme"),
                run_batch_id=batch_id,
                insight_status=InsightStatus.OPEN if is_unknown else InsightStatus.RESOLVED,
            ))
        else:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="bacs", rule_id="BACS_POWER",
                status="OUT_OF_SCOPE", severity="low",
                evidence="CVC <= 70 kW, non assujetti BACS",
                run_batch_id=batch_id,
            ))

        # ---- DECRET TERTIAIRE ----
        tertiaire = getattr(site, "tertiaire_area_m2", None) or 0
        if tertiaire >= 1000:
            # 18 sites assujettis: 6 OK, 6 UNKNOWN (a faire), 6 NOK (en retard)
            bucket = idx % 3  # cycles through 0,1,2
            if bucket == 0:
                # OK: data complete
                findings.append(ComplianceFinding(
                    site_id=site.id, regulation="decret_tertiaire_operat",
                    rule_id="DT_OPERAT", status="OK", severity="low",
                    deadline=date(2030, 12, 31),
                    evidence="Declaration OPERAT soumise et validee",
                    run_batch_id=batch_id,
                    insight_status=InsightStatus.RESOLVED,
                ))
            elif bucket == 1:
                # UNKNOWN: partial data (a faire)
                findings.append(ComplianceFinding(
                    site_id=site.id, regulation="decret_tertiaire_operat",
                    rule_id="DT_ENERGY_DATA", status="UNKNOWN", severity="medium",
                    deadline=date(2030, 12, 31),
                    evidence="Donnees de consommation partielles, declaration OPERAT incomplete",
                    recommended_actions_json=json.dumps(
                        ["Completer les donnees energetiques annuelles",
                         "Soumettre la declaration sur la plateforme OPERAT"]
                    ),
                    run_batch_id=batch_id,
                    insight_status=InsightStatus.OPEN,
                ))
            else:
                # NOK: en retard
                findings.append(ComplianceFinding(
                    site_id=site.id, regulation="decret_tertiaire_operat",
                    rule_id="DT_TRAJECTORY_2030", status="NOK", severity="high",
                    deadline=date(2026, 9, 30),
                    evidence="Trajectoire -40% non atteinte, echeance proche",
                    recommended_actions_json=json.dumps(
                        ["Mettre en place un plan de sobriete energetique",
                         "Auditer les postes de consommation prioritaires",
                         "Declarer les actions sur OPERAT avant la prochaine echeance"]
                    ),
                    run_batch_id=batch_id,
                    insight_status=InsightStatus.ACK,
                ))
        else:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="decret_tertiaire_operat",
                rule_id="DT_SCOPE", status="OUT_OF_SCOPE", severity="low",
                evidence=f"Surface tertiaire < 1000 m2 ({tertiaire:.0f} m2), non assujetti",
                run_batch_id=batch_id,
            ))

        # ---- APER ----
        parking = getattr(site, "parking_area_m2", None) or 0
        roof = getattr(site, "roof_area_m2", None) or 0
        if parking >= 1500:
            # 4 OK (PV installed), rest UNKNOWN (a evaluer)
            is_ok = idx < 4
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="aper", rule_id="APER_PARKING",
                status="OK" if is_ok else "UNKNOWN",
                severity="low" if is_ok else "high",
                deadline=date(2026, 7, 1),
                evidence="Parking > 1500 m2" + (
                    " — ombriere PV installee" if is_ok
                    else " — installation ombriere PV a evaluer"),
                recommended_actions_json=None if is_ok else json.dumps(
                    ["Realiser une etude de faisabilite ombriere PV",
                     "Obtenir devis aupres de 3 installateurs agrees"]
                ),
                run_batch_id=batch_id,
                insight_status=InsightStatus.RESOLVED if is_ok else InsightStatus.OPEN,
            ))
        elif roof >= 500:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="aper", rule_id="APER_TOITURE",
                status="UNKNOWN", severity="medium",
                evidence=f"Toiture {roof:.0f} m2 > 500 m2, potentiel ENR a evaluer",
                recommended_actions_json=json.dumps(
                    ["Evaluer le potentiel solaire de la toiture"]
                ),
                run_batch_id=batch_id,
                insight_status=InsightStatus.OPEN,
            ))
        else:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="aper", rule_id="APER_PARKING",
                status="OUT_OF_SCOPE", severity="low",
                evidence="Parking < 1500 m2 et toiture < 500 m2, non assujetti APER",
                run_batch_id=batch_id,
            ))

    return findings


# ---------------------------------------------------------------------------
# Main seed function
# ---------------------------------------------------------------------------

def seed_casino_36(db: Session):
    """
    Create Groupe Casino (36 sites) + compliance findings + superuser.
    Returns dict with created counts.
    """
    # 1. Organisation
    org = Organisation(nom="Groupe Casino", type_client="retail", actif=True, siren="554008671")
    db.add(org)
    db.flush()

    # 2. Entite Juridique
    ej = EntiteJuridique(
        organisation_id=org.id, nom="Casino France SAS",
        siren="554008671", siret="55400867100014",
        naf_code="4711F", region_code="ARA",
    )
    db.add(ej)
    db.flush()

    # 3. Portefeuilles (3)
    pf_hyper = Portefeuille(entite_juridique_id=ej.id, nom="Hypermarches",
                            description="12 hypermarches Casino France")
    pf_proxi = Portefeuille(entite_juridique_id=ej.id, nom="Proximite",
                            description="12 magasins Casino Proximite")
    pf_logi = Portefeuille(entite_juridique_id=ej.id, nom="Logistique",
                           description="12 entrepots et plateformes logistiques")
    db.add_all([pf_hyper, pf_proxi, pf_logi])
    db.flush()
    pf_ids = [pf_hyper.id, pf_proxi.id, pf_logi.id]

    # 4. Sites (36)
    site_defs = _build_sites()
    created_sites = []
    for i, s in enumerate(site_defs):
        pf_id = pf_ids[i // 12]  # 0-11 → hyper, 12-23 → proxi, 24-35 → logi
        cvc_kw = s.pop("cvc_power_kw")
        annual_kwh = s.pop("annual_kwh_total")
        site = Site(
            portefeuille_id=pf_id, actif=True,
            annual_kwh_total=annual_kwh,
            data_source="demo",
            **s,
        )
        db.add(site)
        db.flush()
        # Store cvc for findings generation
        site.cvc_power_kw = cvc_kw
        created_sites.append(site)

        # Compteur (electricity for all, gas for ~12 sites)
        db.add(Compteur(
            site_id=site.id, type=TypeCompteur.ELECTRICITE,
            numero_serie=f"CASINO-E-{site.id:03d}",
            puissance_souscrite_kw=random.randint(50, 500),
            meter_id=f"{random.randint(10000000000000, 99999999999999)}",
            energy_vector=EnergyVector.ELECTRICITY, actif=True,
        ))
        if i < 12:  # gas for hypermarches
            db.add(Compteur(
                site_id=site.id, type=TypeCompteur.GAZ,
                numero_serie=f"CASINO-G-{site.id:03d}",
                meter_id=f"GRD{random.randint(100000000, 999999999)}",
                energy_vector=EnergyVector.GAS, actif=True,
            ))

    db.flush()

    # 5. OPERAT status for tertiaire sites
    for i, site in enumerate(created_sites):
        if site.tertiaire_area_m2 and site.tertiaire_area_m2 >= 1000:
            bucket = i % 3
            if bucket == 0:
                site.operat_status = OperatStatus.SUBMITTED
            elif bucket == 1:
                site.operat_status = OperatStatus.IN_PROGRESS
            else:
                site.operat_status = OperatStatus.NOT_STARTED
    db.flush()

    # 6. Compliance run batch
    batch = ComplianceRunBatch(
        org_id=org.id, triggered_by="seed",
        started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
        sites_count=36, findings_count=0, nok_count=0, unknown_count=0,
    )
    db.add(batch)
    db.flush()

    # 7. Compliance findings (BACS, Tertiaire, APER)
    findings = _generate_findings(db, created_sites, batch.id)
    db.add_all(findings)
    db.flush()

    # Update batch counts
    batch.findings_count = len(findings)
    batch.nok_count = sum(1 for f in findings if f.status == "NOK")
    batch.unknown_count = sum(1 for f in findings if f.status == "UNKNOWN")

    # 8. Superuser
    try:
        from models.iam import User, UserOrgRole, UserScope
        from models.enums import UserRole, ScopeLevel
        from services.iam_service import hash_password

        user = User(
            email="promeos@promeos.io",
            hashed_password=hash_password("promeos2024"),
            nom="Admin", prenom="Promeos", actif=True,
        )
        db.add(user)
        db.flush()

        uor = UserOrgRole(user_id=user.id, org_id=org.id, role=UserRole.DG_OWNER)
        db.add(uor)
        db.flush()

        scope = UserScope(user_org_role_id=uor.id, scope_level=ScopeLevel.ORG, scope_id=org.id)
        db.add(scope)
    except Exception:
        pass  # IAM models may not be available in test context

    db.commit()

    return {
        "org_id": org.id,
        "org_nom": org.nom,
        "sites_count": len(created_sites),
        "findings_count": len(findings),
        "nok_count": batch.nok_count,
        "unknown_count": batch.unknown_count,
        "batch_id": batch.id,
    }


if __name__ == "__main__":
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import SessionLocal
    db = SessionLocal()
    result = seed_casino_36(db)
    print(f"Seed complete: {result}")
