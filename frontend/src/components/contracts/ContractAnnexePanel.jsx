/**
 * PROMEOS — Slide Panel detail Annexe
 * Banner heritage, donnees site, grille tarifaire (source cadre|override), volume.
 */
import { useState, useEffect } from 'react';
import { X, ArrowLeft, Edit2 } from 'lucide-react';
import { Button } from '../../ui';
import { getAnnexe } from '../../services/api';

const STATUS_CFG = {
  active: { cls: 'bg-emerald-50 text-emerald-700', dot: 'bg-emerald-500', label: 'Actif' },
  expiring: { cls: 'bg-amber-50 text-amber-700', dot: 'bg-amber-500', label: 'Expire bientot' },
  expired: { cls: 'bg-red-50 text-red-700', dot: 'bg-red-500', label: 'Expire' },
};

export default function ContractAnnexePanel({ cadreId, annexeId, onClose, onOpenCadre }) {
  const [annexe, setAnnexe] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!annexeId || !cadreId) return;
    setLoading(true);
    getAnnexe(cadreId, annexeId)
      .then(setAnnexe)
      .finally(() => setLoading(false));
  }, [cadreId, annexeId]);

  if (!annexeId) return null;

  const st = STATUS_CFG[annexe?.status] || STATUS_CFG.active;

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
              <span className="px-2 py-0.5 rounded bg-blue-50 text-blue-700 font-bold text-[10px]">
                Annexe
              </span>
              <span>{annexe?.annexe_ref}</span>
              <span>·</span>
              <button
                onClick={() => {
                  onClose();
                  onOpenCadre?.();
                }}
                className="text-blue-600 font-semibold hover:underline"
              >
                {annexe?.cadre_ref}
              </button>
            </div>
            <h2 className="text-lg font-extrabold">
              {annexe?.site_name || '...'} — {annexe?.cadre_supplier}
            </h2>
            <div className="flex gap-2 mt-1.5">
              <span
                className={`inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-[10px] font-bold ${st.cls}`}
              >
                <span className={`w-1.5 h-1.5 rounded-full ${st.dot}`} />
                {st.label}
              </span>
              <span className="text-xs font-semibold">⚡ Electricite</span>
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
        ) : annexe ? (
          <div className="p-5 space-y-5">
            {/* Heritage banner */}
            {!annexe.has_price_override && (
              <div className="bg-teal-50 border border-teal-200 rounded-lg p-3 text-xs text-teal-800 leading-relaxed">
                <b>ℹ️ Heritage cadre :</b> fournisseur, dates, modele prix, grille tarifaire. Champs
                marques{' '}
                <span className="bg-teal-100 px-1 py-0.5 rounded text-[9px] font-bold">cadre</span>{' '}
                geres au niveau contrat cadre.
              </div>
            )}

            {/* Donnees site */}
            <Section title="Donnees specifiques site">
              <div className="grid grid-cols-2 gap-2">
                <Info label="Site" value={annexe.site_name} />
                <Info
                  label="PRM"
                  value={annexe.delivery_point_id ? `PDL #${annexe.delivery_point_id}` : '—'}
                />
                <Info
                  label="PS"
                  value={annexe.subscribed_power_kva ? `${annexe.subscribed_power_kva} kVA` : '—'}
                />
                <Info label="Option" value={annexe.tariff_option?.toUpperCase() || '—'} />
                <Info label="Segment" value={annexe.segment_enedis || '—'} />
              </div>
            </Section>

            {/* Pricing grid */}
            {annexe.resolved_pricing?.length > 0 && (
              <Section title="Grille tarifaire effective">
                {!annexe.has_price_override && (
                  <div className="text-xs text-teal-700 font-semibold mb-1.5">
                    ↓ Prix herites du cadre
                  </div>
                )}
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
                        Source
                      </th>
                    </tr>
                  </thead>
                  <tbody>
                    {annexe.resolved_pricing.map((p, i) => (
                      <tr key={i}>
                        <td className="p-2 border border-gray-100">{p.period_code}</td>
                        <td className="p-2 border border-gray-100">{p.season}</td>
                        <td className="p-2 border border-gray-100 text-right font-bold tabular-nums">
                          {p.unit_price_eur_kwh?.toFixed(4) || '—'}
                        </td>
                        <td
                          className={`p-2 border border-gray-100 text-right text-[10px] font-semibold ${p.source === 'cadre' ? 'text-teal-600' : 'text-amber-600'}`}
                        >
                          {p.source}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </Section>
            )}

            {/* Volume commitment */}
            {annexe.volume_commitment && (
              <Section title="Engagement volume">
                <div className="grid grid-cols-2 gap-2">
                  <Info
                    label="Volume"
                    value={`${Math.round(annexe.volume_commitment.annual_kwh / 1000)} MWh/an`}
                  />
                  <Info
                    label="Tolerance"
                    value={`±${annexe.volume_commitment.tolerance_pct_up}%`}
                  />
                  <Info
                    label="Penalite depassement"
                    value={
                      annexe.volume_commitment.penalty_eur_kwh_above
                        ? `${annexe.volume_commitment.penalty_eur_kwh_above} €/kWh`
                        : '—'
                    }
                  />
                  <Info
                    label="Penalite sous-conso"
                    value={
                      annexe.volume_commitment.penalty_eur_kwh_below
                        ? `${annexe.volume_commitment.penalty_eur_kwh_below} €/kWh`
                        : '—'
                    }
                  />
                </div>
              </Section>
            )}

            {/* CTAs */}
            <div className="flex gap-2 flex-wrap">
              <Button size="sm" variant="primary">
                📊 Shadow billing
              </Button>
              <Button size="sm">
                <Edit2 size={12} className="mr-1" />
                Modifier
              </Button>
              <Button
                size="sm"
                onClick={() => {
                  onClose();
                  onOpenCadre?.();
                }}
              >
                <ArrowLeft size={12} className="mr-1" />
                Cadre
              </Button>
            </div>
          </div>
        ) : (
          <div className="p-6 text-center text-gray-400">Annexe non trouvee</div>
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

function Info({ label, value }) {
  return (
    <div>
      <div className="text-[10px] text-gray-400">{label}</div>
      <div className="text-sm font-semibold">{value || '—'}</div>
    </div>
  );
}
