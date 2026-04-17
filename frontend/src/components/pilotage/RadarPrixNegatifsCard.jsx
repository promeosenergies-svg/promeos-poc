/**
 * RadarPrixNegatifsCard - Pilotage V1.
 *
 * Fenetres favorables probables a J+7. Wording doctrine cote client :
 * "fenetre favorable probable" (pas "prix negatif").
 *
 * Source : Barometre Flex 2026 (RTE/Enedis/GIMELEC, avril 2026).
 */
import { useEffect, useState } from 'react';
import { getRadarPrixNegatifs } from '../../services/api/pilotage';
import { Skeleton, InfoTip } from '../../ui';

const WEEKDAY = ['dim', 'lun', 'mar', 'mer', 'jeu', 'ven', 'sam'];

function formatDateTime(iso) {
  if (!iso) return '—';
  try {
    const d = new Date(iso);
    return `${WEEKDAY[d.getDay()]} ${String(d.getDate()).padStart(2, '0')}/${String(
      d.getMonth() + 1
    ).padStart(2, '0')} · ${String(d.getHours()).padStart(2, '0')}h`;
  } catch {
    return iso;
  }
}

function formatRange(debut, fin) {
  if (!debut || !fin) return '—';
  try {
    const a = new Date(debut);
    const b = new Date(fin);
    return `${WEEKDAY[a.getDay()]} ${String(a.getDate()).padStart(2, '0')}/${String(
      a.getMonth() + 1
    ).padStart(2, '0')} · ${String(a.getHours()).padStart(2, '0')}h–${String(b.getHours()).padStart(
      2,
      '0'
    )}h`;
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
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
  }, [horizonDays]);

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

  const fenetres = data?.fenetres_predites || [];
  const emptyMsg =
    'Historique insuffisant ou aucune récurrence détectée sur l’horizon demandé. Revenez demain.';

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3"
      data-testid="pilotage-radar-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Radar fenêtres favorables</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Probabilité de créneaux à prix effondrés dans les {data?.horizon_jours ?? horizonDays}{' '}
            jours.
          </p>
        </div>
        <span className="inline-flex items-center gap-1 bg-emerald-50 text-emerald-700 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap">
          Anticipation J+{data?.horizon_jours ?? horizonDays}
        </span>
      </div>

      {fenetres.length === 0 ? (
        <p className="text-xs text-gray-500">{emptyMsg}</p>
      ) : (
        <ul className="space-y-2">
          {fenetres.slice(0, 4).map((f, idx) => (
            <li
              key={`${f.datetime_debut}-${idx}`}
              className="flex items-center justify-between gap-3 text-xs border border-gray-100 rounded-lg px-2.5 py-2"
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
              <div className="text-right whitespace-nowrap">
                <div className="text-sm font-semibold text-emerald-700">
                  {Math.round((f.probabilite || 0) * 100)}%
                </div>
                <div className="text-[10px] text-gray-400">probable</div>
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
        <span className="uppercase tracking-wide">{data?.confiance || 'indicative'}</span>
      </div>
    </div>
  );
}
