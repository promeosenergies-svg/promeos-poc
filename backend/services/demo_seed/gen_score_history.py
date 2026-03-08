"""
PROMEOS — Step 33 : Seed 6 mois d'historique de score conformite.
Progression realiste par site.
"""

from datetime import date

from models.compliance_score_history import ComplianceScoreHistory


# Scores progressifs par site (6 mois, du plus ancien au plus recent)
_PROGRESSIONS = {
    "paris": [45, 48, 52, 58, 63, 68],
    "lyon": [60, 62, 65, 70, 72, 75],
    "marseille": [30, 33, 36, 40, 43, 47],
    "nice": [25, 28, 32, 35, 38, 42],
    "toulouse": [50, 53, 56, 59, 62, 65],
}


def _grade(score):
    if score >= 80:
        return "A"
    if score >= 60:
        return "B"
    if score >= 40:
        return "C"
    if score >= 20:
        return "D"
    return "F"


def seed_score_history(db, org_id: int, sites: list) -> dict:
    """
    Genere 6 mois d'historique de score pour les sites HELIOS.
    Idempotent via check avant insert.
    """
    today = date.today()
    created = 0

    # Build site lookup by name keyword
    site_map = {}
    for site in sites:
        name_lower = site.nom.lower()
        for key in _PROGRESSIONS:
            if key in name_lower:
                site_map[key] = site
                break

    # For sites not matching any keyword, assign default progression
    default_scores = [40, 43, 47, 50, 53, 56]

    all_sites_to_seed = []
    for key, site in site_map.items():
        all_sites_to_seed.append((site, _PROGRESSIONS[key]))

    for site in sites:
        if site not in [s for s, _ in all_sites_to_seed]:
            all_sites_to_seed.append((site, default_scores))

    for site, scores in all_sites_to_seed:
        for i in range(6):
            # Proper month arithmetic: go back (5-i) months from current month
            months_back = 5 - i
            y = today.year
            m = today.month - months_back
            while m <= 0:
                m += 12
                y -= 1
            month_key = f"{y:04d}-{m:02d}"

            existing = db.query(ComplianceScoreHistory).filter_by(site_id=site.id, month_key=month_key).first()
            if existing:
                continue

            score = scores[i] if i < len(scores) else scores[-1]
            entry = ComplianceScoreHistory(
                site_id=site.id,
                org_id=org_id,
                month_key=month_key,
                score=float(score),
                grade=_grade(score),
            )
            db.add(entry)
            created += 1

    db.flush()
    return {"entries_created": created, "sites_count": len(all_sites_to_seed)}
