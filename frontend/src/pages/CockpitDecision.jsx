/**
 * CockpitDecision — Page Synthèse stratégique refonte WOW (29/04/2026, Étape 2).
 *
 * Audience : DG / CFO / dirigeant non-sachant · 3 minutes
 * Doctrine §11.3 : page de décision, source unique partagée avec Pilotage.
 *
 * Cible : `docs/maquettes/cockpit-sol2/cockpit-synthese-strategique.html`
 *
 * Sections (top → bottom) :
 *   1. Header — kicker + switch + H1 Fraunces "Synthèse stratégique · semaine N · pour CODIR"
 *   2. Pills EPEX + bouton Rapport COMEX
 *   3. Narrative stratégique 4 lignes denses + push hebdo "+X vs S-1"
 *   4. Triptyque KPI hybride avec badges Calculé/Modélisé + drill_down_href
 *   5. 3 décisions à arbitrer cette semaine (cards narrées)
 *   6. Trajectoire 2030 lissée (SVG)
 *   7. Facture prévisionnelle 5 sites + composantes inactives collapsées
 *   8. Teaser Flex Intelligence
 *   9. Footer Sol
 *
 * Sources data :
 *   - useCockpitFacts('current_year') → triptyque + narrative + push hebdo
 *   - getCockpitDecisionsTop3() → 3 décisions narrées
 *   - getCockpitTrajectory() → réel + objectif + projection + jalons
 *   - getPurchasePortfolioCostSimulation(orgId) → facture composantes
 */
import { memo, useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';
import { ArrowRight, FileText, Sparkles } from 'lucide-react';

import useCockpitFacts from '../hooks/useCockpitFacts';
import SolKickerWithSwitch from '../ui/sol/SolKickerWithSwitch';
import AcronymTooltip from '../ui/sol/AcronymTooltip';
import KpiCard from '../components/cockpit/KpiCard';
import KpiSkeleton from '../components/cockpit/KpiSkeleton';
import {
  getCockpitDecisionsTop3,
  getCockpitTrajectory,
  getPurchasePortfolioCostSimulation,
} from '../services/api/cockpit';
import { useScope } from '../contexts/ScopeContext';
import { splitMwh, fmtEurShort } from '../utils/format';
import { getIsoWeek, relativeTime, daysUntil } from '../utils/date';
import { severityTone } from '../ui/sol/solTones';

// ── Triptyque KPI hybride avec badges ────────────────────────────
// Étape 11 : KpiCard + KpiSkeleton factorisés dans `components/cockpit/`.
// `KpiHybrideCard` local supprimé → utilise `<KpiCard variant="confidence" .../>`.
// KpiSkeleton local supprimé → utilise `<KpiSkeleton variant="confidence" />`.

function KpiTriptyqueHybride({ facts }) {
  const compliance = facts?.compliance || {};
  const exposure = facts?.exposure?.total || {};
  const potential = facts?.potential_recoverable || {};

  const expSplit = (() => {
    const v = exposure.value_eur;
    if (v == null) return { value: '—', unit: '' };
    return {
      value:
        v >= 1000 ? (v / 1000).toLocaleString('fr-FR', { maximumFractionDigits: 1 }) : v.toString(),
      unit: v >= 1000 ? 'k€' : '€',
    };
  })();

  const potSplit = splitMwh(potential.value_mwh_year);

  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
      {/* Phase 14.B (audit véracité Sophie) : le label "Trajectoire 2030"
          était trompeur — il mappait sur compliance.score (score conformité
          DT/BACS/APER pondéré RegOps), pas sur consumption.trajectory_2030_score
          (avancement -40 % MWh DT, exposé séparément dans la SVG ci-dessous).
          Renommé "Score conformité" cohérent avec la donnée réelle. La
          trajectoire MWh DT reste visible via TrajectoryDTSmoothed plus bas. */}
      <KpiCard
        variant="confidence"
        label="Score conformité"
        tooltip="Score pondéré RegOps : Décret Tertiaire (DT) + Décret BACS + loi APER. Note /100 — 100 = entièrement conforme. Pour la trajectoire MWh DT cf. graphique ci-dessous."
        value={compliance.score != null ? compliance.score : '—'}
        unit={compliance.score != null ? `/${compliance.max || 100}` : ''}
        badge="calculated_regulatory"
        source="RegOps · DT + BACS + APER pondéré"
        drillHref="/conformite?scope=org&filter=non_conform"
        drillLabel={`Voir ${compliance.non_conform_sites || 0} sites NC`}
      />
      {/* Phase 21.B.2 (audit Phase 17 P0 KPI orphelin) — tooltip décomposition
          des composantes pénalités. Le backend expose `exposure.components`
          avec [{label, count, unit_value_eur, value_eur, regulatory_article}]
          (cf cockpit_facts_service::_build_exposure). On affiche désormais
          le détail "3× DT à risque (3 750 €) + 1× BACS NC (1 500 €) = 12,8 k€"
          au survol/focus du KPI — plus besoin de cliquer "Voir détail".
          Chaque CFO/DAF non-sachant peut auditer le calcul en 1 hover. */}
      <KpiCard
        variant="confidence"
        label="Exposition pénalités"
        tooltip={
          (facts?.exposure?.components || []).length > 0
            ? (() => {
                const comps = facts.exposure.components;
                const lines = comps
                  .map(
                    (c) =>
                      `${c.count}× ${c.label} (${(c.unit_value_eur || 0).toLocaleString('fr-FR')} €/an) = ${(c.value_eur || 0).toLocaleString('fr-FR')} € · ${c.regulatory_article || ''}`
                  )
                  .join(' | ');
                const total = (exposure.value_eur || 0).toLocaleString('fr-FR');
                return `Décomposition : ${lines} → Total ${total} €/an. Chaque pénalité est calculée loi à la main (article réglementaire affiché par composante).`;
              })()
            : 'Risque pénalités calculé loi à la main : Décret Tertiaire (7 500 €/site NC, 3 750 €/site à risque) + BACS (1 500 €/site NC) + OPERAT (1 500 €/déclaration manquante). Source doctrine PROMEOS canonique.'
        }
        value={expSplit.value}
        unit={expSplit.unit}
        badge={exposure.category || 'calculated_regulatory'}
        source={exposure.regulatory_article || 'Décret 2019-771 art. 9'}
        drillHref="/conformite?scope=org&view=exposure_components"
        drillLabel="Voir détail composantes"
      />
      <KpiCard
        variant="confidence"
        label="Potentiel récupérable"
        value={potSplit.value !== '—' ? potSplit.value : '—'}
        unit={potSplit.unit ? `${potSplit.unit}/an` : ''}
        badge={potential.method || 'modeled_cee'}
        source={
          potential.references?.length
            ? `${potential.references[0]}${potential.leverage_count ? ` · ${potential.leverage_count} leviers` : ''}`
            : 'CEE'
        }
        drillHref="/anomalies?status=open&sort=mwh_desc"
        drillLabel={`Voir ${potential.leverage_count || 0} actions`}
      />
    </div>
  );
}

