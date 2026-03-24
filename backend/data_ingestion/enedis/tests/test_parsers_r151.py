"""Tests for the R151 XML parser — pure parsing, no DB, no encryption."""

import pytest

from data_ingestion.enedis.parsers.r151 import (
    ParsedR151Donnee,
    ParsedR151File,
    ParsedR151PRM,
    ParsedR151Releve,
    R151ParseError,
    parse_r151,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic R151 XML builders
# ---------------------------------------------------------------------------


def _make_ct_dist_xml(
    id_ct="HCB",
    libelle="Heures Creuses Saison Basse",
    rang="1",
    valeur="83044953",
    indice="0",
) -> str:
    """Build a <Classe_Temporelle_Distributeur> XML fragment."""
    return f"""\
<Classe_Temporelle_Distributeur>
  <Id_Classe_Temporelle>{id_ct}</Id_Classe_Temporelle>
  <Libelle_Classe_Temporelle>{libelle}</Libelle_Classe_Temporelle>
  <Rang_Cadran>{rang}</Rang_Cadran>
  <Valeur>{valeur}</Valeur>
  <Indice_Vraisemblance>{indice}</Indice_Vraisemblance>
</Classe_Temporelle_Distributeur>"""


def _make_ct_xml(
    id_ct="HC",
    libelle="Heures Creuses",
    rang="1",
    valeur="18047813",
    indice="0",
) -> str:
    """Build a <Classe_Temporelle> XML fragment."""
    return f"""\
<Classe_Temporelle>
  <Id_Classe_Temporelle>{id_ct}</Id_Classe_Temporelle>
  <Libelle_Classe_Temporelle>{libelle}</Libelle_Classe_Temporelle>
  <Rang_Cadran>{rang}</Rang_Cadran>
  <Valeur>{valeur}</Valeur>
  <Indice_Vraisemblance>{indice}</Indice_Vraisemblance>
</Classe_Temporelle>"""


def _make_pmax_xml(valeur="7452") -> str:
    """Build a <Puissance_Maximale> XML fragment."""
    return f"""\
<Puissance_Maximale>
  <Valeur>{valeur}</Valeur>
</Puissance_Maximale>"""


def _make_releve_xml(
    date_releve="2024-12-17",
    id_cal_fourn="FC020831",
    libelle_cal_fourn="Heures Pleines/Creuses",
    id_cal_dist="DI000003",
    libelle_cal_dist="Avec differenciation temporelle",
    id_affaire="M07E7D2I",
    donnees_xml="",
) -> str:
    """Build a <Donnees_Releve> XML fragment."""
    return f"""\
<Donnees_Releve>
  <Date_Releve>{date_releve}</Date_Releve>
  <Id_Calendrier_Fournisseur>{id_cal_fourn}</Id_Calendrier_Fournisseur>
  <Libelle_Calendrier_Fournisseur>{libelle_cal_fourn}</Libelle_Calendrier_Fournisseur>
  <Id_Calendrier_Distributeur>{id_cal_dist}</Id_Calendrier_Distributeur>
  <Libelle_Calendrier_Distributeur>{libelle_cal_dist}</Libelle_Calendrier_Distributeur>
  <Id_Affaire>{id_affaire}</Id_Affaire>
  {donnees_xml}
</Donnees_Releve>"""


def _make_r151_xml(
    prm_xml="",
    header_xml="",
    ns_attr="",
) -> bytes:
    """Build a minimal valid R151 XML document.

    If header_xml is empty, a default En_Tete_Flux is generated.
    """
    if not header_xml:
        header_xml = """\
<En_Tete_Flux>
  <Identifiant_Flux>R151</Identifiant_Flux>
  <Libelle_Flux>Puissances maximales et index des PRM du segment C5 sur abonnement</Libelle_Flux>
  <Version_XSD>V1</Version_XSD>
  <Identifiant_Emetteur>ERDF</Identifiant_Emetteur>
  <Identifiant_Destinataire>23X--130624--EE1</Identifiant_Destinataire>
  <Date_Creation>2024-12-19T03:06:52+01:00</Date_Creation>
  <Identifiant_Contrat>GRD-F121</Identifiant_Contrat>
  <Numero_Abonnement>3363155</Numero_Abonnement>
  <Unite_Mesure_Index>Wh</Unite_Mesure_Index>
  <Unite_Mesure_Puissance>VA</Unite_Mesure_Puissance>
</En_Tete_Flux>"""

    ns = f' {ns_attr}' if ns_attr else ""
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<R151{ns}>
  {header_xml}
  {prm_xml}
</R151>""".encode("utf-8")


def _make_prm_xml(prm_id="17745151915440", releves_xml="") -> str:
    """Build a <PRM> XML fragment."""
    return f"""\
<PRM>
  <Id_PRM>{prm_id}</Id_PRM>
  {releves_xml}
</PRM>"""


def _make_full_releve_xml() -> str:
    """Build a releve with all 3 types of donnees."""
    donnees = "\n".join([
        _make_ct_dist_xml(id_ct="HCB", valeur="83044953"),
        _make_ct_dist_xml(id_ct="HPB", valeur="72000000"),
        _make_ct_xml(id_ct="HC", valeur="18047813"),
        _make_ct_xml(id_ct="HP", valeur="15000000"),
        _make_pmax_xml(valeur="7452"),
    ])
    return _make_releve_xml(donnees_xml=donnees)


# ---------------------------------------------------------------------------
# Tests — Nominal parsing
# ---------------------------------------------------------------------------


class TestParseR151Nominal:
    def test_parsing_nominal_all_types(self):
        """Full XML with CT_DIST + CT + PMAX extracts all donnees correctly."""
        releve = _make_full_releve_xml()
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        assert len(result.prms) == 1
        assert result.prms[0].point_id == "17745151915440"
        assert len(result.prms[0].releves) == 1

        donnees = result.prms[0].releves[0].donnees
        assert len(donnees) == 5

        types = [d.type_donnee for d in donnees]
        assert types.count("CT_DIST") == 2
        assert types.count("CT") == 2
        assert types.count("PMAX") == 1

    def test_ct_dist_fields(self):
        """Classe_Temporelle_Distributeur parsed with type_donnee=CT_DIST."""
        donnees = _make_ct_dist_xml(
            id_ct="HCB",
            libelle="Heures Creuses Saison Basse",
            rang="1",
            valeur="83044953",
            indice="0",
        )
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        d = result.prms[0].releves[0].donnees[0]
        assert d.type_donnee == "CT_DIST"
        assert d.id_classe_temporelle == "HCB"
        assert d.libelle_classe_temporelle == "Heures Creuses Saison Basse"
        assert d.rang_cadran == "1"
        assert d.valeur == "83044953"
        assert d.indice_vraisemblance == "0"

    def test_ct_fields(self):
        """Classe_Temporelle parsed with type_donnee=CT."""
        donnees = _make_ct_xml(
            id_ct="HC",
            libelle="Heures Creuses",
            rang="1",
            valeur="18047813",
            indice="0",
        )
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        d = result.prms[0].releves[0].donnees[0]
        assert d.type_donnee == "CT"
        assert d.id_classe_temporelle == "HC"
        assert d.libelle_classe_temporelle == "Heures Creuses"
        assert d.rang_cadran == "1"
        assert d.valeur == "18047813"
        assert d.indice_vraisemblance == "0"

    def test_pmax_fields(self):
        """Puissance_Maximale parsed with type_donnee=PMAX, optional fields None."""
        donnees = _make_pmax_xml(valeur="7452")
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        d = result.prms[0].releves[0].donnees[0]
        assert d.type_donnee == "PMAX"
        assert d.valeur == "7452"
        assert d.id_classe_temporelle is None
        assert d.libelle_classe_temporelle is None
        assert d.rang_cadran is None
        assert d.indice_vraisemblance is None


# ---------------------------------------------------------------------------
# Tests — Header parsing
# ---------------------------------------------------------------------------


class TestParseR151Header:
    def test_header_fields_in_raw_dict(self):
        """All En_Tete_Flux fields present in raw dict."""
        prm = _make_prm_xml()
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        raw = result.header.raw
        assert raw["Identifiant_Flux"] == "R151"
        assert raw["Libelle_Flux"] == "Puissances maximales et index des PRM du segment C5 sur abonnement"
        assert raw["Version_XSD"] == "V1"
        assert raw["Identifiant_Emetteur"] == "ERDF"
        assert raw["Identifiant_Destinataire"] == "23X--130624--EE1"
        assert raw["Date_Creation"] == "2024-12-19T03:06:52+01:00"
        assert raw["Identifiant_Contrat"] == "GRD-F121"
        assert raw["Numero_Abonnement"] == "3363155"
        assert raw["Unite_Mesure_Index"] == "Wh"
        assert raw["Unite_Mesure_Puissance"] == "VA"


# ---------------------------------------------------------------------------
# Tests — Namespace tolerance
# ---------------------------------------------------------------------------


class TestParseR151Tolerance:
    def test_namespace_tolerance_xmlns_xsi(self):
        """With xmlns:xsi attribute, parsing still works."""
        donnees = _make_ct_dist_xml(id_ct="HCB", valeur="83044953")
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(prm_id="17745151915440", releves_xml=releve)
        xml = _make_r151_xml(
            prm_xml=prm,
            ns_attr='xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        )
        result = parse_r151(xml)

        assert len(result.prms) == 1
        assert result.prms[0].point_id == "17745151915440"
        assert len(result.prms[0].releves[0].donnees) == 1
        assert result.prms[0].releves[0].donnees[0].valeur == "83044953"

    def test_values_are_raw_strings(self):
        """All values remain strings, no numeric conversion."""
        donnees = "\n".join([
            _make_ct_dist_xml(valeur="83044953", rang="1", indice="0"),
            _make_pmax_xml(valeur="7452"),
        ])
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        d_ct = result.prms[0].releves[0].donnees[0]
        assert isinstance(d_ct.valeur, str)
        assert isinstance(d_ct.rang_cadran, str)
        assert isinstance(d_ct.indice_vraisemblance, str)

        d_pmax = result.prms[0].releves[0].donnees[1]
        assert isinstance(d_pmax.valeur, str)


# ---------------------------------------------------------------------------
# Tests — Multiple PRMs and releves
# ---------------------------------------------------------------------------


class TestParseR151MultiplePRMs:
    def test_multiple_prm_blocks(self):
        """N PRM blocks are all parsed."""
        prm1 = _make_prm_xml(
            prm_id="17745151915440",
            releves_xml=_make_releve_xml(donnees_xml=_make_ct_dist_xml()),
        )
        prm2 = _make_prm_xml(
            prm_id="99999999999999",
            releves_xml=_make_releve_xml(donnees_xml=_make_ct_xml()),
        )
        xml = _make_r151_xml(prm_xml=prm1 + prm2)
        result = parse_r151(xml)

        assert len(result.prms) == 2
        assert result.prms[0].point_id == "17745151915440"
        assert result.prms[1].point_id == "99999999999999"

    def test_multiple_releves_per_prm(self):
        """N Donnees_Releve per PRM are all parsed."""
        releve1 = _make_releve_xml(
            date_releve="2024-12-17",
            donnees_xml=_make_ct_dist_xml(id_ct="HCB"),
        )
        releve2 = _make_releve_xml(
            date_releve="2024-11-17",
            donnees_xml=_make_ct_dist_xml(id_ct="HPB"),
        )
        prm = _make_prm_xml(releves_xml=releve1 + releve2)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        assert len(result.prms[0].releves) == 2
        assert result.prms[0].releves[0].date_releve == "2024-12-17"
        assert result.prms[0].releves[1].date_releve == "2024-11-17"


# ---------------------------------------------------------------------------
# Tests — Optional donnee blocks
# ---------------------------------------------------------------------------


class TestParseR151OptionalBlocks:
    def test_no_ct_dist(self):
        """Releve without Classe_Temporelle_Distributeur is OK."""
        donnees = _make_ct_xml() + _make_pmax_xml()
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        types = [d.type_donnee for d in result.prms[0].releves[0].donnees]
        assert "CT_DIST" not in types
        assert "CT" in types
        assert "PMAX" in types

    def test_no_ct(self):
        """Releve without Classe_Temporelle is OK."""
        donnees = _make_ct_dist_xml() + _make_pmax_xml()
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        types = [d.type_donnee for d in result.prms[0].releves[0].donnees]
        assert "CT_DIST" in types
        assert "CT" not in types
        assert "PMAX" in types

    def test_no_pmax(self):
        """Releve without Puissance_Maximale is OK."""
        donnees = _make_ct_dist_xml() + _make_ct_xml()
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        types = [d.type_donnee for d in result.prms[0].releves[0].donnees]
        assert "CT_DIST" in types
        assert "CT" in types
        assert "PMAX" not in types

    def test_empty_releve_no_donnees(self):
        """Releve without any donnees blocks has empty list, no error."""
        releve = _make_releve_xml(donnees_xml="")
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        assert len(result.prms[0].releves[0].donnees) == 0


# ---------------------------------------------------------------------------
# Tests — Error handling
# ---------------------------------------------------------------------------


class TestParseR151Errors:
    def test_invalid_xml_raises(self):
        with pytest.raises(R151ParseError, match="Invalid XML"):
            parse_r151(b"not xml at all")

    def test_wrong_root_tag_raises(self):
        xml = b'<?xml version="1.0"?><NotR151/>'
        with pytest.raises(R151ParseError, match="Expected root <R151>"):
            parse_r151(xml)

    def test_missing_header_raises(self):
        xml = b"""\
<?xml version="1.0"?><R151><PRM><Id_PRM>123</Id_PRM></PRM></R151>"""
        with pytest.raises(R151ParseError, match="Missing <En_Tete_Flux>"):
            parse_r151(xml)

    def test_missing_id_prm_raises(self):
        prm = "<PRM><Donnees_Releve><Date_Releve>2024-12-17</Date_Releve></Donnees_Releve></PRM>"
        xml = _make_r151_xml(prm_xml=prm)
        with pytest.raises(R151ParseError, match="Missing or empty <Id_PRM>"):
            parse_r151(xml)

    def test_missing_date_releve_raises(self):
        releve_no_date = """\
<Donnees_Releve>
  <Id_Calendrier_Fournisseur>FC020831</Id_Calendrier_Fournisseur>
</Donnees_Releve>"""
        prm = _make_prm_xml(releves_xml=releve_no_date)
        xml = _make_r151_xml(prm_xml=prm)
        with pytest.raises(R151ParseError, match="Missing <Date_Releve>"):
            parse_r151(xml)


# ---------------------------------------------------------------------------
# Tests — CT_DIST class IDs
# ---------------------------------------------------------------------------


class TestParseR151ClassIDs:
    def test_all_ct_dist_class_ids(self):
        """HCB, HCH, HPB, HPH are all accepted as CT_DIST class IDs."""
        donnees = "\n".join([
            _make_ct_dist_xml(id_ct="HCB", valeur="1000"),
            _make_ct_dist_xml(id_ct="HCH", valeur="2000"),
            _make_ct_dist_xml(id_ct="HPB", valeur="3000"),
            _make_ct_dist_xml(id_ct="HPH", valeur="4000"),
        ])
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        ids = [d.id_classe_temporelle for d in result.prms[0].releves[0].donnees]
        assert ids == ["HCB", "HCH", "HPB", "HPH"]

    def test_ct_class_ids_hc_hp(self):
        """HC and HP are accepted as CT (fournisseur) class IDs."""
        donnees = "\n".join([
            _make_ct_xml(id_ct="HC", valeur="5000"),
            _make_ct_xml(id_ct="HP", valeur="6000"),
        ])
        releve = _make_releve_xml(donnees_xml=donnees)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        ids = [d.id_classe_temporelle for d in result.prms[0].releves[0].donnees]
        assert ids == ["HC", "HP"]


# ---------------------------------------------------------------------------
# Tests — total_donnees property
# ---------------------------------------------------------------------------


class TestParseR151TotalDonnees:
    def test_total_donnees_across_prms_and_releves(self):
        """total_donnees counts across all PRMs and releves."""
        # PRM 1: 1 releve with 3 donnees
        donnees1 = "\n".join([
            _make_ct_dist_xml(id_ct="HCB"),
            _make_ct_xml(id_ct="HC"),
            _make_pmax_xml(),
        ])
        releve1 = _make_releve_xml(donnees_xml=donnees1)
        prm1 = _make_prm_xml(prm_id="11111111111111", releves_xml=releve1)

        # PRM 2: 1 releve with 2 donnees
        donnees2 = "\n".join([
            _make_ct_dist_xml(id_ct="HPB"),
            _make_ct_xml(id_ct="HP"),
        ])
        releve2 = _make_releve_xml(date_releve="2024-11-17", donnees_xml=donnees2)
        prm2 = _make_prm_xml(prm_id="22222222222222", releves_xml=releve2)

        xml = _make_r151_xml(prm_xml=prm1 + prm2)
        result = parse_r151(xml)

        assert result.total_donnees == 5

    def test_total_donnees_zero_when_no_donnees(self):
        """total_donnees is 0 when no PRM blocks."""
        xml = _make_r151_xml(prm_xml="")
        result = parse_r151(xml)
        assert result.total_donnees == 0


# ---------------------------------------------------------------------------
# Tests — Releve context fields
# ---------------------------------------------------------------------------


class TestParseR151ReleveContext:
    def test_releve_context_fields_extracted(self):
        """Calendar IDs and labels preserved in releve."""
        releve = _make_releve_xml(
            date_releve="2024-12-17",
            id_cal_fourn="FC020831",
            libelle_cal_fourn="Heures Pleines/Creuses",
            id_cal_dist="DI000003",
            libelle_cal_dist="Avec differenciation temporelle",
            id_affaire="M07E7D2I",
            donnees_xml=_make_ct_dist_xml(),
        )
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r151_xml(prm_xml=prm)
        result = parse_r151(xml)

        r = result.prms[0].releves[0]
        assert r.date_releve == "2024-12-17"
        assert r.id_calendrier_fournisseur == "FC020831"
        assert r.libelle_calendrier_fournisseur == "Heures Pleines/Creuses"
        assert r.id_calendrier_distributeur == "DI000003"
        assert r.libelle_calendrier_distributeur == "Avec differenciation temporelle"
        assert r.id_affaire == "M07E7D2I"
