view: /bill-intel
slug: factures
viewport_baseline: 1440x900
captured_at: 2026-05-09T07:18:19Z

ux_findings:
  reading_pattern_detected: "Z-pattern partiel"
  hero_message_present: true
  hero_message_clarity: 4
  cta_position_consistent: true
  cognitive_load_score: 3
  notes: "Hero narratif Sol bien présent (kicker FACTURATION + titre Fraunces 'Vos factures - verifiees, recalculees, expliquees' + sous-titre 'shadow billing v1.2'). Narrative 2-3 lignes citant 90 anomalies / 19,8 k€ / TURPE 7 / accise / CTA / TVA. Cognitive load alourdi par 3 toolbars superposees (top bar PROMEOS + scope bar Groupe HELIOS + tabs Anomalies & Audit / Chronologie + boutons Capacite EDI / Importer PDF / Auditer tout)."

ui_findings:
  red_surface_ratio_estime: "0.18"
  font_families_count_estime: 3
  font_sizes_count_estime: 6
  alignment_grid_respected: partiel
  whitespace_balance: 3
  doctrine_palette_journal_respectee: true
  notes: "Triptyque Fraunces/DM Sans/JetBrains Mono respecte. Palette journal creme/brun chaleureux conforme. Card Anomalie facture (rose/rouge) + Patrimoine en alerte (jaune/ambre) + Formuler 105 contestations (creme) coherentes. Surface rouge contenue (~18% via card alerte rose) - non excessive mais visuellement dominante au-dessus du fold."

cx_findings:
  next_action_obviousness: 3
  drill_down_breadcrumb_present: true
  back_navigation_predictable: true
  state_persistence_visible: true
  notes: "Breadcrumb kicker 'FACTURATION' + segment scope 'Groupe HELIOS' clair. Bouton 'Auditer tout' principal CTA mais en concurrence avec 'Importer PDF' / 'Capacite EDI' / 'Optimiser facture mageste' - hierarchie CTA peu lisible. Bandeau bas 'Comment ca marche PROMEOS recalcule la totalite' = onboarding inline pertinent."

customer_success_findings:
  time_to_first_decision_seconds_estime: 25
  onboarding_friction: 3
  empty_state_helpful: n/a
  error_state_actionable: n/a
  test_dirigeant_non_sachant_pass: false
  test_3_secondes_pass: true
  notes: "Test 3 secondes: dirigeant lit '90 anomalies, 19,8 k€ a recuperer' = comprehension immediate du gain. Test dirigeant non-sachant FAIL: acronymes bruts TURPE / CSPE / TICFE / CTA / TVA / capacite (CIEE) / EDI exposes sans transformation. KPI 'CIBLE A AUDITER 110' sans tooltip ni unite explicite. Footer bandeau cyan utile mais reste l'utilisateur doit decoder lui-meme."

violations_vs_grammar:
  - law: "L3_kpi_3_max_tooltip_source"
    severity: P1
    description: "3 KPIs respecte (19,8 k€ / 110 / 0 €) mais aucun tooltip '?' visible et footer source par KPI absent (pas de mention Shadow billing v1.2 / TURPE 7 / barème CRE par KPI). Footer SCM global (Source / Confiance / Mis a jour) absent au-dessus du fold."
  - law: "L4_acronymes_transformes"
    severity: P0
    description: "Acronymes bruts dans la narrative et chips: TURPE 7, CSPE, TICFE, CTA, TVA, EDI, CIEE non transformes en recit. Doctrine §6.3 anti-pattern explicite. Chip 'Capacite EDI' = double acronyme."
  - law: "L6_footer_source_timestamp"
    severity: P0
    description: "Aucun SolPageFooter visible (Source · Confiance · Mis a jour). Mention 'shadow billing v1.2' en italique sous le titre n'est pas un footer SCM normalise."
  - law: "L7_densite_editoriale"
    severity: P1
    description: "Card 'Patrimoine en alerte' avec icone + 1 ligne 'aucune description' - densite faible vs cards adjacentes (Anomalie facture -2,1 k€ / Formuler 105 contestations) bien densifiees. Risque anti-pattern §4 si etat reste vide."
  - law: "L9_action_pousse_pas_tire"
    severity: P2
    description: "5 boutons d'action en haut (Capacite EDI / Importer PDF / Auditer tout / Optimiser facture mageste / 2 toggles) sans hierarchisation push: produit attend que l'utilisateur clique. Aucune action pre-priorisee 'commencez ici'."

screenshots:
  - screenshots/factures/1440x900-above.png
  - screenshots/factures/1440x900-full.png
  - screenshots/factures/1024x1366-above.png

quick_wins_proposes:
  - "Ajouter tooltip '?' sur chaque KPI (19,8 k€ / 110 / 0 €) avec definition + source RegOps/CRE/Enedis."
  - "Transformer acronymes en chips lisibles: 'TURPE 7' -> 'tarif acheminement reseau (TURPE 7)', 'accise + CTA' -> 'taxes electricite (accise + CTA)', supprimer 'EDI' / 'CIEE' du label bouton."
  - "Ajouter SolPageFooter unique en bas de page (Source: Shadow billing v1.2 + barèmes CRE/JORFTEXT · Confiance: high · Mis a jour: ISO8601)."
  - "Reduire CTA secondaires (Capacite EDI / Importer PDF) en menu kebab. Garder 'Auditer tout' principal."
  - "Densifier card 'Patrimoine en alerte' avec montant impact estime + nb sites concernes."

verdict_global: "Score 6.0/10. Grammaire Sol largement appliquee (kicker + titre Fraunces + narrative chiffree + 3 week-cards typees + densite). Bloque doctrine sur L4 acronymes bruts (TURPE/CSPE/TICFE/CTA/EDI/CIEE) et L6 footer SCM absent. Test 3s passe, test dirigeant non-sachant echoue."
