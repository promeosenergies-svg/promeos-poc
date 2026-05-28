"""Tests Conformite S1 — TRI par typologie modulation.

S1 #324 Chantier 3 (2026-05-27) — verifie que `simulate_modulation` calcule
les TRI par typologie conformement Article 11.I de l'arrete 10/04/2020.

Couverture :
  T1. Portefeuille multi-typologie -> 3 TRI distincts + decision composite.
  T2. Chaque entree tri_par_typologie a label_fr + source + source_url.
  T3. disproportion_globale True si une typologie depasse son seuil.
  T4. Actions sans typologie -> warning + pas dans decomposition.
  T5. Typologie inconnue -> warning + fallback UNKNOWN.
"""

from __future__ import annotations

import os
import sys
import uuid

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture
def fresh_efa_with_ref():
    """Cree une EFA avec annee de reference (pour le test modulation)."""
    from database import SessionLocal
    from models.tertiaire import TertiaireEfa, TertiaireEfaConsumption

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:8]
    efa = TertiaireEfa(
        nom=f"EFA Modulation Test {suffix}",
        org_id=1,
        reference_year=2019,
        reference_year_kwh=500000,
    )
    try:
        db.add(efa)
        db.flush()
        conso_ref = TertiaireEfaConsumption(
            efa_id=efa.id,
            year=2019,
            kwh_total=500000,
            is_reference=True,
            source="factures",
            reliability="high",
        )
        conso_now = TertiaireEfaConsumption(
            efa_id=efa.id,
            year=2024,
            kwh_total=460000,
            is_reference=False,
            source="factures",
            reliability="high",
        )
        db.add(conso_ref)
        db.add(conso_now)
        db.commit()
        yield (db, efa.id)
    finally:
        try:
            db.query(TertiaireEfaConsumption).filter_by(efa_id=efa.id).delete()
            db.delete(efa)
            db.commit()
        except Exception:
            db.rollback()
        db.close()


def test_t1_multi_typology_yields_distinct_tris(fresh_efa_with_ref):
    """3 actions, 3 typologies, 3 TRI distincts dans la decomposition."""
    from services.tertiaire_modulation_service import simulate_modulation

    db, efa_id = fresh_efa_with_ref
    contraintes = [
        {
            "type": "economique",
            "description": "Travaux structurels enveloppe (TRI > 30 ans toleres)",
            "actions": [
                {
                    "label": "ITE facade",
                    "cout_eur": 200000,
                    "economie_annuelle_kwh": 80000,
                    "economie_annuelle_eur": 8000,
                    "duree_vie_ans": 35,
                    "typologie": "STRUCTURAL_ENVELOPE",
                },
                {
                    "label": "Remplacement chaudiere CVC",
                    "cout_eur": 60000,
                    "economie_annuelle_kwh": 40000,
                    "economie_annuelle_eur": 4000,
                    "duree_vie_ans": 18,
                    "typologie": "ENERGY_EQUIPMENT",
                },
                {
                    "label": "GTB BACS pilotage",
                    "cout_eur": 50000,
                    "economie_annuelle_kwh": 30000,
                    "economie_annuelle_eur": 3000,
                    "duree_vie_ans": 12,
                    "typologie": "OPTIMIZATION_SYSTEM",
                },
            ],
        }
    ]
    result = simulate_modulation(db, efa_id, contraintes)
    assert len(result.tri_par_typologie) == 3, (
        f"Attendu 3 typologies distinctes, got {len(result.tri_par_typologie)} : {result.tri_par_typologie}"
    )
    typos = {entry["typologie"] for entry in result.tri_par_typologie}
    assert typos == {"STRUCTURAL_ENVELOPE", "ENERGY_EQUIPMENT", "OPTIMIZATION_SYSTEM"}