// ── Narrative stratégique avec push hebdo ─────────────────────────

function StrategicNarrative({ facts }) {
  if (!facts) return null;
  const c = facts.compliance || {};
  const exp = facts.exposure?.total || {};
  const expDelta = facts.exposure?.delta_vs_last_week;
  const pot = facts.potential_recoverable || {};
  const consDrift = facts.consumption?.sites_in_drift ?? 0;
  const sitesCount = facts.scope?.site_count ?? 0;
  const ncSites = c.non_conform_sites ?? 0;
  const atRiskSites = c.at_risk_sites ?? 0;

  // Phase 14.E (audit véracité Sophie/Marie) : la narrative disait "tous les
  // sites alignés" si consumption.sites_in_drift = 0, ignorant le statut
  // conformité réglementaire (NC + à risque) — contradiction frontale avec
  // le KPI exposition 12,8 k€ et le score 37/100.
  // Phase 16.F : si sitesOff = sitesCount (tous les sites en écart), on
  // reformule pour éviter la phrase redondante "patrimoine de 5 sites
  // présente 5 sites en écart" qui dégrade la crédibilité (audit Phase 15
  // /code-reviewer P2). On dit "l'ensemble du patrimoine est en écart" pour
  // signaler la sévérité avec une formule moins mécanique.
  // Phase 16.bis.A (régression audit /simplify Phase 16) : `driftText` ne
  // contient plus "de la trajectoire" — la JSX ci-dessous l'ajoute en suffixe
  // (" de la trajectoire 2030"). Avant : la branche "ensemble" + suffix
  // produisait "...l'ensemble du patrimoine en écart de la trajectoire de la
  // trajectoire 2030" (double phrase visible démo).
  const sitesOff = Math.max(consDrift, ncSites + atRiskSites);
  let driftText;
  if (sitesOff <= 0) {
    driftText = 'tous les sites alignés';
  } else if (sitesCount > 0 && sitesOff >= sitesCount) {
    driftText = "l'ensemble du patrimoine en écart";
  } else {
    driftText = `${sitesOff} site${sitesOff > 1 ? 's' : ''} en écart`;
  }
  const expText = exp.value_eur != null ? fmtEurShort(exp.value_eur) : '—';
  const expDeltaText =
    expDelta?.value_eur != null && expDelta.value_eur !== 0
      ? `, en hausse de ${fmtEurShort(Math.abs(expDelta.value_eur))} vs semaine précédente`
      : '';
  const potText = pot.value_mwh_year != null ? `${potSplitInline(pot.value_mwh_year)}` : '—';

  return (
    <p
      className="my-5"
      style={{
        fontSize: 15,
        lineHeight: 1.65,
        color: 'var(--sol-ink-700)',
        maxWidth: '64ch',
      }}
    >
      Votre patrimoine de {sitesCount} site{sitesCount > 1 ? 's' : ''} présente{' '}
      <strong style={{ color: 'var(--sol-ink-900)', fontWeight: 500 }}>{driftText}</strong> de la
      trajectoire 2030 (<AcronymTooltip acronym="DT">Décret Tertiaire</AcronymTooltip> n°2019-771,
      jalons −40 % / 2030, −50 % / 2040, −60 % / 2050). Score conformité{' '}
      <strong style={{ color: 'var(--sol-ink-900)', fontWeight: 500 }}>
        {c.score != null ? `${c.score}/${c.max || 100}` : '—'}
      </strong>
      . Exposition aux pénalités réglementaires{' '}
      <strong style={{ color: 'var(--sol-ink-900)', fontWeight: 500 }}>{expText}</strong> calculée
      loi à la main{expDeltaText}. Trois décisions à arbitrer cette semaine pour mobiliser{' '}
      <strong style={{ color: 'var(--sol-ink-900)', fontWeight: 500 }}>{potText}</strong> de
      potentiel énergétique récupérable.
    </p>
  );
}

function potSplitInline(v) {
  const s = splitMwh(v);
  return `${s.value} ${s.unit}/an`;
}

// ── 3 décisions à arbitrer ────────────────────────────────────────
// Tons sévérité hissés en SoT (Étape 2.bis) → severityTone() depuis solTones.js

// Phase 15.B (audit Phase 14 P1-A : règle d'or zero business logic in
// frontend) : NarrativeFallback retiré. Le backend cockpit_decisions_service
// pré-remplit `decision.narrative` avec un template SoT
// (_DECISION_NARRATIVE_FALLBACK_BY_LEVER) — un seul mapping levier→texte,
// plus de duplication FE/BE possible.

