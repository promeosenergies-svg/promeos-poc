"""Action Center V4 P0-1 fix (2026-05-25) — anti-régression : /api/cockpit/
priorities ne doit JAMAIS renvoyer un action_url pointant vers /anomalies
(page legacy gated OFF en V4 ON, clic = 404 utilisateur cf. audit deep §6).
"""

from __future__ import annotations

import re
from pathlib import Path

ROUTE = Path(__file__).resolve().parents[1] / "routes" / "cockpit.py"


def test_no_legacy_anomalies_url_in_cockpit_priorities_action_urls():
    """Source-guard P0-1 : aucune `action_url` littérale `/anomalies` dans
    la fonction `get_cockpit_priorities`. Les liens doivent passer par le
    helper `_safe_action_url()` qui mappe vers les hubs canoniques
    (/conformite, /bill-intel, /patrimoine) avec fallback /centre-action.

    Tolère la mention `/anomalies` dans les commentaires (audit historique)
    mais interdit toute interpolation `f"/anomalies..."` dans une
    `action_url`.
    """
    text = ROUTE.read_text(encoding="utf-8")
    # Cherche toutes les lignes contenant à la fois "action_url" et "/anomalies"
    bad_lines = []
    for i, line in enumerate(text.splitlines(), start=1):
        if "action_url" in line and "/anomalies" in line:
            stripped = line.lstrip()
            if stripped.startswith("#"):
                continue  # commentaire historique acceptable
            bad_lines.append((i, line.strip()))
    assert not bad_lines, (
        f"Action Center V4 P0-1 régression : /api/cockpit/priorities pointe "
        f"encore vers /anomalies (page gated OFF). Voir audit deep §6 P0-1. "
        f"Lignes : {bad_lines}"
    )


def test_safe_action_url_helper_present():
    """Garantit la présence du helper `_safe_action_url` qui mappe les
    domaines vers les hubs canoniques."""
    text = ROUTE.read_text(encoding="utf-8")
    assert "_safe_action_url" in text, (
        "Helper _safe_action_url manquant — sans lui le fix P0-1 peut être "
        "contourné par un futur ajout. cf. audit deep §6."
    )
    # Le helper doit lister les 3 hubs canoniques + fallback /centre-action.
    for hub in ("/conformite", "/bill-intel", "/patrimoine", "/centre-action"):
        assert hub in text, f"Hub canonique {hub} absent de cockpit.py"


def test_no_legacy_actions_url_in_overdue_priority():
    """Source 2 (ActionPlanItem overdue) : action_url ne doit plus être
    `/actions/{id}` (route gated OFF V4 ON) mais le hub /centre-action."""
    text = ROUTE.read_text(encoding="utf-8")
    # Cherche un pattern f"/actions/{...}" littéral dans action_url
    pattern = re.compile(r'action_url["\s:=]+f?"/actions/\{')
    matches = pattern.findall(text)
    assert not matches, (
        f"Action Center V4 P0-1 : /actions/{{id}} encore utilisé comme "
        f"action_url (gated OFF V4). Utiliser _HUB_FALLBACK. Matches: {matches}"
    )
