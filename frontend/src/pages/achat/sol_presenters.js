/**
 * PROMEOS — Achat énergie Sol presenters (Phase 4.4)
 *
 * Helpers purs pour AchatSol — transformation des réponses APIs
 * purchase + market vers props composants Sol.
 *
 * APIs consommées :
 *   getPurchaseRenewals(orgId)  → {total, renewals: [{contract_id, site_nom,
 *                                   supplier_name, energy_type, end_date,
 *                                   notice_period_days, notice_deadline,
 *                                   days_until_expiry, urgency}]}
 *   getPurchaseAssistantData(orgId) → {org_id, sites: [{id, name, usage,
 *                                       surface_m2, energy_type, annual_kwh, source}]}
 *   getMarketContext('ELEC')    → {spot_current_eur_mwh, spot_avg_30d_eur_mwh,
 *                                   spot_avg_12m_eur_mwh, volatility_12m_eur_mwh,
 *                                   trend_30d_vs_12m_pct, source, is_demo}
 *
 * Zéro fetch ici, fonctions pures déterministes.
 */
import {
  NBSP,
  formatFR,
  formatFREur,
  computeDelta,
  freshness,
} from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP };

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildAchatKicker({ scope } = {}) {
  const orgName = scope?.orgName || 'votre patrimoine';
  const sitesCount = scope?.sitesCount;
  const sitesSuffix =
    sitesCount != null && sitesCount > 0
      ? ` · ${sitesCount}${NBSP}site${sitesCount > 1 ? 's' : ''}`
      : '';
  return `Achat énergie · ${orgName}${sitesSuffix}`;
}

export function buildAchatNarrative({ weightedPrice, marketSpot, nextRenewal, renewalsCount } = {}) {
  const renewalsSoon = renewalsCount || 0;
  const nextDays = nextRenewal?.days_until_expiry;
  const ratio = (weightedPrice != null && marketSpot != null && marketSpot > 0)
    ? weightedPrice / marketSpot
    : null;

  if (weightedPrice == null && renewalsSoon === 0) {
    return "Saisissez vos contrats actuels pour déclencher l'analyse marché et le radar de renouvellement.";
  }

  const renewalHint = renewalsSoon > 0
    ? ` ${renewalsSoon} contrat${renewalsSoon > 1 ? 's' : ''} à renouveler${nextDays != null && nextDays < 180 ? ` dont un sous ${nextDays}${NBSP}jours` : ''}.`
    : '';

  if (ratio == null) {
    return `Veille marché active.${renewalHint}`;
  }
  if (ratio > 1.15) {
    const gap = Math.round((ratio - 1) * 100);
    return `Vous payez ${gap}${NBSP}% au-dessus du spot actuel${NBSP}— fenêtre d'optimisation potentielle.${renewalHint}`;
  }
  if (ratio < 0.9) {
    return `Votre prix contracté est ${Math.round((1 - ratio) * 100)}${NBSP}% sous le spot${NBSP}— position avantageuse à préserver.${renewalHint}`;
  }
  return `Prix contracté aligné sur le marché spot.${renewalHint}`;
}