// Phase 13.E — DecisionCard wrappé `memo` : la liste cycle sur 3 cards
// quand le parent re-render (fetch facts/portfolio/trajectory). Sans memo,
// chaque DecisionCard re-render à chaque parent render même si `decision`
// inchangé — coût visible sur le tooltip provenance hover.
function DecisionCardImpl({ decision, index }) {
  const tone = severityTone(decision.severity);
  const days = daysUntil(decision.echeance);
  const echeanceText = days != null ? `J−${days}` : '—';
  const gainMwh = decision.estimated_gain_mwh_year;
  const penaltyEur = decision.regulatory_penalty_eur?.value_eur;
  const penaltyArticle = decision.regulatory_penalty_eur?.regulatory_article;
  // Étape 4.bis FE : consume les nouveaux champs backend cockpit_decisions_service.
  // Audit Marie + Jean-Marc : "manque CapEx + Économie €/an + Payback + ROI/CO₂".
  const capexEur = decision.investment_capex_eur;
  const savingsEurYear = decision.estimated_savings_eur_year;
  const paybackMonths = decision.payback_months;
  const paybackMonthsNet = decision.payback_months_net_penalty;
  const penaltyAvoidedEurYear = decision.penalty_avoided_eur_year;
  const co2AvoidedT = decision.co2_avoided_t_year;
  const estimationMethod = decision.estimation_method;
  // Étape 9 P0-D : consume backend `category_label` (SoT _classify_lever)
  // au lieu de business logic textuelle FE (audit /simplify règle d'or).
  // Fallback minimal pour rétro-compat si backend ne fournit pas le champ.
  const tagLabel = decision.category_label || 'Investissement';

  return (
    <div
      className="rounded-md mb-2"
      style={{
        background: tone.bg,
        border: `0.5px solid ${tone.line}`,
        padding: '14px 16px',
        display: 'grid',
        gridTemplateColumns: '42px 1fr',
        gap: 14,
      }}
    >
      <div
        className="rounded"
        style={{
          background: 'var(--sol-bg-paper)',
          width: 36,
          height: 36,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          fontFamily: 'var(--sol-font-display)',
          fontSize: 15,
          fontWeight: 500,
          color: tone.fg,
          alignSelf: 'start',
        }}
      >
        {index + 1}
      </div>
      <div className="min-w-0">
        <div className="flex gap-2 items-center flex-wrap mb-1">
          <span
            className="inline-flex items-center px-2 py-0.5 rounded-full font-mono uppercase tracking-[0.06em]"
            style={{
              fontSize: 11,
              background: tone.chipBg,
              color: tone.fg,
              fontWeight: 500,
            }}
          >
            {tagLabel}
          </span>
          <span
            className="font-mono uppercase tracking-[0.07em]"
            style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
          >
            {decision.site}
          </span>
        </div>
        <div
          style={{
            fontFamily: 'var(--sol-font-display)',
            fontSize: 18,
            fontWeight: 500,
            lineHeight: 1.3,
            color: 'var(--sol-ink-900)',
            marginBottom: 5,
          }}
        >
          {decision.title}
        </div>
        {/* Phase 15.B : `decision.narrative` est désormais TOUJOURS pré-rempli
            par le backend `cockpit_decisions_service.serialize_action_for_decision`
            avec un fallback SoT par lever_key si action.rationale absent.
            Le frontend rend simplement la chaîne — plus de duplication. */}
        {decision.narrative && (
          <div
            style={{
              fontSize: 13.5,
              lineHeight: 1.6,
              color: 'var(--sol-ink-700)',
              marginBottom: 10,
            }}
          >
            {decision.narrative}
          </div>
        )}
        {/* Cards CFO grade : 1ère ligne = signal métier (Volume/Économies/Réf/Échéance).
            2ᵉ ligne = arbitrage financier (CapEx/Payback/CO₂) si données dispos.
            Étape 4.bis FE : audits Marie + Jean-Marc convergents. */}
        <div
          className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-2.5"
          style={{ fontSize: 12.5, color: 'var(--sol-ink-700)' }}
        >
          {gainMwh != null && gainMwh > 0 && (
            <div>
              <span
                className="block font-mono uppercase tracking-[0.05em]"
                style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
              >
                Économies modélisées
              </span>
              <span style={{ fontWeight: 500, color: 'var(--sol-ink-900)' }}>{gainMwh} MWh/an</span>
              {savingsEurYear != null && savingsEurYear > 0 && (
                <span
                  className="block"
                  style={{ fontSize: 11, color: 'var(--sol-succes-fg)', fontWeight: 500 }}
                >
                  ≈ {fmtEurShort(savingsEurYear)}/an
                </span>
              )}
            </div>
          )}
          {penaltyEur != null && (
            <div>
              <span
                className="block font-mono uppercase tracking-[0.05em]"
                style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
              >
                Pénalité légale
              </span>
              <span style={{ fontWeight: 500, color: tone.fg }}>{fmtEurShort(penaltyEur)}/an</span>
            </div>
          )}
          {decision.reference && (
            <div>
              <span
                className="block font-mono uppercase tracking-[0.05em]"
                style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
              >
                Référentiel
              </span>
              <span style={{ fontWeight: 500, color: 'var(--sol-ink-900)' }} className="truncate">
                {decision.reference}
              </span>
            </div>
          )}
          <div>
            <span
              className="block font-mono uppercase tracking-[0.05em]"
              style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
            >
              Échéance
            </span>
            <span style={{ fontWeight: 500, color: tone.fg }}>{echeanceText}</span>
          </div>
        </div>
        {/* Ligne 2 — Arbitrage financier CFO (CapEx + Payback + CO₂) si data dispo. */}
        {(capexEur != null || paybackMonths != null || co2AvoidedT != null) && (
          <div
            className="grid grid-cols-2 md:grid-cols-4 gap-3.5 mb-2.5 pt-2"
            style={{
              fontSize: 12.5,
              color: 'var(--sol-ink-700)',
              borderTop: '0.5px solid rgba(0,0,0,0.06)',
            }}
          >
            {capexEur != null && (
              <div>
                {/* Phase 15.C : AcronymTooltip accessible (tabIndex + role +
                    aria-label) au lieu de title="" sur span parent — WCAG
                    1.4.13 conforme + utilisable au clavier et tactile. */}
                <span
                  className="block font-mono uppercase tracking-[0.05em]"
                  style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
                >
                  Engagement <AcronymTooltip acronym="CapEx">CapEx</AcronymTooltip>
                </span>
                <span style={{ fontWeight: 500, color: 'var(--sol-ink-900)' }}>
                  {fmtEurShort(capexEur)}
                </span>
              </div>
            )}
            {paybackMonths != null && paybackMonths > 0 && (
              <div>
                <span
                  className="block font-mono uppercase tracking-[0.05em]"
                  style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
                >
                  <AcronymTooltip acronym="Payback">Payback</AcronymTooltip>
                </span>
                <span style={{ fontWeight: 500, color: 'var(--sol-ink-900)' }}>
                  {paybackMonths < 24
                    ? `${paybackMonths} mois`
                    : `${(paybackMonths / 12).toFixed(1)} ans`}
                </span>
                {/* Phase 16.bis.D (audit /frontend-design sévère) — fusion
                    des 2 sous-lignes (payback net + sanction évitée) en 1
                    seule phrase body 11px pour éviter le triple-stack mono
                    "valeur · sub1 · sub2 mono". Plus lisible CFO. */}
                {paybackMonthsNet != null &&
                  paybackMonthsNet > 0 &&
                  paybackMonthsNet < paybackMonths && (
                    <span
                      className="block"
                      style={{
                        fontSize: 11,
                        color: 'var(--sol-succes-fg)',
                        fontWeight: 500,
                        marginTop: 1,
                      }}
                    >
                      {paybackMonthsNet < 24
                        ? `${paybackMonthsNet} mois`
                        : `${(paybackMonthsNet / 12).toFixed(1)} ans`}{' '}
                      avec sanction évitée
                      {penaltyAvoidedEurYear ? ` (+ ${fmtEurShort(penaltyAvoidedEurYear)}/an)` : ''}
                    </span>
                  )}
              </div>
            )}
            {co2AvoidedT != null && co2AvoidedT > 0 && (
              <div>
                <span
                  className="block font-mono uppercase tracking-[0.05em]"
                  style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
                >
                  CO₂ évité
                </span>
                <span style={{ fontWeight: 500, color: 'var(--sol-succes-fg)' }}>
                  {co2AvoidedT} t/an
                </span>
              </div>
            )}
            {estimationMethod && (
              <div>
                <span
                  className="block font-mono uppercase tracking-[0.05em]"
                  style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
                >
                  Méthode
                </span>
                <span
                  className="inline-flex items-center px-1.5 py-0.5 rounded font-mono uppercase tracking-[0.05em]"
                  style={{
                    fontSize: 9.5,
                    background: 'var(--sol-attention-bg)',
                    color: 'var(--sol-attention-fg)',
                    fontWeight: 500,
                  }}
                  title={estimationMethod}
                >
                  Estimation
                </span>
              </div>
            )}
          </div>
        )}
        <div className="flex gap-2 flex-wrap">
          {/* Étape 9 P0-C : link vers Pilotage avec query focus pour permettre
              au futur Pilotage d'highlighter l'action correspondante (V2).
              Avant : anchor #decision-${decision.id} cassée car Pilotage rend
              id="decision-{rank}" sur les priorities (rank 1-5) — pas d'id
              action backend (audit nav Phase 5 P0). */}
          <Link
            to={`/cockpit/jour?focus=action-${decision.id}`}
            className="no-underline hover:underline"
            style={{ fontSize: 12.5, fontWeight: 500, color: tone.fg }}
          >
            Voir preuve opérationnelle →
          </Link>
          <span style={{ color: 'var(--sol-ink-400)' }}>·</span>
          <Link
            to={`/anomalies?action=${decision.id}`}
            className="no-underline hover:underline"
            style={{ fontSize: 12.5, fontWeight: 500, color: tone.fg }}
          >
            Méthodologie levier →
          </Link>
        </div>
      </div>
    </div>
  );
}

