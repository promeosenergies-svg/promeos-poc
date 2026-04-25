/**
 * PROMEOS — Business errors catalog (frontend)
 *
 * Catalogue FR centralisé pour les messages d'erreur métier et les
 * fallbacks narratifs utilisés par les composants Sol quand les données
 * API sont absentes, partielles ou en erreur.
 *
 * Chaque entrée suit la forme :
 *   {
 *     tag:        'attention' | 'afaire' | 'succes' | 'refuse',
 *     tagLabel:   string (ex "À regarder", "Info temporaire"),
 *     title:      phrase courte affirmative,
 *     body:       phrase explicative, vouvoiement strict,
 *     footer:     ligne mono 11px optionnelle,
 *     footerRight: marqueur court optionnel (ex "✓ Clean", "⌘K"),
 *     ctaLabel?:  libellé CTA primaire (first-time empty states T2V),
 *     ctaHref?:   route React Router pour navigate (query params OK),
 *   }
 *
 * Convention clé : <module>.<cas> (ex "conformite.no_drift").
 * Helper `businessErrorFallback(key)` retourne l'entrée formatée
 * pour passer directement dans un SolWeekCard ou SolKpiCard.
 *
 * Alignement stratégie CX : ces fallbacks évitent les "—" disgracieux,
 * préservent la voix Sol (vouvoiement, chiffres d'abord quand possible)
 * et gardent toujours une issue (jamais de dead-end pour l'utilisateur).
 */

