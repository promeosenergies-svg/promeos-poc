/**
 * HeroImpactBar — Barre d'impact financier ventilée (hero zone).
 * Pas de calcul métier : tout vient de l'API /cockpit/executive-v2.
 */
import { ShieldAlert, FileWarning, TrendingUp, CheckCircle2 } from 'lucide-react';
import { fmtEur } from '../../utils/format';

const SEGMENTS = [
  {
    key: 'conformite',
    label: 'Conformité',
    bg: 'bg-red-50',
    text: 'text-red-700',
    border: 'border-red-200',
    icon: ShieldAlert,
  },
  {
    key: 'factures',
    label: 'Factures',
    bg: 'bg-amber-50',
    text: 'text-amber-700',
    border: 'border-amber-200',
    icon: FileWarning,
  },
  {
    key: 'optimisation',
    label: 'Optimisation',
    bg: 'bg-emerald-50',
    text: 'text-emerald-700',
    border: 'border-emerald-200',
    icon: TrendingUp,
  },
];

export default function HeroImpactBar({
  totalEur,
  conformiteEur,
  facturesEur,
  optimisationEur,
  sitesConcernes,
}) {
  // État vide / maîtrisé
  if (!totalEur || totalEur === 0) {
    return (
      <div className="flex items-center gap-3 px-5 py-4 bg-emerald-50 border border-emerald-200 rounded-xl">
        <CheckCircle2 size={20} className="text-emerald-600 shrink-0" />
        <div>
          <p className="text-sm font-semibold text-emerald-800">
            Situation maîtrisée — aucun risque identifié
          </p>
          <p className="text-xs text-emerald-600 mt-0.5">Tous les indicateurs sont au vert</p>
        </div>
      </div>
    );
  }

  const segments = [
    { ...SEGMENTS[0], val: conformiteEur },
    { ...SEGMENTS[1], val: facturesEur },
    { ...SEGMENTS[2], val: optimisationEur },
  ].filter((s) => s.val > 0);

  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5">
      <div className="flex flex-col lg:flex-row lg:items-start gap-5">
        {/* Gauche : total */}
        <div className="shrink-0">
          <p className="text-sm text-gray-500">Impact financier total identifié</p>
          <p className="text-3xl font-bold text-gray-900 mt-1">{fmtEur(totalEur)}</p>
          <p className="text-xs text-gray-400 mt-1">
            {sitesConcernes} site{sitesConcernes > 1 ? 's' : ''} · {segments.length} catégorie
            {segments.length > 1 ? 's' : ''} de risque
          </p>
        </div>

        {/* Droite : barre ventilée + légende */}
        <div className="flex-1 min-w-0">
          {/* Barre proportionnelle */}
          <div className="flex rounded-lg overflow-hidden h-9">
            {segments.map((seg) => {
              const pct = totalEur > 0 ? (seg.val / totalEur) * 100 : 0;
              return (
                <div
                  key={seg.key}
                  className={`${seg.bg} transition-all`}
                  style={{ width: `${pct}%`, minWidth: '8px' }}
                  title={`${seg.label}: ${fmtEur(seg.val)}`}
                />
              );
            })}
          </div>

          {/* Légende sous la barre — toujours lisible */}
          <div className="flex items-center gap-4 mt-2">
            {segments.map((seg) => {
              const Icon = seg.icon;
              return (
                <div key={seg.key} className="flex items-center gap-1.5">
                  <Icon size={12} className={`${seg.text} shrink-0`} />
                  <span className={`text-xs font-medium ${seg.text}`}>{seg.label}</span>
                  <span className={`text-xs font-bold ${seg.text}`}>{fmtEur(seg.val)}</span>
                </div>
              );
            })}
          </div>

          <p className="text-[11px] text-gray-400 mt-1 text-right">
            Pénalités + surcoûts + économies manquées
          </p>
        </div>
      </div>
    </div>
  );
}
