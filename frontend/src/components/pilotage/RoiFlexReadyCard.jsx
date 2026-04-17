/**
 * RoiFlexReadyCard - Pilotage V1.
 *
 * Gain annuel estime Flex Ready(R) pour le site courant.
 * 3 composantes : evitement pointe + decalage NEBCO + CEE BAT-TH-116.
 *
 * Sources : Barometre Flex 2026 (RTE/Enedis/GIMELEC), fiche CEE BAT-TH-116.
 */
import { useEffect, useState } from 'react';
import { getRoiFlexReady } from '../../services/api/pilotage';
import { Skeleton, InfoTip } from '../../ui';

const DEFAULT_DEMO_SITE = 'retail-001';

function fmtEuro(n) {
  if (n == null) return '—';
  return Number(n).toLocaleString('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  });
}

function ComposanteBar({ label, value, total, color, tooltip }) {
  const pct = total > 0 ? Math.max(2, Math.round((value / total) * 100)) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-gray-700 flex items-center gap-1">
          {label}
          {tooltip ? <InfoTip content={tooltip} /> : null}
        </span>
        <span className="font-medium text-gray-900">{fmtEuro(value)}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RoiFlexReadyCard({ siteId }) {
  const resolvedSiteId = siteId || DEFAULT_DEMO_SITE;

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancel = false;
    setLoading(true);
    setError(null);
    getRoiFlexReady(resolvedSiteId)
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
  }, [resolvedSiteId]);

  if (loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-roi-card"
      >
        <Skeleton className="h-5 w-40 mb-3" />
        <Skeleton className="h-10 w-32 mb-4" />
        <Skeleton className="h-20 rounded" />
      </div>
    );
  }

  if (error || !data) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4"
        data-testid="pilotage-roi-card"
      >
        <h3 className="text-sm font-semibold text-gray-800 mb-2">Gain annuel Flex Ready®</h3>
        <p className="text-xs text-gray-500">
          Site sans données Flex Ready® — sélectionnez un site démo ou terminer le seed.
        </p>
      </div>
    );
  }

  const { gain_annuel_total_eur, composantes = {}, archetype } = data;
  const total = Number(gain_annuel_total_eur || 0);

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3"
      data-testid="pilotage-roi-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Gain annuel Flex Ready®</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Valorisation cumulée — site {resolvedSiteId}
          </p>
        </div>
        <span
          className="inline-flex items-center bg-indigo-50 text-indigo-700 text-[10px] font-medium px-2 py-0.5 rounded-full whitespace-nowrap"
          title="Standard NF EN IEC 62746-4"
        >
          Flex Ready® 62746-4
        </span>
      </div>

      <div>
        <div className="text-3xl font-bold text-gray-900 leading-none">{fmtEuro(total)}</div>
        <div className="text-[11px] text-gray-500 mt-1">
          Archétype : {archetype || 'indéterminé'} · confiance {data.confiance || 'indicative'}
        </div>
      </div>

      <div className="space-y-2.5">
        <ComposanteBar
          label="Évitement pointe"
          value={composantes.evitement_pointe_eur || 0}
          total={total}
          color="bg-amber-500"
          tooltip="kW pilotable × heures pointe évitées × spread €/MWh"
        />
        <ComposanteBar
          label="Décalage NEBCO"
          value={composantes.decalage_nebco_eur || 0}
          total={total}
          color="bg-emerald-500"
          tooltip="kW décalable × ~200 h/an × 60 €/MWh spread"
        />
        <ComposanteBar
          label="CEE BAT-TH-116"
          value={composantes.cee_bacs_eur || 0}
          total={total}
          color="bg-sky-500"
          tooltip="3,5 €/m² × surface — fiche GTB/BACS"
        />
      </div>

      <div className="text-[10px] text-gray-400 mt-auto pt-1 border-t border-gray-100">
        Source : {data.source || 'Baromètre Flex 2026 + fiche CEE'}
      </div>
    </div>
  );
}
