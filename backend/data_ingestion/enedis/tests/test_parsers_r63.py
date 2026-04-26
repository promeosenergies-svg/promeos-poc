"""Tests for the R63 parser."""

import json

import pytest

from data_ingestion.enedis.parsers.r63 import R63ParseError, parse_r63_payload


def _r63_json(extra: dict | None = None) -> bytes:
    payload = {
        "header": {
            "siDemandeur": "SGE",
            "typeDestinataire": "SI",
            "idDestinataire": "GRD-F001",
            "codeFlux": "R63",
            "idDemande": "M053Q0D3",
            "modePublication": "P",
            "idCanalContact": "WEB",
            "format": "JSON",
        },
        "mesures": [
            {
                "idPrm": "30000000000001",
                "etapeMetier": "MESURE",
                "periode": {"dateDebut": "2026-01-01", "dateFin": "2026-01-02"},
                "modeCalcul": "BRUT",
                "grandeur": [
                    {
                        "grandeurMetier": "CONS",
                        "grandeurPhysique": "EA",
                        "unite": "Wh",
                        "points": [
                            {"d": "2026-01-01T00:00:00+01:00", "v": "10", "p": "PT5M", "n": "R", "tc": "A", "iv": 0},
                            {"d": "2026-01-01T00:05:00+01:00", "v": "11", "p": "PT5M", "n": "R", "ec": 1},
                        ],
                    },
                    {
                        "grandeurMetier": "CONS",
                        "grandeurPhysique": "ERI",
                        "unite": "varh",
                        "points": [{"d": "2026-01-01T00:00:00+01:00", "v": "2", "p": "PT5M", "n": "R"}],
                    },
                ],
            },
            {
                "idPrm": "30000000000002",
                "etapeMetier": "MESURE",
                "periode": {"dateDebut": "2026-01-01", "dateFin": "2026-01-02"},
                "modeCalcul": "BRUT",
                "grandeur": [
                    {
                        "grandeurMetier": "CONS",
                        "grandeurPhysique": "EA",
                        "unite": "Wh",
                        "points": [{"d": "2026-01-01T00:00:00+01:00", "v": "20", "p": "PT5M", "n": "R"}],
                    }
                ],
            },
        ],
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload).encode()


def test_r63_json_flattens_multiple_prms_grandeurs_and_points():
    parsed = parse_r63_payload(_r63_json(), "JSON", "payload.json")

    assert parsed.total_measures == 4
    assert parsed.header.raw["codeFlux"] == "R63"
    assert parsed.rows[0].point_id == "30000000000001"
    assert parsed.rows[0].grandeur_physique == "EA"
    assert parsed.rows[0].indice_vraisemblance == "0"
    assert parsed.rows[1].etat_complementaire == "1"
    assert parsed.rows[-1].point_id == "30000000000002"


def test_r63_json_unknown_fields_are_warnings():
    parsed = parse_r63_payload(_r63_json({"unexpectedTop": "kept as warning"}), "JSON", "payload.json")

    assert {"code": "unknown_json_field", "path": "$.unexpectedTop"} in parsed.header.raw["warnings"]


def test_r63_json_missing_structural_field_fails():
    payload = json.loads(_r63_json())
    del payload["mesures"][0]["idPrm"]

    with pytest.raises(R63ParseError, match="idPrm"):
        parse_r63_payload(json.dumps(payload).encode(), "JSON", "payload.json")


def test_r63_csv_maps_accented_and_optional_headers():
    csv_payload = (
        "Identifiant PRM;Date de début;Date de fin;Grandeur physique;Grandeur métier;Etape métier;Unité;"
        "Horodate;Valeur;Nature;Pas;Mode calcul;tc;Indice de vraisemblance;ec\n"
        "30000000000001;2026-01-01;2026-01-02;EA;CONS;MESURE;Wh;"
        "2026-01-01T00:00:00+01:00;10;R;PT5M;BRUT;A;0;1\n"
    ).encode("utf-8-sig")

    parsed = parse_r63_payload(csv_payload, "CSV", "payload.csv")

    assert parsed.total_measures == 1
    row = parsed.rows[0]
    assert row.point_id == "30000000000001"
    assert row.grandeur_metier == "CONS"
    assert row.mode_calcul == "BRUT"
    assert row.type_correction == "A"
    assert row.indice_vraisemblance == "0"
    assert row.etat_complementaire == "1"


def test_r63_csv_maps_unaccented_headers():
    csv_payload = (
        "Identifiant PRM;Date de debut;Date de fin;Grandeur physique;Grandeur metier;Etape metier;Unite;"
        "Horodate;Valeur;Nature;Pas\n"
        "30000000000001;2026-01-01;2026-01-02;EA;CONS;MESURE;Wh;2026-01-01T00:00:00+01:00;10;R;PT5M\n"
    ).encode()

    parsed = parse_r63_payload(csv_payload, "CSV", "payload.csv")

    assert parsed.rows[0].unite == "Wh"


def test_r63_csv_missing_mandatory_header_fails():
    csv_payload = "Identifiant PRM;Date de debut\n30000000000001;2026-01-01\n".encode()

    with pytest.raises(R63ParseError, match="missing mandatory header"):
        parse_r63_payload(csv_payload, "CSV", "payload.csv")


def test_r63_csv_missing_mandatory_cell_fails():
    csv_payload = (
        "Identifiant PRM;Date de debut;Date de fin;Grandeur physique;Grandeur metier;Etape metier;Unite;"
        "Horodate;Valeur;Nature;Pas\n"
        "30000000000001;2026-01-01;2026-01-02;EA;CONS;MESURE;Wh;;10;R;PT5M\n"
    ).encode()

    with pytest.raises(R63ParseError, match="row 2"):
        parse_r63_payload(csv_payload, "CSV", "payload.csv")
