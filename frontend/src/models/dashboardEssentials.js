/**
 * PROMEOS — dashboardEssentials.js (Sprint WOW Phase 7.0 + V21 Cockpit + Cockpit V2)
 * Pure model layer for Dashboard "Essentiels Patrimoine".
 * No React imports — fully testable in isolation.
 *
 * Exports:
 *   buildWatchlist(kpis, sites)                 → WatchItem[] (max 5, severity-sorted)
 *   checkConsistency(kpis)                      → { ok, issues }
 *   buildTopSites(sites)                        → { worst: SiteItem[], best: SiteItem[] }
 *   buildOpportunities(kpis, sites, opts)       → Opportunity[] (max 3)
 *   buildBriefing(kpis, watchlist)              → BriefingItem[] (max 3, priority-sorted)
 *   buildTodayActions(kpis, watchlist, opps)    → TodayAction[] (max 5, deduped)
 *   buildExecutiveSummary(kpis, topSites)       → ExecBullet[] (max 3)
 *   buildExecutiveKpis(kpis, sites)             → ExecKpi[] (4 tuiles décideur)
 *   buildDashboardEssentials(sites, opts)       → aggregated result object
 */
import { formatPercentFR } from '../utils/format';
import {
  RISK_THRESHOLDS,
  COVERAGE_THRESHOLDS,
  CONFORMITY_THRESHOLDS,
  MATURITY_THRESHOLDS,
  READINESS_WEIGHTS,
  getRiskStatus,
  SEVERITY_RANK,
  COMPLIANCE_SCORE_THRESHOLDS,
} from '../lib/constants';

// ── buildWatchlist ──────────────────────────────────────────────────────────

/**
 * Build sorted watchlist from precomputed kpis + raw sites.
 * Returns max 5 items ordered by severity (critical first).
 *
 * @param {object} kpis         — from computeKpis(sites)
 * @param {object[]} sites      — scopedSites array
 * @returns {WatchItem[]}
 *
 * WatchItem: { id, label, severity, path, cta }
 */
export function buildWatchlist(kpis, sites = []) {
  const items = [];

  // 1. Non-conformes — critical
  const nc = kpis.nonConformes;
  if (nc > 0) {
    items.push({
      id: 'non_conformes',
      label: `${nc} site${nc > 1 ? 's' : ''} non conforme${nc > 1 ? 's' : ''} — actions requises`,
      severity: 'critical',
      path: '/conformite',
      cta: 'Voir conformité',
    });
  }

  // 2. Sites à risque — high
  const ar = kpis.aRisque;
  if (ar > 0) {
    items.push({
      id: 'a_risque',
      label: `${ar} site${ar > 1 ? 's' : ''} à risque réglementaire`,
      severity: 'high',
      path: '/actions',
      cta: "Plan d'action",
    });
  }

  // 3. Sites without consumption data — warn
  const sitesWithoutData = sites.filter((s) => !s.conso_kwh_an || s.conso_kwh_an === 0);
  if (sitesWithoutData.length > 0) {
    const n = sitesWithoutData.length;
    items.push({
      id: 'no_conso_data',
      label: `Données manquantes sur ${n} site${n > 1 ? 's' : ''}`,
      severity: 'warn',
      path: '/consommations/import',
      cta: 'Importer',
    });
  }

  // 4. Low data coverage — medium (only if N >= 3 and not already covered by #3)
  if (
    kpis.couvertureDonnees < COVERAGE_THRESHOLDS.warn &&
    kpis.total >= 3 &&
    sitesWithoutData.length === 0
  ) {
    items.push({
      id: 'low_coverage',
      label: `Couverture données insuffisante : ${formatPercentFR(kpis.couvertureDonnees)}`,
      severity: 'medium',
      path: '/consommations/import',
      cta: 'Compléter',
    });
  }

  // Sort by severity rank, cap at 5
  items.sort((a, b) => (SEVERITY_RANK[a.severity] ?? 99) - (SEVERITY_RANK[b.severity] ?? 99));
  return items.slice(0, 5);
}

// ── checkConsistency ────────────────────────────────────────────────────────

/**
 * Detect data inconsistencies in the dashboard.
 * Returns { ok, issues } — issues is an array of { code, label } objects.
 *
 * @param {object} kpis — from computeKpis(sites)
 * @returns {{ ok: boolean, issues: Issue[] }}
 */
