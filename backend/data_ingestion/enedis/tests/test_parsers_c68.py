"""Tests for the C68 parser."""

import json

import pytest

from data_ingestion.enedis.parsers.c68 import C68ParseError, parse_c68_payload


def test_c68_json_top_level_array_extracts_one_row_per_prm():
    payload = [
        {
            "idPrm": "30000000000001",
            "siret": "12345678900011",
            "siren": "123456789",
            "domaineTension": "BT",
            "puissanceSouscrite": {"valeur": "36", "unite": "kVA"},
            "situationsContractuelles": [
                {"dateDebut": "2024-01-01", "segment": "C5", "etatContractuel": "ANCIEN"},
                {
                    "dateDebut": "2025-01-01",
                    "segment": "C4",
                    "etatContractuel": "ACTIF",
                    "formuleTarifaireAcheminement": "BTINFCU4",
                },
            ],
            "rattachements": [{"role": "synthetic"}],
        },
        {"idPrm": "30000000000002", "puissanceRaccordementInjection": {"valeur": "12", "unite": "kVA"}},
    ]

    parsed = parse_c68_payload(json.dumps(payload).encode(), "JSON", "payload.json")

    assert parsed.total_prms == 2
    row = parsed.rows[0]
    assert row.point_id == "30000000000001"
    assert row.siret == "12345678900011"
    assert row.segment == "C4"
    assert row.etat_contractuel == "ACTIF"
    assert row.puissance_souscrite_valeur == "36"
    assert row.puissance_souscrite_unite == "kVA"
    assert json.loads(row.payload_raw)["rattachements"] == [{"role": "synthetic"}]


def test_c68_json_extracts_type_injection_from_latest_contractual_situation():
    payload = [
        {
            "idPrm": "30000000000001",
            "situationsContractuelles": [
                {"dateDebut": "2024-01-01", "typeInjection": "ANCIEN"},
                {"dateDebut": "2025-01-01", "typeInjection": "SURPLUS"},
            ],
        }
    ]

    parsed = parse_c68_payload(json.dumps(payload).encode(), "JSON", "payload.json")

    assert parsed.rows[0].type_injection == "SURPLUS"


def test_c68_json_extracts_v12_nested_single_contract_without_date_debut():
    payload = [
        {
            "idPrm": "30000119007533",
            "situationAlimentation": {
                "alimentationPrincipale": {
                    "domaineTension": "HTA",
                    "puissanceLimiteSoutirage": {"unite": "kW", "valeur": 21200},
                    "puissanceRaccordementSoutirage": {"unite": "kW", "valeur": 4890},
                    "tensionLivraison": "20 kV",
                }
            },
            "situationComptage": {
                "caracteristiquesReleve": {"periodicite": "QUOTID"},
                "dispositifComptage": {"media": "IP", "modeReleve": "TRLV", "typeComptage": "ICE"},
            },
            "situationsContractuelles": [
                {
                    "clientFinal": {
                        "informationsClient": {
                            "personneMorale": {"numSiren": "123456789", "numSiret": "12345678900011"}
                        }
                    },
                    "informationsContractuelles": {"etatContractuel": "SERVC"},
                    "segment": "C1",
                    "structureTarifaire": {
                        "formuleTarifaireAcheminement": {"code": "HTALU5"},
                        "puissanceSouscrite": {"unite": "kW", "valeur": "4890"},
                    },
                }
            ],
        }
    ]

    parsed = parse_c68_payload(json.dumps(payload).encode(), "JSON", "payload.json")

    row = parsed.rows[0]
    assert row.segment == "C1"
    assert row.etat_contractuel == "SERVC"
    assert row.formule_tarifaire_acheminement == "HTALU5"
    assert row.siret == "12345678900011"
    assert row.siren == "123456789"
    assert row.domaine_tension == "HTA"
    assert row.tension_livraison == "20 kV"
    assert row.type_comptage == "ICE"
    assert row.mode_releve == "TRLV"
    assert row.media_comptage == "IP"
    assert row.periodicite_releve == "QUOTID"
    assert row.puissance_souscrite_valeur == "4890"
    assert row.puissance_souscrite_unite == "kW"
    assert row.puissance_limite_soutirage_valeur == "21200"
    assert row.puissance_raccordement_soutirage_valeur == "4890"
    assert row.warnings == []


def test_c68_json_ambiguous_contractual_situation_warns_and_nulls_summary():
    payload = [
        {
            "idPrm": "30000000000001",
            "situationsContractuelles": [
                {"dateDebut": "2025-01-01", "segment": "C5"},
                {"dateDebut": "2025-01-01", "segment": "C4"},
            ],
        }
    ]

    parsed = parse_c68_payload(json.dumps(payload).encode(), "JSON", "payload.json")

    assert parsed.rows[0].segment is None
    assert parsed.rows[0].warnings[0]["code"] == "ambiguous_contractual_situation"


def test_c68_json_missing_id_prm_is_fatal():
    with pytest.raises(C68ParseError, match="missing idPrm"):
        parse_c68_payload(b"[{}]", "JSON", "payload.json")


def test_c68_csv_207_style_extracts_allowlisted_columns_and_preserves_unknowns():
    csv_payload = (
        "PRM;Segment;Etat contractuel;SIRET;SIREN;Domaine Tension;Puissance Souscrite Valeur;"
        "Puissance Souscrite Unite;Colonne inconnue\n"
        "30000000000001;C5;ACTIF;12345678900011;123456789;BT;36;kVA;preserve\n"
    ).encode("utf-8-sig")

    parsed = parse_c68_payload(csv_payload, "CSV", "payload.csv")

    assert parsed.total_prms == 1
    row = parsed.rows[0]
    assert row.point_id == "30000000000001"
    assert row.segment == "C5"
    assert row.siret == "12345678900011"
    assert row.puissance_souscrite_valeur == "36"
    assert json.loads(row.payload_raw)["Colonne inconnue"] == "preserve"
    assert parsed.warnings[0]["code"] == "unknown_csv_columns"


def test_c68_csv_211_style_extracts_v12_additions():
    csv_payload = (
        "PRM;Type Injection;Refus de pose Linky;Date refus de pose Linky;Borne Fixe\n30000000000001;SURPLUS;NON;;OUI\n"
    ).encode()

    parsed = parse_c68_payload(csv_payload, "CSV", "payload.csv")

    assert parsed.rows[0].type_injection == "SURPLUS"
    assert parsed.rows[0].borne_fixe == "OUI"
    assert parsed.rows[0].refus_pose_linky == "NON"
    assert json.loads(parsed.rows[0].payload_raw)["Type Injection"] == "SURPLUS"


def test_c68_csv_missing_prm_header_or_value_is_fatal():
    with pytest.raises(C68ParseError, match="missing mandatory header"):
        parse_c68_payload(b"Segment\nC5\n", "CSV", "payload.csv")

    with pytest.raises(C68ParseError, match="missing mandatory PRM"):
        parse_c68_payload(b"PRM;Segment\n;C5\n", "CSV", "payload.csv")
