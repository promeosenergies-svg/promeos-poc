view: /onboarding
slug: onboarding
viewport_baseline: 1440x900
captured_at: 2026-05-09T07:18:19Z

ux_findings:
  reading_pattern_detected: "F-pattern"
  hero_message_present: true
  hero_message_clarity: 2
  cta_position_consistent: false
  cognitive_load_score: 2
  notes: "FINDING CRITIQUE: la route /onboarding ne mene PAS a un onboarding. Elle affiche en realite la page Cockpit Strategique 'Synthese strategique - semaine 19 pour la direction' (sidebar 'Synthese strategique' active, kicker COCKPIT > VUE COMEX). Aucun parcours premier pas, aucun wizard, aucune introduction. Pour un nouvel utilisateur arrivant sur /onboarding, la page ne propose ni accueil, ni explication produit, ni etapes guidees."

ui_findings:
  red_surface_ratio_estime: "0.05"
  font_families_count_estime: 3
  font_sizes_count_estime: 5
  alignment_grid_respected: true
  whitespace_balance: 3
  doctrine_palette_journal_respectee: true
  notes: "Visuel doctrinal Sol correct (Fraunces titre + narrative + cards typees CONFORMITE / CONSO / ACHAT) mais c'est l'UI du Cockpit Strategique, pas d'un onboarding. Triptyque typo respecte, palette journal creme/brun OK."

cx_findings:
  next_action_obviousness: 1
  drill_down_breadcrumb_present: true
  back_navigation_predictable: false
  state_persistence_visible: false
  notes: "Pour un parcours onboarding: aucune progression (1/3, 2/3...) visible, aucun bouton Suivant/Passer, aucun objectif d'etape. Le breadcrumb 'COCKPIT > VUE COMEX' contredit la route /onboarding - rupture de coherence URL/contenu. Bouton 'Rapport COMEX' en haut a droite n'a aucun sens pour un nouvel arrivant."

customer_success_findings:
  time_to_first_decision_seconds_estime: 90
  onboarding_friction: 5
  empty_state_helpful: false
  error_state_actionable: false
  test_dirigeant_non_sachant_pass: false
  test_3_secondes_pass: false
  notes: "Test 2 doctrine §7 (dirigeant non-sachant): FAIL absolu. Un DAF non-spécialiste qui arrive sur /onboarding pour la 1re fois voit 'Synthese strategique semaine 19' avec 90 anomalies / 19,8 k€ / 0,52 GWh / OPERAT / DT / BACS / CVC / ARENH - acronymes denses sans transformation, prerequiert deja la connaissance produit. Test 8 emplacement: FAIL - URL /onboarding ne mene pas au bon contenu, doctrine §11 'le bon endroit pour chaque brique' viole. Onboarding friction maximale: rien ne prend l'utilisateur par la main."

violations_vs_grammar:
  - law: "L1_hero_preambule"
    severity: P0
    description: "Hero 'Synthese strategique - semaine 19 pour la direction' presuppose un utilisateur execute deja onboarde. Pour un nouvel arrivant /onboarding, aucun preambule de bienvenue ('Bienvenue sur PROMEOS - voici comment commencer en 3 minutes')."
  - law: "L4_acronymes_transformes"
    severity: P0
    description: "Cards exposent CVC (Decret BACS) / OPERAT / DT / BACS / APER / ARENH / TICGN / CSPE / 24/7 detection sans transformation. Doctrine §6.3 anti-pattern: 'acronymes bruts dans les titres'. Pour un onboarding, c'est disqualifiant."
  - law: "L8_kicker_breadcrumb"
    severity: P0
    description: "Kicker 'COCKPIT > VUE COMEX' contradictoire avec URL /onboarding. La doctrine §5 exige un kicker contextualise; ici il pointe vers une autre fonction du produit. Rupture de promesse URL <-> contenu."
  - law: "L9_action_pousse_pas_tire"
    severity: P0
    description: "Doctrine principe 6: 'le produit pousse, ne tire pas'. Sur /onboarding, AUCUNE poussee: pas d'etape 1, pas de CTA 'Connecter Enedis', pas de 'Importer 1re facture', pas d'invitation. L'utilisateur est largue devant un dashboard COMEX."
  - law: "L5_empty_state_contextualise"
    severity: P1
    description: "Aucun empty state d'accueil (organisation vide, premier site, premier compteur). Au lieu de l'aider a saisir patrimoine ou connecter compteur, le produit affiche directement les chiffres d'un patrimoine HELIOS demo deja peuple - desorientant en production reelle."
  - law: "L6_footer_source_timestamp"
    severity: P1
    description: "Page herite du footer Cockpit Strategique mais aucun footer specifique onboarding (etape X/Y, lien support, contact CS). Pour un parcours nouveau client, c'est attendu."
  - law: "L11_emplacement_brique"
    severity: P0
    description: "Doctrine §11 (test 8 emplacement): /onboarding doit mener a un onboarding, pas au Cockpit. Mismatch URL/contenu = anti-pattern §6.2 'item de nav qui mene a une page vide ou en chantier'."

screenshots:
  - screenshots/onboarding/1440x900-above.png
  - screenshots/onboarding/1440x900-full.png
  - screenshots/onboarding/1024x1366-above.png

quick_wins_proposes:
  - "URGENT: implementer une vraie page /onboarding avec wizard 3-5 etapes (Bienvenue / Connecter Enedis ou GRDF / Importer 1re facture / Definir patrimoine / Choisir module pilote)."
  - "Si /onboarding doit rester redirige court terme: rediriger explicitement vers /cockpit/strategique ou afficher un splash 'Bienvenue, demarrons par...' avec 3 CTA push."
  - "Ajouter un parcours dirigeant non-sachant: glossaire interactif des 8 acronymes critiques (TURPE / OPERAT / DT / BACS / APER / ARENH / NEBCO / CSPE) accessibles sans formation prealable."
  - "Ajouter etat de progression (1/N) + bouton Passer + sauvegarde reprise."
  - "Verifier dans NavRegistry.js si /onboarding est cable ou orphelin; si orphelin, soit l'implementer Sprint 2, soit le retirer de la nav."

verdict_global: "Score 1.5/10. La route /onboarding est manifestement non implementee et fallback vers le Cockpit Strategique. Pour la cible primaire doctrine (dirigeant non-sachant), c'est un anti-pattern bloquant: aucune main tendue, aucun parcours guide, acronymes bruts d'emblee. P0 absolu pour la roadmap Sol."