export function checkConsistency(kpis) {
  const issues = [];

  // Case 1: All conformes but very low data coverage → suspicious
  const conformeRate = kpis.total > 0 ? kpis.conformes / kpis.total : 0;
  if (
    conformeRate === 1 &&
    kpis.couvertureDonnees < COVERAGE_THRESHOLDS.suspicious &&
    kpis.total > 0
  ) {
    issues.push({
      code: 'all_conformes_low_data',
      label: 'Conformité complète détectée mais peu de données — vérifiez les imports',
    });
  }

  // Case 2: No consumption data at all
  if (kpis.couvertureDonnees === 0 && kpis.total > 0) {
    issues.push({
      code: 'no_data_coverage',
      label: "Aucun site n'a de données de consommation — importez des relevés",
    });
  }

  return { ok: issues.length === 0, issues };
}

// ── buildTopSites ───────────────────────────────────────────────────────────

/**
 * Return worst 5 (non-conformes, sorted by risque DESC) and best 5 (conformes).
 *
 * @param {object[]} sites — scopedSites array
 * @returns {{ worst: SiteItem[], best: SiteItem[] }}
 */
export function buildTopSites(sites = []) {
  if (!sites.length) return { worst: [], best: [] };

  // worst: non-conformes sorted by risque_eur DESC
  const worst = [...sites]
    .filter((s) => s.statut_conformite !== 'conforme')
    .sort((a, b) => (b.risque_eur || 0) - (a.risque_eur || 0))
    .slice(0, 5)
    .map((s) => ({
      id: s.id,
      nom: s.nom,
      ville: s.ville,
      risque_eur: s.risque_eur || 0,
      statut_conformite: s.statut_conformite,
    }));

  // best: conformes sorted by conso_kwh_an ASC (lowest = best managed; nulls last)
  const best = [...sites]
    .filter((s) => s.statut_conformite === 'conforme')
    .sort((a, b) => {
      const av = a.conso_kwh_an || 0;
      const bv = b.conso_kwh_an || 0;
      return av - bv;
    })
    .slice(0, 5)
    .map((s) => ({
      id: s.id,
      nom: s.nom,
      ville: s.ville,
      conso_kwh_an: s.conso_kwh_an || 0,
      statut_conformite: s.statut_conformite,
    }));

  return { worst, best };
}

// ── buildOpportunities ──────────────────────────────────────────────────────

/**
 * Build up to 3 actionable opportunities. Returns [] when !isExpert.
 *
 * @param {object} kpis
 * @param {object[]} sites
 * @param {{ isExpert: boolean }} opts
 * @returns {Opportunity[]}
 *
 * Opportunity: { id, label, sub, icon, path, cta }
 */
export function buildOpportunities(kpis, _sites = [], { isExpert = false } = {}) {
  if (!isExpert) return [];

  const items = [];

  // 1. Incomplete data coverage
  if (kpis.couvertureDonnees < COVERAGE_THRESHOLDS.opportunity && kpis.total > 0) {
    const missingSites = kpis.total - Math.round((kpis.couvertureDonnees * kpis.total) / 100);
    items.push({
      id: 'complete_data',
      label: 'Compléter les données de consommation',
      sub: `${formatPercentFR(kpis.couvertureDonnees)} couvert — ${missingSites} site${kpis.total > 1 ? 's' : ''} sans données`,
      path: '/consommations/explorer',
      cta: 'Explorer',
    });
  }

  // 2. Non-conformes still present
  if (kpis.nonConformes > 0) {
    const n = kpis.nonConformes;
    items.push({
      id: 'reduce_risk',
      label: 'Réduire le risque Décret Tertiaire',
      sub: `${n} site${n > 1 ? 's' : ''} en retard — plan d'actions disponible`,
      path: '/actions',
      cta: "Plan d'action",
    });
  }

  // 3. High financial risk
  if (kpis.risqueTotal > RISK_THRESHOLDS.org.warn) {
    const kEur = Math.round(kpis.risqueTotal / 1000);
    items.push({
      id: 'optimize_subscriptions',
      label: 'Optimiser les abonnements énergie',
      sub: `Risque estimé : ${kEur} k€ — audit des contrats recommandé`,
      path: '/performance',
      cta: 'Analyser',
    });
  }

  return items.slice(0, 3);
}

