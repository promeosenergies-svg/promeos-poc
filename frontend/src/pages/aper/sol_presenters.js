/**
 * PROMEOS — APER Sol presenters (Lot 1.2)
 *
 * Helpers purs pour AperSol — transformation de getAperDashboard()
 * vers props composants Sol.
 *
 * API consommée :
 *   getAperDashboard() → {
 *     parking: {eligible_count, total_surface_m2, sites: [{site_id, site_nom, surface_m2, deadline, category, lat, lon}]},
 *     roof:    {eligible_count, total_surface_m2, sites: [...]}
 *     total_eligible_sites,
 *     next_deadline
 *   }
 *
 * Productibles PV approximés : facteur d'emprise toit 0,15 kWc/m² et
 * parking 0,20 kWc/m² (ombrières). Productible France moyen 1 100 kWh/kWc.
 * Tarif de rachat surplus ≈ 0,10 €/kWh.
 */
import { NBSP, formatFR, formatFREur, freshness } from '../cockpit/sol_presenters';
import { businessErrorFallback } from '../../i18n/business_errors';

export { NBSP };

// Coefficients d'emprise PV (kWc/m²)
const ROOF_KWC_PER_M2 = 0.15;
const PARKING_KWC_PER_M2 = 0.2;
// Productible moyen France (kWh/kWc/an)
const PRODUCTIBLE_KWH_PER_KWC = 1100;
// Prix moyen achat surplus (€/kWh, tarif d'obligation d'achat simplifié)
const PRICE_EUR_PER_KWH = 0.1;

// ─────────────────────────────────────────────────────────────────────────────
// Kicker + narratives
// ─────────────────────────────────────────────────────────────────────────────

export function buildAperKicker({ scope } = {}) {
  const orgName = scope?.orgName || 'votre patrimoine';
  return `Conformité · APER · ${orgName}`;
}

export function buildAperNarrative({ dashboard } = {}) {
  const totalEligible = dashboard?.total_eligible_sites ?? 0;
  const parkingCount = dashboard?.parking?.eligible_count ?? 0;
  const roofCount = dashboard?.roof?.eligible_count ?? 0;
  const nextDeadline = dashboard?.next_deadline;

  if (totalEligible === 0) {
    return "Aucun de vos sites n'atteint les seuils d'assujettissement APER (toit\u00a0≥\u00a0500\u00a0m² ou parking\u00a0≥\u00a01\u00a0500\u00a0m²).";
  }

  const parts = [];
  if (parkingCount > 0) parts.push(`${parkingCount}${NBSP}parking${parkingCount > 1 ? 's' : ''}`);
  if (roofCount > 0) parts.push(`${roofCount}${NBSP}toiture${roofCount > 1 ? 's' : ''}`);
  const composition = parts.join(' + ');

  const deadlineText = nextDeadline ? ` Prochaine échéance : ${formatDateFR(nextDeadline)}.` : '';

  return `${totalEligible}${NBSP}site${totalEligible > 1 ? 's' : ''} éligible${totalEligible > 1 ? 's' : ''} à la loi APER · ${composition}.${deadlineText}`;
}

export function buildAperSubNarrative({ dashboard } = {}) {
  const parkingSurface = dashboard?.parking?.total_surface_m2 ?? 0;
  const roofSurface = dashboard?.roof?.total_surface_m2 ?? 0;
  if (parkingSurface + roofSurface === 0) {
    return 'Sources : cartographie cadastrale + déclarations patrimoine.';
  }
  const parts = [];
  if (parkingSurface > 0) parts.push(`${formatFR(parkingSurface, 0)}${NBSP}m² de parkings`);
  if (roofSurface > 0) parts.push(`${formatFR(roofSurface, 0)}${NBSP}m² de toitures`);
  return `${parts.join(' · ')}. Sources : cartographie cadastrale + déclarations patrimoine.`;
}

// ─────────────────────────────────────────────────────────────────────────────
// KPI interpretations
// ─────────────────────────────────────────────────────────────────────────────

