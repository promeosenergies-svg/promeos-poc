"""Tests for the R50 XML parser -- pure parsing, no DB, no encryption."""

import pytest

from data_ingestion.enedis.parsers.r50 import (
    ParsedR50File,
    ParsedR50PRM,
    ParsedR50Point,
    ParsedR50Releve,
    R50ParseError,
    parse_r50,
)


# ---------------------------------------------------------------------------
# Fixtures -- synthetic R50 XML
# ---------------------------------------------------------------------------


def _make_r50_xml(
    prms_xml: str = "",
    identifiant_flux: str = "R50",
    libelle_flux: str = "Courbes de charge des PRM du segment C5 sur abonnement",
    version_xsd: str = "1.1.0",
    identifiant_emetteur: str = "ERDF",
    identifiant_destinataire: str = "23X--130624--EE1",
    date_creation: str = "2023-01-06T19:02:30+01:00",
    identifiant_contrat: str = "GRD-F121",
    numero_abonnement: str = "3363068",
    pas_publication: str = "30",
    ns_attr: str = "",
) -> bytes:
    """Build a minimal valid R50 XML document."""
    return f"""\
<?xml version="1.0" encoding="UTF-8"?>
<R50{ns_attr}>
  <En_Tete_Flux>
    <Identifiant_Flux>{identifiant_flux}</Identifiant_Flux>
    <Libelle_Flux>{libelle_flux}</Libelle_Flux>
    <Version_XSD>{version_xsd}</Version_XSD>
    <Identifiant_Emetteur>{identifiant_emetteur}</Identifiant_Emetteur>
    <Identifiant_Destinataire>{identifiant_destinataire}</Identifiant_Destinataire>
    <Date_Creation>{date_creation}</Date_Creation>
    <Identifiant_Contrat>{identifiant_contrat}</Identifiant_Contrat>
    <Numero_Abonnement>{numero_abonnement}</Numero_Abonnement>
    <Pas_Publication>{pas_publication}</Pas_Publication>
  </En_Tete_Flux>
  {prms_xml}
</R50>""".encode("utf-8")


def _make_prm_xml(
    id_prm: str = "01445441288824",
    releves_xml: str = "",
) -> str:
    """Build a <PRM> XML fragment."""
    return f"""\
<PRM>
  <Id_PRM>{id_prm}</Id_PRM>
  {releves_xml}
</PRM>"""


def _make_releve_xml(
    date_releve: str = "2023-01-02",
    id_affaire: str | None = "M041AWXF",
    pdcs_xml: str = "",
) -> str:
    """Build a <Donnees_Releve> XML fragment."""
    affaire_part = f"<Id_Affaire>{id_affaire}</Id_Affaire>" if id_affaire else ""
    return f"""\
<Donnees_Releve>
  <Date_Releve>{date_releve}</Date_Releve>
  {affaire_part}
  {pdcs_xml}
</Donnees_Releve>"""


def _make_pdc_xml(
    h: str = "2023-01-02T16:30:00+01:00",
    v: str | None = "20710",
    iv: str | None = "0",
) -> str:
    """Build a <PDC> XML fragment."""
    parts = [f"<H>{h}</H>"]
    if v is not None:
        parts.append(f"<V>{v}</V>")
    if iv is not None:
        parts.append(f"<IV>{iv}</IV>")
    return "<PDC>" + "".join(parts) + "</PDC>"


# ---------------------------------------------------------------------------
# Tests -- Header parsing
# ---------------------------------------------------------------------------


class TestParseR50Header:
    def test_header_fields_in_raw_dict(self):
        xml = _make_r50_xml()
        result = parse_r50(xml)

        raw = result.header.raw
        assert raw["Identifiant_Flux"] == "R50"
        assert raw["Libelle_Flux"] == "Courbes de charge des PRM du segment C5 sur abonnement"
        assert raw["Version_XSD"] == "1.1.0"
        assert raw["Identifiant_Emetteur"] == "ERDF"
        assert raw["Identifiant_Destinataire"] == "23X--130624--EE1"
        assert raw["Date_Creation"] == "2023-01-06T19:02:30+01:00"
        assert raw["Identifiant_Contrat"] == "GRD-F121"
        assert raw["Numero_Abonnement"] == "3363068"
        assert raw["Pas_Publication"] == "30"

    def test_header_custom_values(self):
        xml = _make_r50_xml(
            identifiant_emetteur="ENEDIS",
            pas_publication="10",
        )
        result = parse_r50(xml)

        assert result.header.raw["Identifiant_Emetteur"] == "ENEDIS"
        assert result.header.raw["Pas_Publication"] == "10"


# ---------------------------------------------------------------------------
# Tests -- Nominal parsing
# ---------------------------------------------------------------------------


