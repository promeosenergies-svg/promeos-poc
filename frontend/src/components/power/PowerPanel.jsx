/**
 * PowerPanel — Orchestre les 6 endpoints /api/power/sites/{siteId}/.
 * RÈGLE ABSOLUE : zéro calcul métier. 100% display-only.
 */

import { useState, useEffect } from 'react';
import {
  getPowerProfile,
  getPowerPeaks,
  getPowerFactor,
  getPowerOptimizePs,
} from '../../services/api';

const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });
const fmt1 = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 1 });

export default function PowerPanel({ siteId }) {
  const [profile, setProfile] = useState(null);
  const [peaks, setPeaks] = useState(null);
  const [factor, setFactor] = useState(null);
  const [optimizer, setOptimizer] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!siteId) return;
    setLoading(true);
    Promise.all([
      getPowerProfile(siteId).catch(() => null),
      getPowerPeaks(siteId).catch(() => null),
      getPowerFactor(siteId).catch(() => null),
      getPowerOptimizePs(siteId).catch(() => null),
    ]).then(([prof, pk, fac, opt]) => {
      setProfile(prof);
      setPeaks(pk);
      setFactor(fac);
      setOptimizer(opt);
      setLoading(false);
    });
  }, [siteId]);

  if (loading) {
    return (
      <div className="text-sm text-gray-400 py-6 text-center">Chargement analyse puissance...</div>
    );
  }

  if (!profile?.data_available) {
    return (
      <div className="text-sm text-gray-400 py-6 text-center">Données puissance indisponibles.</div>
    );
  }

  const kpis = profile.kpis || {};
  const contract = profile.contract;

  return (
    <div className="space-y-4">
      {/* KPI Strip */}
      <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
        <KpiCard label="P. Max" value={`${fmt1(kpis.P_max_kw)} kW`} />
        <KpiCard label="P. Baseload" value={`${fmt1(kpis.P_base_kw)} kW`} sub="Percentile 5%" />
        <KpiCard
          label="Utilisation PS"
          value={`${fmt1(kpis.taux_utilisation_ps_pct)}%`}
          alert={kpis.taux_utilisation_ps_pct > 85}
        />
        <KpiCard
          label="tan φ"
          value={factor?.data_available ? fmt1(factor.kpis?.tan_phi_moyen) : '—'}
          alert={factor?.kpis?.au_dessus_seuil}
          sub={factor?.data_available ? `seuil 0.4` : 'Non dispo.'}
        />
        <KpiCard
          label="Coût dépassements"
          value={`${fmt(peaks?.cout_total_estime_eur)} €`}
          alert={(peaks?.cout_total_estime_eur || 0) > 500}
          sub={`${peaks?.n_pics || 0} pics`}
        />
      </div>

      {/* PS par poste */}
      {contract?.ps_par_poste_kva && (
        <div className="bg-white border border-gray-200 rounded-xl p-4">
          <div className="text-[13px] font-semibold mb-2">Puissance Souscrite par Poste</div>
          <div className="text-[10px] text-gray-400 mb-2">
            {contract.fta_code} · {contract.type_compteur}
          </div>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-2">
            {Object.entries(contract.ps_par_poste_kva).map(([poste, kva]) => (
              <div key={poste} className="bg-gray-50 rounded-lg p-2 text-center">
                <div className="text-[10px] text-gray-500 uppercase">{poste}</div>
                <div className="text-sm font-semibold font-mono">{kva} kVA</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Pics détectés */}
      {peaks && peaks.n_pics > 0 && (
        <div className="bg-white border border-red-200 rounded-xl p-4">
          <div className="text-[13px] font-semibold text-red-700 mb-2">
            {peaks.n_pics} pics détectés · Coût estimé {fmt(peaks.cout_total_estime_eur)} €
          </div>
          {peaks.cmdps_par_poste?.map((c) => (
            <div
              key={c.poste}
              className="flex justify-between text-xs py-1 border-b border-gray-50"
            >
              <span className="font-medium">{c.poste}</span>
              <span className="font-mono">
                DQ : {c.dq_kw} kW · {c.duree_depassement_h}h
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Optimiseur PS */}
      {optimizer?.data_available && optimizer.economie_totale_annuelle_eur > 0 && (
        <div className="bg-white border border-green-200 rounded-xl p-4">
          <div className="text-[13px] font-semibold text-green-700 mb-2">
            Optimisation PS · Économie estimée {fmt(optimizer.economie_totale_annuelle_eur)} €/an
          </div>
          {optimizer.eir_requis_global && (
            <div className="text-xs text-amber-600 mb-2">EIR requise (SGE F170)</div>
          )}
          {optimizer.recommandations_par_poste
            ?.filter((r) => r.action !== 'OPTIMAL' && r.action !== 'OK')
            .map((r) => (
              <div
                key={r.poste}
                className="flex justify-between text-xs py-1 border-b border-gray-50"
              >
                <span>
                  {r.poste} : {r.ps_actuelle_kva} → {r.ps_recommandee_kva} kVA
                </span>
                <span className="font-mono text-green-600">
                  -{fmt(r.economie_annuelle_eur)} €/an
                </span>
              </div>
            ))}
        </div>
      )}

      {/* Facteur de puissance */}
      {factor?.data_available && (
        <div
          className={`bg-white border rounded-xl p-4 ${factor.kpis?.au_dessus_seuil ? 'border-amber-200' : 'border-gray-200'}`}
        >
          <div className="text-[13px] font-semibold mb-1">
            Facteur de puissance · tan φ = {fmt1(factor.kpis?.tan_phi_moyen)}
          </div>
          <div className="text-xs text-gray-500">
            Seuil réglementaire : 0.4 · Pénalité estimée : {fmt(factor.kpis?.penalite_estimee_eur)}{' '}
            €
          </div>
          {factor.recommandation && (
            <div
              className={`text-xs mt-1 ${factor.recommandation.code === 'OK' ? 'text-green-600' : 'text-amber-600'}`}
            >
              {factor.recommandation.message}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

function KpiCard({ label, value, sub, alert }) {
  return (
    <div
      className={`rounded-xl border p-3 ${alert ? 'border-red-200 bg-red-50/50' : 'border-gray-200 bg-white'}`}
    >
      <div className="text-[10px] text-gray-500 uppercase tracking-wider">{label}</div>
      <div className="text-sm font-semibold font-mono mt-0.5">{value}</div>
      {sub && <div className="text-[10px] text-gray-400 mt-0.5">{sub}</div>}
    </div>
  );
}
