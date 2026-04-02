"""Tests pour energy_signature_service — régression E = a × DJU + b."""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


def test_benchmark_bureau():
    """Bureau 3500 m² → baseload 700, thermo 52.5."""
    from services.energy_signature_service import _get_signature_benchmark

    bench = _get_signature_benchmark("bureau", 3500)
    assert bench["baseload_expected"] == 700.0  # 200 × 3.5
    assert bench["thermo_expected"] == 52.5  # 15 × 3.5


def test_benchmark_hotel():
    """Hôtel 2000 m² → baseload 800, thermo 40."""
    from services.energy_signature_service import _get_signature_benchmark

    bench = _get_signature_benchmark("hotel", 2000)
    assert bench["baseload_expected"] == 800.0  # 400 × 2
    assert bench["thermo_expected"] == 40.0  # 20 × 2


def test_benchmark_unknown_archetype():
    """Archétype inconnu → fallback bureau."""
    from services.energy_signature_service import _get_signature_benchmark

    bench = _get_signature_benchmark("inconnu", 1000)
    assert bench["baseload_expected"] == 200.0
    assert bench["thermo_expected"] == 15.0


def test_linear_regression_perfect():
    """Régression parfaite y = 2x + 100 → a=2, b=100, R²=1."""
    from services.energy_signature_service import _linear_regression

    x = [0, 5, 10, 15, 20]
    y = [100, 110, 120, 130, 140]  # y = 2x + 100
    a, b, r2 = _linear_regression(x, y)
    assert abs(a - 2.0) < 0.01
    assert abs(b - 100.0) < 0.01
    assert r2 > 0.99


def test_linear_regression_noisy():
    """Régression avec bruit → R² < 1 mais positif."""
    from services.energy_signature_service import _linear_regression

    x = [0, 5, 10, 15, 20]
    y = [102, 108, 122, 128, 142]  # ~y = 2x + 100 avec bruit
    a, b, r2 = _linear_regression(x, y)
    assert a > 0  # pente positive
    assert b > 0  # ordonnée positive
    assert 0 < r2 <= 1.0


def test_compute_signature_with_db():
    """Test intégration avec la vraie DB (DEMO_MODE)."""
    from database.connection import SessionLocal
    from models.site import Site
    from services.energy_signature_service import compute_energy_signature

    db = SessionLocal()
    try:
        site = db.query(Site).first()
        if not site:
            return  # skip si pas de données

        result = compute_energy_signature(db, site.id, months=12)
        assert result is not None

        if "error" not in result:
            sig = result["signature"]
            assert sig["baseload_kwh_day"] >= 0
            assert sig["r_squared"] >= 0
            assert "scatter_data" in result
            assert "regression_line" in result
            assert "benchmark" in result
            assert "savings_potential" in result
    finally:
        db.close()