class TestParseR50Nominal:
    def test_single_prm_single_releve_single_pdc(self):
        pdc = _make_pdc_xml("2023-01-02T16:30:00+01:00", "20710", "0")
        releve = _make_releve_xml(pdcs_xml=pdc)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        assert len(result.prms) == 1
        assert result.prms[0].point_id == "01445441288824"
        assert len(result.prms[0].releves) == 1

        r = result.prms[0].releves[0]
        assert r.date_releve == "2023-01-02"
        assert r.id_affaire == "M041AWXF"
        assert len(r.points) == 1

        p = r.points[0]
        assert p.horodatage == "2023-01-02T16:30:00+01:00"
        assert p.valeur == "20710"
        assert p.indice_vraisemblance == "0"

    def test_multiple_prms(self):
        pdc = _make_pdc_xml()
        releve = _make_releve_xml(pdcs_xml=pdc)
        prm1 = _make_prm_xml(id_prm="01445441288824", releves_xml=releve)
        prm2 = _make_prm_xml(id_prm="09876543210987", releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm1 + prm2)
        result = parse_r50(xml)

        assert len(result.prms) == 2
        assert result.prms[0].point_id == "01445441288824"
        assert result.prms[1].point_id == "09876543210987"

    def test_multiple_releves_per_prm(self):
        pdc = _make_pdc_xml()
        releve1 = _make_releve_xml(date_releve="2023-01-01", pdcs_xml=pdc)
        releve2 = _make_releve_xml(date_releve="2023-01-02", pdcs_xml=pdc)
        releve3 = _make_releve_xml(date_releve="2023-01-03", pdcs_xml=pdc)
        prm = _make_prm_xml(releves_xml=releve1 + releve2 + releve3)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        assert len(result.prms[0].releves) == 3
        assert result.prms[0].releves[0].date_releve == "2023-01-01"
        assert result.prms[0].releves[1].date_releve == "2023-01-02"
        assert result.prms[0].releves[2].date_releve == "2023-01-03"

    def test_multiple_pdcs_per_releve_48_points(self):
        """Typical: 48 half-hour points per day."""
        pdcs = "\n".join(
            _make_pdc_xml(
                h=f"2023-01-02T{i // 2:02d}:{(i % 2) * 30:02d}:00+01:00",
                v=str(20000 + i * 10),
                iv="0",
            )
            for i in range(48)
        )
        releve = _make_releve_xml(pdcs_xml=pdcs)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        assert len(result.prms[0].releves[0].points) == 48
        # Verify first and last
        assert result.prms[0].releves[0].points[0].horodatage == "2023-01-02T00:00:00+01:00"
        assert result.prms[0].releves[0].points[47].horodatage == "2023-01-02T23:30:00+01:00"


# ---------------------------------------------------------------------------
# Tests -- Optional fields / edge cases
# ---------------------------------------------------------------------------


class TestParseR50OptionalFields:
    def test_pdc_without_v_and_iv(self):
        """PDC with only <H> -> valeur=None, indice_vraisemblance=None."""
        pdc = _make_pdc_xml(h="2023-01-02T16:30:00+01:00", v=None, iv=None)
        releve = _make_releve_xml(pdcs_xml=pdc)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        p = result.prms[0].releves[0].points[0]
        assert p.horodatage == "2023-01-02T16:30:00+01:00"
        assert p.valeur is None
        assert p.indice_vraisemblance is None

    def test_pdc_without_iv_only(self):
        """PDC with <H> and <V> but no <IV>."""
        pdc = _make_pdc_xml(h="2023-01-02T16:30:00+01:00", v="20710", iv=None)
        releve = _make_releve_xml(pdcs_xml=pdc)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        p = result.prms[0].releves[0].points[0]
        assert p.valeur == "20710"
        assert p.indice_vraisemblance is None

    def test_releve_without_id_affaire(self):
        """Donnees_Releve without Id_Affaire -> id_affaire=None."""
        pdc = _make_pdc_xml()
        releve = _make_releve_xml(id_affaire=None, pdcs_xml=pdc)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        assert result.prms[0].releves[0].id_affaire is None

    def test_empty_prm_list(self):
        """0 PRM blocks -> no error, empty list, total_points=0."""
        xml = _make_r50_xml(prms_xml="")
        result = parse_r50(xml)

        assert len(result.prms) == 0
        assert result.total_points == 0

    def test_empty_releve_zero_pdcs(self):
        """Releve with 0 PDC -> empty points list."""
        releve = _make_releve_xml(pdcs_xml="")
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        assert len(result.prms[0].releves[0].points) == 0

    def test_values_are_raw_strings(self):
        """All values must remain strings, never converted to int/float."""
        pdc = _make_pdc_xml(h="2023-01-02T16:30:00+01:00", v="20710", iv="0")
        releve = _make_releve_xml(pdcs_xml=pdc)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(prms_xml=prm)
        result = parse_r50(xml)

        p = result.prms[0].releves[0].points[0]
        assert isinstance(p.horodatage, str)
        assert isinstance(p.valeur, str)
        assert isinstance(p.indice_vraisemblance, str)

        r = result.prms[0].releves[0]
        assert isinstance(r.date_releve, str)
        assert isinstance(r.id_affaire, str)

        assert isinstance(result.prms[0].point_id, str)


# ---------------------------------------------------------------------------
# Tests -- total_points
# ---------------------------------------------------------------------------


