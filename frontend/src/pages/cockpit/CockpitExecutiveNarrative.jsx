/**
 * CockpitExecutiveNarrative — Cockpit P1 (2026-05-25).
 *
 * Rend les 2 blocs Executive Narrative injectés par /api/cockpit/strategique :
 *   1. Bloc « Situation en 30 secondes » : 5 chiffres clés (score / surfact /
 *      échéance / actions / sites) — payload.executive_summary.kpis
 *   2. Bloc « Top 3 priorités » : actions cross-briques avec impact +
 *      échéance + CTA unique — payload.top_priorities
 *   3. Bloc « Pourquoi c'est important » : micro-copy actionnable
 *
 * Doctrine §8.1 : zéro logique métier FE — tous les libellés et nombres
 * viennent du backend (compute_executive_narrative). Le FE ne fait que
 * formater visuellement (€ FR, ArrowRight icon, couleur seuil).
 *
 * Doctrine §6.2 hub unique : chaque CTA pointe vers une page existante
 * (/conformite, /bill-intel, /centre-action, /patrimoine).
 */
import React from 'react';
import { Link } from 'react-router-dom';
import {
  ShieldCheck,
  Receipt,
  CalendarClock,
  ListChecks,
  Building2,
  AlertTriangle,
  ArrowRight,
  Info,
} from 'lucide-react';
// Cockpit P1 (2026-05-25) — Glose les acronymes (DT, OPERAT, BACS, APER,
// SMÉ, BEGES) dans les libellés produits par le backend pour rester
// lisibles par DG/DAF non-expert (Phase 3 UX/acronymes).
import SolNarrativeText from '../../ui/sol/SolNarrativeText';

function formatEuros(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  if (value <= 0) return '0 €';
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 0 }).format(value) + ' €';
}

function formatNumber(value) {
  if (typeof value !== 'number' || Number.isNaN(value)) return '—';
  return new Intl.NumberFormat('fr-FR', { maximumFractionDigits: 1 }).format(value);
}

// Mapping KPI id → icône (présentation seule, pas de logique métier).
const KPI_ICONS = {
  score_conformite: ShieldCheck,
  risque_financier_a_contester: Receipt,
  prochaine_echeance: CalendarClock,
  actions_ouvertes: ListChecks,
  sites_dans_perimetre: Building2,
};

function KpiBlock({ kpi }) {
  const Icon = KPI_ICONS[kpi.id] || Info;
  const value = kpi.value;
  let display;
  if (value == null) {
    display = '—';
  } else if (kpi.unit === '€') {
    display = formatEuros(value);
  } else if (kpi.unit === '/100') {
    display = formatNumber(value) + ' /100';
  } else if (kpi.unit === 'jours') {
    display = value + ' j';
  } else {
    display = formatNumber(value);
  }

  // Couleur seuil pour score conformité (présentation, BE fournit la valeur).
  let colorClass = 'text-gray-900';
  if (kpi.id === 'score_conformite' && typeof value === 'number') {
    if (value < 50) colorClass = 'text-red-600';
    else if (value < 70) colorClass = 'text-amber-600';
    else colorClass = 'text-emerald-600';
  } else if (kpi.id === 'risque_financier_a_contester' && value > 0) {
    colorClass = 'text-amber-700';
  } else if (kpi.id === 'prochaine_echeance' && typeof value === 'number' && value < 30) {
    colorClass = 'text-red-600';
  }

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4 flex flex-col gap-1"
      data-testid={`exec-kpi-${kpi.id}`}
      title={`Source : ${kpi.source} · Formule : ${kpi.formula}`}
    >
      <div className="flex items-center gap-2 text-xs font-medium uppercase tracking-wider text-gray-500">
        <Icon size={14} className="text-gray-400" aria-hidden="true" />
        <SolNarrativeText text={kpi.label_fr} />
      </div>
      <div className={`text-2xl font-bold ${colorClass}`} data-testid={`exec-kpi-${kpi.id}-value`}>
        {display}
        {kpi.unit && !['€', '/100', 'jours'].includes(kpi.unit) && (
          <span className="ml-1 text-sm font-normal text-gray-400">{kpi.unit}</span>
        )}
      </div>
      {kpi.sub_label_fr && (
        <p className="text-[11px] text-gray-500">
          <SolNarrativeText text={kpi.sub_label_fr} />
        </p>
      )}
      <p className="text-[10px] text-gray-400 mt-auto">Périmètre : {kpi.scope}</p>
    </div>
  );
}

