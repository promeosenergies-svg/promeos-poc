/**
 * PROMEOS — BriefCodexCard
 *
 * Wow-card exec : Sol pré-rédige le brief CODIR du Directeur Énergie.
 * Texte court (4-6 lignes), prêt à copier-coller dans une présentation
 * ou un mail au CODIR. Source : agrégation solProposal + KPIs cockpit.
 *
 * Différenciateur PROMEOS : seul outil B2B énergie qui *écrit* le brief.
 * Metron/Advizeo donnent les chiffres, PROMEOS donne le texte exec prêt.
 */
import { useMemo, useState } from 'react';
import { Copy, Check, FileText, ChevronDown, ChevronUp } from 'lucide-react';

function formatFREur(eur) {
  if (eur == null || isNaN(eur)) return '—';
  return Math.round(eur).toLocaleString('fr-FR') + ' €';
}

function formatFRMwh(mwh) {
  if (mwh == null || isNaN(mwh)) return '—';
  return Math.round(mwh).toLocaleString('fr-FR') + ' MWh';
}

/**
 * Compose un brief CODIR de 4-6 lignes depuis les données disponibles.
 * Texte structuré : situation → diagnostic → recommandation → décision.
 */
function buildBriefText({
  orgName,
  totalSites,
  facture,
  conformityScore,
  consoMwh,
  co2Tco2,
  sitesAtRisk,
  actionsCount,
  totalImpactEur,
  alertesCount,
  anomaliesCount,
}) {
  const lines = [];

  // Ligne 1 : situation patrimoine — wording fluide qui marche AVEC ou SANS orgName
  // FIX bug audit Jean-Marc : "Notre patrimoine votre patrimoine" quand fallback.
  const introContext = orgName
    ? `Notre groupe ${orgName} pilote ${totalSites} sites tertiaires et`
    : `Le patrimoine de ${totalSites} sites tertiaires`;
  lines.push(
    `${introContext} affiche une facture énergie de ${formatFREur(facture)} HT cette période, pour ${formatFRMwh(consoMwh)} de consommation cumulée.`
  );

  // Ligne 2 : conformité + risque
  if (conformityScore != null) {
    const status =
      conformityScore >= 75 ? 'solide' : conformityScore >= 60 ? 'sous vigilance' : 'à risque';
    lines.push(
      `Notre score de conformité Décret Tertiaire s'établit à ${Math.round(conformityScore)}/100 (${status})${
        sitesAtRisk > 0
          ? `, avec ${sitesAtRisk} site${sitesAtRisk > 1 ? 's' : ''} menaçant la trajectoire 2030.`
          : '.'
      }`
    );
  }

  // Ligne 3 : empreinte CO₂
  if (co2Tco2 != null && co2Tco2 > 0) {
    lines.push(
      `L'empreinte carbone cumulée s'élève à ${Math.round(co2Tco2)} tCO₂eq sur les scopes 1+2 (référentiel ADEME V23.6), donnée mobilisable pour le reporting CSRD.`
    );
  }

  // Ligne 4 : opportunités identifiées par Sol (le wow)
  if (actionsCount > 0 && totalImpactEur > 0) {
    lines.push(
      `Sol a identifié ${actionsCount} levier${actionsCount > 1 ? 's' : ''} d'optimisation chiffré${actionsCount > 1 ? 's' : ''} représentant ${formatFREur(totalImpactEur)}/an d'opportunités cumulées (multi-stream : conformité, facturation, optimisation énergétique).`
    );
  }

  // Ligne 5 : signaux opérationnels
  const signals = [];
  if (alertesCount > 0)
    signals.push(`${alertesCount} alerte${alertesCount > 1 ? 's' : ''} active${alertesCount > 1 ? 's' : ''}`);
  if (anomaliesCount > 0)
    signals.push(
      `${anomaliesCount} anomalie${anomaliesCount > 1 ? 's' : ''} de facturation à arbitrer`
    );
  if (signals.length > 0) {
    lines.push(`À surveiller cette semaine : ${signals.join(', ')}.`);
  }

  // Ligne 6 : décision attendue
  if (totalImpactEur > 0) {
    lines.push(
      `Décision attendue : validation de l'enveloppe pour activer les ${actionsCount} leviers identifiés.`
    );
  } else {
    lines.push(`Décision attendue : aucune action urgente — patrimoine sous contrôle.`);
  }

  return lines.join('\n\n');
}