// ── buildBriefing ────────────────────────────────────────────────────────────

/**
 * Derive up to 3 priority briefing items for the "Briefing du jour" hero card.
 * Items are ordered by severity: critical → high → warn.
 *
 * @param {object} kpis          — from computeKpis(sites)
 * @param {object[]} watchlist   — from buildWatchlist()
 * @param {number}   alertsCount — nombre d'alertes actives (depuis API)
 * @returns {BriefingItem[]}   max 3 items
 *
 * BriefingItem: { id, label, severity, path }
 */
export function buildBriefing(kpis, _watchlist = [], alertsCount = 0) {
  const bullets = [];

  // 1. Non-conformes → critical
  if (kpis.nonConformes > 0) {
    const n = kpis.nonConformes;
    bullets.push({
      id: 'non_conformes',
      label: `${n} site${n > 1 ? 's' : ''} à mettre en conformité`,
      severity: 'critical',
      path: '/conformite',
    });
  }

  // 2. Sites à risque → high
  if (kpis.aRisque > 0) {
    const n = kpis.aRisque;
    bullets.push({
      id: 'a_risque',
      label: `${n} site${n > 1 ? 's' : ''} à risque Décret Tertiaire`,
      severity: 'high',
      path: '/actions',
    });
  }

  // 3. Alertes actives → high
  if (alertsCount > 0) {
    bullets.push({
      id: 'alertes_actives',
      label: `${alertsCount} alerte${alertsCount > 1 ? 's' : ''} active${alertsCount > 1 ? 's' : ''}`,
      severity: alertsCount > 5 ? 'high' : 'warn',
      path: '/notifications',
    });
  }

  // 4. Low data coverage → warn (only when meaningful)
  if (kpis.couvertureDonnees < COVERAGE_THRESHOLDS.opportunity && kpis.total > 0) {
    const missing = kpis.total - Math.round((kpis.couvertureDonnees * kpis.total) / 100);
    bullets.push({
      id: 'coverage',
      label: `${missing} site${missing > 1 ? 's' : ''} sans données de consommation`,
      severity: 'warn',
      path: '/consommations/import',
    });
  }

  return bullets.slice(0, 3);
}

// ── buildTodayActions ────────────────────────────────────────────────────────

/**
 * Build top-5 "À traiter aujourd'hui" list — dedup by id across watchlist + opportunities.
 * Sorted by severity: critical → high → warn → medium → info.
 *
 * @param {object}   kpis
 * @param {object[]} watchlist    — from buildWatchlist()
 * @param {object[]} opportunities — from buildOpportunities()
 * @returns {TodayAction[]}  max 5 items
 *
 * TodayAction: { id, label, severity, path, cta, type }
 */
export function buildTodayActions(kpis, watchlist = [], opportunities = []) {
  const seen = new Set();
  const items = [];

  // Watchlist items first (already severity-sorted, critical issues)
  for (const w of watchlist) {
    if (!seen.has(w.id)) {
      seen.add(w.id);
      items.push({
        id: w.id,
        label: w.label,
        severity: w.severity,
        path: w.path,
        cta: w.cta,
        type: 'watchlist',
      });
    }
  }

  // Opportunities as 'info' (lower priority)
  for (const o of opportunities) {
    if (!seen.has(o.id)) {
      seen.add(o.id);
      items.push({
        id: o.id,
        label: o.label,
        severity: 'info',
        path: o.path,
        cta: o.cta,
        type: 'opportunity',
      });
    }
  }

  // Sort by severity rank, cap at 5
  items.sort((a, b) => (SEVERITY_RANK[a.severity] ?? 99) - (SEVERITY_RANK[b.severity] ?? 99));
  return items.slice(0, 5);
}

// ── buildExecutiveSummary ────────────────────────────────────────────────────

/**
 * Derive 3 executive-level bullets for the "Résumé exécutif" card.
 * One positive ("ce qui va"), one negative ("ce qui dérive"), one opportunity.
 *
 * @param {object}   kpis
 * @param {{ worst: object[], best: object[] }} topSites — from buildTopSites()
 * @returns {ExecBullet[]}   max 3 items
 *
 * ExecBullet: { id, type: 'positive'|'negative'|'warn'|'opportunity', label, sub?, path? }
 */