const DecisionCard = memo(DecisionCardImpl);

function DecisionsList({ decisions, loading }) {
  if (loading) {
    return (
      <div className="space-y-2">
        {[0, 1, 2].map((i) => (
          <div
            key={i}
            className="rounded-md animate-pulse"
            style={{
              background: 'var(--sol-bg-canvas)',
              border: '0.5px solid var(--sol-rule)',
              height: 130,
            }}
          />
        ))}
      </div>
    );
  }
  if (!decisions?.length) {
    return (
      <div
        className="rounded-md p-4 text-center"
        style={{
          background: 'var(--sol-succes-bg)',
          border: '0.5px solid var(--sol-succes-line)',
          color: 'var(--sol-succes-fg)',
        }}
      >
        <strong style={{ fontWeight: 500 }}>
          Aucune décision urgente à arbitrer cette semaine.
        </strong>{' '}
        Toutes les actions sont engagées dans les délais.
      </div>
    );
  }
  return (
    <div>
      {decisions.map((d, i) => (
        <DecisionCard key={d.id} decision={d} index={i} />
      ))}
    </div>
  );
}

// ── Trajectoire 2030 lissée (SVG) ──────────────────────────────────

function TrajectoryDTSmoothed({ trajectory }) {
  if (!trajectory?.annees?.length) return null;
  const { annees, reel_mwh = [], objectif_mwh = [], projection_mwh = [] } = trajectory;
  const allValues = [...reel_mwh, ...objectif_mwh, ...projection_mwh].filter(
    (v) => v != null && Number.isFinite(v)
  );
  if (allValues.length === 0) return null;
  const maxVal = Math.max(...allValues);
  const minVal = Math.min(...allValues);
  const range = maxVal - minVal || 1;

  // Étape 12 user feedback : SVG H=240 + label année à y=H−4 → texte 2030/2050
  // coupé visuellement en bas. Augmentation H + padding.bottom pour laisser
  // respirer les labels année (cf. screenshot user 29/04 "courbe trajectoire
  // coupée"). preserveAspectRatio xMidYMid meet par défaut.
  const W = 800;
  const H = 280;
  const padding = { top: 20, right: 20, bottom: 40, left: 64 };
  const innerW = W - padding.left - padding.right;
  const innerH = H - padding.top - padding.bottom;

  const xFor = (i) => padding.left + (i / (annees.length - 1)) * innerW;
  const yFor = (v) => (v == null ? null : padding.top + innerH - ((v - minVal) / range) * innerH);

  const todayIndex = reel_mwh.findIndex((v) => v == null);
  const todayX = xFor(todayIndex < 0 ? annees.length - 1 : todayIndex);

  const pointsToPath = (values, color) => {
    const points = values
      .map((v, i) => (v == null ? null : `${xFor(i)},${yFor(v)}`))
      .filter(Boolean);
    if (points.length < 2) return null;
    return `M ${points.join(' L ')}`;
  };

  return (
    <div
      className="rounded-md p-4 mb-5"
      style={{
        background: 'var(--sol-bg-paper)',
        border: '0.5px solid var(--sol-rule)',
      }}
    >
      <div className="flex justify-between items-start gap-3 flex-wrap mb-2">
        <div className="max-w-[50ch]">
          <div
            className="font-mono uppercase tracking-[0.07em] mb-1"
            style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
          >
            Trajectoire 2030 · réel vs cible Décret Tertiaire
          </div>
          <div className="text-xs" style={{ color: 'var(--sol-ink-700)', lineHeight: 1.5 }}>
            Avec les actions planifiées et leurs échéances réelles, l'objectif{' '}
            <strong style={{ fontWeight: 500 }}>−40 % / 2030</strong> reste atteignable. Lissage
            temporel par échéance d'action.
          </div>
        </div>
        <div className="flex gap-2 shrink-0 flex-wrap">
          <span
            className="font-mono uppercase tracking-[0.05em] inline-flex items-center gap-1"
            style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
          >
            <span
              style={{
                width: 12,
                height: 2,
                background: 'var(--sol-hch-fg)',
              }}
            />
            Réel
          </span>
          <span
            className="font-mono uppercase tracking-[0.05em] inline-flex items-center gap-1"
            style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
          >
            <span
              style={{
                width: 12,
                height: 2,
                background: 'var(--sol-refuse-fg)',
                borderTop: '1px dashed var(--sol-refuse-fg)',
              }}
            />
            Cible DT
          </span>
          <span
            className="font-mono uppercase tracking-[0.05em] inline-flex items-center gap-1"
            style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
          >
            <span
              style={{
                width: 12,
                height: 2,
                background: 'var(--sol-succes-fg)',
              }}
            />
            Projection
          </span>
        </div>
      </div>
      <svg
        viewBox={`0 0 ${W} ${H}`}
        xmlns="http://www.w3.org/2000/svg"
        style={{ width: '100%', height: 'auto', display: 'block' }}
        role="img"
        aria-label="Trajectoire DT 2020 à 2030"
      >
        {/* Grille horizontale */}
        {[0.25, 0.5, 0.75, 1].map((r) => (
          <line
            key={r}
            x1={padding.left}
            y1={padding.top + innerH * r}
            x2={W - padding.right}
            y2={padding.top + innerH * r}
            stroke="currentColor"
            strokeOpacity={r === 1 ? 0.15 : 0.08}
            strokeDasharray={r === 1 ? '3,3' : '2,3'}
          />
        ))}
        {/* Y axis labels */}
        {[0, 0.25, 0.5, 0.75, 1].map((r) => {
          const y = padding.top + innerH * r;
          const v = Math.round(maxVal - r * range);
          return (
            <text
              key={r}
              x={padding.left - 6}
              y={y + 4}
              textAnchor="end"
              fontFamily="var(--sol-font-mono)"
              fontSize="10"
              fill="currentColor"
              fillOpacity="0.5"
            >
              {v.toLocaleString('fr-FR')}
            </text>
          );
        })}
        {/* Cible DT (rouge dashed) */}
        <path
          d={pointsToPath(objectif_mwh)}
          fill="none"
          stroke="var(--sol-refuse-fg)"
          strokeWidth="1.4"
          strokeDasharray="4,4"
        />
        {/* Réel (bleu) */}
        <path d={pointsToPath(reel_mwh)} fill="none" stroke="var(--sol-hch-fg)" strokeWidth="2" />
        {reel_mwh.map((v, i) =>
          v == null ? null : (
            <circle key={i} cx={xFor(i)} cy={yFor(v)} r="3" fill="var(--sol-hch-fg)" />
          )
        )}
        {/* Projection (verte) */}
        <path
          d={pointsToPath(projection_mwh)}
          fill="none"
          stroke="var(--sol-succes-fg)"
          strokeWidth="2"
        />
        {projection_mwh.map((v, i) =>
          v == null ? null : (
            <circle key={i} cx={xFor(i)} cy={yFor(v)} r="3" fill="var(--sol-succes-fg)" />
          )
        )}
        {/* Ligne aujourd'hui */}
        <line
          x1={todayX}
          y1={padding.top}
          x2={todayX}
          y2={H - padding.bottom}
          stroke="currentColor"
          strokeOpacity="0.25"
          strokeDasharray="2,3"
        />
        <text
          x={todayX}
          y={padding.top - 6}
          textAnchor="middle"
          fontFamily="var(--sol-font-mono)"
          fontSize="10"
          fill="currentColor"
          fillOpacity="0.55"
        >
          aujourd'hui
        </text>
        {/* X axis labels — y positionné dans la zone padding.bottom (40px) */}
        {annees.map((annee, i) =>
          i % 2 === 0 ? (
            <text
              key={annee}
              x={xFor(i)}
              y={H - 14}
              textAnchor="middle"
              fontFamily="var(--sol-font-mono)"
              fontSize="10"
              fill="currentColor"
              fillOpacity="0.55"
            >
              {annee}
            </text>
          ) : null
        )}
      </svg>
      <div
        className="mt-1.5 font-mono uppercase tracking-[0.07em] flex justify-between flex-wrap gap-1"
        style={{ fontSize: 10, color: 'var(--sol-ink-500)' }}
      >
        <span>Source consumption_unified · projection lissée par action.echeance</span>
        <span>Jalons −40%/2030 · −50%/2040 · −60%/2050</span>
      </div>
    </div>
  );
}

