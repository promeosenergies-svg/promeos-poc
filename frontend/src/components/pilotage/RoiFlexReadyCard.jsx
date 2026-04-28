/**
 * RoiFlexReadyCard - Pilotage V1.
 *
 * Gain annuel estime Flex Ready(R) pour le site courant.
 * 3 composantes : evitement pointe + effacement remunere + CEE BAT-TH-116.
 *
 * Sources : Barometre Flex 2026 (RTE/Enedis/GIMELEC), fiche CEE BAT-TH-116.
 */
import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { ArrowRight } from 'lucide-react';
import { getRoiFlexReady } from '../../services/api/pilotage';
import { useScope } from '../../contexts/ScopeContext';
import { toSite } from '../../services/routes';
import { fmtEur } from '../../utils/format';
import { Skeleton, InfoTip } from '../../ui';
import { humaniseArchetype, humaniseSiteId } from './archetypeLabels';

// Phase 0.7 (sprint Cockpit dual sol2) : fallback `'retail-001'` retiré.
// Si pas de siteId résolu (scope HELIOS sans site sélectionné), on rend
// un empty state au lieu de leak Hypermarché Montreuil.

function ComposanteBar({ label, value, total, color, tooltip }) {
  const pct = total > 0 ? Math.max(2, Math.round((value / total) * 100)) : 0;
  return (
    <div className="space-y-1">
      <div className="flex items-center justify-between text-[11px]">
        <span className="text-gray-700 flex items-center gap-1">
          {label}
          {tooltip ? <InfoTip content={tooltip} /> : null}
        </span>
        <span className="font-medium text-gray-900">{fmtEur(value)}</span>
      </div>
      <div className="h-1.5 bg-gray-100 rounded-full overflow-hidden">
        <div className={`h-full ${color} rounded-full`} style={{ width: `${pct}%` }} />
      </div>
    </div>
  );
}

export default function RoiFlexReadyCard({ siteId: siteIdProp }) {
  const navigate = useNavigate();
  const { scope, scopedSites } = useScope();

  // Phase 0.7bis (audit P1 #1) : suppression du fallback `scopedSites[0]?.id`
  // qui est de la business logic frontend (anti-pattern §8.1).
  // Le siteId vient explicitement du prop ou du scope user. Si aucun des
  // deux : empty state propre invitant à sélectionner un site. Le scope
  // switcher du shell UI est responsable du choix du site par défaut.
  const resolvedSiteId = String(siteIdProp || scope?.siteId || '');

  const siteNom = useMemo(() => {
    if (!resolvedSiteId) return null;
    const found = scopedSites?.find((s) => String(s.id) === resolvedSiteId);
    return found?.nom || null;
  }, [scopedSites, resolvedSiteId]);

  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!resolvedSiteId) {
      setLoading(false);
      return;
    }
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

  // Empty state propre quand aucun site dans le scope HELIOS courant
  if (!resolvedSiteId && !loading) {
    return (
      <div
        className="bg-white border border-gray-200 rounded-xl p-4 text-sm text-gray-500"
        data-testid="pilotage-roi-card-empty"
      >
        Sélectionnez un site du portefeuille pour estimer le ROI Flex Ready®.
      </div>
    );
  }

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
          Site pas encore qualifié Flex Ready® — contactez votre CSM pour activer le diagnostic.
        </p>
      </div>
    );
  }

  const { gain_annuel_total_eur, composantes = {}, archetype } = data;
  const total = Number(gain_annuel_total_eur || 0);
  const ctaLabel = scope?.siteId ? 'Voir la fiche site' : 'Explorer un site démo';
  const ctaTarget = scope?.siteId ? toSite(scope.siteId) : '/sites';

  return (
    <div
      className="bg-white border border-gray-200 rounded-xl p-4 flex flex-col gap-3"
      data-testid="pilotage-roi-card"
    >
      <div className="flex items-start justify-between gap-2">
        <div>
          <h3 className="text-sm font-semibold text-gray-800">Gain annuel Flex Ready®</h3>
          <p className="text-[11px] text-gray-500 mt-0.5">
            Valorisation cumulée — {siteNom || humaniseSiteId(resolvedSiteId)}
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
        <div className="text-3xl font-bold text-gray-900 leading-none">{fmtEur(total)}</div>
        <div className="text-[11px] text-gray-500 mt-1">
          Archétype : {humaniseArchetype(archetype)} · confiance {data.confiance || 'indicative'}
        </div>
      </div>

      <div className="space-y-2.5">
        <ComposanteBar
          label="Évitement pointe"
          value={composantes.evitement_pointe_eur || 0}
          total={total}
          color="bg-amber-500"
          tooltip="kW pilotable × heures pointe évitées × écart prix pointe vs creux"
        />
        <ComposanteBar
          label="Effacement rémunéré"
          value={composantes.decalage_nebco_eur || 0}
          total={total}
          color="bg-emerald-500"
          tooltip="Décalage volontaire de consommation vers les fenêtres favorables (~200 h/an × 60 €/MWh)"
        />
        <ComposanteBar
          label="CEE BAT-TH-116"
          value={composantes.cee_bacs_eur || 0}
          total={total}
          color="bg-sky-500"
          tooltip="3,5 €/m² × surface — fiche CEE pilotage bâtiment"
        />
      </div>

      <button
        type="button"
        onClick={() => navigate(ctaTarget)}
        className="mt-1 inline-flex items-center justify-between gap-1 text-xs font-medium text-indigo-700 hover:text-indigo-900 hover:underline"
        data-testid="pilotage-roi-cta"
      >
        <span>{ctaLabel}</span>
        <ArrowRight size={12} />
      </button>

      <div className="text-[10px] text-gray-400 mt-auto pt-1 border-t border-gray-100">
        Source : {data.source || 'Baromètre Flex 2026 + fiche CEE'}
      </div>
    </div>
  );
}