export const BUSINESS_ERRORS = {
  // ── Conformité ───────────────────────────────────────────────────────────
  'conformite.no_drift': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune dérive détectée',
    body: 'Tous vos sites respectent leur trajectoire Décret Tertiaire cette semaine.',
    footer: 'Détection automatique active',
    footerRight: '✓ Stable',
  },
  'conformite.no_recent_validation': {
    tag: 'afaire',
    tagLabel: 'À venir',
    title: 'En attente de prochaine échéance',
    body: "Votre prochaine validation conformité interviendra lors de la prochaine itération OPERAT ou d'un dépôt BACS/APER.",
    footer: 'Veille réglementaire active',
    footerRight: '—',
  },
  'conformite.no_upcoming': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucune échéance sous 90 jours',
    body: 'Votre calendrier réglementaire est à jour pour le trimestre.',
    footer: 'Prochaine fenêtre : audit OPERAT annuel',
    footerRight: '✓ Clean',
  },
  'conformite.api_down': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Calcul en cours',
    body: 'Votre score Décret Tertiaire est en cours de recalcul. Revenez dans quelques minutes.',
    footer: 'Réessai automatique dans 2 min',
    footerRight: '⟳',
  },

  // ── Bill Intelligence (Phase 4.2) ────────────────────────────────────────
  'billing.no_anomalies_detected': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune anomalie détectée',
    body: 'Toutes vos factures analysées ce mois sont conformes au shadow billing.',
    footer: 'Moteur shadow v4.2 · 100 % couverture',
    footerRight: '✓ Clean',
  },
  // Alias rétro-compat (Phase 4.1)
  'billing.no_anomalies': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune anomalie détectée',
    body: 'Toutes vos factures analysées ce mois sont conformes au shadow billing.',
    footer: 'Moteur shadow v4.2 · 100 % couverture',
    footerRight: '✓ Clean',
  },
  'billing.no_invoices_yet': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Importez vos premières factures',
    body: "L'analyse d'anomalies et le shadow billing se déclenchent dès 3 factures importées.",
    footer: 'Import PDF ou CSV',
    footerRight: 'Automatisable',
  },
  'billing.no_invoices': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Importez vos premières factures',
    body: "L'analyse d'anomalies et le shadow billing se déclenchent dès 3 factures importées.",
    footer: 'Import PDF ou CSV',
    footerRight: 'Automatisable',
  },
  'billing.recovery_in_progress': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Contestations en cours de traitement',
    body: "Sol suit l'avancement de vos courriers de contestation. Délai moyen de retour fournisseur\u00a0: 45\u00a0jours.",
    footer: 'Suivi automatique actif',
    footerRight: 'Automatisable',
  },
  'billing.api_down': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Analyse en cours',
    body: 'Votre historique de facturation est en cours de recalcul. Revenez dans quelques minutes.',
    footer: 'Réessai automatique dans 2 min',
    footerRight: '⟳',
  },

  // ── Patrimoine (Phase 4.3) ───────────────────────────────────────────────
  'patrimoine.no_sites': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Créez votre premier site',
    body: 'Commencez par importer votre patrimoine depuis SIREN ou créer un site manuellement.',
    footer: 'Onboarding SIRENE disponible',
    footerRight: 'Automatisable',
    ctaLabel: 'Importer depuis SIREN',
    ctaHref: '/patrimoine?wizard=open',
  },
  'patrimoine.collection_in_progress': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Collecte des données en cours',
    body: 'Vos consommations et surfaces sont en cours de rapprochement. Revenez dans quelques minutes.',
    footer: 'Collecte automatique active',
    footerRight: '⟳',
  },
  'patrimoine.eui_unavailable': {
    tag: 'attention',
    tagLabel: 'Info',
    title: 'Intensité énergétique indisponible',
    body: 'Renseignez les surfaces de vos sites et importez 12\u00a0mois de consommations pour activer le calcul EUI.',
    footer: 'Benchmark ADEME ODP 2024',
    footerRight: '—',
  },
  'patrimoine.all_conforming': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Tous vos sites dans la cible',
    body: 'Aucun site ne dépasse significativement son benchmark ADEME. Votre patrimoine est bien positionné.',
    footer: 'mis à jour automatiquement',
    footerRight: '✓ Clean',
  },

  // ── Achat énergie (Phase 4.4) ────────────────────────────────────────────
  'achat.no_contracts': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Saisissez vos contrats actuels',
    body: 'Le radar de renouvellement et les scénarios post-ARENH se déclenchent dès 1 contrat enregistré.',
    footer: 'Saisie manuelle ou import',
    footerRight: '—',
  },
  'achat.no_renewals_90j': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucun renouvellement sous 90 jours',
    body: 'Votre portefeuille contractuel est stable pour le trimestre à venir.',
    footer: 'Prochaine échéance > 3 mois',
    footerRight: '✓ Stable',
  },
  'achat.all_stable': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Portefeuille contractuel stable',
    body: 'Aucune décision urgente. Votre position tarifaire est cohérente avec le marché.',
    footer: 'surveillance continue',
    footerRight: '✓ Stable',
  },
  'achat.market_data_unavailable': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Données marché en cours de collecte',
    body: 'Les prix EPEX Spot et forward sont en cours de rafraîchissement. Revenez dans quelques minutes.',
    footer: 'source EPEX · MAJ automatique',
    footerRight: '⟳',
  },
  'achat.no_scenarios': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Simulez votre premier scénario',
    body: "Lancez l'assistant d'achat pour comparer offres fournisseurs, indexation et hedging forward.",
    footer: 'assistant disponible',
    footerRight: 'Automatisable',
  },

  // ── Command Center (Lot 1.1) ─────────────────────────────────────────────
  'command.all_clean': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Patrimoine sous contrôle',
    body: 'Aucune alerte critique, toutes les échéances sont sur leur trajectoire.',
    footer: 'Sol veille en continu',
    footerRight: '✓ Stable',
  },
  'command.no_sol_actions': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucune action Sol à valider',
    body: 'Le moteur de détection tourne en arrière-plan. Les prochaines opportunités apparaîtront ici.',
    footer: 'Détection automatique active',
    footerRight: '⟳',
  },

  // ── APER (Lot 1.2) ───────────────────────────────────────────────────────
  'aper.no_eligible': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucun site assujetti APER',
    body: 'Aucun de vos sites n\u2019atteint les seuils d\u2019assujettissement (toit ≥ 500 m² ou parking ≥ 1 500 m²).',
    footer: 'Loi APER non applicable',
    footerRight: '—',
  },
  'aper.study_in_progress': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Études PV en cours',
    body: 'Les études de potentiel solaire sont en cours de réalisation pour vos sites éligibles.',
    footer: 'Sol peut préparer les dossiers DP',
    footerRight: 'Automatisable',
  },

  // ── Monitoring Performance (Lot 1.3) ─────────────────────────────────────
  'monitoring.no_drift': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune dérive active',
    body: 'Toutes vos consommations respectent leur baseline de référence ajustée DJU.',
    footer: 'Baseline Météo-France calibrée',
    footerRight: '✓ Stable',
  },
  'monitoring.calibration_needed': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Calibration de la baseline requise',
    body: 'Importez 12 mois de consommations pour activer la détection de dérives avec normalisation DJU.',
    footer: 'Import télérelève Enedis',
    footerRight: 'Automatisable',
  },

  // ── Conformité Tertiaire (Lot 6 Phase 4) ────────────────────────────────
  'conformite.no_dashboard': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Dashboard conformité indisponible',
    body: "Aucune donnée agrégée Décret Tertiaire n'est disponible. Vérifiez l'import du patrimoine ou contactez le support.",
    footer: 'endpoint /api/tertiaire/dashboard',
    footerRight: '⟳',
  },
  'conformite.no_efa': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucune EFA enregistrée',
    body: "Créez votre première EFA (Entité Fonctionnelle d'Assujettissement) pour démarrer le suivi Décret Tertiaire 2030.",
    footer: 'wizard création disponible',
    footerRight: 'Automatisable',
  },

  // ── Segmentation B2B (Lot 6 Phase 3) ────────────────────────────────────
  'segmentation.low_confidence': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Confiance de segmentation insuffisante',
    body: 'Complétez le questionnaire métier pour améliorer la confiance et obtenir des recommandations PROMEOS adaptées à votre activité.',
    footer: 'minimum 3 questions requises',
    footerRight: 'Automatisable',
  },
  'segmentation.no_naf': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Code NAF manquant',
    body: 'Renseignez votre code NAF (SIRET SIRENE) dans la fiche patrimoine pour activer la détection automatique de typologie.',
    footer: 'import SIRET disponible',
    footerRight: 'Automatisable',
  },

  // ── Compliance Pipeline (Lot 6 Phase 5) ─────────────────────────────────
  'pipeline.no_sites': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Pipeline conformité indisponible',
    body: 'Aucun site dans votre portefeuille. Rendez-vous sur Patrimoine pour importer ou créer vos premiers sites et activer le suivi de conformité.',
    footer: 'import SIRENE disponible',
    footerRight: 'Automatisable',
  },
  'pipeline.filter_no_results': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun site ne correspond à vos filtres',
    body: 'Élargissez ou réinitialisez les filtres (gate, framework, fiabilité) pour retrouver des résultats. Le bouton « Réinitialiser filtres » en haut à droite repart à zéro.',
    footer: 'filtres actifs',
    footerRight: '—',
  },
  'pipeline.all_ready': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Portefeuille entièrement prêt',
    body: 'Tous vos sites passent la gate data conformité et aucune échéance n\u2019est imminente. Continuez la consolidation trajectoire 2030 et attestations BACS / APER.',
    footer: 'surveillance continue',
    footerRight: '✓ Stable',
  },

  // ── Base de connaissance (Lot 6 Phase 2) ────────────────────────────────
  'kb.no_results': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Base de connaissance vide',
    body: "Aucun article indexé pour l'instant. Uploadez votre premier document PDF ou CSV via l'onglet Documents pour démarrer l'indexation FTS5.",
    footer: 'import PDF/CSV disponible',
    footerRight: 'Automatisable',
  },
  'kb.filter_no_results': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun résultat pour votre recherche',
    body: 'Modifiez ou réinitialisez les filtres pour retrouver des articles. La recherche couvre titres, tags et contenu.',
    footer: 'filtres actifs',
    footerRight: '—',
  },

  // ── Watchers (Lot 2 Phase 7) ────────────────────────────────────────────
  'watcher.no_watchers': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun watcher configuré',
    body: 'Créez votre premier watcher pour activer la veille réglementaire et marché automatisée (Légifrance, CRE, RTE).',
    footer: 'configuration légère',
    footerRight: 'Automatisable',
  },
  'watcher.filter_no_results': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun événement ne correspond à vos filtres',
    body: 'Modifiez ou réinitialisez les filtres pour retrouver des résultats.',
    footer: 'filtres actifs',
    footerRight: '—',
  },
  'watcher.pending': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: "Watchers en cours d'initialisation",
    body: 'Les premiers événements seront captés sous 24 h après la création du watcher.',
    footer: 'délai typique',
    footerRight: '⟳',
  },

  // ── Profils horaires (Lot 2 Phase 6) ────────────────────────────────────
  'hourly.no_data': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Données horaires insuffisantes',
    body: "Activez le comptage 30-min dans la fiche Patrimoine du site pour déclencher l'analyse du profil horaire.",
    footer: 'comptage 30-min requis',
    footerRight: 'Automatisable',
  },
  'hourly.profile_pending': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Analyse de profil en cours',
    body: 'Sol analyse vos courbes de charge pour qualifier le profil comportemental. Premier résultat disponible après 14 jours de mesures 30-min.',
    footer: 'moteur anomalies actif',
    footerRight: '⟳',
  },

  // ── Usages (Lot 2 Phase 5) ──────────────────────────────────────────────
  'usage.no_usages': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun usage segmenté',
    body: 'Importez les données de vos compteurs divisionnaires pour activer la segmentation par usage (CVC, éclairage, IT, process).',
    footer: 'minimum 30 jours de données',
    footerRight: 'Automatisable',
  },
  'usage.segmentation_pending': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Segmentation usages en cours',
    body: 'Sol analyse vos courbes de charge pour identifier les usages dominants. Premiers résultats disponibles sous 7 jours de mesures.',
    footer: 'moteur segmentation actif',
    footerRight: '⟳',
  },
  'usage.benchmark_unavailable': {
    tag: 'attention',
    tagLabel: 'Info',
    title: 'Benchmark archétype non disponible',
    body: "Votre activité (code NAF) n'a pas encore de benchmark ADEME OID publié. Les comparaisons se feront uniquement vs votre baseline propre.",
    footer: 'ADEME OID 2024',
    footerRight: '—',
  },

  // ── Renouvellements (Lot 2 Phase 4) ─────────────────────────────────────
  'renewal.no_renewals': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: "Aucun renouvellement dans l'horizon",
    body: "Votre portefeuille est stable sur cette fenêtre. Élargissez l'horizon pour voir les échéances à plus long terme.",
    footer: 'surveillance continue',
    footerRight: '✓ Stable',
  },
  'renewal.filter_no_results': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun renouvellement ne correspond à vos filtres',
    body: 'Modifiez ou réinitialisez les filtres pour retrouver des résultats.',
    footer: 'filtres actifs',
    footerRight: '—',
  },
  'renewal.scenarios_pending': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Scénarios en cours de calcul',
    body: 'Les scénarios de renégociation sont générés sous 24 h après import des contrats. Cliquez sur une ligne pour déclencher le calcul prioritaire.',
    footer: 'moteur scénarios V99',
    footerRight: '⟳',
  },

  // ── Contrats (Lot 2 Phase 3) ────────────────────────────────────────────
  'contract.no_contracts': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun contrat enregistré',
    body: 'Importez vos contrats en cours depuis CSV ou PDF pour activer le radar de renouvellement et les KPIs portefeuille.',
    footer: 'import CSV/PDF disponible',
    footerRight: 'Automatisable',
    ctaLabel: 'Configurer le patrimoine',
    ctaHref: '/patrimoine?wizard=open',
  },
  'contract.filter_no_results': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucun contrat ne correspond à vos filtres',
    body: 'Modifiez ou réinitialisez les filtres pour retrouver des résultats. Utilisez le bouton « Réinitialiser filtres » en haut à droite.',
    footer: 'filtres actifs',
    footerRight: '—',
  },
  'contract.price_unavailable': {
    tag: 'attention',
    tagLabel: 'Info',
    title: 'Prix non renseigné',
    body: "Ce contrat est indexé ou n'a pas encore de prix fixe. Le prix pondéré portefeuille l'exclut du calcul.",
    footer: 'à compléter si prix fixe disponible',
    footerRight: '—',
  },

  // ── Anomalies (Lot 2 Phase 2) ───────────────────────────────────────────
  'anomaly.no_anomalies': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune anomalie active sur votre patrimoine',
    body: "Sol continue à surveiller les factures et les signaux de consommation chaque nuit. Vous serez alerté dès qu'une nouvelle anomalie apparaît.",
    footer: 'Détection ML + shadow billing actifs',
    footerRight: '✓ Clean',
  },
  'anomaly.filter_no_results': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucune anomalie ne correspond à vos filtres',
    body: 'Modifiez ou réinitialisez les filtres pour retrouver des résultats. Utilisez « Réinitialiser filtres » en haut à droite pour repartir à zéro.',
    footer: 'filtres actifs',
    footerRight: '—',
  },

  // ── Diagnostic consommation (Lot 3 Phase 5) ─────────────────────────────
  'diagnostic.no_insights': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune anomalie détectée sur la période',
    body: 'Votre patrimoine est stable sur la fenêtre analysée. Sol continuera à surveiller les profils chaque nuit.',
    footer: 'Détection ML + baseline DJU active',
    footerRight: '✓ Stable',
  },
  'diagnostic.seed_needed': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Lancez un premier diagnostic',
    body: "Importez au moins 30 jours de consommations pour activer la détection d'anomalies. Le bouton « Générer conso démo » simule un jeu de données pour validation.",
    footer: 'minimum 30 jours requis',
    footerRight: 'Automatisable',
  },

  // ── EFA — Décret Tertiaire (Lot 3 Phase 4) ──────────────────────────────
  'efa.proofs_missing': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Pièces justificatives manquantes',
    body: 'Complétez la saisie des pièces (facture, attestation, relevé) pour valider la déclaration OPERAT de cette EFA.',
    footer: 'Saisie requise · upload multi-format',
    footerRight: 'Automatisable',
  },
  'efa.no_findings': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune anomalie détectée',
    body: 'Votre EFA respecte la trajectoire réglementaire. Aucune dérive identifiée sur les obligations applicables.',
    footer: 'Évaluation déterministe active',
    footerRight: '✓ Clean',
  },
  'efa.on_track': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Trajectoire en avance sur les objectifs',
    body: 'Votre EFA dépasse déjà le jalon 2030. Continuez sur cette lancée pour sécuriser -40 % en 2040.',
    footer: 'Marge confortable',
    footerRight: '✓ Avance',
  },
  'efa.evaluation_pending': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Évaluation en attente du prochain OPERAT',
    body: 'Les premiers résultats de trajectoire seront disponibles après la prochaine déclaration OPERAT (fenêtre annuelle 30 septembre).',
    footer: 'Calendrier réglementaire actif',
    footerRight: '⟳',
  },

  // ── RegOps (Lot 3 Phase 3) ───────────────────────────────────────────────
  'regops.no_findings': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucun finding actif sur ce dossier',
    body: "Le moteur déterministe n'a identifié aucune obligation à risque pour ce site. Votre conformité est en ordre.",
    footer: 'Évaluation à jour',
    footerRight: '✓ Clean',
  },
  'regops.evaluation_unavailable': {
    tag: 'attention',
    tagLabel: 'Info temporaire',
    title: 'Évaluation en cours de recalcul',
    body: 'Sol réévalue ce dossier. Les résultats seront mis à jour automatiquement dans quelques minutes.',
    footer: 'Réessai automatique actif',
    footerRight: '⟳',
  },

  // ── Site360Sol (Lot 3 Phase 2) ───────────────────────────────────────────
  'site.not_found': {
    tag: 'attention',
    tagLabel: 'Info',
    title: 'Site introuvable dans votre périmètre',
    body: "Ce site n'appartient pas à votre scope actuel ou a été archivé. Revenez au patrimoine pour le localiser.",
    footer: 'Scope actuel actif',
    footerRight: '—',
  },
  'site.no_anomalies': {
    tag: 'succes',
    tagLabel: 'Bonne nouvelle',
    title: 'Aucune anomalie active',
    body: 'Les factures de ce site sont conformes au shadow billing ce mois.',
    footer: 'Moteur shadow v4.2',
    footerRight: '✓ Clean',
  },
  'site.no_reco': {
    tag: 'afaire',
    tagLabel: 'À faire',
    title: 'Aucune recommandation prioritaire',
    body: "Le moteur de détection n'a pas identifié de levier actionnable cette semaine sur ce site.",
    footer: 'Détection automatique active',
    footerRight: '⟳',
  },

  // ── Generic fallback ─────────────────────────────────────────────────────
  'generic.no_data': {
    tag: 'attention',
    tagLabel: 'Info',
    title: 'Données en cours de collecte',
    body: 'Cette section s\u2019enrichira automatiquement dès que les données correspondantes seront disponibles.',
    footer: '—',
    footerRight: '—',
  },
};