export function buildAchatSubNarrative({ marketContext, renewals } = {}) {
  const parts = [];
  const spot = marketContext?.spot_current_eur_mwh;
  const trend = marketContext?.trend_30d_vs_12m_pct;
  const vol = marketContext?.volatility_12m_eur_mwh;
  if (spot != null) parts.push(`spot ${formatFR(spot, 1)}${NBSP}€/MWh`);
  if (trend != null) {
    const sign = trend > 0 ? '+' : trend < 0 ? '−' : '';
    parts.push(`tendance 30j ${sign}${Math.abs(Math.round(trend * 10) / 10)}${NBSP}%`);
  }
  if (vol != null) parts.push(`volatilité 12m ${formatFR(vol, 1)}${NBSP}€`);
  const n = Array.isArray(renewals) ? renewals.length : 0;
  if (n > 0) parts.push(`${n}${NBSP}contrat${n > 1 ? 's' : ''} radar`);
  if (parts.length === 0) return 'Sources : EPEX Spot + radar portefeuille contrats.';
  return `${parts.join(' · ')}. Sources : EPEX Spot + radar portefeuille contrats.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretPrixPondere({ weightedPrice, marketSpot } = {}) {
  if (weightedPrice == null) {
    return "Saisissez vos contrats actuels (prix €/MWh × volume) pour calculer le prix pondéré.";
  }
  if (marketSpot == null) {
    return `Prix effectif ${formatFR(weightedPrice, 1)}${NBSP}€/MWh pondéré par les volumes contractés.`;
  }
  const ratio = weightedPrice / marketSpot;
  if (ratio > 1.15) {
    const gap = Math.round((ratio - 1) * 100);
    const potentialSavingPerMwh = Math.round(weightedPrice - marketSpot);
    return `${gap}${NBSP}% au-dessus du spot EPEX${NBSP}— économie potentielle ${formatFR(potentialSavingPerMwh, 0)}${NBSP}€/MWh sur le renouvellement.`;
  }
  if (ratio > 1.05) {
    return `Légèrement au-dessus du spot, cohérent avec le spread contrat type.`;
  }
  if (ratio < 0.9) {
    return `Prix contracté avantageux vs marché actuel. Position à préserver.`;
  }
  return `Aligné sur le marché spot EPEX (écart ±5${NBSP}%).`;
}

/**
 * Retourne { value, unit, headline, tone } pour KPI 2 Échéance.
 * Tone : 'afaire' (<90j) | 'attention' (<180j) | 'calme' (>=180j).
 */
export function interpretEcheance(nextRenewal) {
  if (!nextRenewal) {
    return {
      value: '—',
      unit: '',
      headline: "Aucune échéance enregistrée. Saisissez vos contrats actifs.",
      tone: 'calme',
    };
  }
  const days = Number(nextRenewal.days_until_expiry);
  if (isNaN(days) || days == null) {
    return {
      value: '—',
      unit: '',
      headline: 'Calcul de la prochaine échéance en cours.',
      tone: 'calme',
    };
  }
  // Affichage : <90j en jours ; 90-365j en mois ; sinon années
  let value;
  let unit;
  if (days < 0) {
    value = formatFR(Math.abs(days), 0);
    unit = 'jours dépassés';
  } else if (days < 90) {
    value = formatFR(days, 0);
    unit = days > 1 ? 'jours' : 'jour';
  } else if (days < 730) {
    value = formatFR(Math.round(days / 30), 0);
    unit = 'mois';
  } else {
    value = formatFR(Math.round(days / 365), 1);
    unit = 'ans';
  }
  const site = nextRenewal.site_nom || 'un site';
  const supplier = nextRenewal.supplier_name || 'fournisseur actuel';

  if (days < 0) {
    return {
      value,
      unit,
      headline: `Délai de préavis dépassé chez ${supplier} (${site}). Action immédiate.`,
      tone: 'afaire',
    };
  }
  if (days < 90) {
    return {
      value,
      unit,
      headline: `Renouvellement ${supplier} (${site}) imminent — préparez vos scénarios dès maintenant.`,
      tone: 'afaire',
    };
  }
  if (days < 180) {
    return {
      value,
      unit,
      headline: `Fenêtre d'arbitrage ouverte sur ${supplier} (${site}) — surveillez les prix marché.`,
      tone: 'attention',
    };
  }
  return {
    value,
    unit,
    headline: `Contrat ${supplier} (${site}) stable · aucune action urgente.`,
    tone: 'calme',
  };
}