export function interpretAperEligible({ dashboard } = {}) {
  const total = dashboard?.total_eligible_sites ?? 0;
  if (total === 0) return 'Aucun site assujetti à cette obligation.';
  const parking = dashboard?.parking?.eligible_count ?? 0;
  const roof = dashboard?.roof?.eligible_count ?? 0;
  const parts = [];
  if (parking > 0)
    parts.push(`${parking}${NBSP}parking${parking > 1 ? 's' : ''} > 1\u00a0500\u00a0m²`);
  if (roof > 0) parts.push(`${roof}${NBSP}toiture${roof > 1 ? 's' : ''} > 500\u00a0m²`);
  return parts.join(' · ') + '.';
}

export function interpretAperConforming({ conformingCount, totalEligible } = {}) {
  if (totalEligible === 0) return 'Aucun site assujetti à cette obligation.';
  if (conformingCount === 0)
    return "Aucun projet PV validé pour l'instant. Sol peut préparer les études préalables.";
  const pct = Math.round((conformingCount / totalEligible) * 100);
  return `${conformingCount}/${totalEligible} sites avec projet PV validé · ${pct}${NBSP}% de couverture.`;
}

export function interpretAperPotential({ potentialKwc, annualGainEur, dashboard } = {}) {
  if (!potentialKwc) return 'Potentiel solaire en cours de calcul.';
  const parts = [`${formatFR(potentialKwc, 0)}${NBSP}kWc installables`];
  if (annualGainEur > 0) {
    parts.push(
      `productible ${formatFR(Math.round((potentialKwc * PRODUCTIBLE_KWH_PER_KWC) / 1000), 0)}${NBSP}MWh/an`
    );
    parts.push(`gain potentiel ${formatFREur(annualGainEur, 0)}/an`);
  }
  return parts.join(' · ') + '.';
}

// ─────────────────────────────────────────────────────────────────────────────
// Computations
// ─────────────────────────────────────────────────────────────────────────────

/**
 * Calcule le potentiel PV cumulé en kWc (toit × 0,15 + parking × 0,20).
 */
export function computeAperPotentialKwc(dashboard) {
  if (!dashboard) return 0;
  const parkingKwc = (dashboard.parking?.total_surface_m2 ?? 0) * PARKING_KWC_PER_M2;
  const roofKwc = (dashboard.roof?.total_surface_m2 ?? 0) * ROOF_KWC_PER_M2;
  return Math.round(parkingKwc + roofKwc);
}

/**
 * Estime le gain annuel € (productible × prix moyen).
 */
export function computeAperAnnualGain(potentialKwc) {
  if (!potentialKwc) return 0;
  return Math.round(potentialKwc * PRODUCTIBLE_KWH_PER_KWC * PRICE_EUR_PER_KWH);
}

/**
 * Retourne la liste fusionnée des sites éligibles (parking + roof dédupliqués).
 * Chaque site a : site_id, site_nom, parkingSurface, roofSurface, totalKwc, nextDeadline.
 */
export function mergeSitesForBarChart(dashboard) {
  if (!dashboard) return [];
  const merged = new Map();
  for (const p of dashboard.parking?.sites || []) {
    merged.set(p.site_id, {
      site_id: p.site_id,
      site_nom: p.site_nom,
      parking_m2: p.surface_m2 || 0,
      roof_m2: 0,
      deadline: p.deadline,
    });
  }
  for (const r of dashboard.roof?.sites || []) {
    const existing = merged.get(r.site_id);
    if (existing) {
      existing.roof_m2 = r.surface_m2 || 0;
      // Prendre la deadline la plus proche
      if (
        r.deadline &&
        (!existing.deadline || new Date(r.deadline) < new Date(existing.deadline))
      ) {
        existing.deadline = r.deadline;
      }
    } else {
      merged.set(r.site_id, {
        site_id: r.site_id,
        site_nom: r.site_nom,
        parking_m2: 0,
        roof_m2: r.surface_m2 || 0,
        deadline: r.deadline,
      });
    }
  }
  return Array.from(merged.values()).map((s) => ({
    ...s,
    total_kwc: Math.round(s.parking_m2 * PARKING_KWC_PER_M2 + s.roof_m2 * ROOF_KWC_PER_M2),
  }));
}