export function buildExecutiveSummary(kpis, _topSites = {}) {
  const bullets = [];
  const { total, conformes, nonConformes, aRisque, risqueTotal, couvertureDonnees } = kpis;
  const pctConf = total > 0 ? Math.round((conformes / total) * 100) : 0;

  // 1. Positive — what's going well
  if (total === 0) {
    bullets.push({
      id: 'no_sites',
      type: 'warn',
      label: 'Aucun site dans le périmètre',
      sub: 'Importez votre patrimoine pour démarrer',
    });
  } else if (pctConf >= CONFORMITY_THRESHOLDS.positive && nonConformes === 0 && aRisque === 0) {
    bullets.push({
      id: 'conforme_ok',
      type: 'positive',
      label: `${formatPercentFR(pctConf)} des sites en conformité`,
      sub: `${conformes} site${conformes > 1 ? 's' : ''} conforme${conformes > 1 ? 's' : ''} (Décret Tertiaire + BACS)`,
    });
  } else {
    bullets.push({
      id: 'conforme_partial',
      type: pctConf >= CONFORMITY_THRESHOLDS.warn ? 'warn' : 'negative',
      label: `${formatPercentFR(pctConf)} des sites en conformité`,
      sub: `${conformes} sur ${total} sites`,
    });
  }

  // 2. Negative — what's drifting
  if (nonConformes > 0) {
    bullets.push({
      id: 'non_conformes_exec',
      type: 'negative',
      label: `${nonConformes} site${nonConformes > 1 ? 's' : ''} nécessite${nonConformes > 1 ? 'nt' : ''} une mise en conformité`,
      sub: risqueTotal > 0 ? `Risque estimé : ${Math.round(risqueTotal / 1000)} k€` : null,
      path: '/conformite',
    });
  } else if (aRisque > 0) {
    bullets.push({
      id: 'a_risque_exec',
      type: 'warn',
      label: `${aRisque} site${aRisque > 1 ? 's' : ''} à surveiller (conformité réglementaire)`,
      sub: risqueTotal > 0 ? `Risque estimé : ${Math.round(risqueTotal / 1000)} k€` : null,
      path: '/conformite',
    });
  } else if (total > 0) {
    bullets.push({
      id: 'all_ok_exec',
      type: 'positive',
      label: 'Aucun écart réglementaire détecté',
      sub: 'Décret Tertiaire et BACS évalués — périmètre sous contrôle',
    });
  }

  // 3. Opportunity — data coverage or cost optimisation
  if (couvertureDonnees < COVERAGE_THRESHOLDS.opportunity && total > 0) {
    const missingSites = total - Math.round((couvertureDonnees * total) / 100);
    bullets.push({
      id: 'coverage_exec',
      type: 'opportunity',
      label: `${missingSites} site${missingSites > 1 ? 's' : ''} sans données de consommation`,
      sub: 'Importer les relevés pour affiner le score de maturité',
      path: '/consommations/import',
    });
  } else if (risqueTotal > RISK_THRESHOLDS.org.warn) {
    bullets.push({
      id: 'cost_exec',
      type: 'opportunity',
      label: `Optimisation potentielle sur ${Math.round(risqueTotal / 1000)} k€ de risque`,
      sub: 'Audit des contrats et abonnements recommandé',
      path: '/performance',
    });
  }

  return bullets.slice(0, 3);
}

// ── buildExecutiveKpis ───────────────────────────────────────────────────────

/**
 * Build 4 executive KPI tiles for the Vue exécutive décideur row.
 *
 * @param {object}   kpis
 * @param {object[]} sites — scopedSites (for couverture count)
 * @returns {ExecKpi[]}
 *
 * ExecKpi: { id, accentKey, label, value, sub, status, path? }
 */
