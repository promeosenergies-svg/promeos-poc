view: /cockpit/strategique
slug: cockpit-strategique
viewport_baseline: 1440x900
captured_at: 2026-05-09T09:14:00Z

ux_findings:
  reading_pattern_detected: "F-pattern (kicker en haut-gauche, titre, narrative dense, 3 KPIs en bandeau, cards événements dessous)"
  hero_message_present: true
  hero_message_clarity: 2
  cta_position_consistent: true
  cognitive_load_score: 3
  notes: "Hero éditorial bien construit : kicker 'GESTION DE 2030' + titre Fraunces 'Synthèse stratégique – semaine 19 · pour la direction' + narrative dense ~6 lignes citant chiffres et dates. La narrative dépasse cependant les 2-3 lignes recommandées §5 (lecture longue, ~80 mots) ce qui retire l'effet briefing. CTA 'Rapport COMEX' bien positionné en haut-droite."

ui_findings:
  red_surface_ratio_estime: "0.10"
  font_families_count_estime: 3
  font_sizes_count_estime: 8
  alignment_grid_respected: true
  whitespace_balance: 3
  doctrine_palette_journal_respectee: true
  notes: "Triptyque Fraunces / DM Sans / JetBrains Mono cohérent (gros chiffres '50 / 268,5 / 262' en mono tabular). Palette crème/brun + accent rouge sur les cards événements (Décret BACS, Audit). Densité un poil trop forte au-dessus de la fold sur 1024 — le titre passe sur 2 lignes et la narrative reste dense."

cx_findings:
  next_action_obviousness: 3
  drill_down_breadcrumb_present: true
  back_navigation_predictable: true
  state_persistence_visible: true
  notes: "Breadcrumb 'PROMEOS · Synthèse stratégique' + switch angle 'Briefing du jour / Synthèse stratégique' visible. Cards d'événements typées (CONFORMITÉ, FACTURATION, ACHAT) avec impact € chiffré ('72 k€', '24,7 k€'). Bonne signalisation. Le drill-down depuis chaque card vers la page pillar correspondante n'est pas explicite (pas de CTA texte clair)."

customer_success_findings:
  time_to_first_decision_seconds_estime: 30
  onboarding_friction: 3
  empty_state_helpful: n/a
  error_state_actionable: n/a
  test_dirigeant_non_sachant_pass: false
  test_3_secondes_pass: true
  notes: "Test 3 secondes passé : la narrative dense + 3 chiffres clés permettent une saisie rapide d'état pour un sachant. Test dirigeant non-sachant échoué : la narrative cite TURPE, BACS, OPERAT, baseline, exposition contestable, audit énergétique sans transformer ces termes (anti-pattern §6.3 acronymes bruts)."

violations_vs_grammar:
  - law: "L1_hero_preambule"
    severity: P2
    description: "Narrative dépasse 2-3 lignes recommandées (~6 lignes / ~80 mots). Bonne intention éditoriale mais excès de densité — transforme briefing en éditorial long."
  - law: "L3_kpi_3_max_tooltip_source"
    severity: P0
    description: "3 KPIs respectés (50 actions / 268,5 k€ / 262 MWh/an) mais aucun '?' tooltip visible et libellés très techniques ('IMPACT FACTURATION', 'EXPOSITION RÉGULATION') sans source explicite. Footer source absent."
  - law: "L4_acronymes_transformes"
    severity: P0
    description: "Narrative contient TURPE, BACS, OPERAT, audit énergétique, baseline, factor. Acronymes bruts non transformés en récit (anti-pattern §6.3) — directement opposé au principe 10 'transformer la complexité'. Cible primaire (DAF non-sachant) perdue dès la 1ère phrase."
  - law: "L6_footer_source_timestamp"
    severity: P0
    description: "Aucun footer Source · Confiance · Mis à jour visible en bas du hero ni de la page (anti-pattern §6.4). Aucun timestamp 'mis à jour le …'."
  - law: "L8_kicker_breadcrumb"
    severity: P2
    description: "Kicker présent ('GESTION DE 2030 · SEMAINE 19 · ...') mais formulation ambigue ('GESTION DE 2030' au lieu de 'COCKPIT · SEMAINE 19 · PATRIMOINE — 6 SITES' canonique §5)."
  - law: "L9_action_pousse_pas_tire"
    severity: P2
    description: "Cards événements bien typées et chiffrées en €, mais aucun ordre de priorité visuelle clair (toutes même rang). Le produit liste plus qu'il ne pousse une priorité 1."

screenshots:
  - screenshots/cockpit-strategique/1440x900-above.png
  - screenshots/cockpit-strategique/1440x900-full.png
  - screenshots/cockpit-strategique/1024x1366-above.png

quick_wins_proposes:
  - "Réduire la narrative à 2-3 lignes en gardant chiffres clés, déplacer le détail dans une section 'Voir le détail' dépliable — gain L1 + L4 si le détail traduit aussi les acronymes."
  - "Passer chaque acronyme TURPE / BACS / OPERAT / Audit SMÉ par le dictionnaire ADR-004 (transformation en récit) avant rendu."
  - "Ajouter un SolPageFooter unique avec Source (RegOps · ADEME · Bill-Intel) · Confiance · Mis à jour le – et tooltip '?' sur les 3 KPIs."

verdict_global: "Vue éditoriale plus aboutie que cockpit-jour : kicker, narrative chiffrée, cards événements typées et chiffrées en € sont alignées Sol. Mais les acronymes bruts dans le hero (TURPE/BACS/OPERAT) cassent le principe cardinal 10 et la cible primaire non-sachant. Score 5,5/10 — riche mais non encore lisible par un DAF qui découvre l'énergie."
