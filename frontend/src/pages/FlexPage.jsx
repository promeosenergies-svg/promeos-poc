/**
 * FlexPage — Sprint 1.10 (page 10/10 — couverture nav 100%).
 *
 * Pillar §4.6 doctrine PROMEOS Sol : Flex Intelligence — Effacement comme
 * revenu. Audit potentiel flex (chauffage/clim / batterie / PV / process)
 * par site, éligibilité NEBCO RTE, Flex Score 4 dimensions, neutralité
 * agrégateur.
 *
 * Différenciation marché : PROMEOS ne contractualise pas l'effacement —
 * vos données restent chez vous, vous gardez 100 % du revenu en mode
 * auto-effacement OU choisissez un partenaire agrégateur informé.
 *
 * Cf. ADR-001 grammaire Sol industrialisée.
 */
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Zap, ShieldCheck, Settings2 } from 'lucide-react';
import { PageShell, EmptyState } from '../ui';
import SolAcronym from '../ui/sol/SolAcronym';
import { useScope } from '../contexts/ScopeContext';
import { useExpertMode } from '../contexts/ExpertModeContext';
import { scopeKicker } from '../utils/format';
import SolPageHeader from '../ui/sol/SolPageHeader';
// Sprint 2 Vague B ét8'-bis — HOC SolBriefingHead/Footer factorise grammaire §5.
import SolBriefingHead from '../ui/sol/SolBriefingHead';
import SolBriefingFooter from '../ui/sol/SolBriefingFooter';
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
      title={solBriefing?.title || 'Votre potentiel d’effacement, sans engagement'}
      italicHook={
        solBriefing?.italicHook || 'neutralité · pas d’agrégateur · vos données chez vous'
      }
    />
  );

  return (
    <PageShell icon={Zap} title="Flex Intelligence" editorialHeader={flexEditorialFallback}>
      {/* Sprint 1.10 — préambule éditorial Sol §5 vue Flex (ADR-001).
          Pillar §4.6 : Effacement comme revenu — neutralité aggregateur. */}
      {/* Sprint 2 Vague B ét8'-bis — factorisation grammaire §5 via SolBriefingHead. */}
      <SolBriefingHead
        briefing={solBriefing}
        error={solBriefingError}
        onRetry={solBriefingRefetch}
        omitHeader
        onNavigate={navigate}
      />

      {/* Sprint 1.10bis Investisseur P0 + Frontend-design P4 : panneau
          Neutralité promu top-level (vs caché derrière isExpert). C'est LE
          message wedge §4.6 face à Voltalis/GreenFlex/Smart Energie/Veolia/
          EDF Effacement — doit être visible 10s pour démo investisseur.
          Concurrents → formulation générique pour éviter risque marketing
          dans le DOM (Quality P1). */}
      <section
        role="region"
        aria-labelledby="flex-neutralite-heading"
        className="rounded-lg p-6 border"
        style={{
          background: 'var(--sol-calme-bg)',
          borderColor: 'var(--sol-calme-fg)',
        }}
      >
        <div className="flex items-start gap-3">
          <ShieldCheck
            size={20}
            className="mt-0.5 shrink-0"
            style={{ color: 'var(--sol-calme-fg)' }}
            aria-hidden="true"
          />
          <div>
            <h3
              id="flex-neutralite-heading"
              className="font-semibold text-base"
              style={{ color: 'var(--sol-calme-fg-hover)' }}
            >
              Neutralité agrégateur — moat structurel PROMEOS Sol
            </h3>
            <p className="text-sm mt-1.5 leading-relaxed" style={{ color: 'var(--sol-ink-700)' }}>
              Les autres acteurs du marché B2B contractualisent l’agrégation : ils prennent une
              commission sur chaque effacement, vos données partent chez eux. PROMEOS Sol fait
              l’inverse — vos données restent chez vous, aucune commission, vous choisissez
              librement entre auto-effacement (100&nbsp;% du revenu marché capacité) et un
              partenaire agrégateur, comparé objectivement. Si la régulation ouvre l’effacement à
              tous post-décret 2026, vous y êtes déjà ; si l’oligopole persiste, PROMEOS reste
              l’outil de comparaison neutre.
            </p>
          </div>
        </div>
      </section>

      {/* Phase 1 page minimale — audit + inventaire flex en construction
          progressive (cf. project_flexibilite_strategie_produit.md).
          Roadmap S2+ : carpet plot puissance pilotable 24×7, simulateur
          revenus NEBCO/AOFD, comparateur agrégateurs partenaires. */}
      <EmptyState
        icon={ShieldCheck}
        title="Audit Flex — phase 1 disponible"
        text={
          <>
            Le briefing ci-dessus reflète votre potentiel d’effacement à partir des données déjà
            collectées par PROMEOS Sol (patrimoine, actifs pilotables, scores Flex). La cartographie
            24×7 détaillée et le simulateur de revenus marché capacité (
            <SolAcronym code="NEBCO" />, <SolAcronym code="AOFD" />) arrivent en Sprint&nbsp;2.{' '}
            {queryStatus === 'actionable' && (
              <em>Vue filtrée : actifs déjà identifiés comme pilotables.</em>
            )}
            {queryStatus === 'not_assessed' && <em>Vue filtrée : sites non encore évalués.</em>}
          </>
        }
        ctaLabel="Comprendre la méthodologie"
        onCta={() =>
          navigate(solBriefing?.provenance?.methodology_url || '/methodologie/flex-effacement')
        }
      />

      {isExpert && (
        <div
          className="rounded-lg p-6 text-sm border"
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
              aria-hidden="true"
            />
            <div>
              <span className="font-semibold">Roadmap technique Sprint&nbsp;2+ :</span> carpet plot
              puissance pilotable 24×7, simulateur revenus <SolAcronym code="NEBCO" />/
              <SolAcronym code="AOFD" /> avec courbes tarifaires RTE, comparateur multi-agrégateurs
              partenaires (≥&nbsp;4 acteurs certifiés), signal <SolAcronym code="Tempo" /> +{' '}
              <SolAcronym code="EcoWatt" /> en temps réel.
            </div>
          </div>
        </div>
      )}

      {/* Sprint 2 Vague B ét8'-bis — SolPageFooter §5 factorisé via HOC. */}
      <SolBriefingFooter briefing={solBriefing} />
    </PageShell>
  );
}
