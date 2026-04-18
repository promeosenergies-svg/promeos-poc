/**
 * PROMEOS — Cockpit Refonte V2 raw (Sprint 2 refonte).
 *
 * Page reconstruite avec les 8 composants Sol (ui/sol/). Structure
 * exacte maquette V2 raw :
 * docs/sol/maquettes/cockpit-sol-v1-adjusted-v2.html
 *
 * Données : fixtures représentatives (shapes réelles PROMEOS). Le
 * wiring sur les hooks existants (getNotificationsSummary,
 * getComplianceScoreTrend, etc.) se fera dans un sprint de Phase 3+
 * une fois que le design de la rupture sera validé par l'équipe.
 *
 * Helpers interpretCost/interpretCompliance/interpretConsumption/
 * buildCockpitNarrative vivent dans `pages/cockpit/sol_interpreters.js`
 * (fonctions pures présentation, zéro logique métier).
 */
import { useState } from 'react';
import {
  SolHero,
  SolKpiCard,
  SolLoadCurve,
  SolPageHeader,
  SolSectionHead,
  SolSourceChip,
  SolWeekCard,
} from '../ui/sol';
import {
  buildCockpitNarrative,
  buildCockpitSubNarrative,
  buildWeekCards,
  interpretCompliance,
  interpretConsumption,
  interpretCost,
} from './cockpit/sol_interpreters';

// ─────────────────────────────────────────────────────────────────────────────
// Fixtures — shapes représentatives de ce que les hooks PROMEOS renverront.
// À remplacer par useScope + getNotificationsSummary etc. quand visuel
// validé.
// ─────────────────────────────────────────────────────────────────────────────

const FIXTURE = {
  scope: { orgName: 'Patrimoine HELIOS', sitesCount: 5, weekNum: 16 },
  kpis: {
    totalCost: 47_382,
    costDelta: 0.082,
    fournisseurCount: 3,
    topDriverSites: [{ name: 'Lyon' }, { name: 'Nice' }],
    totalConso: 1_847,
    consoDelta: -0.041,
    topBaisseSites: [{ name: 'Paris' }, { name: 'Toulouse' }],
  },
  compliance: {
    score: 62,
    delta: -3,
    deltaDir: 'down',
    freshnessHours: 23,
    sitesAtRisk: 3,
    leadRiskSite: { name: 'Marseille école' },
  },
  alerts: [
    {
      id: 'marseille-derive',
      severity: 'attention',
      title: 'Marseille école dérive',
      summary: (
        <>
          Consommation en hausse de <strong>+12 %</strong> sur 90 jours glissants — probablement la
          CTA défectueuse signalée en février. Je peux générer le plan d'action.
        </>
      ),
      impact: 'chiffré : +4 200 € / an si non-traité',
      automatable: false,
    },
    {
      id: 'operat-lyon',
      severity: 'à_faire',
      title: 'OPERAT Lyon · 30 sept',
      summary: (
        <>
          Déclaration annuelle à déposer dans <strong>5 mois</strong>. Je peux préparer le fichier
          CSV v3.2 à partir de vos données — il vous restera à le déposer.
        </>
      ),
      impact: 'préparation : 4 h → 3 min',
      automatable: true,
    },
    {
      id: 'paris-bacs',
      severity: 'bonne_nouvelle',
      title: 'Paris bureaux · BACS validé',
      summary: (
        <>
          L'obligation BACS sur Paris est <strong>conforme</strong> depuis le rapport d'homologation
          reçu hier. Votre score de conformité gagne <strong>+4 points</strong>.
        </>
      ),
      impact: 'conforme · pièce au dossier',
      automatable: false,
    },
  ],
  solProposal: {
    title_fr: "Contester la facture Lyon de mars auprès d'EDF Entreprises",
    summary_fr:
      "Vous avez été facturé l'accise T1 sur toute la période, alors que vous êtes basculé en T2 depuis le 15 février. Je peux rédiger le courrier et l'envoyer — vous relisez avant, vous gardez la main pendant 24 h.",
    estimated_value_eur: 1847.2,
    confidence: 0.94,
    estimated_time_to_validate_min: 3,
  },
  loadCurve: null, // SolLoadCurve a son propre fallback DEFAULT_DATA
};

// ─────────────────────────────────────────────────────────────────────────────
// Formatters FR (ré-utilise utilitaires format.js si dispo, sinon pure fn)
// ─────────────────────────────────────────────────────────────────────────────

const NBSP = '\u00A0';
const NNBSP = '\u202F';

