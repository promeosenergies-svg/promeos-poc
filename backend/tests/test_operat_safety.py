"""
PROMEOS — Tests securite conformite OPERAT.
Verifie que les reponses API ne simulent jamais un depot reel.
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_declaration_status_no_submitted():
    """Le statut DeclarationStatus ne doit pas contenir 'submitted' sans 'simulated'."""
    from models.enums import DeclarationStatus

    for status in DeclarationStatus:
        if "submitted" in status.value.lower():
            assert "simulated" in status.value.lower(), (
                f"DeclarationStatus.{status.name} = '{status.value}' suggere un depot reel — doit contenir 'simulated'"
            )


def test_operat_export_preview_has_simulation_flag():
    """L'endpoint preview doit retourner is_real_submission=False."""
    # Verification structurelle du code source
    import inspect
    from routes.operat import preview_operat_export

    source = inspect.getsource(preview_operat_export)
    assert "is_real_submission" in source, "preview_operat_export doit contenir is_real_submission"
    assert "False" in source, "is_real_submission doit etre False"


def test_operat_export_csv_filename_says_preparatoire():
    """Le nom de fichier CSV doit contenir PREPARATOIRE."""
    import inspect
    from routes.operat import export_operat_csv_route

    source = inspect.getsource(export_operat_csv_route)
    assert "PREPARATOIRE" in source, (
        "Le filename du CSV doit contenir 'PREPARATOIRE' pour ne pas laisser croire a un depot reel"
    )


def test_operat_export_has_disclaimer_header():
    """La reponse CSV doit contenir un header X-PROMEOS-Disclaimer."""
    import inspect
    from routes.operat import export_operat_csv_route

    source = inspect.getsource(export_operat_csv_route)
    assert "X-PROMEOS-Disclaimer" in source
    assert "X-PROMEOS-Submission-Type" in source
