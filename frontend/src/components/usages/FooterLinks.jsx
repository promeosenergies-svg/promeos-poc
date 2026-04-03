import { useNavigate } from 'react-router-dom';

const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

function plural(n, word) {
  return `${n} ${word}${n > 1 ? 's' : ''}`;
}

function monthsUntil(dateStr) {
  if (!dateStr) return null;
  const end = new Date(dateStr);
  const now = new Date();
  const diff = (end.getFullYear() - now.getFullYear()) * 12 + (end.getMonth() - now.getMonth());
  return diff > 0 ? diff : diff <= 0 ? -1 : null;
}

function getDiagnosticKpi(drifts, activeDrifts) {
  const alertCount = drifts || activeDrifts;
  if (alertCount === 0) return { sub: 'Aucune anomalie', kpi: null, kpiStyle: '' };
  if (drifts > 0) {
    return {
      sub: `${plural(drifts, 'dérive')} détectée${drifts > 1 ? 's' : ''}`,
      kpi: `${plural(alertCount, 'alerte')}`,
      kpiStyle: 'bg-red-50 text-red-600',
    };
  }
  return {
    sub: `${plural(activeDrifts, 'anomalie')}`,
    kpi: `${plural(alertCount, 'alerte')}`,
    kpiStyle: 'bg-red-50 text-red-600',
  };
}

function getRenewalKpi(renewalMonths, contract) {
  if (renewalMonths === -1) {
    return { kpi: 'Contrat expiré', kpiStyle: 'bg-red-50 text-red-600' };
  }
  if (renewalMonths != null && renewalMonths > 0) {
    const style = renewalMonths <= 6 ? 'bg-red-50 text-red-600' : 'bg-blue-50 text-blue-600';
    return { kpi: `Échéance ${renewalMonths} mois`, kpiStyle: style };
  }
  if (contract) return { kpi: 'Contrat actif', kpiStyle: 'bg-green-50 text-green-600' };
  return { kpi: null, kpiStyle: 'bg-green-50 text-green-600' };
}

export default function FooterLinks({ archetypeFilter, dashboard }) {
  const navigate = useNavigate();
  const scope = archetypeFilter ? `?archetype=${archetypeFilter}` : '';

  const baselines = dashboard?.baselines || [];
  const drifts = baselines.filter((b) => b.trend === 'degradation').length;
  const activeDrifts = dashboard?.active_drifts?.length || 0;

  const compliance = dashboard?.compliance;
  const bacsScore = compliance?.bacs_score ?? compliance?.usage_coverage?.coverage_pct ?? null;
  const uncoveredBacs =
    compliance?.items?.filter((i) => i.concerned_by_bacs && !i.bacs_covered).length || 0;

  const billingLinks = dashboard?.billing_links;
  const contract = billingLinks?.contract;
  const renewalMonths = monthsUntil(contract?.end_date);
  const invoiceCount = billingLinks?.invoices?.length || 0;

  const costBreakdown = dashboard?.cost_breakdown;
  const uncoveredPct =
    costBreakdown?.total_kwh > 0 && costBreakdown?.uncovered_kwh > 0
      ? Math.round((costBreakdown.uncovered_kwh / costBreakdown.total_kwh) * 100)
      : 0;

  const sitesCount = dashboard?.sites_count ?? 0;
  const totalSurface = dashboard?.summary?.total_surface_m2 ?? 0;

  const diag = getDiagnosticKpi(drifts, activeDrifts);
  const renewal = getRenewalKpi(renewalMonths, contract);

  const links = [
    {
      title: 'Diagnostic',
      icon: '🔍',
      sub: diag.sub,
      kpi: diag.kpi,
      kpiStyle: diag.kpiStyle,
      to: `/diagnostic-conso${scope}`,
    },
    {
      title: 'Conformité',
      icon: '📋',
      sub: 'Scoring DT / BACS / APER',
      kpi: bacsScore != null ? `BACS ${Math.round(bacsScore)}` : null,
      kpiStyle: uncoveredBacs > 0 ? 'bg-amber-50 text-amber-600' : 'bg-green-50 text-green-600',
      to: `/conformite/tertiaire${scope}#bacs`,
    },
    {
      title: 'Factures',
      icon: '🧾',
      sub: invoiceCount > 0 ? `${plural(invoiceCount, 'facture')} · 12 mois` : 'Suivi & anomalies',
      kpi: uncoveredPct > 5 ? `${uncoveredPct}% non ventilé` : invoiceCount > 0 ? 'OK' : null,
      kpiStyle: uncoveredPct > 5 ? 'bg-amber-50 text-amber-600' : 'bg-green-50 text-green-600',
      to: `/bill-intel${scope}`,
    },
    {
      title: 'Achat énergie',
      icon: '⚡',
      sub: contract?.supplier ? `${contract.supplier}` : 'Stratégie & scénarios',
      kpi: renewal.kpi,
      kpiStyle: renewal.kpiStyle,
      to: `/achat-energie${scope}`,
    },
    {
      title: 'Actions',
      icon: '🎯',
      sub: "Plan d'action cross-module",
      kpi: activeDrifts > 0 ? `${activeDrifts} à traiter` : null,
      kpiStyle: 'bg-amber-50 text-amber-600',
      to: `/actions${scope}`,
    },
    {
      title: 'Patrimoine',
      icon: '🏢',
      sub: `${plural(sitesCount, 'site')} · ${fmt(totalSurface)} m²`,
      kpi: sitesCount > 0 ? plural(sitesCount, 'site') : null,
      kpiStyle: 'bg-blue-50 text-blue-600',
      to: `/patrimoine${scope}`,
    },
  ];

  return (
    <div className="px-7 pb-6 print:hidden">
      <div className="text-[10px] text-gray-400 font-semibold tracking-wide mb-2">
        NAVIGATION CONTEXTUELLE
      </div>
      <div className="grid grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-2.5">
        {links.map((l) => (
          <button
            key={l.to}
            onClick={() => navigate(l.to)}
            className="bg-white border border-gray-200 rounded-xl px-3.5 py-3 text-left hover:border-blue-400 hover:shadow-sm transition-all hover:-translate-y-px group"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-semibold group-hover:text-blue-600 transition-colors">
                {l.icon} {l.title}
              </span>
              <span className="text-gray-300 group-hover:text-blue-400 transition-colors">→</span>
            </div>
            <div className="text-[10px] text-gray-400 mt-0.5">{l.sub}</div>
            {l.kpi && (
              <span
                className={`inline-block text-[9px] font-semibold px-1.5 py-0.5 rounded mt-1.5 ${l.kpiStyle}`}
              >
                {l.kpi}
              </span>
            )}
          </button>
        ))}
      </div>
    </div>
  );
}