function fmtEurValue(n) {
  return new Intl.NumberFormat('fr-FR').format(Math.round(n)).replace(/\s/g, NBSP);
}
function fmtMwhValue(n) {
  return new Intl.NumberFormat('fr-FR').format(Math.round(n)).replace(/\s/g, NBSP);
}
function fmtEurFull(n) {
  return (
    new Intl.NumberFormat('fr-FR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
      .format(n)
      .replace(/\s/g, NBSP) + `${NNBSP}€`
  );
}
function fmtPctDelta(delta, suffix) {
  const sign = delta > 0 ? '+' : '';
  const val = `${sign}${(delta * 100).toFixed(1).replace('.', ',')}${NNBSP}%`;
  const arrow = delta > 0 ? '▲' : '▼';
  return `${arrow} ${val} ${suffix}`;
}

// ─────────────────────────────────────────────────────────────────────────────
// Page
// ─────────────────────────────────────────────────────────────────────────────

export default function CockpitRefonte() {
  const [solDismissed, setSolDismissed] = useState(false);
  const {
    scope,
    kpis,
    compliance,
    alerts,
    solProposal,
  } = FIXTURE;

  const weekCards = buildWeekCards(alerts);

  return (
    <div style={{ padding: '32px 48px 60px' }}>
      {/* Page header éditorial */}
      <SolPageHeader
        kicker={`Cockpit · semaine ${scope.weekNum} · ${scope.orgName.toLowerCase()}`}
        title="Bonjour"
        titleEm=" — voici votre semaine"
        narrative={buildCockpitNarrative({
          alertsCount: alerts.length,
          topAlertTitle: 'la facture de mars sur Lyon',
        })}
        subNarrative={buildCockpitSubNarrative({
          sitesCount: scope.sitesCount,
          nextComexDays: 11,
        })}
      />

      {/* Sol hero : action agentique proposée */}
      {solProposal && !solDismissed && (
        <SolHero
          chip="Sol propose · action agentique"
          title={solProposal.title_fr}
          description={solProposal.summary_fr}
          metrics={[
            solProposal.estimated_value_eur
              ? {
                  value: fmtEurFull(solProposal.estimated_value_eur),
                  label: 'à récupérer',
                }
              : null,
            {
              value: `${Math.round(solProposal.confidence * 100)}${NNBSP}%`,
              label: 'confiance du calcul',
            },
            solProposal.estimated_time_to_validate_min
              ? {
                  value: `${solProposal.estimated_time_to_validate_min}${NNBSP}min`,
                  label: 'pour valider',
                }
              : null,
          ].filter(Boolean)}
          onPrimary={() => window.open('/cockpit/sol', '_self')}
          onSecondary={() => setSolDismissed(true)}
        />
      )}

      {/* Row 3 KPIs signature */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 20,
          marginBottom: 28,
        }}
      >
        <SolKpiCard
          label="Facture énergie · mars"
          value={fmtEurValue(kpis.totalCost)}
          unit="€ HT"
          delta={{
            direction: kpis.costDelta > 0 ? 'up' : 'down',
            text: fmtPctDelta(kpis.costDelta, 'vs février'),
          }}
          headline={interpretCost(kpis, scope)}
          source={{ kind: 'Factures', origin: `${kpis.fournisseurCount} fournisseurs` }}
        />
        <SolKpiCard
          label="Conformité Décret tertiaire"
          value={`${compliance.score}`}
          unit="/100"
          delta={{
            direction: compliance.deltaDir,
            text: `▼ −${Math.abs(compliance.delta)} pts sur 3 mois`,
          }}
          headline={interpretCompliance(compliance)}
          source={{ kind: 'Enedis', freshness: `mis à jour il y a ${compliance.freshnessHours}${NBSP}h` }}
        />
        <SolKpiCard
          label="Consommation · patrimoine"
          value={fmtMwhValue(kpis.totalConso)}
          unit="MWh"
          delta={{
            direction: kpis.consoDelta > 0 ? 'up' : 'down',
            text: fmtPctDelta(kpis.consoDelta, 'vs n−1'),
          }}
          headline={interpretConsumption(kpis, scope)}
          source={{ kind: 'Enedis + GRDF' }}
        />
      </div>

      {/* Cette semaine chez vous — 3 week-cards */}
      <SolSectionHead
        title="Cette semaine chez vous"
        meta={`${weekCards.length} points · actualisé il y a 47 min`}
      />
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(3, 1fr)',
          gap: 16,
          marginBottom: 32,
        }}
      >
        {weekCards.map((card) => (
          <SolWeekCard
            key={card.id}
            tagKind={card.tagKind}
            tagLabel={card.tagLabel}
            title={card.title}
            body={card.body}
            footerLeft={card.footerLeft}
            footerRight={card.footerRight}
            onClick={card.onClick}
          />
        ))}
      </div>

      {/* Courbe de charge — signature HP/HC */}
      <SolSectionHead title="Courbe de charge — Lyon, hier" meta="pas 30 min · HP / HC tarifaires" />
      <SolLoadCurve
        peakPoint={{ time: '14:00', value: 118, label: `pic 14${NNBSP}h · 118${NBSP}kW` }}
        caption={
          <>
            <strong style={{ color: 'var(--sol-ink-900)' }}>85{NNBSP}% de votre consommation</strong>{' '}
            tombe en heures pleines — attendu pour un bureau. Votre contrat est bien calibré.
          </>
        }
        sourceChip={<SolSourceChip kind="Enedis" origin="M023" freshness="complète" />}
      />
    </div>
  );
}