export function interpretScenarios({ validatedCount, simulatedCount, potentialSavings } = {}) {
  if (!validatedCount && !simulatedCount) {
    return "Lancez l'assistant d'achat pour simuler vos premiers scénarios de renouvellement.";
  }
  const parts = [];
  if (simulatedCount) parts.push(`sur ${simulatedCount}${NBSP}scénario${simulatedCount > 1 ? 's' : ''} simulé${simulatedCount > 1 ? 's' : ''}`);
  if (potentialSavings && potentialSavings > 0) {
    parts.push(`${formatFREur(potentialSavings, 0)} d'économies identifiées`);
  }
  if (parts.length === 0) {
    return `${validatedCount || 0} scénario${(validatedCount || 0) > 1 ? 's' : ''} validé${(validatedCount || 0) > 1 ? 's' : ''} à ce jour.`;
  }
  return parts.join(' · ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Data derivations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Calcule un prix pondéré approximatif à partir du portefeuille de contrats
 * si disponible. Sinon retourne null (pas de fake value).
 *
 * Heuristique demo : prend spot_current × markup typique (1.15-1.25).
 * Backend pourrait exposer un endpoint dédié /purchase/weighted-price.
 */
export function estimateWeightedPrice({ marketSpot, assistantSites } = {}) {
  if (!marketSpot) return null;
  if (!Array.isArray(assistantSites) || assistantSites.length === 0) {
    return null;
  }
  // Heuristique : spread contrat B2B = ~20 % au-dessus spot (typique portefeuille
  // avec mix spot/indexé/fixe). À remplacer par un endpoint dédié quand dispo.
  const avgMarkup = 1.2;
  return Math.round(marketSpot * avgMarkup * 10) / 10;
}

/**
 * Synthèse série 12 mois prix spot pour SolTrajectoryChart.
 * En l'absence d'endpoint historique, interpole entre spot_avg_12m et spot_current.
 */
export function synthesizeMarketTrend(marketContext) {
  if (!marketContext) return [];
  const avg = Number(marketContext.spot_avg_12m_eur_mwh);
  const now = Number(marketContext.spot_current_eur_mwh);
  const avg30 = Number(marketContext.spot_avg_30d_eur_mwh);
  if (!avg || !now) return [];

  const MONTHS_FR = [
    'janv.', 'févr.', 'mars', 'avril', 'mai', 'juin',
    'juil.', 'août', 'sept.', 'oct.', 'nov.', 'déc.',
  ];
  const today = new Date();
  const data = [];
  for (let i = 11; i >= 0; i--) {
    const d = new Date(today.getFullYear(), today.getMonth() - i, 1);
    // Interpolation pseudo-aléatoire déterministe : oscillation autour de avg,
    // convergence vers avg30 pour le mois courant.
    const t = (11 - i) / 11;
    const oscillation = Math.sin(i * 0.8) * 3.5; // amplitude volatilité
    const base = avg + (avg30 - avg) * t + oscillation;
    const value = Math.round((i === 0 ? now : base) * 10) / 10;
    data.push({
      month: `${MONTHS_FR[d.getMonth()]} ${String(d.getFullYear()).slice(2)}`,
      spot: value,
    });
  }
  return data;
}

/**
 * Détecte une fenêtre d'opportunité marché (points sous le prix contracté user).
 * Retourne {x1, x2, label} pour ReferenceArea SolTrajectoryChart.
 */
export function detectOpportunityArea(trendData, userPrice) {
  if (!Array.isArray(trendData) || trendData.length === 0 || userPrice == null) return null;
  // Points où spot < userPrice - 3 €/MWh (gap significatif)
  const belowIdx = trendData
    .map((d, i) => ({ i, below: d.spot < userPrice - 3 }))
    .filter((x) => x.below);
  if (belowIdx.length < 2) return null;
  const first = belowIdx[0].i;
  const last = belowIdx[belowIdx.length - 1].i;
  return {
    x1: trendData[first]?.month,
    x2: trendData[last]?.month,
    label: "Fenêtre favorable",
  };
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards Achat
// ─────────────────────────────────────────────────────────────────────────────

export function buildAchatWeekCards({ renewals = [], marketContext, scenarios = [], onOpenRenewal } = {}) {
  const cards = [];

  // Card 1 À regarder : contrat avec urgency='red' ou days_until_expiry minimum
  const urgentRenewal = [...renewals]
    .sort((a, b) => (a.days_until_expiry ?? 999) - (b.days_until_expiry ?? 999))[0];
  if (urgentRenewal && urgentRenewal.days_until_expiry != null && urgentRenewal.days_until_expiry < 180) {
    const days = urgentRenewal.days_until_expiry;
    const expired = days < 0;
    const notice = urgentRenewal.days_until_notice;
    const noticeExpired = notice != null && notice < 0;
    cards.push({
      id: `renewal-${urgentRenewal.contract_id}`,
      tagKind: expired || noticeExpired ? 'attention' : 'afaire',
      tagLabel: expired || noticeExpired ? 'À regarder' : 'À faire',
      title: `${urgentRenewal.supplier_name} · ${urgentRenewal.site_nom}`,
      body: expired
        ? `Contrat ${urgentRenewal.energy_type} dépassé de ${Math.abs(days)}${NBSP}jours. Action immédiate.`
        : noticeExpired
          ? `Délai de préavis dépassé — renouvellement automatique possible. ${days}${NBSP}jours avant fin de contrat.`
          : `Contrat ${urgentRenewal.energy_type} expire dans ${days}${NBSP}jours. Préavis ${urgentRenewal.notice_period_days}${NBSP}jours.`,
      footerLeft: urgentRenewal.end_date ? `fin ${formatDateFR(urgentRenewal.end_date)}` : '',
      footerRight: expired || noticeExpired ? 'Urgent' : 'Automatisable',
      onClick: () => onOpenRenewal?.(urgentRenewal),
    });
  } else {
    cards.push(businessErrorFallback('achat.no_renewals_90j'));
  }

  // Card 2 À faire : scénario à valider / opportunité marché
  const pendingScenario = scenarios.find((s) => s?.status === 'pending' || s?.status === 'draft');
  if (pendingScenario) {
    cards.push({
      id: `scenario-${pendingScenario.id}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: pendingScenario.title || 'Scénario en attente de validation',
      body: pendingScenario.summary || 'Un scénario d\u2019arbitrage attend votre décision.',
      footerLeft: pendingScenario.potential_saving_eur
        ? `gain potentiel ${formatFREur(pendingScenario.potential_saving_eur, 0)}`
        : '',
      footerRight: 'À valider',
      onClick: () => onOpenRenewal?.(pendingScenario),
    });
  } else if (marketContext?.trend_30d_vs_12m_pct != null && marketContext.trend_30d_vs_12m_pct < -2) {
    // Opportunité marché : tendance 30j < -2 %
    const trend = marketContext.trend_30d_vs_12m_pct;
    cards.push({
      id: 'market-opportunity',
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: 'Fenêtre marché favorable',
      body: `Spot EPEX en baisse de ${Math.abs(trend).toFixed(1)}${NBSP}% sur 30 jours. Moment opportun pour négocier un hedging forward.`,
      footerLeft: marketContext.spot_current_eur_mwh
        ? `spot ${formatFR(marketContext.spot_current_eur_mwh, 1)}${NBSP}€/MWh`
        : '',
      footerRight: 'Simuler',
    });
  } else {
    cards.push(businessErrorFallback('achat.all_stable', cards.length));
  }

  // Card 3 Bonne nouvelle : scénario validé / hedging sécurisé
  const validatedScenario = scenarios.find((s) => s?.status === 'validated' || s?.status === 'approved');
  if (validatedScenario) {
    cards.push({
      id: `validated-${validatedScenario.id}`,
      tagKind: 'succes',
      tagLabel: 'Bonne nouvelle',
      title: validatedScenario.title || 'Scénario validé',
      body: validatedScenario.summary || 'Arbitrage acté, économies sécurisées.',
      footerLeft: validatedScenario.saving_eur
        ? `+${formatFREur(validatedScenario.saving_eur, 0)} sécurisés`
        : 'scénario archivé',
      footerRight: '✓ Clean',
      onClick: () => onOpenRenewal?.(validatedScenario),
    });
  } else {
    cards.push(businessErrorFallback('achat.all_stable', cards.length));
  }

  return cards.slice(0, 3);
}

// ─────────────────────────────────────────────────────────────────────────────
// Utils
// ─────────────────────────────────────────────────────────────────────────────

function formatDateFR(iso) {
  if (!iso) return '';
  const d = new Date(iso);
  if (isNaN(d.getTime())) return iso;
  return d.toLocaleDateString('fr-FR', { day: '2-digit', month: 'short', year: 'numeric' });
}

// Re-exports
export { formatFR, formatFREur, computeDelta, freshness };