export function buildExecutiveKpis(kpis, sites = []) {
  const { total, conformes, nonConformes, aRisque, risqueTotal, couvertureDonnees } = kpis;
  // A.2: Score unifié (0-100) si fourni par l'API, sinon fallback % conformes
  const complianceScore = kpis.compliance_score != null ? Math.round(kpis.compliance_score) : null;
  const pctConf =
    complianceScore != null
      ? complianceScore
      : total > 0
        ? Math.round((conformes / total) * 100)
        : 0;
  // Maturité score — continuous action readiness (0-100)
  const actionsActives =
    total > 0 ? Math.round((conformes / total) * 60 + ((total - nonConformes) / total) * 40) : 80;
  const readinessScore =
    total > 0
      ? Math.round(
          couvertureDonnees * READINESS_WEIGHTS.data +
            pctConf * READINESS_WEIGHTS.conformity +
            actionsActives * READINESS_WEIGHTS.actions
        )
      : 0;
  const sitesWithData = sites.filter((s) => s.conso_kwh_an > 0).length;

  return [
    {
      id: 'conformite',
      accentKey: 'conformite',
      label: 'Conformité réglementaire',
      value: total > 0 ? `${pctConf} / 100` : '—',
      rawValue: pctConf,
      messageCtx: { totalSites: total, sitesAtRisk: aRisque, sitesNonConformes: nonConformes },
      sub:
        complianceScore != null
          ? `Décret Tertiaire 45% · BACS 30% · APER 25%${kpis.compliance_confidence === 'low' ? ' · Données partielles' : ''}`
          : `${conformes} sur ${total} site${total !== 1 ? 's' : ''} conforme${conformes !== 1 ? 's' : ''}`,
      status:
        pctConf < COMPLIANCE_SCORE_THRESHOLDS.warn
          ? 'crit'
          : pctConf < COMPLIANCE_SCORE_THRESHOLDS.ok
            ? 'warn'
            : total > 0
              ? 'ok'
              : 'neutral',
      path: '/conformite',
      explain: 'compliance_score',
    },
    {
      id: 'risque',
      accentKey: 'risque',
      label: 'Risque financier',
      value: risqueTotal > 0 ? `${Math.round(risqueTotal / 1000)} k€` : '—',
      rawValue: risqueTotal,
      messageCtx: { sitesAtRisk: nonConformes + aRisque },
      sub: `${nonConformes + aRisque} site${nonConformes + aRisque !== 1 ? 's' : ''} concerné${nonConformes + aRisque !== 1 ? 's' : ''} (périmètre sélectionné)`,
      status: getRiskStatus(risqueTotal),
      path: '/actions',
    },
    {
      id: 'maturite',
      accentKey: 'maturite',
      label: 'Maturité plateforme',
      value: total > 0 ? formatPercentFR(readinessScore) : '—',
      rawValue: readinessScore,
      messageCtx: {},
      sub: 'Score combiné données, conformité et actions',
      status:
        readinessScore < MATURITY_THRESHOLDS.crit
          ? 'crit'
          : readinessScore < MATURITY_THRESHOLDS.warn
            ? 'warn'
            : 'ok',
    },
    {
      id: 'couverture',
      accentKey: 'neutral',
      label: 'Complétude données',
      value: total > 0 ? formatPercentFR(couvertureDonnees) : '—',
      rawValue: couvertureDonnees,
      messageCtx: {},
      sub: `${sitesWithData}/${total} site${total !== 1 ? 's' : ''} avec données de consommation`,
      status: couvertureDonnees < COVERAGE_THRESHOLDS.warn ? 'warn' : 'ok',
      path: '/consommations/import',
    },
  ];
}

// ── buildDashboardEssentials ────────────────────────────────────────────────

/**
 * Main aggregator — compute all dashboard model outputs from raw sites.
 * Mirrors the kpis useMemo in Cockpit.jsx but as a pure function.
 *
 * @param {object[]} sites         — scopedSites
 * @param {{ isExpert: boolean }}  opts
 * @returns dashboard essentials object
 */
export function buildDashboardEssentials(sites = [], { isExpert = false } = {}) {
  const total = sites.length;
  const conformes = sites.filter((s) => s.statut_conformite === 'conforme').length;
  const nonConformes = sites.filter((s) => s.statut_conformite === 'non_conforme').length;
  const aRisque = sites.filter((s) => s.statut_conformite === 'a_risque').length;
  const risqueTotal = sites.reduce((sum, s) => sum + (s.risque_eur || 0), 0);
  const couvertureDonnees =
    total > 0 ? Math.round((sites.filter((s) => s.conso_kwh_an > 0).length / total) * 100) : 0;

  const kpis = { total, conformes, nonConformes, aRisque, risqueTotal, couvertureDonnees };
  const watchlist = buildWatchlist(kpis, sites);
  const topSites = buildTopSites(sites);
  const opportunities = buildOpportunities(kpis, sites, { isExpert });

  const briefing = buildBriefing(kpis, watchlist);
  const consistency = checkConsistency(kpis);

  return {
    kpis,
    watchlist,
    briefing,
    topSites,
    opportunities,
    todayActions: buildTodayActions(kpis, watchlist, opportunities),
    executiveSummary: buildExecutiveSummary(kpis, topSites),
    executiveKpis: buildExecutiveKpis(kpis, sites),
    consistency,
    healthState: computeHealthState({ kpis, watchlist, briefing, consistency, alertsCount: 0 }),
  };
}

