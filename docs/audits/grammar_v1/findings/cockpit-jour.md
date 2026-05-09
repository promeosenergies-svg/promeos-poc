view: /cockpit/jour
slug: cockpit-jour
viewport_baseline: 1440x900
captured_at: 2026-05-09T09:14:00Z

ux_findings:
  reading_pattern_detected: "F-pattern (titre haut-gauche, KPIs en bandeau, charts dessous, liste actions en bas)"
  hero_message_present: true
  hero_message_clarity: 2
  cta_position_consistent: partiel
  cognitive_load_score: 3
  notes: "Le titre Fraunces 'Bonjour — voici ce qui mérite votre attention · samedi 9 mai' joue son rôle de hero mais la narrative 2-3 lignes sourcée prévue par §5 n'est pas visible — l'utilisateur passe directement aux 3 KPIs sans transition éditoriale. Les 4 cartes 'Site … nécessite une revue conformité' en bas saturent le bas de page et masquent toute hiérarchisation (toutes même priorité visuelle, même libellé)."

ui_findings:
  red_surface_ratio_estime: "0.18"
  font_families_count_estime: 2
  font_sizes_count_estime: 7
  alignment_grid_respected: true
  whitespace_balance: 3
  doctrine_palette_journal_respectee: true
  notes: "Palette crème/brun chaleureuse respectée. Ambre clair pour les rangées d'actions. Triptyque Fraunces (titre) + DM Sans (body) + JetBrains Mono (chiffres KPIs) cohérent. Forte densité visuelle dans les KPIs (variation %) mais peu d'espace de respiration entre charts et liste d'actions — le 1024 montre un chevauchement de densité."

cx_findings:
  next_action_obviousness: 3
  drill_down_breadcrumb_present: true
  back_navigation_predictable: true
  state_persistence_visible: true
  notes: "Breadcrumb 'PROMEOS · Briefing du jour' visible avec switch d'angle (Briefing du jour / Synthèse stratégique). Bouton 'Centre d'action' en haut à droite. Mais 4 actions identiques 'revue conformité' empilées ne disent pas laquelle traiter en premier — pas de scoring impact € visible."

customer_success_findings:
  time_to_first_decision_seconds_estime: 45
  onboarding_friction: 3
  empty_state_helpful: n/a
  error_state_actionable: n/a
  test_dirigeant_non_sachant_pass: false
  test_3_secondes_pass: false
  notes: "Test 3 secondes échoué : un DAF non-sachant voit '16,6 MWh', '5,0 t CO₂e', '121 j' sans comprendre la trajectoire (variations affichées mais pas le sens 'bon ou mauvais'). Test dirigeant non-sachant échoué : 4 actions identiques en bas ne disent pas par où commencer."

violations_vs_grammar:
  - law: "L1_hero_preambule"
    severity: P1
    description: "Hero présent (titre Fraunces + date) mais narrative 2-3 lignes sourcée absente entre titre et KPIs — l'utilisateur saute directement aux chiffres sans préambule éditorial."
  - law: "L3_kpi_3_max_tooltip_source"
    severity: P0
    description: "3 KPIs respectés (énergie / CO₂ / jours) mais aucun '?' tooltip visible et aucun footer source (RegOps / ADEME / EPEX) attaché aux KPIs. Crédibilité B2B affaiblie, anti-pattern §6.4."
  - law: "L4_acronymes_transformes"
    severity: P2
    description: "'CO₂e' (équivalent) et unités 't' / 'MWh' / 'j' affichées brutes sans transformation en récit pour non-sachant. Pas de phrase 'cela représente l'équivalent de…'."
  - law: "L6_footer_source_timestamp"
    severity: P0
    description: "Footer Source · Confiance · Mis à jour absent en bas de page (anti-pattern §6.4 KPI sans définition/source/formule). Aucune mention 'mis à jour le' visible."
  - law: "L7_densite_editoriale"
    severity: P1
    description: "Liste des 4-5 actions de bas de page utilise des rangées de ~80-100 px chacune avec contenu textuel quasi-identique ('Site X nécessite une revue conformité') = densité éditoriale faible, pas d'impact € visible, pas de criticité différenciée."
  - law: "L9_action_pousse_pas_tire"
    severity: P1
    description: "Les 'actions' empilées en bas listent simplement les sites sans pousser une priorité claire. Le produit n'oriente pas vers 'commencez par X parce que Y' (principe 6 doctrine)."

screenshots:
  - screenshots/cockpit-jour/1440x900-above.png
  - screenshots/cockpit-jour/1440x900-full.png
  - screenshots/cockpit-jour/1024x1366-above.png

quick_wins_proposes:
  - "Ajouter une narrative 2-3 lignes sous le titre ('Cette semaine, votre patrimoine consomme X MWh, soit Y % vs SA-1, avec 4 sites à revoir avant le 30/05') pour passer L1."
  - "Attacher un tooltip '?' à chaque KPI avec définition + source (ADEME pour CO₂, RegOps pour conformité), et ajouter un SolPageFooter unique (Source · Confiance · Mis à jour)."
  - "Trier les 4-5 actions par criticité/impact € et ajouter un kicker typé 'À FAIRE D'ICI 30/05' au lieu de 4 lignes identiques."

verdict_global: "La vue respecte la palette journal Sol et le triptyque typo, mais la grammaire éditoriale §5 reste partielle : narrative manquante, KPIs sans tooltip ni footer source, actions empilées sans hiérarchisation. Score 5/10 — cosmétiquement Sol, mais doctrinalement encore proche d'un dashboard."
