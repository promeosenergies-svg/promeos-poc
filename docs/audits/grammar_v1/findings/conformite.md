view: /conformite
slug: conformite
viewport_baseline: 1440x900
captured_at: 2026-05-09T09:14:00Z

ux_findings:
  reading_pattern_detected: "F-pattern bien tenu — kicker top, titre Fraunces narratif, narrative chiffrée 2-3 lignes, ligne de 3 KPIs, week-cards typées, sections 'Achever vos contrats énergie' et 'Conformité majeure 2030/40'"
  hero_message_present: true
  hero_message_clarity: 4
  cta_position_consistent: true
  cognitive_load_score: 3
  notes: "Le hero raconte bien la trajectoire : 'trajectoire 2030 et échéances par jalon'. Narrative cite Décret 2019-771, score 50/100 sur 119 sites. Trois KPIs 15 k€ / 50/100 / J-144 lisibles. Week-cards typées 'À faire' / 'Sous tension' / 'Vigilance trajectoire 2030'."

ui_findings:
  red_surface_ratio_estime: "0.06"
  font_families_count_estime: 2
  font_sizes_count_estime: 5
  alignment_grid_respected: true
  whitespace_balance: 4
  doctrine_palette_journal_respectee: true
  notes: "Palette journal très bien tenue — week-cards rose/sable/orange chaud, accents rouges modérés (badge 'Conformité majeure' rouge clair). Triptyque typo respecté (Fraunces titre + DM Sans body + mono kicker / KPI). C'est l'une des pages les plus alignées palette doctrine vue à date."

cx_findings:
  next_action_obviousness: 4
  drill_down_breadcrumb_present: true
  back_navigation_predictable: true
  state_persistence_visible: true
  notes: "Breadcrumb 'PROMEOS · Conformité · Conformité' (redondance mineure mais lisible). CTA 'Créer une action' visible en haut à droite + bouton 'Démarrer' dans week-card 'À faire'. Bandeau 'Conformité majeure 2030/40' avec badge rouge attire bien l'œil et propose action."

customer_success_findings:
  time_to_first_decision_seconds_estime: 20
  onboarding_friction: 2
  empty_state_helpful: n/a
  error_state_actionable: true
  test_dirigeant_non_sachant_pass: false
  test_3_secondes_pass: true
  notes: "Test 3s passé — un dirigeant comprend qu'il y a 144 jours avant échéance + 50/100 score + 15 k€ d'enjeu. Mais test non-sachant échoue partiellement : les acronymes 'BACS GISMO/CTC', 'Loi APER', 'Audit énergétique obligatoire à ISS' apparaissent en clair dans les week-cards et bas de page sans transformation narrative. 'BACS' / 'APER' / 'ISS' bruts."

violations_vs_grammar:
  - law: "L4_acronymes_transformes"
    severity: P0
    description: "Acronymes bruts dans les titres/labels : 'Audit énergétique obligatoire à ISS', 'BACS GISMO/CTC', 'Loi APER (EN58)', 'Préparer l'échéance Loi APER (EN58)'. Anti-pattern §6.3 explicite. La doctrine impose la transformation en récit ('audit obligatoire si effectif > 250 / CA > 50 M€' au lieu de 'à ISS')."
  - law: "L3_kpi_3_max_tooltip_source"
    severity: P2
    description: "3 KPIs respectés (15 k€ / 50/100 / J-144), bonne discipline. Mais aucun '?' tooltip visible à côté des libellés 'BUDGET RISQUE', 'SCORE AUDIT', 'PROCHAINE ÉCHÉANCE'."
  - law: "L6_footer_source_timestamp"
    severity: P1
    description: "Pas de SolPageFooter visible (Source RegOps · Confiance · Mis à jour) en bas de fold. Source 'Décret 2019-771' citée en narrative mais sans footer SCM canonique."
  - law: "L7_densite_editoriale"
    severity: P2
    description: "Bonne densité globalement mais bloc 'Achever vos contrats énergie' dense et bas de page 'Préparer l'échéance Loi APER (EN58)' empilé sans hiérarchie narrative claire."

screenshots:
  - screenshots/conformite/1440x900-above.png
  - screenshots/conformite/1440x900-full.png
  - screenshots/conformite/1024x1366-above.png

quick_wins_proposes:
  - "Transformer 'BACS GISMO/CTC' → 'Pilotage automatique du bâtiment (obligation 2027)' et 'Loi APER (EN58)' → 'Ombrières solaires sur parkings (loi APER)' partout dans la page."
  - "Ajouter tooltip '?' sur les 3 KPIs (formule + source RegOps)."
  - "Ajouter SolPageFooter SCM en bas (Source RegOps · Décret 2019-771 · Confiance high · Mis à jour HH:MM)."

verdict_global: "Conformité est l'une des pages les mieux alignées doctrine Sol v1.1 — hero narratif, 3 KPIs, week-cards typées, palette journal exemplaire. Mais elle viole frontalement L4 (acronymes BACS/APER/ISS bruts dans titres et bas de page) — c'est précisément le test de transformation que la doctrine impose. Score : 7/10."