// ── computeHealthState ─────────────────────────────────────────────────────

/**
 * Compute unified health state from dashboard signals.
 * Pure function — no side effects, fully testable.
 *
 * @param {object} signals
 * @param {object}   signals.kpis         — { nonConformes, aRisque, ... }
 * @param {object[]} signals.watchlist     — from buildWatchlist()
 * @param {object[]} signals.briefing      — from buildBriefing()
 * @param {{ ok, issues }} signals.consistency — from checkConsistency()
 * @param {number}   signals.alertsCount   — critical + warn alert count
 * @returns {HealthState}
 */
export function computeHealthState({
  kpis,
  watchlist = [],
  briefing: _briefing = [],
  consistency = { ok: true },
  alertsCount = 0,
}) {
  const reasons = [];

  // Collect reasons from watchlist (already severity-sorted)
  for (const w of watchlist) {
    reasons.push({ id: w.id, label: w.label, severity: w.severity, link: w.path });
  }

  // Add consistency issues as 'warn'
  if (!consistency.ok) {
    for (const issue of consistency.issues || []) {
      reasons.push({
        id: `consistency-${issue.code}`,
        label: issue.label,
        severity: 'warn',
        link: '/consommations/import',
      });
    }
  }

  // Add active alerts as reasons (so they influence banner even without watchlist items)
  if (alertsCount > 0) {
    reasons.push({
      id: 'alerts-active',
      label: `${alertsCount} alerte${alertsCount > 1 ? 's' : ''} active${alertsCount > 1 ? 's' : ''}`,
      severity: alertsCount > 5 ? 'high' : 'medium',
      link: '/notifications',
    });
  }

  // 0% conformité with sites present = problem
  if (kpis.total > 0 && kpis.conformes === 0 && kpis.nonConformes === 0 && kpis.aRisque === 0) {
    reasons.push({
      id: 'conformite-unknown',
      label: 'Conformité non évaluée — lancer un scan',
      severity: 'warn',
      link: '/conformite',
    });
  }

  // Determine level
  const hasCritical = reasons.some((r) => r.severity === 'critical') || kpis.nonConformes > 0;
  const hasWarn =
    reasons.some((r) => ['high', 'warn', 'medium'].includes(r.severity)) ||
    alertsCount > 0 ||
    kpis.aRisque > 0;

  let level, title, subtitle;
  if (hasCritical) {
    level = 'RED';
    title = 'Actions requises';
    const critCount = reasons.filter((r) => r.severity === 'critical').length;
    subtitle = `${critCount} point${critCount > 1 ? 's' : ''} critique${critCount > 1 ? 's' : ''} — intervention recommandée`;
  } else if (hasWarn) {
    level = 'AMBER';
    title = "Points d'attention";
    subtitle = `${reasons.length} point${reasons.length > 1 ? 's' : ''} à surveiller`;
  } else {
    level = 'GREEN';
    title = 'Tout est sous contrôle';
    subtitle = 'Aucune action urgente — continuez la surveillance';
  }

  // CTA logic
  const primaryCta = hasCritical
    ? { label: 'Voir conformité', to: '/conformite' }
    : hasWarn
      ? { label: "Plan d'action", to: '/actions' }
      : { label: 'Explorer', to: '/consommations/explorer' };

  const secondaryCta =
    reasons.length > 3
      ? { label: `Voir les ${reasons.length} points`, to: '/anomalies' }
      : undefined;

  return {
    level,
    title,
    subtitle,
    reasons: reasons.slice(0, 3),
    allReasonCount: reasons.length,
    primaryCta,
    secondaryCta,
  };
}
