/**
 * Carte compacte "Potentiel NEBCO + BACS↔Flex" pour la colonne droite Usages.
 * Affiche kW pilotable par usage, badge NEBCO, revenu estimé, lien BACS↔Flex ROI.
 */

const fmt = (n) =>
  n == null ? '—' : Number(n).toLocaleString('fr-FR', { maximumFractionDigits: 0 });

const PILOT_COLORS = {
  haute: '#16A34A',
  moyenne: '#D97706',
  faible: '#9CA3AF',
  variable: '#6366F1',
};

const CHECKLIST_LABELS = {
  puissance_100kw: '≥100kW',
  telereleve_enedis: 'Télérelève',
  gtb_installed: 'GTB',
  historique_12m: 'Historique 12m',
  disponibilite_80pct: 'Dispo ≥80%',
  agregateur_contact: 'Agrégateur',
};

export default function FlexNebcoCard({ data }) {
  if (!data || !data.by_usage?.length) return null;

  const { flex_summary: fs, by_usage, bacs_flex_link: bfl, go_nogo_checklist: gnc } = data;
  const eligible = fs?.nebco_eligible;

  return (
    <div className="bg-white border border-gray-200 rounded-xl p-4 overflow-hidden">
      <div className="flex justify-between items-center mb-3">
        <span className="text-[13px] font-semibold">Potentiel flexibilité</span>
        <span
          className={`text-[10px] font-semibold px-2 py-0.5 rounded ${
            eligible ? 'bg-green-50 text-green-700' : 'bg-gray-100 text-gray-500'
          }`}
        >
          {eligible ? 'NEBCO éligible' : `${fmt(fs?.total_pilotable_kw)} kW < 100 kW`}
        </span>
      </div>

      {/* kW par usage */}
      {by_usage
        .filter((u) => u.kw_pilotable > 0)
        .slice(0, 5)
        .map((u) => (
          <div key={u.usage} className="flex items-center gap-2 py-0.5">
            <div className="w-[80px] text-[11px] font-medium truncate">{u.usage}</div>
            <div className="flex-1 h-3 bg-gray-100 rounded overflow-hidden">
              <div
                className="h-full rounded"
                style={{
                  width: `${Math.min(100, (u.kw_pilotable / Math.max(fs?.total_pilotable_kw, 1)) * 100)}%`,
                  background: PILOT_COLORS[u.pilotability] || PILOT_COLORS.faible,
                }}
              />
            </div>
            <div className="min-w-[50px] text-right text-[10px] text-gray-500 font-mono">
              {fmt(u.kw_pilotable)} kW
            </div>
          </div>
        ))}

      {/* Revenu estimé */}
      {fs?.estimated_revenue_eur_year && (
        <div className="mt-2.5 p-2 bg-green-50 rounded text-[11px] text-green-700 font-medium">
          Revenu estimé : {fmt(fs.estimated_revenue_eur_year.nebco_low)} —{' '}
          {fmt(fs.estimated_revenue_eur_year.nebco_high)} €/an
          <span className="text-green-500 font-normal ml-1">
            (+ {fmt(fs.estimated_revenue_eur_year.capacity)} € capacité)
          </span>
        </div>
      )}

      {/* Lien BACS↔Flex — le différenciateur */}
      {bfl?.kw_unlocked_by_bacs > 0 && (
        <div className="mt-2 p-2 bg-amber-50 border border-amber-200 rounded text-[11px]">
          <div className="font-medium text-amber-800">BACS → Flex : ROI {bfl.roi_months} mois</div>
          <div className="text-amber-600 mt-0.5">
            Conformité BACS ({fmt(bfl.bacs_cost_estimate_eur)} €) débloque{' '}
            {fmt(bfl.kw_unlocked_by_bacs)} kW → {fmt(bfl.flex_revenue_unlocked_eur_year)} €/an
          </div>
        </div>
      )}

      {/* Checklist compacte */}
      {gnc && (
        <div className="mt-2 flex flex-wrap gap-x-2 gap-y-0.5 text-[10px] text-gray-400">
          {Object.entries(gnc).map(([k, v]) => (
            <span key={k}>
              {v ? '✅' : '⬜'} {CHECKLIST_LABELS[k] || k}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}
