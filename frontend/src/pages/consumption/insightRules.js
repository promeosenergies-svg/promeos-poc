/**
 * PROMEOS — insightRules
 * Pure functions that generate insight badges from Explorer Motor data.
 * Each rule receives the full data object and returns 0 or 1 insight.
 *
 * insight shape: { id, label, severity: 'info'|'warn'|'crit', detail }
 */

/**
 * Main entry point: run all rules and collect insights.
 * @param {object} data  — from useExplorerMotor (primaryTunnel, primaryHphc, etc.)
 * @param {string} mode  — agrege|superpose|empile|separe
 * @param {string} unit  — kwh|kw|eur
 * @returns {object[]} array of insights sorted by severity
 */
export function computeInsights(data = {}, mode = 'agrege', unit = 'kwh') {
  const rules = [
    ruleOutsideBandHigh,
    ruleBaseLoadDrift,
    ruleHpRatioHigh,
    ruleTargetOverBudget,
    ruleGasLeakSuspect,
    ruleLowConfidence,
  ];

  const insights = [];
  for (const rule of rules) {
    try {
      const insight = rule(data, mode, unit);
      if (insight) insights.push(insight);
    } catch {
      // Silent — never crash the page due to a bad insight rule
    }
  }

  // Sort: crit first, then warn, then info
  const ORDER = { crit: 0, warn: 1, info: 2 };
  return insights.sort((a, b) => (ORDER[a.severity] ?? 3) - (ORDER[b.severity] ?? 3));
}

// ── Individual rules ──────────────────────────────────────────────────────

/**
 * Tunnel: % outside band > 15% → warn
 */
function ruleOutsideBandHigh({ primaryTunnel } = {}) {
  if (!primaryTunnel) return null;
  const pct = primaryTunnel.outside_pct;
  if (pct == null || pct <= 15) return null;
  return {
    id: 'outside_band_high',
    label: `${pct}% hors bande tunnel`,
    severity: pct > 30 ? 'crit' : 'warn',
    detail: `${pct}% des relevés sont hors de l'enveloppe P10-P90 sur la période analysée.`,
  };
}

/**
 * Gas: base_drift > 10% → warn
 */
function ruleBaseLoadDrift({ primaryWeather } = {}) {
  if (!primaryWeather?.drift) return null;
  const drift = primaryWeather.drift.base_drift_pct;
  if (drift == null || Math.abs(drift) < 10) return null;
  return {
    id: 'base_load_drift',
    label: `Derive talon gaz ${drift > 0 ? '+' : ''}${drift}%`,
    severity: Math.abs(drift) > 20 ? 'crit' : 'warn',
    detail: `La consommation de base (hors chauffage) a derive de ${drift}% par rapport a la periode de reference.`,
  };
}

/**
 * HP/HC: hp_ratio > 0.7 → info (high HP consumption)
 */
function ruleHpRatioHigh({ primaryHphc } = {}) {
  if (!primaryHphc) return null;
  const ratio = primaryHphc.hp_ratio;
  if (ratio == null || ratio <= 0.7) return null;
  const pct = Math.round(ratio * 100);
  return {
    id: 'hp_ratio_high',
    label: `Ratio HP élevé (${pct}%)`,
    severity: ratio > 0.85 ? 'warn' : 'info',
    detail: `${pct}% de la consommation electrique est en Heures Pleines. Un report vers HC pourrait reduire la facture.`,
  };
}

/**
 * Targets: YTD progress > 110% of target → crit
 */
function ruleTargetOverBudget({ primaryProgression } = {}) {
  if (!primaryProgression) return null;
  const pct = primaryProgression.progress_pct;
  if (pct == null || pct <= 110) return null;
  const over = Math.round(pct - 100);
  return {
    id: 'target_over_budget',
    label: `Budget depasse de ${over}%`,
    severity: pct > 130 ? 'crit' : 'warn',
    detail: `La consommation YTD depasse l'objectif de ${over}%. Run-rate annuel : ${(primaryProgression.run_rate_kwh || 0).toLocaleString('fr-FR')} kWh.`,
  };
}

/**
 * Gas: probable_leak alert present → crit
 */
function ruleGasLeakSuspect({ primaryWeather } = {}) {
  if (!primaryWeather?.alerts?.length) return null;
  const leak = primaryWeather.alerts.find((a) => a.type === 'probable_leak');
  if (!leak) return null;
  return {
    id: 'gas_leak_suspect',
    label: 'Fuite gaz probable',
    severity: 'crit',
    detail:
      leak.message || "Consommation de base estivale anormalement elevee. Verifiez l'installation.",
  };
}

/**
 * Any panel with low confidence → info
 */
function ruleLowConfidence({ primaryTunnel, primaryHphc, primaryGas } = {}) {
  const panels = [primaryTunnel, primaryHphc, primaryGas].filter(Boolean);
  const hasLow = panels.some((p) => p.confidence === 'low');
  if (!hasLow) return null;
  return {
    id: 'low_confidence',
    label: 'Donnees insuffisantes',
    severity: 'info',
    detail:
      'Un ou plusieurs panneaux disposent de peu de relevés. Les analyses peuvent etre moins fiables.',
  };
}