// ── Facture portefeuille ──────────────────────────────────────────

function FacturePortefeuille({ portfolio }) {
  if (!portfolio) return null;
  const total = portfolio.total_portfolio_eur || 0;
  // Agrégation composantes au niveau portfolio
  const compsAgg = (portfolio.sites || []).reduce(
    (acc, s) => {
      const c = s.composantes || {};
      acc.fourniture += c.fourniture_eur || 0;
      acc.turpe += c.turpe_eur || 0;
      acc.taxes += c.accise_cta_tva_eur || 0;
      acc.capacite += c.capacite_eur || 0;
      acc.vnu += c.vnu_eur || 0;
      acc.cbam += c.cbam_scope || 0;
      return acc;
    },
    { fourniture: 0, turpe: 0, taxes: 0, capacite: 0, vnu: 0, cbam: 0 }
  );

  const totalActif = compsAgg.fourniture + compsAgg.turpe + compsAgg.taxes + compsAgg.capacite;
  const pct = (v) => (totalActif > 0 ? Math.round((v / totalActif) * 100) : 0);

  const composantes = [
    {
      label: 'Fourniture énergie',
      value: compsAgg.fourniture,
      pct: pct(compsAgg.fourniture),
      color: 'var(--sol-succes-fg)',
    },
    {
      label: "Tarif d'acheminement TURPE 7",
      acronym: 'TURPE',
      value: compsAgg.turpe,
      pct: pct(compsAgg.turpe),
      color: 'var(--sol-ink-700)',
    },
    {
      label: 'Taxes (accise + CTA + TVA)',
      acronym: 'CTA',
      value: compsAgg.taxes,
      pct: pct(compsAgg.taxes),
      color: 'var(--sol-attention-fg)',
    },
    {
      label: 'Mécanisme capacité (RTE)',
      value: compsAgg.capacite,
      pct: pct(compsAgg.capacite),
      color: 'var(--sol-ink-700)',
    },
  ];

  const inactives =
    compsAgg.vnu === 0 && compsAgg.cbam === 0
      ? [
          {
            label: 'Versement Nucléaire Universel',
            acronym: 'VNU',
            desc: 'dormant, activation prévue 2027',
          },
          {
            label: 'Taxe carbone aux frontières',
            acronym: 'CBAM',
            desc: 'non applicable, secteur tertiaire hors périmètre',
          },
        ]
      : [];

  return (
    <div className="rounded-md p-4 mb-5" style={{ background: 'var(--sol-bg-canvas)' }}>
      <div className="flex justify-between items-start gap-3 flex-wrap mb-3">
        <div>
          <div
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 18,
              fontWeight: 500,
              marginBottom: 3,
              color: 'var(--sol-ink-900)',
            }}
          >
            Facture énergie prévisionnelle{' '}
            {portfolio.site_count ? `${portfolio.site_count} sites` : 'portefeuille'}
            <span
              className="ml-2 inline-flex items-center px-1.5 py-0.5 rounded font-mono uppercase tracking-[0.06em]"
              style={{
                fontSize: 9.5,
                background: 'var(--sol-succes-bg)',
                color: 'var(--sol-succes-fg)',
                fontWeight: 500,
              }}
            >
              Calculé
            </span>
          </div>
          <div
            className="font-mono uppercase tracking-[0.07em]"
            style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
          >
            Périmètre {portfolio.site_count} sites · post-
            <AcronymTooltip acronym="ARENH">ARENH</AcronymTooltip> 01/01/2026
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 32,
              fontWeight: 500,
              lineHeight: 1,
              color: 'var(--sol-ink-900)',
            }}
          >
            {fmtEurShort(total)}
          </div>
          {/* Étape 4.bis FE : delta vs 2024 backend (P1 audit Jean-Marc CFO).
              Effet WOW : "562 k€" seul → "562 k€ · −22,5% vs 2024" sourcé. */}
          {portfolio.delta_vs_2024?.delta_pct != null && (
            <div
              className="font-mono uppercase tracking-[0.07em] mt-1"
              style={{
                fontSize: 11,
                color:
                  portfolio.delta_vs_2024.delta_pct < 0
                    ? 'var(--sol-succes-fg)'
                    : 'var(--sol-attention-fg)',
                fontWeight: 500,
              }}
              title={
                portfolio.delta_vs_2024.source || 'Médiane CRE T4 2025 · ETI tertiaire post-ARENH'
              }
            >
              {portfolio.delta_vs_2024.delta_pct > 0 ? '+ ' : '− '}
              {Math.abs(portfolio.delta_vs_2024.delta_pct)} % vs 2024
            </div>
          )}
        </div>
      </div>

      <div className="space-y-1.5">
        {composantes.map((c) => (
          <div key={c.label}>
            <div className="flex justify-between" style={{ fontSize: 13 }}>
              <span>
                {c.acronym ? (
                  <AcronymTooltip acronym={c.acronym}>{c.label}</AcronymTooltip>
                ) : (
                  c.label
                )}
              </span>
              <span style={{ fontWeight: 500 }}>{fmtEurShort(c.value)}</span>
            </div>
            <div
              className="rounded-full overflow-hidden mt-0.5"
              style={{ height: 6, background: 'var(--sol-bg-paper)' }}
            >
              <div
                className="h-full"
                style={{
                  width: `${c.pct}%`,
                  background: c.color,
                  transition: 'width 0.3s',
                }}
              />
            </div>
          </div>
        ))}
      </div>

      {inactives.length > 0 && (
        <details className="mt-3 pt-2.5" style={{ borderTop: '0.5px solid var(--sol-rule)' }}>
          <summary
            className="cursor-pointer font-mono uppercase tracking-[0.07em] list-none"
            style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
          >
            + Composantes inactives · {inactives.length} ligne
            {inactives.length > 1 ? 's' : ''}
          </summary>
          <div
            className="mt-2"
            style={{ fontSize: 12.5, color: 'var(--sol-ink-500)', lineHeight: 1.6 }}
          >
            {inactives.map((i) => (
              <div key={i.label}>
                <AcronymTooltip acronym={i.acronym}>{i.label}</AcronymTooltip> ({i.acronym}) —{' '}
                <em style={{ fontStyle: 'italic' }}>{i.desc}</em>
              </div>
            ))}
          </div>
        </details>
      )}
    </div>
  );
}

