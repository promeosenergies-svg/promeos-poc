"""Tests for the R64 parser."""

import json

import pytest

from data_ingestion.enedis.parsers.r64 import R64ParseError, parse_r64_payload


def _r64_json(extra: dict | None = None) -> bytes:
    payload = {
        "header": {
            "siDemandeur": "SGE",
            "typeDestinataire": "SI",
            "idDestinataire": "GRD-F001",
            "codeFlux": "R64",
            "idDemande": "M06IFF1Z",
            "modePublication": "P",
            "idCanalContact": "WEB",
            "format": "JSON",
        },
        "mesures": [
            {
                "idPrm": "30000000000001",
                "periode": {"dateDebut": "2026-01-01", "dateFin": "2026-01-02"},
                "contexte": [
                    {
                        "etapeMetier": "RELEVE",
                        "contexteReleve": "NORMAL",
                        "typeReleve": "INDEX",
                        "motifReleve": "PERIODIQUE",
                        "grandeur": [
                            {
                                "grandeurMetier": "CONS",
                                "grandeurPhysique": "EA",
                                "unite": "Wh",
                                "calendrier": [
                                    {
                                        "idCalendrier": "CAL1",
                                        "libelleCalendrier": "Calendrier",
                                        "libelleGrille": "Grille",
                                        "classeTemporelle": [
                                            {
                                                "idClasseTemporelle": "HP",
                                                "libelleClasseTemporelle": "Heures pleines",
                                                "codeCadran": "01",
                                                "valeur": [
                                                    {"d": "2026-01-01T00:00:00+01:00", "v": 100, "iv": 0},
                                                    {"d": "2026-01-01T01:00:00+01:00", "v": 110, "iv": 1},
                                                ],
                                            }
                                        ],
                                    }
                                ],
                            },
                            {
                                "grandeurMetier": "CONS",
                                "grandeurPhysique": "PMA",
                                "unite": "VA",
                                "cadranTotalisateur": {
                                    "codeCadran": "TOT",
                                    "valeur": [{"d": "2026-01-01T00:00:00+01:00", "v": 42, "iv": None}],
                                },
                            },
                        ],
                    }
                ],
            }
        ],
    }
    if extra:
        payload.update(extra)
    return json.dumps(payload).encode()


def test_r64_json_flattens_nested_values_without_cross_product():
    parsed = parse_r64_payload(_r64_json(), "JSON", "payload.json")

    assert parsed.total_measures == 3
    first = parsed.rows[0]
    assert first.point_id == "30000000000001"
    assert first.id_calendrier == "CAL1"
    assert first.id_classe_temporelle == "HP"
    assert first.valeur == "100"
    assert parsed.rows[-1].grandeur_physique == "PMA"
    assert parsed.rows[-1].code_cadran == "TOT"


def test_r64_json_unknown_top_level_field_warns():
    parsed = parse_r64_payload(_r64_json({"extraRoot": True}), "JSON", "payload.json")

    assert {"code": "unknown_json_field", "path": "$.extraRoot"} in parsed.header.raw["warnings"]


def test_r64_json_disconnected_grandeur_fails():
    payload = json.loads(_r64_json())
    grandeur = payload["mesures"][0]["contexte"][0]["grandeur"][0]
    grandeur.pop("calendrier")

    with pytest.raises(R64ParseError, match="no reachable valeur"):
        parse_r64_payload(json.dumps(payload).encode(), "JSON", "payload.json")


def test_r64_csv_maps_observed_headers():
    csv_payload = (
        "Identifiant PRM;Date de début;Date de fin;Grandeur physique;Grandeur métier;Etape métier;Unité;"
        "Horodate;Valeur;Contexte relève;Type relève;Motif relève;Grille;Identifiant calendrier;"
        "Libellé calendrier;Libellé grille;Identifiant classe temporelle;Libellé classe temporelle;"
        "Cadran;Indice de vraisemblance\n"
        "30000000000001;2026-01-01;2026-01-02;EA;CONS;RELEVE;Wh;"
        "2026-01-01T00:00:00+01:00;100;NORMAL;INDEX;PERIODIQUE;GRD;CAL1;"
        "Calendrier;Grille;HP;Heures pleines;01;0\n"
    ).encode("utf-8-sig")

    parsed = parse_r64_payload(csv_payload, "CSV", "payload.csv")

    assert parsed.total_measures == 1
    row = parsed.rows[0]
    assert row.contexte_releve == "NORMAL"
    assert row.code_grille == "GRD"
    assert row.id_calendrier == "CAL1"
    assert row.id_classe_temporelle == "HP"
    assert row.code_cadran == "01"
    assert row.indice_vraisemblance == "0"
    assert row.valeur == "100"


def test_r64_csv_missing_mandatory_header_fails():
    with pytest.raises(R64ParseError, match="missing mandatory header"):
        parse_r64_payload(b"Identifiant PRM;Date de debut\n30000000000001;2026-01-01\n", "CSV", "payload.csv")