function PriorityCard({ priority }) {
  const { label_fr, why_fr, impact, deadline, perimetre_fr, cta, priority_rank } = priority;
  const impactDisplay =
    impact?.unit === '€' ? formatEuros(impact.value) : `${impact?.value ?? '—'} ${impact?.unit ?? ''}`;
  const deadlineDisplay = deadline?.days_remaining != null
    ? `dans ${deadline.days_remaining} j`
    : null;

  return (
    <div
      className="rounded-lg border border-gray-200 bg-white p-4 flex flex-col gap-2"
      data-testid={`exec-priority-${priority_rank}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-center gap-2">
          <span className="inline-flex items-center justify-center w-6 h-6 rounded-full bg-emerald-100 text-emerald-700 text-xs font-bold">
            {priority_rank}
          </span>
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            {why_fr}
          </span>
        </div>
        <span className="text-[10px] text-gray-400">{perimetre_fr}</span>
      </div>
      <p className="text-sm font-medium text-gray-900">
        <SolNarrativeText text={label_fr} />
      </p>
      <div className="flex items-center gap-3 text-xs text-gray-600">
        <span>
          <strong className="text-gray-900">Impact :</strong> {impactDisplay}
        </span>
        {deadlineDisplay && (
          <span>
            <strong className="text-gray-900">Échéance :</strong> {deadlineDisplay}
          </span>
        )}
      </div>
      {cta?.link && (
        <Link
          to={cta.link}
          className="mt-auto inline-flex items-center gap-1 text-xs font-medium text-emerald-700 hover:text-emerald-800"
          data-testid={`exec-priority-${priority_rank}-cta`}
        >
          {cta.label_fr || 'Ouvrir'}
          <ArrowRight size={12} aria-hidden="true" />
        </Link>
      )}
    </div>
  );
}

const WHY_MICROCOPY = [
  { label: 'Risque réglementaire', desc: 'Échéance ou non-conformité avec impact financier potentiel.' },
  { label: 'Montant à contester', desc: 'Surfacturation détectée — gain immédiat possible.' },
  { label: 'Donnée manquante', desc: 'Information bloquante pour évaluer un site ou une obligation.' },
  { label: 'Action en attente', desc: 'Tâche assignée à un pilote, non clôturée.' },
];

/**
 * @param {object} props
 * @param {{ kpis: Array, _error?: string }|null} props.executiveSummary
 * @param {Array} props.topPriorities
 */
export default function CockpitExecutiveNarrative({ executiveSummary, topPriorities }) {
  const kpis = executiveSummary?.kpis || [];
  const priorities = topPriorities || [];

  if (kpis.length === 0 && priorities.length === 0) {
    return null;
  }

  return (
    <section
      className="mt-3 mb-5 space-y-4"
      data-testid="cockpit-executive-narrative"
      aria-label="Synthèse exécutive"
    >
      {/* Bloc 1 — Situation en 30 secondes */}
      {kpis.length > 0 && (
        <div data-testid="exec-situation">
          <h3 className="mb-2 text-sm font-semibold text-gray-700 flex items-center gap-2">
            <Info size={16} className="text-emerald-600" aria-hidden="true" />
            Situation en 30 secondes
          </h3>
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
            {kpis.map((k) => (
              <KpiBlock key={k.id} kpi={k} />
            ))}
          </div>
        </div>
      )}

      {/* Bloc 2 — Top 3 priorités */}
      {priorities.length > 0 && (
        <div data-testid="exec-top-priorities">
          <h3 className="mb-2 text-sm font-semibold text-gray-700 flex items-center gap-2">
            <AlertTriangle size={16} className="text-amber-600" aria-hidden="true" />
            Top {priorities.length} priorité{priorities.length > 1 ? 's' : ''} — à traiter maintenant
          </h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {priorities.map((p) => (
              <PriorityCard key={p.id} priority={p} />
            ))}
          </div>
        </div>
      )}

      {/* Bloc 3 — Pourquoi c'est important (micro-copy actionnable) */}
      <details
        className="rounded-lg border border-gray-100 bg-gray-50/40"
        data-testid="exec-why-microcopy"
      >
        <summary className="cursor-pointer select-none p-3 text-sm font-medium text-gray-700">
          Pourquoi c'est important
        </summary>
        <div className="border-t border-gray-100 p-3 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3">
          {WHY_MICROCOPY.map((item) => (
            <div key={item.label} className="text-xs">
              <p className="font-semibold text-gray-800">{item.label}</p>
              <p className="text-gray-600 mt-0.5">{item.desc}</p>
            </div>
          ))}
        </div>
      </details>
    </section>
  );
}