// ── Teaser Flex Intelligence ──────────────────────────────────────

function FlexTeaser({ flexPotential }) {
  // Étape 4.bis FE : consume backend `_facts.flex_potential` sourcé (P0-E).
  // Plus de fallback "~21 k€" non sourcé qui violait la règle d'or chiffres
  // fiables (audit Sophie VC). Affiche `Indicatif` si méthode heuristique.
  const eurYear = flexPotential?.eur_year;
  const method = flexPotential?.method;
  const source = flexPotential?.source;
  const eurText = eurYear != null ? fmtEurShort(eurYear) : '—';
  const isIndicative = method === 'heuristic_per_site' || method === 'indicative';
  return (
    <div
      className="rounded-md p-3 mb-5 flex items-center gap-3 flex-wrap"
      style={{
        background: 'var(--sol-hce-bg)',
        border: '0.5px solid var(--sol-rule)',
      }}
    >
      <Sparkles size={16} style={{ color: 'var(--sol-hce-fg)' }} aria-hidden="true" />
      <div
        style={{
          fontSize: 13.5,
          lineHeight: 1.5,
          color: 'var(--sol-ink-700)',
          flex: 1,
          minWidth: 200,
        }}
      >
        <strong style={{ color: 'var(--sol-hce-fg)', fontWeight: 500 }}>
          Gisement Flex portefeuille — {eurText}/an
        </strong>
        {isIndicative && (
          <span
            className="ml-1.5 inline-flex items-center px-1.5 py-0.5 rounded font-mono uppercase tracking-[0.06em]"
            style={{
              fontSize: 9,
              background: 'var(--sol-hce-bg)',
              color: 'var(--sol-hce-fg)',
              fontWeight: 500,
              border: '0.5px solid var(--sol-rule)',
            }}
            title={source || 'Estimation indicative'}
          >
            Indicatif
          </span>
        )}{' '}
        identifié sur logistique frigorifique ·{' '}
        <AcronymTooltip acronym="NEBCO">NEBCO</AcronymTooltip> /{' '}
        <AcronymTooltip acronym="AOFD">AOFD</AcronymTooltip>. Activation possible via partenaire
        d'agrégation.
      </div>
      <Link
        to="/flex"
        className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium no-underline transition-colors hover:bg-[var(--sol-bg-paper)]"
        style={{
          fontSize: 12.5,
          border: '0.5px solid var(--sol-ink-300)',
          background: 'var(--sol-bg-paper)',
          color: 'var(--sol-ink-900)',
        }}
      >
        Voir Flex Intelligence
        <ArrowRight size={12} aria-hidden="true" style={{ opacity: 0.6 }} />
      </Link>
    </div>
  );
}

// ── Page racine ──────────────────────────────────────────────────