/**
 * Convertit sites → data SolBarChart axe catégoriel.
 * `current` = kWc toiture, `previous` = kWc parking (séparés visuellement).
 */
export function adaptAperToBarChart(sites) {
  if (!Array.isArray(sites)) return [];
  return sites
    .sort((a, b) => b.total_kwc - a.total_kwc)
    .slice(0, 8)
    .map((s) => ({
      site: shortName(s.site_nom),
      current: Math.round(s.roof_m2 * ROOF_KWC_PER_M2),
      previous: Math.round(s.parking_m2 * PARKING_KWC_PER_M2),
    }));
}

function shortName(name) {
  if (!name) return 'Site';
  const clean = name.replace(/HELIOS\s*/gi, '').trim();
  return clean.length > 18 ? clean.slice(0, 16) + '…' : clean;
}

// ─────────────────────────────────────────────────────────────────────────────
// Week-cards APER
// ─────────────────────────────────────────────────────────────────────────────

/**
 * 3 week-cards APER avec fallbacks businessErrors.
 *   Card 1 À regarder  : site éligible avec deadline la plus proche
 *   Card 2 À faire     : 2ème site dans la liste (prochain dossier à préparer)
 *   Card 3 Bonne nouvelle : fallback aper.study_in_progress (V2 pas de validation réelle)
 */
export function buildAperWeekCards({ sites = [], onNavigateSite = null } = {}) {
  const cards = [];

  const sorted = [...sites].sort((a, b) => {
    const da = a.deadline ? new Date(a.deadline).getTime() : Infinity;
    const db = b.deadline ? new Date(b.deadline).getTime() : Infinity;
    return da - db;
  });

  // Card 1 À regarder
  const urgent = sorted[0];
  if (urgent) {
    const kwc = urgent.total_kwc || 0;
    const surfaceText = [
      urgent.roof_m2 > 0 ? `toit ${formatFR(urgent.roof_m2, 0)}${NBSP}m²` : null,
      urgent.parking_m2 > 0 ? `parking ${formatFR(urgent.parking_m2, 0)}${NBSP}m²` : null,
    ]
      .filter(Boolean)
      .join(' + ');
    cards.push({
      id: `urgent-${urgent.site_id}`,
      tagKind: 'attention',
      tagLabel: 'À regarder',
      title: urgent.site_nom,
      body: `Éligible APER · ${surfaceText}. Potentiel ${formatFR(kwc, 0)}${NBSP}kWc.`,
      footerLeft: urgent.deadline ? `échéance ${formatDateFR(urgent.deadline)}` : '',
      footerRight: '⌘K',
      onClick: onNavigateSite ? () => onNavigateSite(urgent.site_id) : undefined,
    });
  } else {
    cards.push(businessErrorFallback('aper.no_eligible', cards.length));
  }

  // Card 2 À faire : 2ème site
  const next = sorted[1];
  if (next) {
    const kwc = next.total_kwc || 0;
    cards.push({
      id: `next-${next.site_id}`,
      tagKind: 'afaire',
      tagLabel: 'À faire',
      title: next.site_nom,
      body: `Projet PV à étudier · potentiel ${formatFR(kwc, 0)}${NBSP}kWc.`,
      footerLeft: next.deadline ? `échéance ${formatDateFR(next.deadline)}` : '',
      footerRight: 'Automatisable',
      onClick: onNavigateSite ? () => onNavigateSite(next.site_id) : undefined,
    });
  } else {
    cards.push(businessErrorFallback('aper.study_in_progress', cards.length));
  }

  // Card 3 Bonne nouvelle : fallback (V2 pas de validation réelle en démo)
  cards.push(businessErrorFallback('aper.study_in_progress', cards.length));

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
export { formatFR, formatFREur, freshness };
