"""
Tests for consumption_unified scope bypass fixes.
Validates that site/{site_id} and reconcile/{site_id} endpoints
reject requests when the site does not belong to the resolved org.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from fastapi.testclient import TestClient


def _get_client():
    from main import app

    return TestClient(app)


def _get_valid_site_and_org():
    """Return (site_id, org_id) for a site that belongs to the org, or (None, None)."""
    from database import SessionLocal
    from models import Site, Portefeuille, EntiteJuridique

    db = SessionLocal()
    try:
        row = (
            db.query(Site.id, EntiteJuridique.organisation_id)
            .join(Portefeuille, Portefeuille.id == Site.portefeuille_id)
            .join(EntiteJuridique, EntiteJuridique.id == Portefeuille.entite_juridique_id)
            .first()
        )
        if row:
            return row[0], row[1]
        return None, None
    finally:
        db.close()


def _get_other_org_id(exclude_org_id: int):
    """Return an org_id different from exclude_org_id, or None."""
    from database import SessionLocal
    from models import Organisation

    db = SessionLocal()
    try:
        org = db.query(Organisation).filter(Organisation.id != exclude_org_id).first()
        return org.id if org else None
    finally:
        db.close()


class TestConsumptionUnifiedScopeBypass(unittest.TestCase):
    """Verify that site-level endpoints enforce org scope."""

    def test_consumption_unified_site_requires_valid_scope(self):
        """GET /consumption-unified/site/{site_id} with wrong org returns 404."""
        site_id, org_id = _get_valid_site_and_org()
        if site_id is None:
            self.skipTest("No site data in DB")

        other_org_id = _get_other_org_id(org_id)
        if other_org_id is None:
            self.skipTest("Only one org in DB, cannot test cross-org access")

        client = _get_client()
        resp = client.get(
            f"/api/consumption-unified/site/{site_id}",
            headers={"X-Org-Id": str(other_org_id)},
        )
        self.assertEqual(resp.status_code, 404, "Should reject site access from wrong org")

    def test_consumption_unified_reconcile_requires_valid_scope(self):
        """GET /consumption-unified/reconcile/{site_id} with wrong org returns 404."""
        site_id, org_id = _get_valid_site_and_org()
        if site_id is None:
            self.skipTest("No site data in DB")

        other_org_id = _get_other_org_id(org_id)
        if other_org_id is None:
            self.skipTest("Only one org in DB, cannot test cross-org access")

        client = _get_client()
        resp = client.get(
            f"/api/consumption-unified/reconcile/{site_id}",
            headers={"X-Org-Id": str(other_org_id)},
        )
        self.assertEqual(resp.status_code, 404, "Should reject reconcile access from wrong org")

    def test_consumption_unified_site_valid_scope(self):
        """GET /consumption-unified/site/{site_id} with correct org succeeds (not 404 for scope)."""
        site_id, org_id = _get_valid_site_and_org()
        if site_id is None:
            self.skipTest("No site data in DB")

        client = _get_client()
        resp = client.get(
            f"/api/consumption-unified/site/{site_id}",
            headers={"X-Org-Id": str(org_id)},
        )
        # Should NOT be 404 with "accès refusé" — might be 200 or another status
        # but not a scope rejection
        if resp.status_code == 404:
            data = resp.json()
            self.assertNotIn(
                "accès refusé",
                data.get("detail", ""),
                "Valid org should not get scope-rejection 404",
            )


if __name__ == "__main__":
    unittest.main()
