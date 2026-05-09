view: /sites/1
slug: site-paris-bureaux
viewport_baseline: 1440x900
captured_at: 2026-05-09T09:14:00Z

ux_findings:
  reading_pattern_detected: "Z-pattern partiel — titre site à gauche, badges scope/conformité au centre, CTAs à droite, puis ligne de 3 KPIs scope, puis tabs, puis double colonne 'Indicateurs clés' / 'Intelligence énergétique'"
  hero_message_present: false
  hero_message_clarity: 2
  cta_position_consistent: true
  cognitive_load_score: 4
  notes: "Le hero est un en-tête fiche site classique (titre + adresse + KPIs ligne) sans narrative éditoriale 2-3 lignes. Pas de récit qui dit 'voici ce qui mérite attention sur ce site cette semaine'. Densité d'information forte mais récit absent — c'est plus un dashboard qu'un briefing."

ui_findings:
  red_surface_ratio_estime: "0.02"
  font_families_count_estime: 2
  font_sizes_count_estime: 6
  alignment_grid_respected: partiel
  whitespace_balance: 3
  doctrine_palette_journal_respectee: true
  notes: "Palette crème/sable correcte, badges 'Bon état' vert et 'Compléter les données' bleu cohérents. Ligne KPIs scope (605 MWh / 7500 € / 3€) mélange tailles et couleurs. Tabs 'Résumé / Énergie / Conformité / Analytics / Factures / Achat / Flexibilité / Onboarding / Contrats / Puissance' = 10 tabs, c'est très dense — frôle l'anti-pattern 'menus à 4 niveaux'."

cx_findings:
  next_action_obviousness: 3
  drill_down_breadcrumb_present: true
  back_navigation_predictable: true
  state_persistence_visible: true
  notes: "Breadcrumb 'Patrimoine · Sites · Groupe HELIOS · HELIOS Immobilier SAS · Siège HELIOS Paris' = drill-down explicite et hiérarchique, conforme principe 11. CTAs 'Exécuter rapport' + 'Compléter les données' visibles à droite — bonne convention. Bouton 'Bon état' agit-il comme CTA ? Ambigu."

customer_success_findings:
  time_to_first_decision_seconds_estime: 45
  onboarding_friction: 3
  empty_state_helpful: n/a
  error_state_actionable: n/a
  test_dirigeant_non_sachant_pass: false
  test_3_secondes_pass: false
  notes: "Un dirigeant non-sachant ne sait pas en 3s ce qu'il doit faire ici : trop d'indicateurs simultanés (10 tabs + 2 colonnes 'Indicateurs clés' et 'Intelligence énergétique' avec 3 KPIs chacune + zone Anomalies en bas). Le test des 3s échoue : pas de phrase qui résume la situation du site. Le 'Score conformité 16%' visible en haut est inquiétant mais sans contextualisation narrative."

violations_vs_grammar:
  - law: "L1_hero_preambule"
    severity: P0
    description: "Aucune narrative 2-3 lignes en intro après le titre. La page commence directement par une grille de KPIs et badges — anti-pattern §6.1 explicite : 'Page qui commence par un tableau ou une grille de KPIs sans préambule'."
  - law: "L3_kpi_3_max_tooltip_source"
    severity: P0
    description: "Bien plus de 3 KPIs visibles au-dessus du fold (3 ligne haute + 3 'Indicateurs clés' + 3 'Intelligence énergétique' = 9 KPIs simultanés). Aucun tooltip '?' visible. Violation directe de §5 'KPIs : 3 maximum'."
  - law: "L6_footer_source_timestamp"
    severity: P1
    description: "Pas de SolPageFooter visible avec Source · Confiance · Mis à jour. Le contenu est riche mais non sourcé en pied de page."
  - law: "L7_densite_editoriale"
    severity: P1
    description: "Densité d'information très élevée mais peu structurée éditorialement : 10 tabs en barre, 2 colonnes parallèles, blocs 'Pointes de livraison' / 'Anomalies détectées' empilés. Violation principe 8 'simplicité iPhone-grade'."
  - law: "L8_kicker_breadcrumb"
    severity: P2
    description: "Breadcrumb hiérarchique présent (point fort) mais pas de kicker éditorial typographié mono ('SITE · SEMAINE 19 · BUREAUX PARIS') — c'est un fil d'Ariane technique au sens §5."
  - law: "L9_action_pousse_pas_tire"
    severity: P1
    description: "La page ne pousse pas une action prioritaire. 'Compléter les données' est un CTA générique, pas un signal métier (ex : 'votre site dérive de baseline depuis 3 semaines, voici quoi vérifier'). Violation principe 6."
  - law: "L10_coherence_chiffres"
    severity: P2
    description: "605 MWh apparaît dans le hero ET dans 'Indicateurs clés' — cohérent. Mais 7 500 € (Pointe) vs 7 500 € budget vs 3 € (Intensité ?) demande au lecteur de décoder lui-même."

screenshots:
  - screenshots/site-paris-bureaux/1440x900-above.png
  - screenshots/site-paris-bureaux/1440x900-full.png
  - screenshots/site-paris-bureaux/1024x1366-above.png

quick_wins_proposes:
  - "Ajouter une narrative 2-3 lignes sous le titre (ex : 'Ce siège tertiaire 605 MWh/an dérive de 4% vs baseline. Conformité DT à 16% — jalon 2030 à risque. 4 actions prioritaires identifiées')."
  - "Réduire les KPIs above-the-fold à 3 max (consommation, conformité, économie potentielle), reporter les autres en tab 'Énergie'."
  - "Ajouter SolPageFooter SCM en bas (Source RegOps + ConsumptionUnified · Confiance · Mis à jour)."

verdict_global: "Site360 est riche en données mais structuré comme un dashboard classique, pas comme un briefing site. Le drill-down breadcrumb est exemplaire (point fort). Mais l'absence de narrative hero, la prolifération de KPIs (≥9 above-fold) et les 10 tabs violent frontalement §5 et §6.1. Score : 5/10."
