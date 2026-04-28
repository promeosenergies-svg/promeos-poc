/**
 * BriefCodexCard — pré-rédige le brief CODIR du Directeur Énergie.
 *
 * 2 modes consultables via toggle :
 *   - "Bullets DAF" (default) : 6 chiffres bruts pour Excel/CFO
 *   - "Narratif COMEX"        : 6 paragraphes prêts à coller en présentation
 *
 * Source : props (agrégation hooks Cockpit). Display-only.
 */
import { useMemo, useState } from 'react';
import { Copy, Check, FileText, ChevronDown, ChevronUp, List, AlignLeft } from 'lucide-react';
import { fmtEurFull, fmtMwh } from '../utils/format';
import SolNarrativeText from '../ui/sol/SolNarrativeText';

const SENTINEL_FALLBACKS = new Set(['votre patrimoine', 'patrimoine', 'organisation']);

function isRealOrgName(name) {
  return (
    name &&
    typeof name === 'string' &&
    name.length >= 3 &&
    !SENTINEL_FALLBACKS.has(name.toLowerCase().trim())
  );
}

/**
 * Mode "Narratif COMEX" : 6 paragraphes prêts à coller.
 */
function buildBriefNarrative(args) {
  const {
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
  } = args;
  const lines = [];

  const introContext = isRealOrgName(orgName)
    ? `Notre groupe ${orgName} pilote ${totalSites} sites tertiaires et`
    : `Le patrimoine de ${totalSites} sites tertiaires`;
  lines.push(
    `${introContext} affiche une facture énergie de ${fmtEurFull(facture)} HT cette période, pour ${fmtMwh(consoMwh)} de consommation cumulée.`
  );

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

  if (co2Tco2 != null && co2Tco2 > 0) {
    lines.push(
      `L'empreinte carbone cumulée s'élève à ${Math.round(co2Tco2)} tCO₂eq sur les scopes 1+2 (référentiel ADEME V23.6), donnée mobilisable pour le reporting CSRD.`
    );
  }

  if (actionsCount > 0 && totalImpactEur > 0) {
    lines.push(
      `Le moteur PROMEOS a identifié ${actionsCount} levier${actionsCount > 1 ? 's' : ''} d'optimisation chiffré${actionsCount > 1 ? 's' : ''} représentant ${fmtEurFull(totalImpactEur)}/an d'opportunités cumulées (multi-stream : conformité, facturation, optimisation énergétique).`
    );
  }

  const signals = [];
  if (alertesCount > 0)
    signals.push(
      `${alertesCount} alerte${alertesCount > 1 ? 's' : ''} active${alertesCount > 1 ? 's' : ''}`
    );
  if (anomaliesCount > 0)
    signals.push(
      `${anomaliesCount} anomalie${anomaliesCount > 1 ? 's' : ''} de facturation à arbitrer`
    );
  if (signals.length > 0) {
    lines.push(`À surveiller cette semaine : ${signals.join(', ')}.`);
  }

  if (totalImpactEur > 0) {
    lines.push(
      `Décision attendue : arbitrage du plan d'investissement pour activer les ${actionsCount} leviers — gain récurrent ${fmtEurFull(totalImpactEur)}/an, payback cible ≤ 3 ans (l'enveloppe précise est chiffrée action par action dans le module Plan d'action, à valider avant CODIR).`
    );
  } else {
    lines.push(`Décision attendue : aucune action urgente — patrimoine sous contrôle.`);
  }

  return lines.join('\n\n');
}

/** Mode "Bullets DAF" : 6 lignes max, format Excel CFO. */
function buildBriefBullets(args) {
  const {
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
  } = args;
  const bullets = [
    `• Périmètre · ${totalSites} sites tertiaires`,
    `• Facture énergie · ${fmtEurFull(facture)} HT (${fmtMwh(consoMwh)})`,
    `• Score conformité DT · ${conformityScore != null ? Math.round(conformityScore) + '/100' : '—'}${sitesAtRisk > 0 ? ` · ${sitesAtRisk} site${sitesAtRisk > 1 ? 's' : ''} à risque 2030` : ''}`,
    // Phase 4 quick win 3 : ligne CO₂ toujours rendue (parité Bullets/Narratif).
    // Le narratif l'inclut systématiquement quand co2 > 0 ; on s'aligne avec un
    // fallback explicite « donnée non calculée » plutôt que disparition silencieuse.
    `• Empreinte carbone · ${
      co2Tco2 != null && co2Tco2 > 0
        ? `${Math.round(co2Tco2)} tCO₂eq (scopes 1+2 ADEME V23.6)`
        : '— (donnée non calculée)'
    }`,
  ];
  if (actionsCount > 0 && totalImpactEur > 0) {
    bullets.push(
      `• Leviers identifiés · ${actionsCount} actions · ${fmtEurFull(totalImpactEur)}/an potentiel cumulé · payback cible ≤ 3 ans`
    );
  }
  const signals = [];
  if (alertesCount > 0) signals.push(`${alertesCount} alerte${alertesCount > 1 ? 's' : ''}`);
  if (anomaliesCount > 0)
    signals.push(`${anomaliesCount} anomalie${anomaliesCount > 1 ? 's' : ''} facturation`);
  if (signals.length > 0) {
    bullets.push(`• À traiter cette semaine · ${signals.join(' · ')}`);
  }
  return bullets.join('\n');
}

