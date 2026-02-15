"""
PROMEOS - Demo Seed: Compliance Generator
Creates compliance findings (BACS, Decret Tertiaire, APER),
obligations, and evidence records.
"""
import json
import random
from datetime import date, datetime

from models import (
    ComplianceRunBatch, ComplianceFinding, Obligation, Evidence,
    TypeObligation, StatutConformite, TypeEvidence, StatutEvidence,
    InsightStatus,
)


def generate_compliance(db, org, sites: list, rng: random.Random) -> dict:
    """
    Generate compliance findings, obligations, and evidence for all sites.
    Returns counts.
    """
    # Compliance run batch
    batch = ComplianceRunBatch(
        org_id=org.id, triggered_by="demo_seed",
        started_at=datetime.utcnow(), completed_at=datetime.utcnow(),
        sites_count=len(sites), findings_count=0, nok_count=0, unknown_count=0,
    )
    db.add(batch)
    db.flush()

    findings = []
    obligations_count = 0
    evidences_count = 0

    for idx, site in enumerate(sites):
        cvc_kw = 0
        if hasattr(site, '_cvc_kw'):
            cvc_kw = site._cvc_kw
        elif site.batiments:
            for b in site.batiments:
                cvc_kw += (b.cvc_power_kw or 0)

        tertiaire = site.tertiaire_area_m2 or 0
        parking = site.parking_area_m2 or 0
        roof = site.roof_area_m2 or 0

        # ---- BACS ----
        if cvc_kw > 290:
            is_nok = idx % 5 < 2  # ~40% NOK
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
                run_batch_id=batch.id,
                insight_status=InsightStatus.OPEN if is_nok else InsightStatus.RESOLVED,
            ))
        elif cvc_kw > 70:
            is_unknown = idx % 4 == 0
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="bacs", rule_id="BACS_LOW_DEADLINE",
                status="UNKNOWN" if is_unknown else "OK",
                severity="high" if is_unknown else "low",
                deadline=date(2030, 1, 1),
                evidence="CVC 70-290 kW" + (
                    " — donnees CVC incompletes" if is_unknown else " — conforme"),
                run_batch_id=batch.id,
                insight_status=InsightStatus.OPEN if is_unknown else InsightStatus.RESOLVED,
            ))
        else:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="bacs", rule_id="BACS_POWER",
                status="OUT_OF_SCOPE", severity="low",
                evidence="CVC <= 70 kW, non assujetti BACS",
                run_batch_id=batch.id,
            ))

        # ---- DECRET TERTIAIRE ----
        if tertiaire >= 1000:
            bucket = idx % 3
            if bucket == 0:
                findings.append(ComplianceFinding(
                    site_id=site.id, regulation="decret_tertiaire_operat",
                    rule_id="DT_OPERAT", status="OK", severity="low",
                    deadline=date(2030, 12, 31),
                    evidence="Declaration OPERAT soumise et validee",
                    run_batch_id=batch.id, insight_status=InsightStatus.RESOLVED,
                ))
            elif bucket == 1:
                findings.append(ComplianceFinding(
                    site_id=site.id, regulation="decret_tertiaire_operat",
                    rule_id="DT_ENERGY_DATA", status="UNKNOWN", severity="medium",
                    deadline=date(2030, 12, 31),
                    evidence="Donnees de consommation partielles, declaration incomplete",
                    recommended_actions_json=json.dumps([
                        "Completer les donnees energetiques annuelles",
                        "Soumettre la declaration sur OPERAT"
                    ]),
                    run_batch_id=batch.id, insight_status=InsightStatus.OPEN,
                ))
            else:
                findings.append(ComplianceFinding(
                    site_id=site.id, regulation="decret_tertiaire_operat",
                    rule_id="DT_TRAJECTORY_2030", status="NOK", severity="high",
                    deadline=date(2026, 9, 30),
                    evidence="Trajectoire -40% non atteinte, echeance proche",
                    recommended_actions_json=json.dumps([
                        "Mettre en place un plan de sobriete energetique",
                        "Auditer les postes de consommation prioritaires"
                    ]),
                    run_batch_id=batch.id, insight_status=InsightStatus.ACK,
                ))
        else:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="decret_tertiaire_operat",
                rule_id="DT_SCOPE", status="OUT_OF_SCOPE", severity="low",
                evidence=f"Surface tertiaire < 1000 m2 ({tertiaire:.0f} m2)",
                run_batch_id=batch.id,
            ))

        # ---- APER ----
        if parking >= 1500:
            is_ok = idx % 5 < 2
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="aper", rule_id="APER_PARKING",
                status="OK" if is_ok else "UNKNOWN",
                severity="low" if is_ok else "high",
                deadline=date(2026, 7, 1),
                evidence="Parking > 1500 m2" + (
                    " — ombriere PV installee" if is_ok
                    else " — installation ombriere PV a evaluer"),
                recommended_actions_json=None if is_ok else json.dumps([
                    "Realiser une etude de faisabilite ombriere PV"
                ]),
                run_batch_id=batch.id,
                insight_status=InsightStatus.RESOLVED if is_ok else InsightStatus.OPEN,
            ))
        elif roof >= 500:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="aper", rule_id="APER_TOITURE",
                status="UNKNOWN", severity="medium",
                evidence=f"Toiture {roof:.0f} m2, potentiel ENR a evaluer",
                recommended_actions_json=json.dumps([
                    "Evaluer le potentiel solaire de la toiture"
                ]),
                run_batch_id=batch.id, insight_status=InsightStatus.OPEN,
            ))
        else:
            findings.append(ComplianceFinding(
                site_id=site.id, regulation="aper", rule_id="APER_PARKING",
                status="OUT_OF_SCOPE", severity="low",
                evidence="Parking < 1500 m2 et toiture < 500 m2",
                run_batch_id=batch.id,
            ))

        # ---- Obligations ----
        if tertiaire >= 1000:
            db.add(Obligation(
                site_id=site.id, type=TypeObligation.DECRET_TERTIAIRE,
                description="Declaration annuelle OPERAT",
                echeance=date(2030, 12, 31),
                statut=StatutConformite.CONFORME if idx % 3 == 0 else StatutConformite.A_RISQUE,
                avancement_pct=rng.randint(20, 80),
            ))
            obligations_count += 1

        if cvc_kw > 70:
            db.add(Obligation(
                site_id=site.id, type=TypeObligation.BACS,
                description="Mise en conformite BACS",
                echeance=date(2025, 1, 1) if cvc_kw > 290 else date(2030, 1, 1),
                statut=StatutConformite.CONFORME if idx % 3 == 0 else StatutConformite.NON_CONFORME,
                avancement_pct=rng.randint(0, 100),
            ))
            obligations_count += 1

        # ---- Evidence (some sites have evidence, some missing) ----
        if idx % 3 == 0:
            db.add(Evidence(
                site_id=site.id, type=TypeEvidence.AUDIT,
                statut=StatutEvidence.VALIDE,
                note="Audit energetique realise en 2024",
            ))
            evidences_count += 1
        elif idx % 3 == 1:
            db.add(Evidence(
                site_id=site.id, type=TypeEvidence.ATTESTATION_BACS,
                statut=StatutEvidence.EN_ATTENTE,
                note="Attestation BACS en cours de validation",
            ))
            evidences_count += 1
        else:
            db.add(Evidence(
                site_id=site.id, type=TypeEvidence.DECLARATION,
                statut=StatutEvidence.MANQUANT,
                note="Declaration OPERAT manquante",
            ))
            evidences_count += 1

    db.add_all(findings)
    db.flush()

    # Update batch counts
    batch.findings_count = len(findings)
    batch.nok_count = sum(1 for f in findings if f.status == "NOK")
    batch.unknown_count = sum(1 for f in findings if f.status == "UNKNOWN")

    return {
        "findings_count": len(findings),
        "nok_count": batch.nok_count,
        "unknown_count": batch.unknown_count,
        "obligations_count": obligations_count,
        "evidences_count": evidences_count,
        "batch_id": batch.id,
    }