export default function CockpitDecision() {
  const { facts, loading: factsLoading } = useCockpitFacts('current_month');
  const { org } = useScope();
  const [decisions, setDecisions] = useState(null);
  const [decisionsLoading, setDecisionsLoading] = useState(true);
  const [trajectory, setTrajectory] = useState(null);
  const [portfolio, setPortfolio] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setDecisionsLoading(true);
    Promise.all([
      // Backend Étape 4 P0-A + P0-B : serializer dédoublonne désormais
      // site×levier et le typo "système système" est purgé via
      // _dedup_adjacent_words. Plus besoin de dédup FE.
      getCockpitDecisionsTop3()
        .then((d) => (cancelled ? null : setDecisions(d?.decisions || [])))
        .catch(() => (cancelled ? null : setDecisions([]))),
      getCockpitTrajectory()
        .then((d) => (cancelled ? null : setTrajectory(d)))
        .catch(() => (cancelled ? null : setTrajectory(null))),
    ]).finally(() => {
      if (!cancelled) setDecisionsLoading(false);
    });
    return () => {
      cancelled = true;
    };
  }, [org?.id]);

  useEffect(() => {
    if (!org?.id) return;
    let cancelled = false;
    getPurchasePortfolioCostSimulation(org.id)
      .then((d) => (cancelled ? null : setPortfolio(d)))
      .catch(() => (cancelled ? null : setPortfolio(null)));
    return () => {
      cancelled = true;
    };
  }, [org?.id]);

  const sitesCount = facts?.scope?.site_count ?? org?.sites_count ?? 0;
  const orgName = facts?.scope?.org_name || org?.name || '';
  const lastUpdate = facts?.metadata?.last_update;
  const sources = facts?.metadata?.sources || [];
  const confidence = facts?.metadata?.confidence;
  // Phase 13.E : memo des derived values stables (lastUpdate change rarement,
  // weekIso ne change qu'en rollover hebdomadaire, printGenDate calcul Date+
  // toLocale inutile à chaque render).
  const lastUpdateRel = useMemo(() => relativeTime(lastUpdate), [lastUpdate]);
  const weekIso = useMemo(() => getIsoWeek(), []);

  // EPEX live — backend exposera /api/marche/spot V2 (post-Refonte sprint).
  // Étape 6.bis : masquer la pill complètement si null plutôt qu'afficher
  // une valeur hardcodée 78 €/MWh — règle d'or chiffres fiables 27/04
  // (audit /simplify P0 + audit Sophie VC : "perte de confiance immédiate"
  // si placeholder sans source affiché à un investisseur).
  const epexPrice = facts?.market?.epex_eur_per_mwh ?? null;
  const showEpexPill = epexPrice != null && Number.isFinite(epexPrice);

  const scopeLabel = `${orgName}${sitesCount ? ` — ${sitesCount} sites` : ''}`;

  // Phase 13.B — Rapport COMEX print : date génération formatée FR pour
  // l'en-tête PDF natif (visible uniquement via window.print()).
  // Phase 13.E memo : Date + toLocale est cher relativement à un render React.
  const printGenDate = useMemo(
    () =>
      new Date().toLocaleDateString('fr-FR', {
        day: '2-digit',
        month: 'long',
        year: 'numeric',
      }),
    []
  );

  return (
    <div
      className="max-w-[1280px] mx-auto"
      style={{
        background: 'var(--sol-bg-paper)',
        borderRadius: 12,
        border: '0.5px solid var(--sol-rule)',
        padding: '1.5rem 1.6rem 1.2rem',
      }}
    >
      {/* Phase 13.B — Header impression (caché écran, visible PDF print).
          Rendu autoportant pour partage CODIR : nom client, période,
          date de génération, source d'autorité PROMEOS. */}
      <div data-print-header>
        <div className="flex justify-between items-baseline">
          <div
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 18,
              fontWeight: 500,
              color: 'var(--sol-ink-900)',
              letterSpacing: '0.01em',
            }}
          >
            PROMEOS · Cockpit énergétique
          </div>
          <div
            className="font-mono uppercase tracking-[0.06em]"
            style={{ fontSize: 9, color: 'var(--sol-ink-500)' }}
          >
            Généré le {printGenDate}
          </div>
        </div>
        <div
          className="mt-1 font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 10, color: 'var(--sol-ink-700)' }}
        >
          Synthèse stratégique · {scopeLabel} · semaine {weekIso}
        </div>
      </div>

      {/* Header */}
      <div className="flex justify-between items-start gap-4 flex-wrap">
        <div className="flex-1 min-w-[260px]">
          <SolKickerWithSwitch scope={`Cockpit · ${scopeLabel}`} currentRoute="strategique" />
          <h1
            className="mt-1.5 mb-1"
            style={{
              fontFamily: 'var(--sol-font-display)',
              fontSize: 26,
              fontWeight: 500,
              lineHeight: 1.2,
              color: 'var(--sol-ink-900)',
            }}
          >
            Synthèse stratégique{' '}
            <em
              style={{
                fontStyle: 'italic',
                color: 'var(--sol-ink-700)',
                fontWeight: 400,
              }}
            >
              · semaine {weekIso} · pour CODIR
            </em>
          </h1>
          <div
            className="mt-1.5 font-mono uppercase tracking-[0.07em]"
            style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
          >
            Données {lastUpdateRel} · pour comité direction de la semaine
          </div>
        </div>
        <div className="flex gap-1.5 flex-wrap items-center">
          {showEpexPill && (
            <span
              className="inline-flex items-center gap-1.5 px-2.5 py-0.5 rounded-full font-mono uppercase tracking-[0.04em]"
              style={{
                fontSize: 11,
                border: '0.5px solid var(--sol-rule)',
                color: 'var(--sol-ink-700)',
                background: 'var(--sol-bg-paper)',
              }}
              title="Cours EPEX SPOT day-ahead (J−1, publication 12h45)"
            >
              <AcronymTooltip acronym="EPEX">EPEX</AcronymTooltip> {epexPrice} €/MWh
            </span>
          )}
          {/* Étape 9 P0-C : bouton "Rapport COMEX" — câblé en attendant
              l'export PDF V2 (P1 audit Jean-Marc CFO). Pour l'instant :
              window.print() qui produit un PDF browser-natif satisfaisant
              pour démo investisseur (en attendant un PDF généré backend
              avec watermark provenance). Audit nav Phase 5 P0 résolu :
              le bouton n'est plus inerte. */}
          <button
            type="button"
            onClick={() => {
              try {
                window.print();
              } catch (e) {
                // Fallback navigation vers méthodologie si print indisponible
                window.location.href = '/methodologie/cockpit-decision';
              }
            }}
            className="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-md font-medium transition-colors hover:bg-[var(--sol-bg-canvas)]"
            style={{
              fontSize: 13,
              border: '0.5px solid var(--sol-ink-300)',
              background: 'var(--sol-bg-paper)',
              color: 'var(--sol-ink-900)',
              cursor: 'pointer',
            }}
            title="Imprimer la synthèse stratégique au format PDF (export PDF dédié V2)"
          >
            <FileText size={14} aria-hidden="true" />
            Rapport COMEX
            <ArrowRight size={12} aria-hidden="true" style={{ opacity: 0.6 }} />
          </button>
        </div>
      </div>

      {/* Narrative stratégique 4 lignes denses + push hebdo */}
      <div data-print-section>
        <StrategicNarrative facts={facts} />
      </div>

      {/* Triptyque KPI hybride avec badges Calculé/Modélisé */}
      <div data-print-section>
        {factsLoading && !facts ? (
          <div className="grid grid-cols-1 md:grid-cols-3 gap-3 mb-6">
            {[0, 1, 2].map((i) => (
              <KpiSkeleton key={i} variant="confidence" />
            ))}
          </div>
        ) : (
          <KpiTriptyqueHybride facts={facts} />
        )}
      </div>

      {/* 3 décisions à arbitrer */}
      <div data-print-section>
        <div
          className="font-mono uppercase tracking-[0.07em] mb-2"
          style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
        >
          3 décisions à arbitrer · semaine {weekIso} · classement par échéance
        </div>
        <div className="mb-6">
          <DecisionsList decisions={decisions} loading={decisionsLoading} />
        </div>
      </div>

      {/* Trajectoire 2030 */}
      {trajectory && (
        <div data-print-section>
          <TrajectoryDTSmoothed trajectory={trajectory} />
        </div>
      )}

      {/* Facture portefeuille */}
      {portfolio && (
        <div data-print-section>
          <FacturePortefeuille portfolio={portfolio} />
        </div>
      )}

      {/* Teaser Flex Intelligence */}
      <div data-print-section>
        <FlexTeaser flexPotential={facts?.flex_potential} />
      </div>

      {/* Phase 13.D — Footer signaux moat (caché print).
          Doctrine simple+différenciant : 3 mécanismes réglementaires uniquement
          tracés par PROMEOS post-ARENH (VNU + TURPE 7 méridiennes + APER).
          Marie/Sophie investisseur voit instantanément les moats vs Tilt /
          Selectra / Deepki / Metron / ProcuraGate (cf reference_mix_e_2026
          + reference_competitive_intelligence_2026). */}
      <div
        data-print-hide
        className="mt-3 mb-3 flex gap-1.5 flex-wrap items-center"
        style={{
          paddingTop: 12,
          borderTop: '0.5px dashed var(--sol-rule)',
        }}
      >
        <div
          className="font-mono uppercase tracking-[0.07em] mr-1"
          style={{ fontSize: 9.5, color: 'var(--sol-ink-400)' }}
        >
          Suivi exclusif post-ARENH
        </div>
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-md font-mono uppercase tracking-[0.05em]"
          style={{
            fontSize: 10,
            border: '0.5px solid var(--sol-rule)',
            color: 'var(--sol-ink-700)',
            background: 'var(--sol-bg-paper)',
          }}
          title="Versement Nucléaire Universel — Décret 2026-55 + CRE 2026-52. Seuils 78 / 110 €/MWh. Activation 2027 si EPEX dépasse seuil."
        >
          <AcronymTooltip acronym="VNU">VNU</AcronymTooltip>{' '}
          <span style={{ marginLeft: 4, color: 'var(--sol-ink-500)' }}>seuil 78 €/MWh</span>
        </span>
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-md font-mono uppercase tracking-[0.05em]"
          style={{
            fontSize: 10,
            border: '0.5px solid var(--sol-rule)',
            color: 'var(--sol-ink-700)',
            background: 'var(--sol-bg-paper)',
          }}
          title="TURPE 7 reprogrammation HC — méridiennes 11h-17h obligatoires (CRE 2025-78, brochure Enedis p.13-14). Cycle 5 ans."
        >
          <AcronymTooltip acronym="TURPE">TURPE 7</AcronymTooltip>{' '}
          <span style={{ marginLeft: 4, color: 'var(--sol-ink-500)' }}>HC méridiennes</span>
        </span>
        <span
          className="inline-flex items-center px-2 py-0.5 rounded-md font-mono uppercase tracking-[0.05em]"
          style={{
            fontSize: 10,
            border: '0.5px solid var(--sol-rule)',
            color: 'var(--sol-ink-700)',
            background: 'var(--sol-bg-paper)',
          }}
          title="Loi APER 2023-175 — solarisation parkings >1500 m². Échéance 1/07/2026 ou 1/07/2028 selon surface. Sanction 20 €/m²/an."
        >
          <AcronymTooltip acronym="APER">APER</AcronymTooltip>{' '}
          <span style={{ marginLeft: 4, color: 'var(--sol-ink-500)' }}>parkings &gt; 1 500 m²</span>
        </span>
      </div>

      {/* Phase 21.A (REG-3 audit triple Phase 20.bis) — réconciliation cross-source
          de la consommation annuelle. Le backend `_facts.consumption` expose
          désormais 2 valeurs distinctes pour aider l'auditeur terrain :
            - `annual_mwh` (élec metered 365j glissants, KPI temps réel)
            - `annual_mwh_dt` (élec + gaz multi-énergie via ConsumptionTarget,
              aligné Décret Tertiaire 2019-771 art. R131-39)
          Avant : audit constatait 595 / 746 / 262 MWh sur 3 routes sans
          réconciliation. Désormais : la note explicite expose les 2 valeurs
          avec leur scope. */}
      {(facts?.consumption?.annual_mwh != null || facts?.consumption?.annual_mwh_dt != null) && (
        <div
          className="mt-3 font-mono uppercase tracking-[0.06em]"
          style={{
            fontSize: 10,
            color: 'var(--sol-ink-500)',
            paddingTop: 8,
            borderTop: '0.5px dashed var(--sol-rule)',
          }}
        >
          <span style={{ color: 'var(--sol-ink-700)' }}>Conso annuelle</span>{' '}
          {facts.consumption.annual_mwh != null && (
            <>
              · <strong>{facts.consumption.annual_mwh.toLocaleString('fr-FR')} MWh</strong> élec
              metered 365j
            </>
          )}
          {facts.consumption.annual_mwh_dt != null && (
            <>
              {' · '}
              <strong>{facts.consumption.annual_mwh_dt.toLocaleString('fr-FR')} MWh</strong> élec +
              gaz aligné <AcronymTooltip acronym="DT">DT</AcronymTooltip>
            </>
          )}
        </div>
      )}

      {/* Footer Sol (visible écran + print) */}
      <div
        className="flex justify-between flex-wrap gap-2.5 pt-3"
        style={{ borderTop: '0.5px solid var(--sol-rule)' }}
      >
        <div
          className="font-mono uppercase tracking-[0.07em]"
          style={{ fontSize: 11, color: 'var(--sol-ink-500)' }}
        >
          Source {sources.join(' + ') || 'PROMEOS'} · Décret 2019-771 art. 9
          {confidence ? ` · confiance ${confidence}` : ''}
          {' · mis à jour '}
          {lastUpdateRel} ·{' '}
          <Link
            to="/methodologie/cockpit-decision"
            className="no-underline hover:underline"
            style={{
              color: 'var(--sol-ink-500)',
              borderBottom: '0.5px dotted var(--sol-ink-400)',
            }}
          >
            méthodologie
          </Link>
        </div>
      </div>

      {/* Phase 13.B — Footer impression (caché écran, visible PDF print).
          Signature de provenance + URL méthodologie pour traçabilité CODIR. */}
      <div data-print-footer>
        Document généré par PROMEOS · Synthèse stratégique {scopeLabel} · {printGenDate} · semaine{' '}
        {weekIso}
        <br />
        Sources : {sources.join(' + ') || 'PROMEOS'}
        {confidence ? ` · niveau de confiance ${confidence}` : ''} · méthodologie complète sur{' '}
        promeos.io/methodologie/cockpit-decision
      </div>
    </div>
  );
}
