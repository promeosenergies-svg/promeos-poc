/**
 * Utility functions extracted from ConformitePage.
 * Pure logic, no React — can be imported by page and sub-components.
 */
import { REG_LABELS, REG_DESCRIPTIONS } from '../../domain/compliance/complianceLabels.fr';

/**
 * Resolve scope type and id from scope object.
 */
export function resolveScopeLabel(scope) {
  const scopeType = scope.siteId ? 'site' : scope.portefeuilleId ? 'portefeuille' : 'org';
  const scopeId = scope.siteId || scope.portefeuilleId || scope.orgId;
  return { scopeType, scopeId, label: `${scopeType}/${scopeId}` };
}

/**
 * Build API scope params from ScopeContext.
 * Always includes org_id. Adds portefeuille_id or site_id based on scope.
 */
export function buildScopeParams(scope, scopedSites) {
  const params = { org_id: scope.orgId };
  if (scopedSites.length === 1) {
    params.site_id = scopedSites[0].id;
  } else if (scope.portefeuilleId) {
    params.portefeuille_id = scope.portefeuilleId;
  }
  return params;
}

/**
 * Parse a bundle response for error state.
 * Returns null if the bundle is healthy, or an error object with message/error_code/trace_id/hint.
 */
export function parseBundleError(bundle) {
  if (!bundle) return { message: 'Donnees de conformite indisponibles' };
  if (bundle.error_code) {
    return {
      message: bundle.empty_reason_message || 'Donnees de conformite indisponibles',
      error_code: bundle.error_code,
      trace_id: bundle.trace_id,
      hint: bundle.hint,
    };
  }
  return null;
}

/**
 * Compute aggregated BACS v2 summary from bundle.bacs_v2 data.
 */
export function computeBacsV2Summary(bacsV2Data) {
  if (!bacsV2Data) return null;
  const entries = Object.values(bacsV2Data);
  if (entries.length === 0) return null;
  const applicable = entries.some((e) => e.applicable);
  const deadlines = entries.map((e) => e.deadline).filter(Boolean);
  const closest = deadlines.length ? deadlines.sort()[0] : null;
  const maxPutile = Math.max(...entries.map((e) => e.putile_kw || 0));
  // Seuil applicable = base sur le putile max reel (pas le max des seuils)
  const applicableThreshold = maxPutile >= 290 ? 290 : 70;
  const triExemption = entries.some((e) => e.tri_exemption);
  return {
    applicable,
    deadline: closest,
    putile_kw: maxPutile || null,
    threshold_kw: applicableThreshold || null,
    tier: maxPutile >= 290 ? 'TIER1' : 'TIER2',
    tri_exemption: triExemption,
  };
}

/**
 * Compute human-readable scope label.
 */
export function computeScopeLabel(org, scope, scopedSites, portefeuilles) {
  const orgName = org?.nom || 'Societe';
  if (scope?.siteId) {
    const site = scopedSites?.[0];
    return `${orgName} · Site: ${site?.nom || scope.siteId}`;
  }
  if (scope?.portefeuilleId) {
    const pf = portefeuilles?.find((p) => p.id === scope.portefeuilleId);
    return `${orgName} · Portefeuille: ${pf?.nom || scope.portefeuilleId} (${scopedSites?.length || 0} sites)`;
  }
  return `${orgName} · Societe (${scopedSites?.length || 0} sites)`;
}

export function isOverdue(obligation) {
  if (!obligation.echeance || obligation.statut === 'conforme') return false;
  return new Date(obligation.echeance) < new Date();
}

/**
 * Format a deadline date with contextual wording.
 * Past deadlines for non-conforme obligations show "Echeance depassee depuis le ..."
 * Future deadlines show the date normally.
 */
export function formatDeadline(echeance, statut) {
  if (!echeance) return null;
  const d = new Date(echeance);
  const formatted = d.toLocaleDateString('fr-FR', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });
  if (statut !== 'conforme' && d < new Date()) {
    return { text: `Échéance dépassée depuis le ${formatted}`, overdue: true };
  }
  return { text: formatted, overdue: false };
}

/**
 * Transform API sitesData (from /compliance/sites) into obligation-like objects
 * grouped by regulation, for display in ObligationCard.
 */
export function sitesToObligations(sitesData, _summary) {
  if (!sitesData || !sitesData.length) return [];
  const byReg = {};

  for (const site of sitesData) {
    for (const f of site.findings) {
      // CEE = incentive, not obligation — skip here
      if (f.category === 'incentive' || (f.regulation || '').toLowerCase().includes('cee'))
        continue;
      const reg = f.regulation;
      if (!byReg[reg]) {
        byReg[reg] = {
          id: reg,
          regulation: REG_LABELS[reg] || reg,
          code: reg,
          description: REG_DESCRIPTIONS[reg] || reg,
          severity: 'low',
          statut: 'conforme',
          echeance: null,
          sites_concernes: 0,
          sites_conformes: 0,
          findings: [],
          _site_ids_all: new Set(),
          _site_ids_ok: new Set(),
        };
      }
      const obl = byReg[reg];
      obl.findings.push({ ...f, site_nom: site.site_nom, site_id: site.site_id });
      obl._site_ids_all.add(site.site_id);

      // Track worst severity
      const sevOrder = { critical: 4, high: 3, medium: 2, low: 1 };
      if (f.severity && (sevOrder[f.severity] || 0) > (sevOrder[obl.severity] || 0)) {
        obl.severity = f.severity;
      }

      // Track worst status
      if (f.status === 'NOK') {
        obl.statut = 'non_conforme';
      } else if (f.status === 'UNKNOWN' && obl.statut === 'conforme') {
        obl.statut = 'a_qualifier';
      } else if (f.status === 'OUT_OF_SCOPE') {
        if (obl.statut === 'conforme') obl.statut = 'hors_perimetre';
      }

      // Track closest deadline
      if (f.deadline) {
        if (!obl.echeance || f.deadline < obl.echeance) {
          obl.echeance = f.deadline;
        }
      }

      // Track OK sites
      if (f.status === 'OK') {
        obl._site_ids_ok.add(site.site_id);
      }
    }
  }

  return Object.values(byReg).map((obl) => ({
    ...obl,
    sites_concernes: obl._site_ids_all.size,
    sites_conformes: obl._site_ids_ok.size,
    proof_status:
      obl.statut === 'conforme'
        ? 'ok'
        : obl.statut === 'a_qualifier'
          ? 'pending'
          : obl.statut === 'a_risque'
            ? 'in_progress'
            : 'missing',
    pourquoi: `${obl._site_ids_all.size} site(s) concerné(s) par ${obl.regulation}`,
    quoi_faire:
      obl.findings
        .filter((f) => f.actions?.length)
        .flatMap((f) => f.actions)
        .filter((v, i, a) => a.indexOf(v) === i)
        .join('. ') || 'Évaluer la conformité',
    preuve: 'Attestation ou rapport de conformité',
    impact_eur: 0,
  }));
}

/**
 * Extract CEE/incentive findings from sitesData (separated from obligations).
 */
export function sitesToIncentives(sitesData) {
  if (!sitesData || !sitesData.length) return [];
  const items = [];
  for (const site of sitesData) {
    for (const f of site.findings) {
      if (f.category === 'incentive' || (f.regulation || '').toLowerCase().includes('cee')) {
        items.push({ ...f, site_nom: site.site_nom, site_id: site.site_id });
      }
    }
  }
  return items;
}
