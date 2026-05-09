view: /?actionCenter=open&tab=actions
slug: centre-action
viewport_baseline: 1440x900
captured_at: 2026-05-09T09:14:00Z

ux_findings:
  reading_pattern_detected: "F-pattern vertical (titre slide-over → tabs → liste 8 items homogènes)"
  hero_message_present: false
  hero_message_clarity: 4
  cta_position_consistent: true
  cognitive_load_score: 3
  notes: "Titre 'Centre d'actions' minimal sans kicker ni narrative. 3 tabs (Actions 8 / Alertes / Historique) + liste verticale de 8 items quasi-tous similaires ('Site X nécessite une revue conformité'). Aucun préambule éditorial, aucune hiérarchisation. Pas de phrase 'voici ce qui mérite votre attention en priorité aujourd'hui'."

ui_findings:
  red_surface_ratio_estime: "0.0"
  font_families_count_estime: 2
  font_sizes_count_estime: 4
  alignment_grid_respected: true
  whitespace_balance: 4
  doctrine_palette_journal_respectee: true
  notes: "Slide-over crème/blanc avec puces vertes uniformes pour les 8 items. Palette journal respectée mais zéro signal couleur de criticité (toutes les puces vertes alors que 4 items concernent conformité = P0 légal, et 4 autres concernent des données patrimoniales incomplètes = P2). Whitespace généreux en bas (~50 % de hauteur vide après le 8e item)."

cx_findings:
  next_action_obviousness: 4
  drill_down_breadcrumb_present: false
  back_navigation_predictable: true
  state_persistence_visible: true
  notes: "Le compteur '8' sur tab Actions est clair. Bouton croix de fermeture standard. 'Voir tout l'historique →' en footer mais aucune action 'Tout traiter' ou 'Trier par impact €'. Items cliquables (chevron droit) mais pas de prévisualisation au survol."

customer_success_findings:
  time_to_first_decision_seconds_estime: 60
  onboarding_friction: 4
  empty_state_helpful: n/a
  error_state_actionable: false
  test_dirigeant_non_sachant_pass: false
  test_3_secondes_pass: false
  notes: "Test 3 secondes échoué : 8 items quasi-identiques sans hiérarchie, sans impact € visible, sans deadline visible. Test dirigeant non-sachant échoué : 'nécessite une revue conformité' / 'Aucun contrat actif' / 'Aucun point de livraison' / 'Données patrimoniales incomplètes (25 %)' — copy purement technique, aucune transformation en récit (que faire ? quel risque financier ? quelle deadline ?). 4 items concernant 'Site Test Phase 2' = pollution data jamais filtrée — preuve que le centre d'action est un journal brut pas un briefing."

violations_vs_grammar:
  - law: "L1_hero_preambule"
    severity: P0
    description: "Aucun hero / aucune narrative / aucun préambule. Le panel commence directement par la liste. Anti-pattern §6.1 'page qui commence par un tableau ou une grille sans préambule' (transposé au slide-over)."
  - law: "L3_kpi_3_max_tooltip_source"
    severity: P1
    description: "Aucun KPI synthétique ('5 actions critiques / 1,2 M€ exposition / 30 jours avant prochaine deadline'). Le compteur '8' sur le tab est le seul agrégat — pas de tooltip ni source."
  - law: "L4_acronymes_transformes"
    severity: P1
    description: "'revue conformité' / 'point de livraison' / 'contrat actif' restent des termes métier non vulgarisés. Aucune phrase orientée action ('vérifier le siège HELIOS Paris avant le 30/05 — 7 500 € de pénalité Décret Tertiaire évitable')."
  - law: "L5_empty_state_contextualise"
    severity: P2
    description: "Pas d'empty state ici (8 items présents) mais la zone vide en bas du panel (~400 px) viole le principe 4 'pas plus de 200 px sans information utile'."
  - law: "L6_footer_source_timestamp"
    severity: P0
    description: "Aucun footer Source · Confiance · Mis à jour. On ne sait pas d'où viennent ces 8 actions, quand elles ont été générées, ni leur niveau de confiance. Anti-pattern §6.4 KPI/signal sans source."
  - law: "L7_densite_editoriale"
    severity: P0
    description: "8 items sur ~600 px, puis ~400 px de vide jusqu'au footer 'Voir tout l'historique'. >200 px sans information utile = violation directe principe 4. Densité éditoriale très faible : aucun item n'apporte impact €, deadline, criticité, source."
  - law: "L8_kicker_breadcrumb"
    severity: P1
    description: "Pas de kicker contextualisé ('CENTRE D'ACTION · SEMAINE 19 · 5 PRIORITAIRES SUR 8') — juste le titre brut 'Centre d'actions'."
  - law: "L9_action_pousse_pas_tire"
    severity: P0
    description: "Liste plate 8 items quasi-identiques sans hiérarchisation par impact ni urgence. Le produit ne pousse rien — il liste. Violation directe principe 6 doctrine ('le produit pousse, ne tire pas') et principe 5 ('glanceable summary')."
  - law: "L10_coherence_chiffres"
    severity: P2
    description: "4 items concernent 'Site Test Phase 2' (1 contrat / 1 conformité / 1 PDL / 1 patrimoine 25 %). Doublon partiel : sont-ce 4 actions distinctes ou 1 site mal configuré ? Pas de groupement par site visible — risque de divergence de comptage avec d'autres écrans."

screenshots:
  - screenshots/centre-action/1440x900-above.png
  - screenshots/centre-action/1440x900-full.png
  - screenshots/centre-action/1024x1366-above.png

quick_wins_proposes:
  - "Ajouter un hero éditorial 2 lignes en haut du panel : kicker 'CENTRE D'ACTION · SAMEDI 9 MAI · 5 PRIORITAIRES SUR 8' + narrative ('5 sites à revoir avant le 30/05 — exposition Décret Tertiaire 37 500 € évitable')."
  - "Trier les 8 items par impact € et urgence, ajouter un badge couleur (rouge / ambre / vert) ; grouper les 4 actions 'Site Test Phase 2' sous une seule entrée 'site mal configuré'."
  - "Ajouter un footer Source · Confiance · Mis à jour le — et un encart synthèse 3 chiffres haut de panel (actions critiques · € exposition · prochaine deadline)."

verdict_global: "Le centre d'action est aujourd'hui un journal brut sans hero ni hiérarchisation : exactement l'anti-pattern §6.1 et §6.4 que la doctrine cherche à éliminer. C'est pourtant le composant cardinal du principe 6 ('le produit pousse'). Score 3/10 — fondations Sol UI présentes (palette, typo) mais grammaire éditoriale absente."