def test_t2_each_typology_entry_has_source_and_label(fresh_efa_with_ref):
    from services.tertiaire_modulation_service import simulate_modulation

    db, efa_id = fresh_efa_with_ref
    contraintes = [
        {
            "type": "economique",
            "description": "Test",
            "actions": [
                {
                    "label": "Test CVC",
                    "cout_eur": 30000,
                    "economie_annuelle_kwh": 20000,
                    "economie_annuelle_eur": 2000,
                    "duree_vie_ans": 12,
                    "typologie": "ENERGY_EQUIPMENT",
                },
            ],
        }
    ]
    result = simulate_modulation(db, efa_id, contraintes)
    entry = result.tri_par_typologie[0]
    assert (
        entry["label_fr"] and "équipements" in entry["label_fr"].lower() or "equipements" in entry["label_fr"].lower()
    )
    assert "Article 11.I" in entry["source"]
    assert entry["source_url"].startswith("https://www.legifrance.gouv.fr/")
    assert entry["seuil_disproportion_ans"] == 15
    assert entry["tri_ans"] is not None


def test_t3_disproportion_globale_when_typology_exceeds_threshold(fresh_efa_with_ref):
    """OPTIMIZATION_SYSTEM avec TRI 12 ans > 10 ans -> disproportion_globale=True."""
    from services.tertiaire_modulation_service import simulate_modulation

    db, efa_id = fresh_efa_with_ref
    contraintes = [
        {
            "type": "economique",
            "description": "GTB peu rentable",
            "actions": [
                {
                    "label": "GTB lente",
                    "cout_eur": 24000,
                    "economie_annuelle_kwh": 5000,
                    "economie_annuelle_eur": 2000,  # TRI = 12 ans
                    "duree_vie_ans": 15,
                    "typologie": "OPTIMIZATION_SYSTEM",
                },
            ],
        }
    ]
    result = simulate_modulation(db, efa_id, contraintes)
    assert result.disproportion_globale is True
    assert (
        "OPTIMIZATION_SYSTEM" in result.disproportion_explication
        or "optimisation" in result.disproportion_explication.lower()
    )
    assert "12" in result.disproportion_explication and "10" in result.disproportion_explication


def test_t4_action_without_typology_warns(fresh_efa_with_ref):
    """Action sans typologie -> warning + pas dans decomposition typologique."""
    from services.tertiaire_modulation_service import simulate_modulation

    db, efa_id = fresh_efa_with_ref
    contraintes = [
        {
            "type": "economique",
            "description": "Test sans typologie",
            "actions": [
                {
                    "label": "Action mystere",
                    "cout_eur": 10000,
                    "economie_annuelle_kwh": 5000,
                    "economie_annuelle_eur": 500,
                    "duree_vie_ans": 10,
                    # typologie absente -> UNKNOWN
                },
            ],
        }
    ]
    result = simulate_modulation(db, efa_id, contraintes)
    assert len(result.tri_par_typologie) == 0, "Action UNKNOWN ne doit pas figurer dans la decomposition typologique."
    # Warning explicite + decision non calculable.
    has_warning = any("typologie" in w.lower() for w in result.warnings)
    assert has_warning, f"Warning typologie attendu, got warnings: {result.warnings}"
    assert "non calculable" in result.disproportion_explication.lower()


def test_t5_unknown_typology_falls_back_to_unknown(fresh_efa_with_ref):
    """Typologie non reconnue -> fallback UNKNOWN + warning."""
    from services.tertiaire_modulation_service import simulate_modulation

    db, efa_id = fresh_efa_with_ref
    contraintes = [
        {
            "type": "economique",
            "description": "Test typologie invalide",
            "actions": [
                {
                    "label": "Action fake typo",
                    "cout_eur": 10000,
                    "economie_annuelle_kwh": 5000,
                    "economie_annuelle_eur": 500,
                    "duree_vie_ans": 10,
                    "typologie": "MAGIC_TYPOLOGY",
                },
            ],
        }
    ]
    result = simulate_modulation(db, efa_id, contraintes)
    # Pas dans la decomposition (UNKNOWN -> rien).
    assert len(result.tri_par_typologie) == 0
    # Warning explicite citant les typologies valides.
    has_warning = any("MAGIC_TYPOLOGY" in w or "inconnue" in w.lower() for w in result.warnings)
    assert has_warning, f"Warning typologie inconnue attendu, got warnings: {result.warnings}"
