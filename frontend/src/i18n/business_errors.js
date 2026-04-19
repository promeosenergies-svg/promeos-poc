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
    body:
      "Votre prochaine validation conformité interviendra lors de la prochaine itération OPERAT ou d'un dépôt BACS/APER.",
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
    body:
      "Votre score Décret Tertiaire est en cours de recalcul. Revenez dans quelques minutes.",
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
    body: "Commencez par importer votre patrimoine depuis SIREN ou créer un site manuellement.",
    footer: 'Onboarding SIRENE disponible',
    footerRight: 'Automatisable',
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
    body: "Renseignez les surfaces de vos sites et importez 12\u00a0mois de consommations pour activer le calcul EUI.",
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
 * @param {string} key — ex "conformite.no_drift"
 * @returns {{tagKind, tagLabel, title, body, footerLeft, footerRight, id}}
 */
export function businessErrorFallback(key) {
  const entry = BUSINESS_ERRORS[key] || BUSINESS_ERRORS['generic.no_data'];
  return {
    id: `be-${key || 'generic'}`,
    tagKind: entry.tag,
    tagLabel: entry.tagLabel,
    title: entry.title,
    body: entry.body,
    footerLeft: entry.footer,
    footerRight: entry.footerRight,
  };
}
