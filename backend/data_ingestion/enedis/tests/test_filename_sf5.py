"""Tests for SF5 Enedis filename classification and metadata parsing."""

import pytest

from data_ingestion.enedis.decrypt import SKIP_FLUX_TYPES, classify_flux
from data_ingestion.enedis.enums import FluxType
from data_ingestion.enedis.filename import FilenameParseError, parse_enedis_filename


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("ENEDIS_R63_P_CdC_M053Q0D3_00001_20230918161101.zip", FluxType.R63),
        ("ENEDIS_R64_P_INDEX_M06IFF1Z_00001_20240627165441.zip", FluxType.R64),
        ("ENEDIS_C68_P_ITC_M05GIGM1_00001_20231204101954.zip", FluxType.C68),
        ("ENEDIS_R63A_R_CDC_M01ABCDE_GRD-F345_00001_20230918161101.zip", FluxType.R63A),
        ("ENEDIS_R63B_R_CDC_M01ABCDE_123456789_00001_20230918161101.zip", FluxType.R63B),
        ("ENEDIS_R64A_R_INDEX_M01ABCDE_GRD-F345_00001_20230918161101.zip", FluxType.R64A),
        ("ENEDIS_R64B_R_INDEX_M01ABCDE_GRD-F345_00001_20230918161101.zip", FluxType.R64B),
        ("ENEDIS_R65_P_FOO_M01ABCDE_00001_20230918161101.zip", FluxType.R65),
        ("ENEDIS_R66_P_FOO_M01ABCDE_00001_20230918161101.zip", FluxType.R66),
        ("ENEDIS_R66B_P_FOO_M01ABCDE_00001_20230918161101.zip", FluxType.R66B),
        ("ENEDIS_R67_P_FOO_M01ABCDE_00001_20230918161101.zip", FluxType.R67),
        ("ENEDIS_CR.M023_P_CR_M01ABCDE_00001_20230918161101.zip", FluxType.CR_M023),
        ("ENEDIS_CR-M023_P_CR_M01ABCDE_00001_20230918161101.zip", FluxType.CR_M023),
        ("CR.M023.zip", FluxType.CR_M023),
    ],
)
def test_classifies_supported_and_known_skipped_sf5_codes(filename, expected):
    assert classify_flux(filename) == expected


def test_known_unsupported_sf5_codes_are_skipped():
    for flux_type in (
        FluxType.R63A,
        FluxType.R63B,
        FluxType.R64A,
        FluxType.R64B,
        FluxType.R65,
        FluxType.R66,
        FluxType.R66B,
        FluxType.R67,
        FluxType.CR_M023,
    ):
        assert flux_type in SKIP_FLUX_TYPES
    assert FluxType.R63 not in SKIP_FLUX_TYPES
    assert FluxType.R64 not in SKIP_FLUX_TYPES
    assert FluxType.C68 not in SKIP_FLUX_TYPES


def test_r63a_and_r64b_are_not_normalized_to_punctual_families():
    assert classify_flux("ENEDIS_R63A_R_CDC_M01ABCDE_GRD-F345_00001_20230918161101.zip") == FluxType.R63A
    assert classify_flux("ENEDIS_R64B_R_INDEX_M01ABCDE_GRD-F345_00001_20230918161101.zip") == FluxType.R64B


def test_parse_m023_six_token_filename_preserves_raw_values():
    meta = parse_enedis_filename("Enedis_R63_P_CdC_M053Q0D3_00001_20230918161101.JSON")

    assert meta.original_name == "Enedis_R63_P_CdC_M053Q0D3_00001_20230918161101.JSON"
    assert meta.extension == "JSON"
    assert meta.code_flux == "R63"
    assert meta.flux_type == FluxType.R63
    assert meta.mode_publication == "P"
    assert meta.type_donnee == "CdC"
    assert meta.id_demande == "M053Q0D3"
    assert meta.num_sequence == "00001"
    assert meta.publication_horodatage == "20230918161101"
    assert meta.siren_publication is None
    assert meta.code_contrat_publication is None


def test_parse_rec_seven_token_filename_splits_non_siren_extra_identifier():
    meta = parse_enedis_filename("ENEDIS_R63A_R_CDC_M01ABCDE_GRD-F345_00002_20230918161101.zip")

    assert meta.flux_type == FluxType.R63A
    assert meta.code_contrat_publication == "GRD-F345"
    assert meta.siren_publication is None
    assert meta.num_sequence == "00002"


def test_parse_rec_seven_token_filename_splits_siren_extra_identifier():
    meta = parse_enedis_filename("ENEDIS_R64B_R_INDEX_M01ABCDE_123456789_00003_20230918161101.zip")

    assert meta.flux_type == FluxType.R64B
    assert meta.siren_publication == "123456789"
    assert meta.code_contrat_publication is None
    assert meta.num_sequence == "00003"


def test_invalid_supported_sf5_filename_shape_has_structured_error():
    with pytest.raises(FilenameParseError) as excinfo:
        parse_enedis_filename("ENEDIS_R63_P_CdC_ONLYFOUR.zip")

    assert excinfo.value.filename == "ENEDIS_R63_P_CdC_ONLYFOUR.zip"
    assert excinfo.value.code_flux == "R63"
    assert "expected" in excinfo.value.message


@pytest.mark.parametrize(
    "filename, expected",
    [
        ("ENEDIS_23X--130624--EE1_R4H_CDC_20260302.zip", FluxType.R4H),
        ("ENEDIS_23X--130624--EE1_R4M_CDC_20251203.zip", FluxType.R4M),
        ("ENEDIS_23X--130624--EE1_R4Q_CDC_20230519.zip", FluxType.R4Q),
        ("ENEDIS_R171_C_00000099895595_GRDF_23X.zip", FluxType.R171),
        ("ERDF_R50_23X--130624--EE1_GRD-F121.zip", FluxType.R50),
        ("ERDF_R151_23X--130624--EE1_GRD-F121.zip", FluxType.R151),
        ("ENEDIS_R172_30000550403414_192431565.zip", FluxType.R172),
        ("ENEDIS_X14_GRD-F121_00072.zip", FluxType.X14),
        ("Enedis_SGE_HDM_A08693PL.csv", FluxType.HDM),
    ],
)
def test_legacy_classification_regressions(filename, expected):
    assert classify_flux(filename) == expected
