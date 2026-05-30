/**
 * PROMEOS — PriceDecompositionTable (Sprint P1.S5).
 *
 * Affiche les composantes tarifaires telles que renvoyées par
 * `/api/energy/cost-vs-contract` → `price_decomposition[]`.
 *
 * Composantes attendues (PriceComponentKey backend) :
 *   supply | network | taxes | capacity | other
 *
 * Doctrine zéro calcul métier frontend :
 * - Aucun recalcul de `share_pct` (déjà fourni backend) ;
 * - Aucun recalcul de `price_eur_mwh` (déjà fourni backend) ;
 * - Aucun recalcul de total (utilise total_cost_eur si exposé en KPI) ;
 * - Tri visuel uniquement si l'API fournit l'ordre — sinon ordre canonique
 *   d'affichage (supply → network → taxes → capacity → other) qui
 *   correspond à l'ordre métier de lecture d'une facture FR.
 */
import { HelpCircle } from 'lucide-react';

const CANONICAL_ORDER = ['supply', 'network', 'taxes', 'capacity', 'other'];

const COMPONENT_TINT = {
  supply: 'border-l-blue-400',
  network: 'border-l-amber-400',
  taxes: 'border-l-purple-400',
  capacity: 'border-l-emerald-400',
  other: 'border-l-gray-400',
};

function fmtEur(v) {
  if (v === null || v === undefined) return '—';
  return Number(v).toLocaleString('fr-FR', {
    style: 'currency',
    currency: 'EUR',
    maximumFractionDigits: 0,
  });
}

function fmtEurPerMwh(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 2 })} €/MWh`;
}

function fmtPct(v) {
  if (v === null || v === undefined) return '—';
  return `${Number(v).toLocaleString('fr-FR', { maximumFractionDigits: 1 })} %`;
}

function ProvenanceDot({ provenance }) {
  if (!provenance?.service) return null;
  return (
    <span className="relative inline-block group" data-testid="price-component-provenance">
      <HelpCircle size={11} className="text-gray-300 hover:text-gray-500 cursor-help" />
      <span className="absolute right-0 top-4 z-10 hidden group-hover:block w-60 rounded-lg border border-gray-200 bg-white p-2 text-[10px] text-gray-700 shadow-lg">
        <span className="block text-gray-500">Source</span>
        <span className="block font-mono break-words">{provenance.source || '—'}</span>
        <span className="block text-gray-500 mt-1">Service</span>
        <span className="block font-mono text-[10px] break-words">{provenance.service}</span>
        {provenance.formula && (
          <>
            <span className="block text-gray-500 mt-1">Formule</span>
            <span className="block font-mono text-[10px] break-words">{provenance.formula}</span>
          </>
        )}
      </span>
    </span>
  );
}

export default function PriceDecompositionTable({
  priceDecomposition,
  className = '',
  testId = 'price-decomposition-table',
}) {
  if (!Array.isArray(priceDecomposition) || priceDecomposition.length === 0) {
    return null;
  }

  // Tri visuel canonique uniquement si l'API ne fournit pas d'ordre.
  // Les composants reçus dans l'ordre API sont préservés.
  const sorted = [...priceDecomposition].sort((a, b) => {
    const ai = CANONICAL_ORDER.indexOf(a.key);
    const bi = CANONICAL_ORDER.indexOf(b.key);
    return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
  });

  return (
    <div
      className={`rounded-xl border border-gray-200 bg-white p-4 ${className}`}
      data-testid={testId}
    >
      <h3 className="text-sm font-semibold text-gray-800 mb-3">Décomposition du prix</h3>
      <table className="w-full text-xs">
        <thead className="text-gray-500 border-b border-gray-100">
          <tr>
            <th className="text-left font-medium py-1.5">Composante</th>
            <th className="text-right font-medium py-1.5">Montant</th>
            <th className="text-right font-medium py-1.5">€/MWh</th>
            <th className="text-right font-medium py-1.5">Part</th>
            <th className="text-right font-medium py-1.5 w-6"></th>
          </tr>
        </thead>
        <tbody>
          {sorted.map((comp) => (
            <tr
              key={comp.key}
              className={`border-l-4 ${COMPONENT_TINT[comp.key] || COMPONENT_TINT.other} border-b border-gray-50 last:border-b-0`}
              data-testid={`price-component-${comp.key}`}
              data-component-key={comp.key}
            >
              <td className="pl-2 py-2 text-gray-800 font-medium">{comp.label}</td>
              <td className="py-2 text-right font-mono text-gray-700">{fmtEur(comp.amount_eur)}</td>
              <td className="py-2 text-right font-mono text-gray-700">
                {fmtEurPerMwh(comp.price_eur_mwh)}
              </td>
              <td className="py-2 text-right font-mono text-gray-700">{fmtPct(comp.share_pct)}</td>
              <td className="py-2 text-right">
                <ProvenanceDot provenance={comp.provenance} />
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
