/**
 * PROMEOS — TopSitesCard (Sprint WOW Phase 7.0)
 * Two-column view: worst 5 (à risque) / best 5 (exemplaires).
 * Collapsed by default — "Analyse détaillée ▾" toggle.
 *
 * Props:
 *   topSites    {{ worst, best }} — from buildTopSites()
 *   onNavigate  {fn}             — navigate(path)
 */
import { useState } from 'react';
import { ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import { Card, CardBody, StatusDot } from '../../ui';

// ── Site row ─────────────────────────────────────────────────────────────────

function SiteRow({ site, dotStatus, sub, onNavigate }) {
  return (
    <button
      onClick={() => onNavigate?.(`/sites/${site.id}`)}
      title={site.nom}
      className="w-full flex items-center justify-between gap-2 py-2 hover:bg-gray-50 rounded px-1 text-left transition focus-visible:ring-2 focus-visible:ring-blue-500"
    >
      <div className="flex items-center gap-2 min-w-0">
        <StatusDot status={dotStatus} />
        <span className="text-sm text-gray-800 font-medium truncate">{site.nom}</span>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <span className="text-xs text-gray-400">{sub}</span>
        <ArrowRight size={12} className="text-gray-300" />
      </div>
    </button>
  );
}

// ── Column ───────────────────────────────────────────────────────────────────

function Column({ title, sites, dotStatus, subFn, onNavigate, emptyText }) {
  return (
    <div>
      <p className="text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">{title}</p>
      {sites.length > 0 ? (
        <div className="space-y-0.5">
          {sites.map((site) => (
            <SiteRow
              key={site.id}
              site={site}
              dotStatus={dotStatus(site)}
              sub={subFn(site)}
              onNavigate={onNavigate}
            />
          ))}
        </div>
      ) : (
        <p className="text-xs text-gray-400 italic py-2">{emptyText}</p>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────

export default function TopSitesCard({ topSites = { worst: [], best: [] }, onNavigate }) {
  const [expanded, setExpanded] = useState(false);
  const { worst = [], best = [] } = topSites;

  if (!worst.length && !best.length) return null;

  const worstDot = (site) => (site.statut_conformite === 'non_conforme' ? 'crit' : 'warn');

  const worstSub = (site) =>
    site.risque_eur > 0
      ? `${(site.risque_eur || 0).toLocaleString('fr-FR')}\u00a0€`
      : 'Risque non chiffré';

  const bestSub = () => 'Conforme';

  return (
    <Card>
      {/* Collapsible header */}
      <button
        onClick={() => setExpanded((v) => !v)}
        className="w-full flex items-center justify-between px-5 py-3.5 hover:bg-gray-50 transition rounded-t-xl focus-visible:ring-2 focus-visible:ring-blue-500"
        aria-expanded={expanded}
      >
        <h3 className="text-sm font-semibold text-gray-800">Analyse détaillée des sites</h3>
        {expanded ? (
          <ChevronUp size={16} className="text-gray-400" />
        ) : (
          <ChevronDown size={16} className="text-gray-400" />
        )}
      </button>

      {expanded && (
        <CardBody className="pt-1">
          <div className="grid grid-cols-2 gap-6">
            <Column
              title="Sites à risque"
              sites={worst}
              dotStatus={worstDot}
              subFn={worstSub}
              onNavigate={onNavigate}
              emptyText="Aucun site à risque — félicitations !"
            />
            <Column
              title="Sites exemplaires"
              sites={best}
              dotStatus={() => 'ok'}
              subFn={bestSub}
              onNavigate={onNavigate}
              emptyText="Aucun site conforme pour l'instant."
            />
          </div>
        </CardBody>
      )}
    </Card>
  );
}