const MODES = {
  bullets: { label: 'Bullets DAF', Icon: List, build: buildBriefBullets },
  narrative: { label: 'Narratif COMEX', Icon: AlignLeft, build: buildBriefNarrative },
};

// Persistance utilisateur du mode choisi (Phase 4 quick win 3) — le CFO en
// présentation veut presque toujours « Narratif COMEX » alors que le default
// produit reste « Bullets DAF ». Sans persistance, +1 clic systématique à
// chaque visite. Cf. audit CX 26/04/2026.
const BRIEF_MODE_STORAGE_KEY = 'promeos_brief_codex_mode';

function readStoredMode() {
  try {
    const v = localStorage.getItem(BRIEF_MODE_STORAGE_KEY);
    return v && v in MODES ? v : null;
  } catch {
    return null;
  }
}

function persistMode(mode) {
  try {
    localStorage.setItem(BRIEF_MODE_STORAGE_KEY, mode);
  } catch {
    /* noop */
  }
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
  defaultExpanded = false,
  defaultMode = 'bullets',
}) {
  const [mode, setMode] = useState(
    () => readStoredMode() ?? (defaultMode in MODES ? defaultMode : 'bullets')
  );
  const handleModeChange = (key) => {
    setMode(key);
    persistMode(key);
  };
  const [copied, setCopied] = useState(false);
  const [expanded, setExpanded] = useState(defaultExpanded);

  const briefText = useMemo(
    () =>
      MODES[mode].build({
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
      mode,
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
    <div className="bg-white border border-gray-200 border-l-4 border-l-gray-700 rounded-lg">
      {/* Header — toggle expand + mode switcher + copy */}
      <div className="flex items-center justify-between gap-4 px-4 py-3">
        <button
          type="button"
          onClick={() => setExpanded((s) => !s)}
          aria-expanded={expanded}
          aria-controls="brief-codex-content"
          className="flex items-center gap-3 min-w-0 flex-1 min-h-[44px] cursor-pointer focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 rounded text-left"
        >
          <span className="inline-flex items-center gap-1.5 px-2 py-1 rounded-full bg-gray-100 text-gray-700 font-mono text-[11px] uppercase tracking-wider font-semibold">
            <FileText size={11} aria-hidden="true" />
            Brief CODIR
          </span>
          <span className="text-sm font-medium text-gray-900">
            Synthèse exécutive · {expanded ? 'masquer' : 'voir'}
          </span>
          <span aria-hidden="true" className="ml-auto inline-flex p-1">
            {expanded ? (
              <ChevronUp size={16} className="text-gray-400" />
            ) : (
              <ChevronDown size={16} className="text-gray-400" />
            )}
          </span>
        </button>
        <button
          type="button"
          onClick={handleCopy}
          aria-label={copied ? 'Brief copié' : 'Copier le brief'}
          className={`inline-flex items-center gap-1.5 px-3.5 py-2 min-h-[44px] rounded-md text-sm font-medium border whitespace-nowrap transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blue-500 focus-visible:ring-offset-1 ${
            copied
              ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
              : 'bg-white text-gray-700 border-gray-200 hover:bg-gray-50'
          }`}
        >
          {copied ? (
            <>
              <Check size={14} aria-hidden="true" /> Copié
            </>
          ) : (
            <>
              <Copy size={14} aria-hidden="true" /> Copier le brief
            </>
          )}
        </button>
      </div>

      {/* Brief content + mode switcher */}
      {expanded && (
        <div id="brief-codex-content" className="px-4 pb-4 space-y-2">
          {/* Mode switcher : Bullets DAF (chiffres bruts) vs Narratif COMEX. */}
          <div
            className="inline-flex p-0.5 rounded-md bg-gray-100 border border-gray-200"
            role="tablist"
            aria-label="Format du brief"
          >
            {Object.entries(MODES).map(([key, { label, Icon }]) => {
              const active = mode === key;
              return (
                <button
                  key={key}
                  type="button"
                  role="tab"
                  aria-selected={active}
                  onClick={() => handleModeChange(key)}
                  className={`inline-flex items-center gap-1.5 px-3 py-1.5 rounded text-xs font-medium transition-colors ${
                    active
                      ? 'bg-white text-gray-900 shadow-sm'
                      : 'text-gray-600 hover:text-gray-800'
                  }`}
                >
                  <Icon size={12} aria-hidden="true" />
                  {label}
                </button>
              );
            })}
          </div>

          <div className="bg-gray-50 border border-gray-100 rounded-md px-4 py-3 text-sm leading-relaxed text-gray-700">
            <SolNarrativeText text={briefText} />
          </div>
          <p className="text-[10.5px] text-gray-400 font-mono tracking-wide">
            Texte généré automatiquement — modifiable avant envoi
          </p>
        </div>
      )}
    </div>
  );
}