/**
 * Retourne l'entrée formatée pour injection directe dans un SolWeekCard.
 * Si la clé est inconnue, retourne l'entrée "generic.no_data".
 *
 * Fix Phase 4.5 : accepte un `slot` optionnel pour désambiguïser l'id
 * quand le même fallback est utilisé dans plusieurs cards consécutives
 * (ex : Card 2 ET Card 3 fallback sur 'achat.all_stable'). Évite les
 * "duplicate keys" warnings React.
 *
 * @param {string} key — ex "conformite.no_drift"
 * @param {string|number} [slot] — suffixe désambiguïsant (ex "slot2")
 * @returns {{tagKind, tagLabel, title, body, footerLeft, footerRight, id}}
 */
export function businessErrorFallback(key, slot = null) {
  const entry = BUSINESS_ERRORS[key] || BUSINESS_ERRORS['generic.no_data'];
  const baseId = `be-${key || 'generic'}`;
  return {
    id: slot != null ? `${baseId}-${slot}` : baseId,
    tagKind: entry.tag,
    tagLabel: entry.tagLabel,
    title: entry.title,
    body: entry.body,
    footerLeft: entry.footer,
    footerRight: entry.footerRight,
    // CTA optionnel (first-time empty states T2V) — page consommatrice
    // wire navigate(ctaHref) dans l'onClick de SolExpertGridFull.emptyState.action.
    ctaLabel: entry.ctaLabel,
    ctaHref: entry.ctaHref,
  };
}