export default function BriefCodexCard({
  orgName,
  totalSites = 0,
  facture,
  conformityScore,
  consoMwh,
  co2Tco2,
  sitesAtRisk = 0,
  actionsCount = 0,
  totalImpactEur = 0,
  alertesCount = 0,
  anomaliesCount = 0,
}) {
  const briefText = useMemo(
    () =>
      buildBriefText({
        orgName,
        totalSites,
        facture,
        conformityScore,
        consoMwh,
        co2Tco2,
        sitesAtRisk,
        actionsCount,
        totalImpactEur,
        alertesCount,
        anomaliesCount,
      }),
    [
      orgName,
      totalSites,
      facture,
      conformityScore,
      consoMwh,
      co2Tco2,
      sitesAtRisk,
      actionsCount,
      totalImpactEur,
      alertesCount,
      anomaliesCount,
    ]
  );

  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(false);

  const handleCopy = async (e) => {
    e?.stopPropagation();
    try {
      await navigator.clipboard.writeText(briefText);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      setCopied(false);
    }
  };

  if (totalSites === 0) return null;

  return (
    <div
      style={{
        background: 'var(--sol-bg-paper)',
        border: '1px solid var(--sol-ink-200)',
        borderLeft: '3px solid var(--sol-ink-700)',
        borderRadius: 8,
      }}
    >
      {/* Header collapsable — économise ~500px en first-paint
          (audit UX A1 : duplique SolHero + KPIs si toujours déplié). */}
      <button
        type="button"
        onClick={() => setExpanded((s) => !s)}
        style={{
          all: 'unset',
          cursor: 'pointer',
          width: '100%',
          padding: '14px 22px',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          gap: 16,
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, minWidth: 0 }}>
          <span
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontFamily: 'var(--sol-font-mono)',
              fontSize: 9.5,
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              color: 'var(--sol-ink-700)',
              fontWeight: 600,
              background: 'var(--sol-ink-100, #f3f4f6)',
              padding: '3px 8px',
              borderRadius: 99,
            }}
          >
            <FileText size={10} />
            Brief CODIR
          </span>
          <span
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13,
              fontWeight: 500,
              color: 'var(--sol-ink-900)',
            }}
          >
            Synthèse exécutive · {expanded ? 'masquer' : 'voir'} le texte
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          <button
            type="button"
            onClick={handleCopy}
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 12.5,
              fontWeight: 500,
              padding: '5px 10px',
              borderRadius: 6,
              border: '1px solid var(--sol-ink-200)',
              background: copied ? 'var(--sol-calme-bg)' : 'var(--sol-bg-paper)',
              color: copied ? 'var(--sol-calme-fg)' : 'var(--sol-ink-700)',
              cursor: 'pointer',
              display: 'inline-flex',
              alignItems: 'center',
              gap: 5,
              whiteSpace: 'nowrap',
            }}
          >
            {copied ? (
              <>
                <Check size={12} /> Copié
              </>
            ) : (
              <>
                <Copy size={12} /> Copier
              </>
            )}
          </button>
          {expanded ? (
            <ChevronUp size={16} style={{ color: 'var(--sol-ink-400)' }} />
          ) : (
            <ChevronDown size={16} style={{ color: 'var(--sol-ink-400)' }} />
          )}
        </div>
      </button>

      {/* Brief text expandable */}
      {expanded && (
        <div style={{ padding: '0 22px 18px' }}>
          <div
            style={{
              fontFamily: 'var(--sol-font-body)',
              fontSize: 13.5,
              lineHeight: 1.65,
              color: 'var(--sol-ink-700)',
              whiteSpace: 'pre-wrap',
              background: 'var(--sol-bg-canvas, #fafaf6)',
              border: '1px solid var(--sol-ink-100, #f3f4f6)',
              borderRadius: 6,
              padding: '14px 16px',
              maxWidth: 820,
            }}
          >
            {briefText}
          </div>
          <div
            style={{
              marginTop: 8,
              fontSize: 10.5,
              color: 'var(--sol-ink-400)',
              fontFamily: 'var(--sol-font-mono)',
              letterSpacing: '0.04em',
            }}
          >
            Texte généré automatiquement — modifiable avant envoi
          </div>
        </div>
      )}
    </div>
  );
}