class TestParseR50TotalPoints:
    def test_total_points_across_prms_and_releves(self):
        """total_points should count all PDCs across all PRMs and releves."""
        # PRM 1: 2 releves with 3 and 2 points
        pdcs_r1 = "\n".join(_make_pdc_xml(h=f"2023-01-01T{i:02d}:00:00+01:00") for i in range(3))
        pdcs_r2 = "\n".join(_make_pdc_xml(h=f"2023-01-02T{i:02d}:00:00+01:00") for i in range(2))
        releve1 = _make_releve_xml(date_releve="2023-01-01", pdcs_xml=pdcs_r1)
        releve2 = _make_releve_xml(date_releve="2023-01-02", pdcs_xml=pdcs_r2)
        prm1 = _make_prm_xml(id_prm="11111111111111", releves_xml=releve1 + releve2)

        # PRM 2: 1 releve with 4 points
        pdcs_r3 = "\n".join(_make_pdc_xml(h=f"2023-01-01T{i:02d}:00:00+01:00") for i in range(4))
        releve3 = _make_releve_xml(date_releve="2023-01-01", pdcs_xml=pdcs_r3)
        prm2 = _make_prm_xml(id_prm="22222222222222", releves_xml=releve3)

        xml = _make_r50_xml(prms_xml=prm1 + prm2)
        result = parse_r50(xml)

        assert result.total_points == 3 + 2 + 4  # = 9


# ---------------------------------------------------------------------------
# Tests -- Namespace tolerance
# ---------------------------------------------------------------------------


class TestParseR50Namespace:
    def test_with_xmlns_xsi_namespace(self):
        """R50 with xmlns:xsi attribute -> parsed identically."""
        pdc = _make_pdc_xml("2023-01-02T16:30:00+01:00", "20710", "0")
        releve = _make_releve_xml(pdcs_xml=pdc)
        prm = _make_prm_xml(releves_xml=releve)
        xml = _make_r50_xml(
            prms_xml=prm,
            ns_attr=' xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"',
        )
        result = parse_r50(xml)

        assert len(result.prms) == 1
        assert result.prms[0].point_id == "01445441288824"
        assert result.prms[0].releves[0].points[0].valeur == "20710"
        assert result.header.raw["Identifiant_Flux"] == "R50"


# ---------------------------------------------------------------------------
# Tests -- Error handling
# ---------------------------------------------------------------------------


class TestParseR50Errors:
    def test_invalid_xml_raises(self):
        with pytest.raises(R50ParseError, match="Invalid XML"):
            parse_r50(b"not xml at all")

    def test_wrong_root_tag_raises(self):
        xml = b'<?xml version="1.0"?><NotR50/>'
        with pytest.raises(R50ParseError, match="Expected root <R50>"):
            parse_r50(xml)

    def test_missing_header_raises(self):
        xml = b"""\
<?xml version="1.0"?><R50>
<PRM><Id_PRM>01445441288824</Id_PRM></PRM>
</R50>"""
        with pytest.raises(R50ParseError, match="Missing <En_Tete_Flux>"):
            parse_r50(xml)

    def test_missing_id_prm_raises(self):
        xml = b"""\
<?xml version="1.0"?><R50>
<En_Tete_Flux><Identifiant_Flux>R50</Identifiant_Flux></En_Tete_Flux>
<PRM><Donnees_Releve><Date_Releve>2023-01-02</Date_Releve></Donnees_Releve></PRM>
</R50>"""
        with pytest.raises(R50ParseError, match="Missing or empty <Id_PRM>"):
            parse_r50(xml)

    def test_empty_id_prm_raises(self):
        xml = b"""\
<?xml version="1.0"?><R50>
<En_Tete_Flux><Identifiant_Flux>R50</Identifiant_Flux></En_Tete_Flux>
<PRM><Id_PRM>  </Id_PRM></PRM>
</R50>"""
        with pytest.raises(R50ParseError, match="Missing or empty <Id_PRM>"):
            parse_r50(xml)

    def test_missing_date_releve_raises(self):
        xml = b"""\
<?xml version="1.0"?><R50>
<En_Tete_Flux><Identifiant_Flux>R50</Identifiant_Flux></En_Tete_Flux>
<PRM><Id_PRM>01445441288824</Id_PRM>
<Donnees_Releve><PDC><H>2023-01-02T16:30:00+01:00</H></PDC></Donnees_Releve>
</PRM></R50>"""
        with pytest.raises(R50ParseError, match="Missing or empty <Date_Releve>"):
            parse_r50(xml)

    def test_missing_h_in_pdc_raises(self):
        xml = b"""\
<?xml version="1.0"?><R50>
<En_Tete_Flux><Identifiant_Flux>R50</Identifiant_Flux></En_Tete_Flux>
<PRM><Id_PRM>01445441288824</Id_PRM>
<Donnees_Releve><Date_Releve>2023-01-02</Date_Releve>
<PDC><V>20710</V><IV>0</IV></PDC>
</Donnees_Releve></PRM></R50>"""
        with pytest.raises(R50ParseError, match="Missing or empty <H>"):
            parse_r50(xml)
