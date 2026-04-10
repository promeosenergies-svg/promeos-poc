/**
 * PROMEOS — Slide Panel detail Cadre
 * 6 sections: Shadow billing, Alertes, Info cadre, Grille tarifaire, Annexes, Events.
 */
import { useState, useEffect } from 'react';
import { X, AlertTriangle, ChevronRight, Plus, _RefreshCw, Edit2, _Trash2 } from 'lucide-react';
import { _Badge, Button } from '../../ui';
import { getCadre, _getCoherence } from '../../services/api';

const STATUS_CFG = {
  active: { cls: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500', label: 'Actif' },
  expiring: { cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500', label: 'Expire bientot' },
  expired: { cls: 'bg-red-50 text-red-700', dot: 'bg-red-500', label: 'Expire' },
  draft: { cls: 'bg-gray-50 text-gray-500', dot: 'bg-gray-400', label: 'Brouillon' },
};

export default function ContractCadrePanel({ cadreId, onClose, onOpenAnnexe }) {
  const [cadre, setCadre] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!cadreId) return;
    setLoading(true);
    getCadre(cadreId)
      .then(setCadre)
      .finally(() => setLoading(false));
  }, [cadreId]);

  if (!cadreId) return null;

  const st = STATUS_CFG[cadre?.status] || STATUS_CFG.active;

  return (
    <div
      className="fixed inset-0 z-50 flex"
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <div className="absolute inset-0 bg-black/30 backdrop-blur-[2px]" />
      <div className="ml-auto relative w-[700px] max-w-[94vw] h-full bg-white overflow-y-auto shadow-xl animate-slide-in">
        {/* Header */}
        <div className="sticky top-0 z-10 bg-white border-b px-5 py-4 flex justify-between items-start">
          <div>
            <div className="flex items-center gap-2 text-xs text-gray-400 mb-1">
              <span className="px-2 py-0.5 rounded bg-purple-50 text-purple-700 font-bold text-[10px]">
                Cadre
              </span>
              <span>{cadre?.contract_ref}</span>
            </div>
            <h2 className="text-lg font-extrabold">{cadre?.supplier_name || '...'}</h2>
            <div className="flex gap-2 mt-1.5 flex-wrap">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${st.cls}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                {st.label}
                {cadre?.days_to_expiry != null &&
                  cadre.days_to_expiry <= 90 &&
                  ` ${cadre.days_to_expiry}j`}
              </span>
              <span className="text-xs font-semibold">
                {cadre?.energy_type === 'elec' ? '⚡ Electricite' : '🔵 Gaz'}
              </span>
              {cadre?.pricing_model && (
                <span className="px-2 py-0.5 rounded bg-amber-50 text-amber-800 text-[10px] font-bold">
                  {cadre.pricing_model}
                </span>
              )}
            </div>
          </div>
          <button
            onClick={onClose}
            className="w-7 h-7 rounded border flex items-center justify-center text-gray-400 hover:text-gray-700"
          >
            <X size={14} />
          </button>
        </div>

        {loading ? (
          <div className="p-6 text-center text-gray-400">Chargement...</div>
        ) : cadre ? (
          <div className="p-5 space-y-5">
            {/* Shadow billing card */}
            {cadre.budget_eur > 0 && (
              <div className="bg-purple-50 border border-purple-200 rounded-lg p-3.5">
                <h4 className="text-xs font-bold text-purple-700 mb-1">
                  ⚡ Shadow billing — Ecart global
                </h4>
                <div className="text-lg font-extrabold text-purple-700">
                  {cadre.total_shadow_gap_eur != null
                    ? `${cadre.total_shadow_gap_eur >= 0 ? '+' : ''}${cadre.total_shadow_gap_eur.toLocaleString('fr-FR')} € HT`
                    : '—'}
                </div>
              </div>
            )}

            {/* Coherence alerts */}
            {cadre.coherence?.length > 0 && (
              <div className="space-y-1.5">
                {cadre.coherence.map((r, i) => (
                  <div
                    key={i}
                    className={`flex items-start gap-2 p-2.5 rounded-lg text-xs ${r.level === 'error' ? 'bg-red-50 border border-red-200' : 'bg-amber-50 border border-amber-200'}`}
                  >
                    <AlertTriangle
                      size={14}
                      className={r.level === 'error' ? 'text-red-500' : 'text-amber-500'}
                    />
                    <div>
                      <b>{r.rule_id}</b> — {r.message}
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Info cadre */}
            <Section title="Informations cadre (partagees)">
              <InfoGrid
                items={[
                  { label: 'Fournisseur', value: cadre.supplier_name },
                  { label: 'Reference', value: cadre.contract_ref },
                  {
                    label: 'Type',
                    value: cadre.contract_type === 'CADRE' ? 'Contrat cadre' : 'Contrat unique',
                  },
                  { label: 'Debut', value: fmtDate(cadre.start_date) },
                  { label: 'Fin', value: fmtDate(cadre.end_date) },
                  { label: 'Reconduction', value: cadre.tacit_renewal ? 'Oui' : 'Non' },
                  {
                    label: 'Preavis',
                    value: cadre.notice_period_months ? `${cadre.notice_period_months} mois` : '—',
                  },
                  {
                    label: 'Offre verte',
                    value: cadre.is_green ? `Oui (${cadre.green_percentage || 100}%)` : 'Non',
                  },
                ]}
              />
            </Section>

            {/* Pricing grid */}
            {cadre.pricing?.length > 0 && (
              <Section title="Grille tarifaire cadre (fourniture HT)">
                <table className="w-full text-xs border-collapse">
                  <thead>
                    <tr className="bg-gray-50">
                      <th className="text-left p-2 font-bold text-gray-400 uppercase text-[9px] tracking-wider border border-gray-100">
                        Periode
                      </th>
                      <th className="text-left p-2 font-bold text-gray-400 uppercase text-[9px] tracking-wider border border-gray-100">
                        Saison
                      </th>
                      <th className="text-right p-2 font-bold text-gray-400 uppercase text-[9px] tracking-wider border border-gray-100">
                        €/kWh
                      </th>
                      <th className="text-right p-2 font-bold text-gray-400 uppercase text-[9px] tracking-wider border border-gray-100">
                        Abo €/mois
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {cadre.pricing.map((p, i) => (
                      <tr key={i}>
                        <td className="p-2 border border-gray-100">{p.period_code}</td>
                        <td className="p-2 border border-gray-100">{p.season}</td>
                        <td className="p-2 border border-gray-100 text-right font-bold tabular-nums">
                          {p.unit_price_eur_kwh?.toFixed(4) || '—'}
                        </td>
                        <td className="p-2 border border-gray-100 text-right font-bold tabular-nums">
                          {p.subscription_eur_month?.toFixed(2) || '—'}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="mt-1 text-[10px] text-gray-400">
                  Herite par toutes annexes sauf override
                </div>
              </Section>
            )}

            {/* Annexes list */}
            <Section title={`Annexes (${cadre.annexes?.length || 0})`}>
              {cadre.annexes?.map((a) => {
                const ast = STATUS_CFG[a.status] || STATUS_CFG.active;
                return (
                  <div
                    key={a.id}
                    className="flex items-center gap-3 p-3 border border-gray-100 rounded-lg mb-1.5 cursor-pointer hover:border-blue-400 hover:bg-blue-50/30 transition"
                    onClick={() => onOpenAnnexe?.(a.id)}
                  >
                    <div className="flex-1">
                      <div className="font-bold text-sm">{a.site_name}</div>
                      <div className="text-[11px] text-gray-400">
                        {a.subscribed_power_kva && `${a.subscribed_power_kva} kVA · `}
                        {a.tariff_option && `${a.tariff_option.toUpperCase()} · `}
                        {a.volume_mwh && `${a.volume_mwh} MWh`}
                      </div>
                    </div>
                    <span
                      className={`px-2 py-0.5 rounded text-[10px] font-bold ${a.has_price_override ? 'bg-blue-100 text-blue-700' : 'bg-gray-100 text-gray-400 italic'}`}
                    >
                      {a.has_price_override ? 'override' : 'herite'}
                    </span>
                    <span
                      className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${ast.cls}`}
                    >
                      <span className={`w-1.5 h-1.5 rounded-full ${ast.dot}`} />
                      {ast.label}
                    </span>
                    <ChevronRight size={14} className="text-gray-300" />
                  </div>
                );
              })}
              <button className="mt-1.5 text-xs font-semibold text-blue-600 flex items-center gap-1 hover:underline">
                <Plus size={12} /> Ajouter annexe
              </button>
            </Section>

            {/* Events timeline */}
            {cadre.events?.length > 0 && (
              <Section title="Evenements">
                <div className="relative pl-5">
                  <div className="absolute left-1.5 top-1 bottom-1 w-0.5 bg-gray-200" />
                  {cadre.events.map((e, i) => (
                    <div key={i} className="relative mb-3">
                      <div className="absolute -left-[15.5px] top-1.5 w-2 h-2 rounded-full border-2 border-blue-500 bg-white" />
                      <div className="text-[10px] text-gray-400">{fmtDate(e.event_date)}</div>
                      <div className="text-xs font-semibold">
                        {e.event_type} — {e.description}
                      </div>
                    </div>
                  ))}
                </div>
              </Section>
            )}

            {/* CTAs */}
            <div className="flex gap-2 flex-wrap">
              <Button size="sm" variant="primary">
                🔄 Renouvellement
              </Button>
              <Button size="sm">📊 Shadow billing</Button>
              <Button size="sm">
                <Edit2 size={12} className="mr-1" />
                Modifier
              </Button>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-gray-400">Cadre non trouve</div>
        )}
      </div>
    </div>
  );
}

function Section({ title, children }) {
  return (
    <div>
      <h3 className="text-[11px] font-bold text-gray-400 uppercase tracking-wider mb-2.5 pb-1.5 border-b border-gray-100">
        {title}
      </h3>
      {children}
    </div>
  );
}

function InfoGrid({ items }) {
  return (
    <div className="grid grid-cols-2 gap-2">
      {items.map(({ label, value }) => (
        <div key={label}>
          <div className="text-[10px] text-gray-400">{label}</div>
          <div className="text-sm font-semibold">{value || '—'}</div>
        </div>
      ))}
    </div>
  );
}

function fmtDate(d) {
  if (!d) return '—';
  try {
    return new Date(d).toLocaleDateString('fr-FR', {
      day: '2-digit',
      month: '2-digit',
      year: 'numeric',
    });
  } catch {
    return d;
  }
}
