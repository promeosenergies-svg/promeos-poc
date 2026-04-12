/**
 * PROMEOS — Flex (module stratégique)
 * Route: /flex
 * Vue portefeuille flexibilité : scoring, quick wins, potentiel NEBEF/FCR/Tempo.
 */
import { PageShell } from '../ui';
import { Zap, TrendingUp, Target } from 'lucide-react';
import FlexPortfolioSummary from '../components/flex/FlexPortfolioSummary';
import FlexPotentialCard from '../components/flex/FlexPotentialCard';
import FlexScoreCard from '../components/flex/FlexScoreCard';
import TariffWindowsCard from '../components/flex/TariffWindowsCard';
import FlexNebcoCard from '../components/usages/FlexNebcoCard';
import ScopeSummary from '../components/ScopeSummary';

export default function FlexPage() {
  return (
    <PageShell icon={Zap} title="Flexibilité énergétique" subtitle={<ScopeSummary />}>
      <div className="space-y-5 max-w-7xl">
        {/* Intro éditoriale */}
        <div className="bg-gradient-to-r from-yellow-50 to-amber-50 border border-amber-100 rounded-xl p-4">
          <div className="flex items-start gap-3">
            <div className="p-2 bg-amber-100 rounded-lg">
              <TrendingUp size={18} className="text-amber-700" />
            </div>
            <div>
              <h3 className="text-sm font-semibold text-gray-900 mb-1">
                Transformez vos contraintes tarifaires en revenus
              </h3>
              <p className="text-xs text-gray-600 leading-relaxed">
                PROMEOS identifie automatiquement les gisements de flexibilité sur votre
                portefeuille : effacement NEBEF, participation capacité, arbitrage HP/HC dynamique,
                Tempo Bleu/Blanc/Rouge. Chaque site est scoré sur son potentiel économique annuel.
              </p>
            </div>
          </div>
        </div>

        {/* Portfolio summary */}
        <FlexPortfolioSummary />

        {/* Cards row */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <FlexScoreCard />
          <FlexPotentialCard />
        </div>

        {/* Tariff windows + NEBCO */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <TariffWindowsCard />
          <FlexNebcoCard />
        </div>

        {/* Call to action */}
        <div className="bg-gray-50 border border-gray-200 rounded-xl p-5 flex items-center gap-4">
          <Target size={24} className="text-violet-600 shrink-0" />
          <div className="flex-1">
            <h4 className="text-sm font-semibold text-gray-900">
              Prêt à valoriser vos effacements ?
            </h4>
            <p className="text-xs text-gray-600">
              PROMEOS vous met en relation avec les agrégateurs NEBEF partenaires (commission
              marketplace).
            </p>
          </div>
        </div>
      </div>
    </PageShell>
  );
}
