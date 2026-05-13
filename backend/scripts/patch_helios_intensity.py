"""PROMEOS — Patch DB Phase 3.6 Vague DD : enrichit sites HELIOS pour modes REG/PERF.

Le seed HELIOS S de base ne renseigne pas intensity_kwh_m2_tertiaire +
annee_reference_operat, ce qui force le dispatcher Synthèse Stratégique
en mode DATA_INSUFFICIENT (ratio unknown > 30 %).

Ce script complète :
  - intensity_kwh_m2_tertiaire (calculé via annual_kwh_total / tertiaire_area_m2
    ou défaut sectoriel)
  - annee_reference_operat (2015 par défaut, médian de la fenêtre DT)
  - cvc_power_kw sur les bâtiments (défaut 80 kW pour bureau)
  - effectif_total + chiffre_affaires_eur sur Organisation HELIOS

Cible : HELIOS demo (is_demo=True, organisation_id=1) → réactive le mode
REGULATORY_DRIVEN dans la démo.

Usage : python -m scripts.patch_helios_intensity
"""

from __future__ import annotations

from database import SessionLocal
from models.batiment import Batiment
from models.organisation import Organisation
from models.site import Site


def run():
    db = SessionLocal()
    try:
        # 1. Organisation HELIOS — effectif + CA pour SMÉ APPLICABLE
        org = db.query(Organisation).filter(Organisation.id == 1).first()
        if org:
            if org.effectif_total is None:
                org.effectif_total = 380
            if org.chiffre_affaires_eur is None:
                org.chiffre_affaires_eur = 80_000_000.0
            print(
                f"✓ Organisation #{org.id} {org.nom} : effectif={org.effectif_total}, CA={org.chiffre_affaires_eur / 1e6:.0f} M€"
            )

        # 2. Sites HELIOS — intensity + annee_reference_operat + usage_principal
        sites = db.query(Site).all()
        patched_sites = 0
        for s in sites:
            if s.tertiaire_area_m2 is None:
                # Si tertiaire_area_m2 n'est pas renseigné, on prend surface_m2 par défaut
                s.tertiaire_area_m2 = s.surface_m2 or 1500
            if s.intensity_kwh_m2_tertiaire is None:
                # Calcul si annual_kwh_total dispo, sinon défaut 180 (médian bureaux)
                if s.annual_kwh_total and s.tertiaire_area_m2:
                    s.intensity_kwh_m2_tertiaire = round(float(s.annual_kwh_total) / float(s.tertiaire_area_m2), 1)
                else:
                    s.intensity_kwh_m2_tertiaire = 180.0
            if s.annee_reference_operat is None:
                s.annee_reference_operat = 2015
            if s.usage_principal is None:
                s.usage_principal = "BUREAUX"
            patched_sites += 1
            print(
                f"✓ Site #{s.id} {s.nom} : "
                f"intensity={s.intensity_kwh_m2_tertiaire:.0f} kWh/m², "
                f"annee_ref={s.annee_reference_operat}, usage={s.usage_principal}"
            )

        # 3. Bâtiments HELIOS — cvc_power_kw
        batiments = db.query(Batiment).all()
        patched_bats = 0
        for b in batiments:
            if b.cvc_power_kw is None:
                # Défaut 80 kW pour bureau tertiaire (au-dessus du seuil Tier 2 = 70 kW)
                b.cvc_power_kw = 80.0
            patched_bats += 1

        db.commit()
        print(f"\n✅ Patch terminé : {patched_sites} sites + {patched_bats} bâtiments + 1 organisation patchés.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
