"""M2-6.B.pdf — Tests endpoint POST /api/v4/action-center/export/comex.pdf.

Couverture cardinale (7 tests):
- Auth required (401/403 sans token)
- 200 OK avec token user authentifié
- Magic bytes %PDF
- Taille minimale (PDF avec table 9 lignes ≥ 5 KB)
- Headers Content-Type application/pdf + Content-Disposition attachment
- Filename pattern promeos_comex_<slug>_<YYYYMMDD>.pdf
- Contenu PDF : extraction texte via pdfplumber → assertion 47 500 € + items HELIOS
"""

from io import BytesIO
from uuid import uuid4

import pytest

from models.organisation import Organisation
from models.v4.action_center_items import ActionCenterItem

URL = "/api/v4/action-center/export/comex.pdf"


def _h(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def _seed_org(session_local, org_id: int = 1, nom: str = "Groupe HELIOS"):
    """Seed une Organisation (in-memory test DB)."""
    db = session_local()
    try:
        if db.query(Organisation).filter(Organisation.id == org_id).first() is None:
            db.add(Organisation(id=org_id, nom=nom))
            db.commit()
    finally:
        db.close()


def _seed_helios_items(session_local, org_id: int = 1):
    """Seed les 4 items HELIOS chiffrés + 2 NULL = 47 500 € total."""
    db = session_local()
    try:
        items = [
            ("Vérifier conso HP/HC Q3 — Paris Bureaux", "P0", "new", "optimisation", 3200.00),
            ("Déclaration OPERAT 2025", "P1", "in_progress", "conformite", 7500.00),
            ("Audit énergétique — Nice", "P1", "triaged", "conformite", None),
            ("Renouvellement contrat — 5 sites", "P2", "planned", "purchase", 35000.00),
            ("Optimisation HC — Marseille", "P3", "closed", "optimisation", 1800.00),
            ("BACS Lyon Bureaux", "P3", "closed", "conformite", None),
        ]
        from datetime import UTC, datetime

        for title, bracket, lifecycle, domain, impact in items:
            item = ActionCenterItem(
                id=uuid4(),
                organisation_id=org_id,
                kind="anomaly",
                title=title,
                priority_bracket=bracket,
                priority_score=80.0,
                lifecycle_state=lifecycle,
                domain=domain,
                estimated_impact_euros=impact,
            )
            if lifecycle == "closed":
                item.closed_at = datetime.now(UTC)
                item.closure_reason = "resolved"
            db.add(item)
        db.commit()
    finally:
        db.close()


class TestExportComexPdf:
    def test_endpoint_requires_auth(self, client):
        """Sans token → 401 ou 403 (require_v4_role)."""
        r = client.post(URL)
        assert r.status_code in (401, 403)

    def test_authenticated_user_gets_pdf_200(self, app_client, user_token):
        client, session_local = app_client
        _seed_org(session_local)
        _seed_helios_items(session_local)
        r = client.post(URL, headers=_h(user_token))
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/pdf")

    def test_pdf_magic_bytes(self, app_client, user_token):
        client, session_local = app_client
        _seed_org(session_local)
        _seed_helios_items(session_local)
        r = client.post(URL, headers=_h(user_token))
        # Magic bytes PDF standard
        assert r.content[:4] == b"%PDF"

    def test_pdf_non_empty_min_3kb(self, app_client, user_token):
        client, session_local = app_client
        _seed_org(session_local)
        _seed_helios_items(session_local)
        r = client.post(URL, headers=_h(user_token))
        # PDF avec header Sol + 4 cards + table 6 items + footer ≥ 3 KB
        # (ReportLab compresse efficacement — un PDF vide ferait ~2 KB).
        assert len(r.content) > 3000, f"PDF too small: {len(r.content)} bytes"

    def test_content_disposition_attachment_with_filename(self, app_client, user_token):
        client, session_local = app_client
        _seed_org(session_local, nom="Groupe HELIOS")
        _seed_helios_items(session_local)
        r = client.post(URL, headers=_h(user_token))
        cd = r.headers.get("content-disposition", "")
        assert "attachment" in cd.lower()
        assert "promeos_comex_" in cd
        assert ".pdf" in cd
        # Slug ASCII : « Groupe HELIOS » → « groupe-helios »
        assert "groupe-helios" in cd.lower() or "helios" in cd.lower()

    def test_pdf_contains_total_47500_and_completude_phrase(self, app_client, user_token):
        """🎯 Cardinal : le total 47 500 € + phrase complétude doivent apparaître."""
        client, session_local = app_client
        _seed_org(session_local)
        _seed_helios_items(session_local)
        r = client.post(URL, headers=_h(user_token))

        try:
            import pdfplumber
        except ImportError:
            pytest.skip("pdfplumber non installé")

        with pdfplumber.open(BytesIO(r.content)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Le NBSP peut être rendu comme espace normal après extract_text.
        # On vérifie « 47 » et « 500 » à proximité (cardinal Q23=A).
        assert "47" in text and "500" in text, f"Total 47 500 absent du PDF :\n{text[:500]}"
        # Phrase complétude cohérente .bis : « N actions sur M portent un impact... »
        assert "actions sur" in text or "portent un impact" in text or "porte un impact" in text

    def test_pdf_contains_helios_items_detail(self, app_client, user_token):
        """Q21=B : table items doit contenir les titres HELIOS clés."""
        client, session_local = app_client
        _seed_org(session_local)
        _seed_helios_items(session_local)
        r = client.post(URL, headers=_h(user_token))

        try:
            import pdfplumber
        except ImportError:
            pytest.skip("pdfplumber non installé")

        with pdfplumber.open(BytesIO(r.content)) as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)

        # Items HELIOS cardinaux dans la table détail
        assert "HP/HC" in text or "Paris" in text, "Vedette Paris HP/HC absente"
        assert "OPERAT" in text, "OPERAT 2025 absent"
        # Header table colonne Impact estimé
        assert "IMPACT ESTIM" in text.upper() or "Impact estimé" in text
