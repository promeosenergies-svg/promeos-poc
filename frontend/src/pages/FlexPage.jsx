/**
 * FlexPage — Sprint 1.10 (page 10/10 — couverture nav 100%).
 *
 * Pillar §4.6 doctrine PROMEOS Sol : Flex Intelligence — Effacement comme
 * revenu. Audit potentiel flex (CVC / batterie / PV / process) par site,
 * éligibilité NEBCO RTE, Flex Score 4 dimensions, neutralité aggregateur.
 *
 * Différenciation marché vs Voltalis / GreenFlex / Smart Energie :
 *   - PROMEOS ne contractualise pas l'effacement
 *   - Données restent chez le client
 *   - Permet auto-effacement OU choix d'aggregateur informé
 *
 * Cf. ADR-001 grammaire Sol industrialisée.
 */
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Zap, Activity, Settings2 } from 'lucide-react';
import { PageShell, EmptyState, Button } from '../ui';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { scopeKicker } from '../utils/format';
import SolPageHeader from '../ui/sol/SolPageHeader';
import SolNarrative from '../ui/sol/SolNarrative';
import SolWeekCards from '../ui/sol/SolWeekCards';
import SolPageFooter from '../ui/sol/SolPageFooter';
import { usePageBriefing } from '../hooks/usePageBriefing';

export default function FlexPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { org, scopedSites } = useScope();
  const { isExpert } = useExpertMode();

  // Sprint 1.10 — briefing éditorial Sol §5 vue Flex Intelligence (ADR-001).
  // Pillar §4.6 doctrine : Effacement comme revenu — neutralité fournisseur,
  // audit sans engagement aggregateur, données chez le client. Sert Energy
  // Manager (priorisation actifs flex) + Marie DAF (gisement € via revenus
  // NEBCO/AOFD) + Investisseur (preuve §4.6 vs Voltalis/GreenFlex/Smart Energie).
  const {
    briefing: solBriefing,
    error: solBriefingError,
    refetch: solBriefingRefetch,
  } = usePageBriefing('flex', { persona: 'daily' });

  const queryStatus = searchParams.get('status');

  const flexEditorialFallback = (
    <SolPageHeader
      kicker={
        solBriefing?.kicker || scopeKicker('FLEX INTELLIGENCE', org?.nom, scopedSites?.length)
      }
      title={solBriefing?.title || "Votre potentiel d'effacement, sans engagement"}
      italicHook={
        solBriefing?.italicHook || 'neutralité · pas d’aggregateur · vos données chez vous'
      }
      subtitle="Audit Flex sans engagement — comparez aggregateurs ou choisissez l'auto-effacement."
    />
  );

  return (
    <PageShell icon={Zap} title="Flex Intelligence" editorialHeader={flexEditorialFallback}>
      {/* Sprint 1.10 — préambule éditorial Sol §5 vue Flex (ADR-001).
          Pillar §4.6 : Effacement comme revenu — neutralité aggregateur. */}
      {solBriefingError && !solBriefing && (
        <SolNarrative error={solBriefingError} onRetry={solBriefingRefetch} />
      )}
      {solBriefing && (
        <SolNarrative
          kicker={null /* déjà rendu dans SolPageHeader éditorialHeader */}
          title={null /* idem — éviter doublon */}
          narrative={solBriefing.narrative}
          kpis={solBriefing.kpis}
        />
      )}
      {solBriefing && (
        <SolWeekCards
          cards={solBriefing.weekCards}
          fallbackBody={solBriefing.fallbackBody}
          tone={solBriefing.narrativeTone}
          onNavigate={navigate}
        />
      )}

      {/* Phase 1 page minimale : audit + inventaire flex en cours d'industrialisation
          (cf. project_flex_usage_sprint.md + project_flexibilite_strategie_produit.md).
          Roadmap S2+ : carpet plot puissance pilotable, simulateur revenus NEBCO,
          comparateur aggregateurs, signal RTE temps réel. */}
      <EmptyState
        icon={Activity}
        title="Audit Flex en construction"
        text={
          <>
            La cartographie complète des actifs pilotables (CVC, froid, batterie, photovoltaïque,
            process) et le simulateur de revenus marché capacité sont en cours de construction.{' '}
            {queryStatus === 'actionable' && (
              <strong>Filtrer sur les actifs déjà identifiés comme pilotables.</strong>
            )}
            {queryStatus === 'not_assessed' && (
              <strong>Filtrer sur les sites non encore évalués.</strong>
            )}
            {!queryStatus && (
              <>
                Le briefing éditorial ci-dessus reflète l'état de votre patrimoine selon les données
                déjà collectées par les autres modules.
              </>
            )}
          </>
        }
        ctaLabel="Voir les anomalies actives"
        onCta={() => navigate('/anomalies?status=open')}
      />

      {isExpert && (
        <div
          className="rounded-lg p-4 text-sm border"
          style={{
            background: 'var(--sol-bg-panel)',
            borderColor: 'var(--sol-line)',
            color: 'var(--sol-ink-700)',
          }}
        >
          <div className="flex items-start gap-3">
            <Settings2
              size={16}
              className="mt-0.5 shrink-0"
              style={{ color: 'var(--sol-ink-500)' }}
            />
            <div>
              <span className="font-semibold">Roadmap technique S2+ :</span> carpet plot puissance
              pilotable 24×7, simulateur revenus NEBCO/AOFD avec courbes tarifaires RTE, comparateur
              aggregateurs (Voltalis / GreenFlex / Smart Energie / Veolia / EDF Effacement). Signal
              Tempo + EcoWatt en temps réel. Toutes données restent chez le client — neutralité
              contractuelle PROMEOS.
            </div>
          </div>
        </div>
      )}

      {/* Sprint 1.10 — SolPageFooter §5 (ADR-001).
          Methodology /methodologie/flex-effacement. */}
      {solBriefing?.provenance && (
        <SolPageFooter
          source={solBriefing.provenance.source}
          confidence={solBriefing.provenance.confidence}
          updatedAt={solBriefing.provenance.updated_at}
          methodologyUrl={solBriefing.provenance.methodology_url}
        />
      )}
    </PageShell>
  );
}
