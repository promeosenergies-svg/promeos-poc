"""Détecteurs d'événements PROMEOS Sol — chantier α (doctrine §10).

Chaque détecteur expose une fonction `detect(db, org_id) -> list[SolEventCard]`
qui interroge l'état DB courant et émet des événements typés.

MVP α (Vague C ét11) : compliance_deadline_detector seul.
Vague C ét12+ : 8 autres détecteurs alignés doctrine §10 event_types.
"""
