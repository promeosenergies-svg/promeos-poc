/**
 * PortefeuilleScoringCard - Pilotage V1.
 *
 * Classement portefeuille multi-sites par potentiel de pilotage.
 * Top-5 + mini-heatmap agregee par archetype.
 *
 * Source : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
 */
import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { getPortefeuilleScoring } from '../../services/api/pilotage';
import { useScope } from '../../contexts/ScopeContext';
import { toSite } from '../../services/routes';
import { fmtEur } from '../../utils/format';
import { Skeleton, InfoTip } from '../../ui';

function scoreBand(s) {
  if (s >= 75) return 'bg-emerald-500';
  if (s >= 55) return 'bg-amber-500';
  if (s >= 35) return 'bg-orange-500';
  return 'bg-gray-300';
}

function heatIntensity(gainTotal, maxGain) {
  if (!maxGain || maxGain <= 0) return 'bg-gray-50';
  const r = gainTotal / maxGain;
  if (r > 0.66) return 'bg-indigo-500 text-white';
  if (r > 0.33) return 'bg-indigo-300 text-indigo-900';
  return 'bg-indigo-100 text-indigo-800';
}

const NUMERIC_ID_RE = /^\d+$/;

export default function PortefeuilleScoringCard() {
  const { scope, scopedSites } = useScope();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Re-fetch au switch d'org ou portefeuille -- scoring recalcule cote backend.
  const scopeKey = `${scope?.orgId ?? 'none'}:${scope?.portefeuilleId ?? 'none'}`;

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    getPortefeuilleScoring()
      .then((d) => {
        if (!cancel) setData(d);
      })
      .catch(() => {
        if (!cancel) setError(true);
      })
      .finally(() => {
        if (!cancel) setLoading(false);
      });
    return () => {
      cancel = true;
    };
  }, [scopeKey]);

  const siteLabel = useMemo(() => {
    const byId = new Map();
    (scopedSites || []).forEach((s) => byId.set(String(s.id), s.nom));
    return (siteIdRaw) => byId.get(String(siteIdRaw)) || siteIdRaw;
  }, [scopedSites]);

  if (loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-portefeuille-card"
      >
        <Skeleton className="h-5 w-48 mb-3" />
        <Skeleton className="h-24 rounded mb-3" />
        <Skeleton className="h-12 rounded" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-portefeuille-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">Classement portefeuille</h3>
        <p className="text-xs text-gray-500">Scoring portefeuille temporairement indisponible.</p>
      </div>
    );
  }

  const {
    nb_sites_total,
    gain_annuel_portefeuille_eur,
    top_10 = [],
    heatmap_archetype = {},
  } = data;
  const top5 = top_10.slice(0, 5);
  const archetypes = Object.entries(heatmap_archetype).sort(
    (a, b) => (b[1]?.gain_total_eur || 0) - (a[1]?.gain_total_eur || 0)
  );
  const maxArchGain = archetypes.reduce((acc, [, v]) => Math.max(acc, v?.gain_total_eur || 0), 0);

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3"
      data-testid="pilotage-portefeuille-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Classement portefeuille</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Sites à prioriser par potentiel de pilotage
          </p>
        </div>
        <div className="text-right">
          <div className="text-[10px] text-gray-400 uppercase tracking-wide">Gain portefeuille</div>
          <div className="text-sm font-bold text-gray-900 whitespace-nowrap">
            {fmtEur(gain_annuel_portefeuille_eur)}/an
          </div>
        </div>
      </div>

      {top5.length === 0 ? (
        <p className="text-xs text-gray-500">Aucun site scopé pour l'instant.</p>
      ) : (
        <ol className="space-y-1.5">
          {top5.map((site) => {
            const siteIdStr = String(site.site_id);
            const isNumeric = NUMERIC_ID_RE.test(siteIdStr);
            const rowInner = (
              <>
                <span className="w-5 text-[10px] text-gray-400 font-medium">#{site.rang}</span>
                <span className="flex-1 min-w-0 truncate text-gray-800">
                  {siteLabel(site.site_id)}
                </span>
                <span className="text-[10px] text-gray-500 truncate max-w-[90px]">
                  {site.archetype || '—'}
                </span>
                <div className="w-20 h-1.5 bg-gray-100 rounded-full overflow-hidden">
                  <div
                    className={`h-full ${scoreBand(site.score)} rounded-full`}
                    style={{ width: `${Math.max(2, Math.round(site.score))}%` }}
                  />
                </div>
                <span className="w-16 text-right text-gray-900 font-medium whitespace-nowrap">
                  {fmtEur(site.gain_annuel_eur)}
                </span>
              </>
            );
            return (
              <li key={siteIdStr} data-testid={`portefeuille-row-${siteIdStr}`}>
                {isNumeric ? (
                  <Link
                    to={toSite(siteIdStr)}
                    className="flex items-center gap-2 text-xs rounded px-1 py-0.5 hover:bg-gray-50 focus:bg-gray-50 focus:outline-none focus:ring-1 focus:ring-indigo-400 no-underline"
                  >
                    {rowInner}
                  </Link>
                ) : (
                  <div
                    className="flex items-center gap-2 text-xs rounded px-1 py-0.5"
                    title="Disponible en production uniquement"
                    aria-disabled="true"
                  >
                    {rowInner}
                  </div>
                )}
              </li>
            );
          })}
        </ol>
      )}

      {archetypes.length > 0 && (
        <div>
          <div className="text-[10px] text-gray-500 uppercase tracking-wide mb-1 flex items-center gap-1">
            Heatmap archétype <InfoTip content="Intensité = gain annuel total par archétype" />
          </div>
          <div className="flex flex-wrap gap-1">
            {archetypes.map(([code, agg]) => (
              <span
                key={code}
                className={`text-[10px] px-2 py-0.5 rounded ${heatIntensity(
                  agg?.gain_total_eur || 0,
                  maxArchGain
                )}`}
                title={`${agg?.nb_sites || 0} site(s) · score moyen ${Math.round(
                  agg?.score_moyen || 0
                )}`}
              >
                {code} · {fmtEur(agg?.gain_total_eur)}
              </span>
            ))}
          </div>
        </div>
      )}

      <div className="text-[10px] text-gray-400 mt-auto pt-1 border-t border-gray-100">
        {nb_sites_total} site(s) · {data.source || 'Baromètre Flex 2026'}
      </div>
    </div>
  );
}
