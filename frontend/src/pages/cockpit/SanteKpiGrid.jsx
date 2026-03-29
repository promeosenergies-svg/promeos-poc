/**
 * SanteKpiGrid — 4 KPI cards santé (Conformité, Qualité données, Contrats, Consommation).
 * Données 100% backend via /cockpit/executive-v2 → sante.
 */
import { ShieldCheck, Database, FileSignature, Zap, AlertTriangle } from 'lucide-react';

const STATUS_DOT = {
  ok: 'bg-emerald-500',
  warn: 'bg-amber-400',
  crit: 'bg-red-500',
};

const CARDS = [
  {
    key: 'conformite',
    label: 'Conformité réglementaire',
    icon: ShieldCheck,
    iconBg: 'bg-blue-50',
    iconText: 'text-blue-600',
    renderValue: (d) => `${d.score} / 100`,
    renderDetail: (d) => (
      <>
        {d.non_conformes > 0 && <span className="text-red-600">{d.non_conformes} NC</span>}
        {d.non_conformes > 0 && d.a_risque > 0 && <span className="text-gray-400"> · </span>}
        {d.a_risque > 0 && <span className="text-amber-600">{d.a_risque} à risque</span>}
        {d.trend && <span className="text-emerald-600 block mt-0.5">{d.trend}</span>}
      </>
    ),
  },
  {
    key: 'qualite_donnees',
    label: 'Qualité données',
    icon: Database,
    iconBg: 'bg-blue-50',
    iconText: 'text-blue-600',
    renderValue: (d) => `${d.score} / 100`,
    renderDetail: (d) =>
      `${d.sites_avec_donnees}/${d.total_sites} sites · ${d.briques_completes} briques OK`,
  },
  {
    key: 'contrats',
    label: 'Contrats énergie',
    icon: FileSignature,
    iconBg: 'bg-purple-50',
    iconText: 'text-purple-600',
    renderValue: (d) => `${d.actifs} actif${d.actifs > 1 ? 's' : ''}`,
    renderDetail: (d) => (
      <>
        <span>{d.couverture_pct}% couverts</span>
        {d.expirant_90j > 0 && (
          <span className="flex items-center gap-1 mt-0.5 text-amber-600">
            <AlertTriangle size={11} className="shrink-0" />
            {d.expirant_90j} expire{d.expirant_90j > 1 ? 'nt' : ''} sous 90j
          </span>
        )}
      </>
    ),
  },
  {
    key: 'consommation',
    label: 'Consommation',
    icon: Zap,
    iconBg: 'bg-indigo-50',
    iconText: 'text-indigo-600',
    renderValue: (d) => `${d.total_mwh?.toLocaleString('fr-FR')} MWh`,
    renderDetail: (d) =>
      `${d.kwh_m2_an?.toLocaleString('fr-FR')} kWh/m²/an · ${d.couverture_pct}% couvert`,
  },
];

export default function SanteKpiGrid({ sante }) {
  if (!sante) return null;

  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {CARDS.map((card) => {
        const data = sante[card.key];
        if (!data) return null;
        const Icon = card.icon;
        const dotClass = STATUS_DOT[data.status] || STATUS_DOT.ok;

        return (
          <div
            key={card.key}
            className="rounded-xl border border-gray-100 bg-white px-4 py-3 flex items-start gap-3"
          >
            {/* Icon */}
            <div
              className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 mt-0.5 ${card.iconBg}`}
            >
              <Icon size={18} className={card.iconText} />
            </div>

            {/* Text */}
            <div className="flex-1 min-w-0">
              <p className="text-[10px] font-medium uppercase tracking-wider text-gray-400">
                {card.label}
              </p>
              <div className="flex items-center gap-1.5 mt-0.5">
                <p className="text-lg font-bold text-gray-900 leading-tight">
                  {card.renderValue(data)}
                </p>
                <span className={`w-2 h-2 rounded-full shrink-0 ${dotClass}`} aria-hidden="true" />
              </div>
              <div className="text-xs text-gray-500 mt-0.5">
                {typeof card.renderDetail === 'function'
                  ? card.renderDetail(data)
                  : card.renderDetail}
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
