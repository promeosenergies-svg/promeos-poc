view: /anomalies
slug: anomalies
viewport_baseline: 1440x900
captured_at: 2026-05-09T09:14:00Z

ux_findings:
  reading_pattern_detected: "F-pattern partiel — kicker en haut, titre narratif large, narrative dense, puis ligne de 3 KPIs, puis 3 week-cards alignées, puis tableau"
  hero_message_present: true
  hero_message_clarity: 4
  cta_position_consistent: true
  cognitive_load_score: 3
  notes: "Le hero raconte bien un récit (5 anomalies critiques, 86,5 k€ récupérables, 3 échéances). Les week-cards sont correctement typées. Le tableau Plan d'actions arrive en dessous, ce qui respecte la hiérarchie briefing → action."

ui_findings:
  red_surface_ratio_estime: "0.04"
  font_families_count_estime: 2
  font_sizes_count_estime: 5
  alignment_grid_respected: true
  whitespace_balance: 4
  doctrine_palette_journal_respectee: true
  notes: "Palette crème/brun tenue, accents rouge réservés aux badges criticité. Triptyque Fraunces (titre) + DM Sans (corps) + mono (kicker / KPI numbers) bien observable. Surfaces colorées des week-cards (rose/sable/sable) respectent la palette journal."

cx_findings:
  next_action_obviousness: 3
  drill_down_breadcrumb_present: true
  back_navigation_predictable: true
  state_persistence_visible: true
  notes: "Breadcrumb 'PROMEOS · Centre d'action · Vos anomalies' visible. Tabs 'Anomalies / Plan d'actions' fournissent ancrage. CTA implicite par lignes du tableau mais bouton 'Quick fix'/'Détails' à droite peu mis en évidence — l'action prioritaire n'est pas escaladée hors tableau."

customer_success_findings:
  time_to_first_decision_seconds_estime: 25
  onboarding_friction: 2
  empty_state_helpful: n/a
  error_state_actionable: n/a
  test_dirigeant_non_sachant_pass: true
  test_3_secondes_pass: true
  notes: "Un dirigeant non-sachant comprend en 3s : 5 anomalies critiques, 86,5 k€ à récupérer. La narrative cite explicitement les sources (Énergétique, Facturation, PROMEOS Sol). Friction faible — le tableau reste un cran trop technique mais le hero compense."

violations_vs_grammar:
  - law: "L3_kpi_3_max_tooltip_source"
    severity: P2
    description: "3 KPIs respectés (86,5 k€ / 36 / 4,5 k€) mais aucun glyphe '?' tooltip visible à côté des libellés. Source non explicitée par KPI individuel — uniquement dans la narrative."
  - law: "L6_footer_source_timestamp"
    severity: P1
    description: "Pas de SolPageFooter en bas de fold visible avec Source · Confiance · Mis à jour. La narrative cite les sources en intro mais le footer SCM canonique manque."
  - law: "L9_action_pousse_pas_tire"
    severity: P2
    description: "Le tableau 'Plan d'actions' liste des items mais aucun item n'est promu en CTA primaire au-dessus du fold (week-cards 'À faire' n'ont pas de bouton d'action explicite hors badge 'À FAIRE')."
  - law: "L10_coherence_chiffres"
    severity: P2
    description: "86,5 k€ apparaît en KPI ET en narrative — bonne cohérence. Mais '5 anomalies critiques' dans narrative vs '36 anomalies' dans KPI 'Anomalies actives' : la distinction critique/total n'est pas typographiquement claire pour un non-sachant."

screenshots:
  - screenshots/anomalies/1440x900-above.png
  - screenshots/anomalies/1440x900-full.png
  - screenshots/anomalies/1024x1366-above.png

quick_wins_proposes:
  - "Ajouter le SolPageFooter (Source RegOps + Bill-Intel · Confiance high · Mis à jour HH:MM) en bas de page."
  - "Ajouter tooltip '?' à côté des 3 KPIs avec définition + source."
  - "Promouvoir l'action #1 du Plan d'actions en CTA primaire dans la week-card 'À faire'."

verdict_global: "La vue Anomalies est l'une des plus alignées Sol v1.1 du repo : kicker, titre Fraunces narratif, narrative chiffrée sourcée, 3 KPIs, 3 week-cards typées. Manque le footer SCM, les tooltips KPI et un CTA primaire promu hors tableau. Score : 7,5/10."
