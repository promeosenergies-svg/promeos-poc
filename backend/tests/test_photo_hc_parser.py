"""
Tests du parser PHOTO HC Enedis + service hc_reprog.

Couverture :
  1. Parser CSV Phase 1 (non saisonnalisé)
  2. Parser CSV Phase 2 (saisonnalisé, colonnes SH/SB)
  3. Détection type PHOTO (M-6, M-2, CR-M)
  4. Gestion erreurs (CSV vide, PRM invalide, colonne manquante)
  5. Service hc_reprog: mapping code HC → fenêtres
  6. Intégration ParsedPhotoRow.is_seasonal
"""

import pytest

from data_ingestion.enedis.parsers.photo_hc import (
    parse_photo_hc,
    PhotoType,
    PhotoParseError,
)
from services.hc_reprog_service import (
    HC_CODE_WINDOWS,
    _code_to_windows,
)


# ═══════════════════════════════════════════════════════════════════════════════
# 1. PARSER CSV PHASE 1
# ═══════════════════════════════════════════════════════════════════════════════


CSV_PHASE1 = """\
PRM;DATE_PREVUE;CODE_HC_ACTUEL;LIB_HC_ACTUEL;CODE_HC_CIBLE;LIB_HC_CIBLE;STATUT
01234567890123;2026-11-15;HC01;22h-06h;HC02;23h-07h;
98765432109876;2026-12-01;HC01;22h-06h;HC03;00h-08h;
"""


class TestParserPhase1:
    def test_parse_basic(self):
        result = parse_photo_hc(CSV_PHASE1, "PHOTO_M6_202605.csv")
        assert result.total_prms == 2
        assert result.is_phase2 is False
        assert result.photo_type == PhotoType.M6

    def test_row_fields(self):
        result = parse_photo_hc(CSV_PHASE1)
        row = result.rows[0]
        assert row.prm == "01234567890123"
        assert row.date_prevue == "2026-11-15"
        assert row.code_hc_actuel == "HC01"
        assert row.code_hc_cible == "HC02"
        assert row.is_seasonal is False

    def test_prm_list(self):
        result = parse_photo_hc(CSV_PHASE1)
        assert result.prm_list == ["01234567890123", "98765432109876"]


# ═══════════════════════════════════════════════════════════════════════════════
# 2. PARSER CSV PHASE 2 (saisonnalisé)
# ═══════════════════════════════════════════════════════════════════════════════


CSV_PHASE2 = """\
PRM;DATE_PREVUE;CODE_HC_ACTUEL;LIB_HC_ACTUEL;CODE_HC_CIBLE_SH;LIB_HC_CIBLE_SH;CODE_HC_CIBLE_SB;LIB_HC_CIBLE_SB;STATUT
01234567890123;2027-01-15;HC01;22h-06h;HCH01;23h-07h hiver;HCB01;01h-06h+12h-15h été;
"""


class TestParserPhase2:
    def test_parse_seasonal(self):
        result = parse_photo_hc(CSV_PHASE2, "PHOTO_M6_Phase2.csv")
        assert result.total_prms == 1
        assert result.is_phase2 is True

    def test_seasonal_row(self):
        result = parse_photo_hc(CSV_PHASE2)
        row = result.rows[0]
        assert row.is_seasonal is True
        assert row.code_hc_cible_sh == "HCH01"
        assert row.code_hc_cible_sb == "HCB01"
        assert row.libelle_hc_cible_sh == "23h-07h hiver"
        assert row.libelle_hc_cible_sb == "01h-06h+12h-15h été"


# ═══════════════════════════════════════════════════════════════════════════════
# 3. DÉTECTION TYPE PHOTO
# ═══════════════════════════════════════════════════════════════════════════════


CSV_CRM = """\
PRM;DATE_PREVUE;DATE_EFFECTIVE;CODE_HC_ACTUEL;LIB_HC_ACTUEL;CODE_HC_CIBLE;LIB_HC_CIBLE;STATUT
01234567890123;2026-11-15;2026-11-20;HC01;22h-06h;HC02;23h-07h;TRAITE
98765432109876;2026-12-01;;HC01;22h-06h;HC03;00h-08h;ABANDON
"""


class TestPhotoTypeDetection:
    def test_m6_from_filename(self):
        result = parse_photo_hc(CSV_PHASE1, "PHOTO_M6_202605.csv")
        assert result.photo_type == PhotoType.M6

    def test_m2_from_filename(self):
        result = parse_photo_hc(CSV_PHASE1, "PHOTO_M2_202609.csv")
        assert result.photo_type == PhotoType.M2

    def test_crm_from_columns(self):
        result = parse_photo_hc(CSV_CRM, "PHOTO_CRM_202611.csv")
        assert result.photo_type == PhotoType.CRM

    def test_crm_from_date_effective_column(self):
        """Détection CR-M via colonne date_effective même sans 'cr' dans le nom"""
        result = parse_photo_hc(CSV_CRM, "photo_202611.csv")
        assert result.photo_type == PhotoType.CRM

    def test_crm_statut_field(self):
        result = parse_photo_hc(CSV_CRM)
        assert result.rows[0].statut == "TRAITE"
        assert result.rows[1].statut == "ABANDON"


