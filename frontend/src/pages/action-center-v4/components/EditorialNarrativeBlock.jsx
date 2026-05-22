import { useActionCenterV4Summary } from '../../../hooks/v4';
import { formatEuros } from '../../../utils/money';
import { PILOTAGE_COPY } from '../constants';
import { SolButton } from './SolButton';

/**
 * M2-5.12 — Bloc narratif éditorial Sol (maquette Sophie Marin 2026-05-22).
 *
 * Posé entre PilotageTabs et NarrativeBar sur la page Pilotage. Composition :
 *  1. Eyebrow status pill — dot vert + libellé MONO uppercase périmètre
 *  2. Phrase éditoriale Fraunces italique grosse avec emphases sémantiques
 *     (chiffres en couleur refuse/attention/succes selon urgence)
 *  3. CTA principal noir (top-right) « Lancer le triage » (disabled MV3)
 *  4. CTAs secondaires (bottom-right) « Voir l'impact » + « Exporter COMEX »
 *     (disabled MV3)
 *
 * Données : `useActionCenterV4Summary` (déjà fetché en parallèle par
 * NarrativeBar — React déduplique le call si le hook est stable). Lecture
 * pure, zéro calcul métier (count_p0 + count_p1 est une somme d'affichage,
 * pas une dérivation business — règle d'or doctrine §6.6 respectée).
 *
 * Props :
 *  - `orgName` (string) : « GROUPE HELIOS » pour l'eyebrow
 *  - `sitesCount` (number) : nombre de sites pour l'eyebrow
 *  - `onLaunchTriage` (fn, optionnel) : si fourni, active le CTA principal
 *  - `onShowImpact` (fn, optionnel) : si fourni, active CTA « Voir l'impact »
 *  - `onExportComex` (fn, optionnel) : si fourni, active CTA « Exporter »
 *
 * En MV3 les 3 CTAs sont rendus disabled avec tooltips « Disponible M2-6 »
 * (cf. PILOTAGE_COPY.ctaXxxDisabledHint) — voir doctrine §6.6 sur l'anti
 * « bouton mort silencieux ». Les handlers arrivent en M2-6.
 */
