/**
 * RadarPrixNegatifsCard - Pilotage V1.
 *
 * Fenetres favorables probables a J+7. Wording doctrine cote client :
 * "fenetre favorable probable" (pas "prix negatif").
 *
 * Source : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
 */
import { useEffect, useMemo, useState } from 'react';
import { CalendarPlus } from 'lucide-react';
import { getRadarPrixNegatifs } from '../../services/api/pilotage';
import { useActionDrawer } from '../../contexts/ActionDrawerContext';
import { useScope } from '../../contexts/ScopeContext';
import { Skeleton, InfoTip } from '../../ui';

// Formatteurs Intl forces sur Europe/Paris -- independant du fuseau navigateur.
// Les backends renvoient des ISO aware Europe/Paris (ex. 2026-04-22T10:00+02:00),
// mais new Date().getHours() rend l'heure locale du navigateur -- pas la bonne.
const RANGE_FMT = new Intl.DateTimeFormat('fr-FR', {
  timeZone: 'Europe/Paris',
  weekday: 'short',
  day: '2-digit',
  month: '2-digit',
  hour: '2-digit',
  hour12: false,
});

const HOUR_FMT = new Intl.DateTimeFormat('fr-FR', {
  timeZone: 'Europe/Paris',
  hour: '2-digit',
  hour12: false,
});

function formatRange(debut, fin) {
  if (!debut || !fin) return '—';
  try {
    return `${RANGE_FMT.format(new Date(debut))}–${HOUR_FMT.format(new Date(fin))}`;
  } catch {
    return `${debut} → ${fin}`;
  }
}

const USAGE_LABEL = {
  ecs: 'ECS',
  ve_recharge: 'Recharge VE',
  pre_charge_froid: 'Pré-charge froid',
};

export default function RadarPrixNegatifsCard({ horizonDays = 7 }) {
  const { openActionDrawer } = useActionDrawer();
  const { scope } = useScope();

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Radar signal est national (ENTSO-E FR) mais on re-fetch au switch d'org
  // pour invalider tout cache stale au niveau du client. Cf. ScopeContext
  // clearApiCache() qui flush les GET lors du changement de scope.
  const scopeKey = `${scope?.orgId ?? 'none'}:${horizonDays}`;

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    getRadarPrixNegatifs(horizonDays)
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
  }, [scopeKey, horizonDays]);

  const hasSite = Boolean(scope?.siteId);

  const handlePlanifier = (fenetre, idx) => {
    if (!hasSite) return;
    const datetime = fenetre?.datetime_debut;
    const usages = (fenetre?.usages_recommandes || []).map((u) => USAGE_LABEL[u] || u).join(' · ');
    openActionDrawer({
      siteId: scope.siteId,
      sourceType: 'pilotage_radar',
      sourceId: datetime || `radar-${idx}`,
      prefill: {
        titre: `Décaler usages flexibles — ${formatRange(
          fenetre?.datetime_debut,
          fenetre?.datetime_fin
        )}`,
        description:
          `Fenêtre favorable probable détectée (${Math.round((fenetre?.probabilite || 0) * 100)}%).` +
          (usages ? ` Usages conseillés : ${usages}.` : ''),
        date_cible: datetime ? datetime.split('T')[0] : null,
      },
    });
  };

  const topFenetres = useMemo(() => (data?.fenetres_predites || []).slice(0, 4), [data]);

  if (loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-radar-card"
      >
        <Skeleton className="h-5 w-56 mb-3" />
        <Skeleton className="h-20 rounded" />
      </div>
    );
  }

  if (error) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-radar-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">Radar fenêtres favorables</h3>
        <p className="text-xs text-gray-500">Signal temporairement indisponible.</p>
      </div>
    );
  }

  const emptyMsg =
    'Historique insuffisant ou aucune récurrence détectée sur l’horizon demandé. Revenez demain.';
  const ctaTitle = hasSite
    ? 'Créer une action planifiée pour cette fenêtre'
    : 'Sélectionnez un site pour planifier un décalage';

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3"
      data-testid="pilotage-radar-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Radar fenêtres favorables</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Fenêtres favorables probables dans les {data?.horizon_jours ?? horizonDays} jours.
          </p>
        </div>
        <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap">
          Anticipation J+{data?.horizon_jours ?? horizonDays}
        </span>
      </div>

      {topFenetres.length === 0 ? (
        <p className="text-xs text-gray-500">{emptyMsg}</p>
      ) : (
        <ul className="space-y-2">
          {topFenetres.map((f, idx) => (
            <li
              key={`${f.datetime_debut}-${idx}`}
              className="flex items-center justify-between gap-3 text-xs border border-gray-100 rounded-lg px-2.5 py-2"
              data-testid={`pilotage-radar-row-${idx}`}
            >
              <div className="flex-1 min-w-0">
                <div className="font-medium text-gray-900">
                  {formatRange(f.datetime_debut, f.datetime_fin)}
                </div>
                <div className="text-[10px] text-gray-500 mt-0.5">
                  {(f.usages_recommandes || []).map((u) => USAGE_LABEL[u] || u).join(' · ') ||
                    'Décaler les usages flexibles'}
                </div>
              </div>
              <div className="flex items-center gap-3 shrink-0 text-right whitespace-nowrap">
                <div>
                  <div className="text-sm font-semibold text-emerald-700">
                    {Math.round((f.probabilite || 0) * 100)}%
                  </div>
                  <div className="text-[10px] text-gray-400">probable</div>
                </div>
                <button
                  type="button"
                  onClick={() => handlePlanifier(f, idx)}
                  disabled={!hasSite}
                  className="inline-flex items-center gap-1 text-[10px] font-medium text-indigo-700 hover:text-indigo-900 hover:underline disabled:text-gray-400 disabled:cursor-not-allowed disabled:hover:no-underline"
                  title={ctaTitle}
                  data-testid={`pilotage-radar-cta-${idx}`}
                >
                  <CalendarPlus size={12} />
                  Planifier
                </button>
              </div>
            </li>
          ))}
        </ul>
      )}

      <div className="flex items-center justify-between text-[10px] text-gray-400 mt-auto pt-1 border-t border-gray-100">
        <span>
          Source : historique marché 90 j{' '}
          <InfoTip content="Baromètre Flex 2026 RTE/Enedis/GIMELEC" />
        </span>
        <span>confiance {data?.confiance || 'indicative'}</span>
      </div>
    </div>
  );
}
