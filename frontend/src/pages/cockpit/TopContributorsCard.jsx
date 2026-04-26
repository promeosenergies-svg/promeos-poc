/**
 * TopContributorsCard — drill-down Pareto sous HeroImpactBar.
 *
 * Source : GET /api/cockpit/top-contributors (lazy fetch à l'expand).
 * Affiche les N sites contributeurs avec breakdown
 * conformité/factures/optimisation et flag certitude (certain/probable/
 * potentiel) pour qualifier la nature du risque côté CODIR.
 */
import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ChevronDown, ChevronUp, ArrowRight } from 'lucide-react';
import { getTopContributors } from '../../services/api';
import { fmtEur } from '../../utils/format';
import { SEVERITY, SEVERITY_CLASSES } from '../../ui/severity';

// Mapping certainty backend (`certain/probable/potentiel`) → severity du
// design system (`critical/warn/ok`) — utilisé pour la pill couleur.
const CERTAINTY_TO_SEVERITY = {
  certain: { label: 'Certain', severity: SEVERITY.CRITICAL },
  probable: { label: 'Probable', severity: SEVERITY.WARN },
  potentiel: { label: 'Potentiel', severity: SEVERITY.OK },
};

export default function TopContributorsCard({ defaultExpanded = false, limit = 5 }) {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(defaultExpanded);

  useEffect(() => {
    if (!expanded || data) return;
    let cancelled = false;
    setLoading(true);
    getTopContributors(limit)
      .then((d) => {
        if (!cancelled) setData(d);
      })
      .catch(() => {
        if (!cancelled) setData({ contributors: [], total_eur: 0, site_count: 0 });
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => {
      cancelled = true;
    };
  }, [expanded, data, limit]);

  return (
    <div className="rounded-xl border border-gray-200 bg-white" data-testid="top-contributors">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        aria-expanded={expanded}
        className="w-full flex items-center justify-between gap-3 px-5 py-3 hover:bg-gray-50/60 rounded-xl transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500"
      >
        <div className="flex items-center gap-3 min-w-0">
          <span className="inline-flex items-center px-2 py-0.5 rounded-full bg-blue-50 text-blue-700 text-[10px] font-semibold uppercase tracking-wider ring-1 ring-blue-200">
            Pareto 80/20
          </span>
          <span className="text-sm font-medium text-gray-900">
            Top {limit} sites contributeurs — où sont les € ?
          </span>
        </div>
        <span aria-hidden="true" className="text-gray-400">
          {expanded ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
        </span>
      </button>

      {expanded && (
        <div className="px-5 pb-4 pt-1 border-t border-gray-100">
          {loading && (
            <div className="py-4 text-xs text-gray-400">Chargement des contributeurs…</div>
          )}
          {!loading && data && data.contributors?.length === 0 && (
            <div className="py-4 text-xs text-gray-400">
              Aucun contributeur identifié sur le périmètre.
            </div>
          )}
          {!loading && data && data.contributors?.length > 0 && (
            <>
              <p className="text-[11px] text-gray-500 mb-3">
                <strong className="text-gray-700">{data.pareto_share_pct}%</strong> de l'impact
                total concentré sur ces {data.contributors.length} site
                {data.contributors.length > 1 ? 's' : ''} ({data.site_count} site
                {data.site_count > 1 ? 's' : ''} contributeur{data.site_count > 1 ? 's' : ''} au
                total).
              </p>
              <ul className="divide-y divide-gray-100">
                {data.contributors.map((c, idx) => {
                  const cert =
                    CERTAINTY_TO_SEVERITY[c.certainty] ?? CERTAINTY_TO_SEVERITY.potentiel;
                  const certClasses = SEVERITY_CLASSES[cert.severity];
                  return (
                    <li key={c.site_id}>
                      <button
                        type="button"
                        onClick={() => navigate(`/sites/${c.site_id}`)}
                        className="w-full flex items-center justify-between gap-3 py-2.5 hover:bg-blue-50/40 -mx-2 px-2 rounded transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 text-left"
                      >
                        <div className="flex items-center gap-3 min-w-0 flex-1">
                          <span
                            className="shrink-0 inline-flex items-center justify-center w-6 h-6 rounded-full bg-gray-100 text-gray-700 text-[11px] font-semibold"
                            aria-hidden="true"
                          >
                            {idx + 1}
                          </span>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-gray-900 truncate">
                              {c.site_nom}
                              {c.ville && (
                                <span className="text-gray-400 font-normal ml-2">{c.ville}</span>
                              )}
                            </p>
                            <p className="text-[11px] text-gray-500 mt-0.5">
                              Conf. {fmtEur(c.conformite_eur)} · Fact. {fmtEur(c.factures_eur)} ·
                              Optim. {fmtEur(c.optimisation_eur)}
                            </p>
                          </div>
                        </div>
                        <div className="shrink-0 flex items-center gap-2">
                          <span
                            className={`inline-flex items-center px-1.5 py-0.5 rounded text-[10px] font-medium ring-1 ${certClasses.pill}`}
                            title={`Niveau de certitude : ${cert.label}`}
                          >
                            {cert.label}
                          </span>
                          <span className="text-sm font-semibold text-gray-900">
                            {fmtEur(c.total_eur)}
                          </span>
                          <ArrowRight size={13} className="text-gray-400" aria-hidden="true" />
                        </div>
                      </button>
                    </li>
                  );
                })}
              </ul>
              <p className="text-[10px] text-gray-400 mt-3">
                Certain = pénalité chiffrée · Probable = anomalie facture détectée · Potentiel =
                économie estimée. Cliquer un site pour le drill-down complet.
              </p>
            </>
          )}
        </div>
      )}
    </div>
  );
}
