"""M2-6.B.pdf — Tests du helper format_euros_full pour PDF COMEX.

Pin le format Q23=A strict FR : `'47 500 €'` (NBSP U+00A0), `'—'` pour NULL,
`'0 €'` pour zéro valide.
"""

from utils.format_euros import DASH, NBSP, format_euros_full


class TestFormatEurosFull:
    def test_simple_amount(self):
        assert format_euros_full(3200) == f"3{NBSP}200{NBSP}€"

    def test_helios_total_cardinal(self):
        """Cardinal M2-6.B : le total HELIOS 47 500 € doit rendre exactement."""
        assert format_euros_full(47500) == f"47{NBSP}500{NBSP}€"

    def test_large_amount(self):
        assert format_euros_full(1234567) == f"1{NBSP}234{NBSP}567{NBSP}€"

    def test_under_thousand(self):
        assert format_euros_full(500) == f"500{NBSP}€"

    def test_zero_is_valid(self):
        """0 = mesure valide (sémantique CFO money.js), ≠ NULL."""
        assert format_euros_full(0) == f"0{NBSP}€"

    def test_null_returns_dash(self):
        assert format_euros_full(None) == DASH

    def test_decimal_rounded_up(self):
        # 3200.50 → ROUND_HALF_UP → 3201
        assert format_euros_full(3200.50) == f"3{NBSP}201{NBSP}€"

    def test_decimal_rounded_down(self):
        assert format_euros_full(3200.40) == f"3{NBSP}200{NBSP}€"

    def test_string_numeric_input(self):
        """Accepte string parseable (cas Numeric SQLAlchemy → str()) ."""
        assert format_euros_full("47500.00") == f"47{NBSP}500{NBSP}€"

    def test_negative_amount(self):
        assert format_euros_full(-1500) == f"-1{NBSP}500{NBSP}€"

    def test_invalid_string_returns_dash(self):
        assert format_euros_full("not-a-number") == DASH

    def test_nan_returns_dash(self):
        assert format_euros_full(float("nan")) == DASH