# ═══════════════════════════════════════════════════════════════════════════════
# 4. GESTION ERREURS
# ═══════════════════════════════════════════════════════════════════════════════


class TestErrors:
    def test_empty_csv(self):
        with pytest.raises(PhotoParseError, match="Empty CSV"):
            parse_photo_hc("")

    def test_missing_prm_column(self):
        with pytest.raises(PhotoParseError, match="Missing PRM"):
            parse_photo_hc("CODE;DATE\n123;2026-01-01\n")

    def test_invalid_prm_skipped(self):
        csv = "PRM;DATE_PREVUE\nINVALID;2026-01-01\n01234567890123;2026-01-01\n"
        result = parse_photo_hc(csv)
        assert result.total_prms == 1
        assert result.rows[0].prm == "01234567890123"

    def test_short_prm_skipped(self):
        csv = "PRM;DATE_PREVUE\n12345;2026-01-01\n01234567890123;2026-01-01\n"
        result = parse_photo_hc(csv)
        assert result.total_prms == 1

    def test_empty_rows_skipped(self):
        csv = "PRM;DATE_PREVUE\n\n01234567890123;2026-01-01\n\n"
        result = parse_photo_hc(csv)
        assert result.total_prms == 1

    def test_bom_handling(self):
        csv_bytes = b"\xef\xbb\xbfPRM;DATE_PREVUE\n01234567890123;2026-01-01\n"
        result = parse_photo_hc(csv_bytes)
        assert result.total_prms == 1

    def test_alias_headers(self):
        """Headers alias (id_prm, hc_cible, resultat) sont reconnus."""
        csv = "ID_PRM;DATE_REPROG_PREVUE;HC_ACTUEL;HC_CIBLE;RESULTAT\n01234567890123;2026-01-01;HC01;HC02;TRAITE\n"
        result = parse_photo_hc(csv)
        assert result.total_prms == 1
        assert result.rows[0].code_hc_actuel == "HC01"
        assert result.rows[0].code_hc_cible == "HC02"
        assert result.rows[0].statut == "TRAITE"


# ═══════════════════════════════════════════════════════════════════════════════
# 5. MAPPING CODES HC → FENÊTRES
# ═══════════════════════════════════════════════════════════════════════════════


class TestHcCodeWindows:
    def test_hc01_legacy(self):
        """HC01 = 22h-06h (Phase 1)"""
        windows = _code_to_windows("HC01")
        assert windows is not None
        assert len(windows) == 1
        assert windows[0]["start"] == "22:00"
        assert windows[0]["end"] == "06:00"

    def test_hc02_legacy(self):
        """HC02 = 23h-07h (Phase 1)"""
        windows = _code_to_windows("HC02")
        assert windows[0]["start"] == "23:00"
        assert windows[0]["end"] == "07:00"

    def test_hch01_winter(self):
        """HCH01 = 23h-07h hiver (Phase 2)"""
        windows = _code_to_windows("HCH01")
        assert windows[0]["period"] == "HCH"
        assert windows[0]["start"] == "23:00"

    def test_hcb01_summer(self):
        """HCB01 = 01h-06h + 12h-15h été (Phase 2, 2 fenêtres)"""
        windows = _code_to_windows("HCB01")
        assert len(windows) == 2
        assert windows[0]["start"] == "01:00"
        assert windows[0]["end"] == "06:00"
        assert windows[1]["start"] == "12:00"
        assert windows[1]["end"] == "15:00"

    def test_unknown_code(self):
        """Code inconnu → None"""
        assert _code_to_windows("ZZZZ") is None

    def test_none_code(self):
        assert _code_to_windows(None) is None

    def test_case_insensitive(self):
        """Codes case-insensitive"""
        assert _code_to_windows("hc01") is not None
        assert _code_to_windows("Hch01") is not None

    def test_all_codes_have_8h(self):
        """Chaque code HC fait exactement 8h de HC/jour (contrainte CRE)."""
        for code, windows in HC_CODE_WINDOWS.items():
            total_minutes = 0
            for w in windows:
                parts_start = w["start"].split(":")
                parts_end = w["end"].split(":")
                start = int(parts_start[0]) * 60 + int(parts_start[1])
                end = int(parts_end[0]) * 60 + int(parts_end[1])
                if end > start:
                    total_minutes += end - start
                else:
                    total_minutes += (24 * 60 - start) + end
            assert total_minutes == 8 * 60, f"{code}: {total_minutes} min au lieu de 480"