export function EditorialNarrativeBlock({
  orgName = 'GROUPE HELIOS',
  sitesCount = 0,
  onLaunchTriage,
  onShowImpact,
  onExportComex,
  // M2-6.B.pdf — état loading injecté par le parent pendant la génération
  // PDF (2-5s ReportLab). Désactive le bouton et affiche un libellé transitoire.
  exportComexLoading = false,
}) {
  const { data, loading, error } = useActionCenterV4Summary();

  // Loading / error : on rend un skeleton compact plutôt que de cacher tout
  // le bloc (le user voit qu'il y a un bloc en cours de chargement).
  if (loading) return <EditorialSkeleton />;
  if (error || !data) return null;

  // Composition de la phrase narrative (lecture pure, pas de calcul métier).
  // Le `+` est une addition d'affichage (combiner 2 compteurs en 1 libellé),
  // pas une agrégation business — la doctrine §6.6 distingue les deux.
  const decisionsCount = (data.count_p0 ?? 0) + (data.count_p1 ?? 0);
  const blockersCount = data.count_at_risk ?? 0;

  return (
    <section
      aria-label="Synthèse narrative du jour"
      className="mb-4 rounded-[10px] border p-5"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
      }}
    >
      {/* Eyebrow pill : dot vert + périmètre tour de contrôle */}
      <div
        className="mb-3 flex items-center gap-1.5 font-mono text-[10.5px] uppercase tracking-[0.14em]"
        style={{ color: 'var(--sol-ink-500)' }}
      >
        <span
          aria-hidden="true"
          style={{ color: 'var(--sol-succes-fg)', fontSize: '12px', lineHeight: 1 }}
        >
          {PILOTAGE_COPY.eyebrowDot}
        </span>
        <span style={{ color: 'var(--sol-ink-700)' }}>{PILOTAGE_COPY.eyebrowLabel}</span>
        <span aria-hidden="true">{PILOTAGE_COPY.eyebrowSeparator}</span>
        <span>{orgName}</span>
        <span aria-hidden="true">{PILOTAGE_COPY.eyebrowSeparator}</span>
        <span>
          {sitesCount} {sitesCount > 1 ? 'SITES' : 'SITE'}
        </span>
      </div>

      <div className="flex items-start justify-between gap-4">
        {/* Phrase narrative éditoriale Fraunces italique 24-28px */}
        <h2
          className="flex-1 text-[24px] italic leading-[1.25] md:text-[28px]"
          style={{
            fontFamily: 'var(--sol-font-display)',
            color: 'var(--sol-ink-900)',
            letterSpacing: '-0.005em',
          }}
        >
          {/* Chiffre décisions en MONO refuse-fg pour saillance */}
          <span
            className="font-mono not-italic"
            style={{ color: 'var(--sol-refuse-fg)', fontWeight: 600 }}
          >
            {decisionsCount}
          </span>{' '}
          {decisionsCount > 1
            ? PILOTAGE_COPY.editorialDecisionsSuffix
            : PILOTAGE_COPY.editorialDecisionSuffixSingular}
          <span style={{ color: 'var(--sol-ink-700)' }}>
            {PILOTAGE_COPY.editorialDecisionsTodaySuffix}
          </span>
          <span aria-hidden="true" className="not-italic" style={{ color: 'var(--sol-ink-300)' }}>
            {' · '}
          </span>
          {blockersCount > 0 ? (
            <>
              <span
                className="font-mono not-italic"
                style={{ color: 'var(--sol-attention-fg)', fontWeight: 600 }}
              >
                {blockersCount}
              </span>{' '}
              {blockersCount > 1
                ? PILOTAGE_COPY.editorialBlockersSuffix
                : PILOTAGE_COPY.editorialBlockerSuffixSingular}
            </>
          ) : (
            <span style={{ color: 'var(--sol-ink-700)' }}>{PILOTAGE_COPY.editorialNoBlockers}</span>
          )}
          <span aria-hidden="true" className="not-italic" style={{ color: 'var(--sol-ink-300)' }}>
            {' · '}
          </span>
          <span style={{ color: 'var(--sol-ink-700)' }}>
            {PILOTAGE_COPY.editorialDataQualityOK.split(' OK')[0]}{' '}
            <span
              className="font-mono not-italic"
              style={{ color: 'var(--sol-succes-fg)', fontWeight: 700 }}
            >
              OK
            </span>
            <span className="not-italic">.</span>
          </span>
        </h2>

        {/* CTA principal noir top-right */}
        <SolButton
          onClick={onLaunchTriage}
          disabled={!onLaunchTriage}
          title={onLaunchTriage ? undefined : PILOTAGE_COPY.ctaTriageDisabledHint}
        >
          ⏱ {PILOTAGE_COPY.ctaTriage}
        </SolButton>
      </div>

      {/* M2-6.B.frontend.bis — Indicateur complétude CFO (Q19=C closeur).
          Format cardinal Amine : « X actions sur Y portent un impact estimé : Z k€ ».
          Q19=C exigeait le total CFO (Z) en plus du ratio (X/Y) déjà livré
          en M2-6.B.frontend ; le bilan initial a livré 50%, .bis ferme l'écart.
          Sources :
            - X = `items_with_impact_known` (numérateur transparence CFO)
            - Y = `items_total` (dénominateur, all-lifecycle cf. doc sémantique)
            - Z = `sums_eur_total` formaté compact (jamais recalcul FE — pin
              source-guard SG_AC_V4_MONEY_01)
          Grammaire FR stricte : 0 et 1 → singulier (« action » + « porte »),
          ≥ 2 → pluriel (« actions » + « portent »). Académie française. */}
      {data.items_total != null && (
        <p
          className="mt-3 text-[12.5px] not-italic"
          style={{
            color: 'var(--sol-ink-500)',
            fontFamily: 'var(--sol-font-display)',
          }}
          data-testid="editorial-completude"
        >
          <span
            className="font-mono not-italic"
            style={{
              color: 'var(--sol-ink-700)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {data.items_with_impact_known ?? 0}
          </span>{' '}
          {(data.items_with_impact_known ?? 0) >= 2 ? 'actions' : 'action'} sur{' '}
          <span
            className="font-mono not-italic"
            style={{
              color: 'var(--sol-ink-700)',
              fontVariantNumeric: 'tabular-nums',
            }}
          >
            {data.items_total}
          </span>{' '}
          {(data.items_with_impact_known ?? 0) >= 2 ? 'portent' : 'porte'} un impact estimé
          {' : '}
          <span
            className="font-mono not-italic"
            style={{
              color: 'var(--sol-ink-700)',
              fontVariantNumeric: 'tabular-nums',
            }}
            data-testid="editorial-completude-sum"
          >
            {formatEuros(data.sums_eur_total ?? 0, 'compact')}
          </span>
        </p>
      )}

      {/* CTAs secondaires bottom-right (alignés droite) */}
      <div className="mt-4 flex items-center justify-end gap-2">
        <SolButton
          variant="secondary"
          onClick={onShowImpact}
          disabled={!onShowImpact}
          title={onShowImpact ? undefined : PILOTAGE_COPY.ctaImpactDisabledHint}
        >
          {PILOTAGE_COPY.ctaImpact}
        </SolButton>
        <SolButton
          variant="secondary"
          onClick={onExportComex}
          disabled={!onExportComex || exportComexLoading}
          title={onExportComex ? undefined : PILOTAGE_COPY.ctaExportDisabledHint}
          data-testid="cta-export-comex"
        >
          {exportComexLoading ? PILOTAGE_COPY.ctaExportLoading : PILOTAGE_COPY.ctaExport}
        </SolButton>
      </div>
    </section>
  );
}

/**
 * Skeleton compact pendant le chargement de /summary. Préserve la hauteur
 * du bloc pour éviter le « content shift » à l'arrivée des données.
 */
function EditorialSkeleton() {
  return (
    <section
      aria-busy="true"
      aria-label="Synthèse narrative en cours de chargement"
      className="mb-4 rounded-[10px] border p-5"
      style={{
        background: 'var(--sol-bg-paper)',
        borderColor: 'var(--sol-rule)',
        minHeight: 140,
      }}
    >
      <div
        className="mb-3 h-3 w-1/3 animate-pulse rounded"
        style={{ background: 'var(--sol-bg-panel)' }}
      />
      <div
        className="h-8 w-3/4 animate-pulse rounded"
        style={{ background: 'var(--sol-bg-panel)' }}
      />
    </section>
  );
}
