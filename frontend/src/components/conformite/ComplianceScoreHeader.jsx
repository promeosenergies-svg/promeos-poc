/**
 * ComplianceScoreHeader — Unified compliance score display with breakdown bars.
 */
import { getComplianceScoreColor, COMPLIANCE_SCORE_THRESHOLDS } from '../../lib/constants';
import { CONFIDENCE_DATA_LABELS } from '../../domain/compliance/complianceLabels.fr';
import {
  DEFAULT_FRAMEWORKS_TOTAL,
  resolvePortfolioConfidence,
} from '../../domain/compliance/confidence';
import { Explain } from '../../ui';
import SolAcronym from '../../ui/sol/SolAcronym';

export default function ComplianceScoreHeader({ complianceScore, segProfile }) {
  if (!complianceScore) return null;

  return (
    <div
      data-section="compliance-score-header"
      className="p-4 bg-white border border-gray-200 rounded-lg"
    >
      <div className="flex items-center gap-6">
        {/* Score display */}
        <div className="text-center min-w-[100px]">
          <p className="text-xs text-gray-500 mb-1">
            <Explain term="compliance_score">Score conformité</Explain>
          </p>
          <span
            className={`text-3xl font-bold ${getComplianceScoreColor(complianceScore.score ?? complianceScore.avg_score)}`}
          >
            {Math.round(complianceScore.score ?? complianceScore.avg_score ?? 0)}
          </span>
          <span className="text-lg text-gray-400">/100</span>
          <div className="relative group inline-block ml-1">
            <button className="text-gray-400 hover:text-gray-600" title="Comment c'est calculé">
              <svg
                xmlns="http://www.w3.org/2000/svg"
                width="14"
                height="14"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
              >
                <circle cx="12" cy="12" r="10" />
                <path d="M9.09 9a3 3 0 0 1 5.83 1c0 2-3 3-3 3" />
                <line x1="12" y1="17" x2="12.01" y2="17" />
              </svg>
            </button>
            <div className="hidden group-hover:block absolute z-50 left-0 top-6 w-72 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs text-gray-600">
              <div className="font-semibold text-gray-800 mb-1">Comment c'est calculé</div>
              <div className="space-y-1">
                <div>
                  <SolAcronym code="Décret Tertiaire" /> × 45% + <SolAcronym code="BACS" /> × 30% +{' '}
                  <SolAcronym code="APER" /> × 25%
                </div>
                <div>Pénalité : −5 pts par finding critique (max −20)</div>
                <div className="text-gray-400 mt-1">
                  Périmètre : sites du scope actif · Instantané
                </div>
                <div className="text-gray-400">
                  Confiance : données partielles si frameworks non évalués
                </div>
              </div>
            </div>
          </div>
          {segProfile?.has_profile && Object.keys(segProfile.answers || {}).length > 0 && (
            <>
              <p className="text-[10px] text-blue-600 font-medium mt-1" data-testid="profile-badge">
                Adapté à votre profil
              </p>
              <p className="text-[9px] text-gray-400 mt-0.5" data-testid="profile-explain">
                Certaines obligations et priorités sont ajustées selon votre profil déclaré ou
                détecté.
              </p>
            </>
          )}
        </div>
        {/* Breakdown bars */}
        <div className="flex-1 space-y-2">
          {(complianceScore.breakdown || []).map((fw) => {
            const fwLabel =
              fw.framework === 'tertiaire_operat'
                ? 'Décret Tertiaire'
                : fw.framework === 'bacs'
                  ? 'BACS'
                  : 'APER';
            const weightPct = fw.weight != null ? `${Math.round(fw.weight * 100)}%` : '';
            const isAvailable = fw.available !== false && fw.source !== 'default';
            return (
              <div key={fw.framework} className="flex items-center gap-2">
                <span className="text-xs text-gray-500 w-36 truncate">
                  {fwLabel}
                  {weightPct && isAvailable ? ` (${weightPct})` : ''}
                </span>
                {isAvailable ? (
                  <>
                    <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${fw.score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : fw.score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                        style={{ width: `${Math.min(100, fw.score)}%` }}
                      />
                    </div>
                    <span
                      className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(fw.score)}`}
                    >
                      {Math.round(fw.score)}
                    </span>
                  </>
                ) : (
                  <span className="text-xs text-gray-400 italic">Non applicable</span>
                )}
              </div>
            );
          })}
          {/* Fallback: show breakdown_avg from portfolio if no breakdown */}
          {!complianceScore.breakdown &&
            complianceScore.breakdown_avg &&
            Object.entries(complianceScore.breakdown_avg).map(([fw, score]) => {
              const fwLabel =
                fw === 'tertiaire_operat' ? 'Décret Tertiaire' : fw === 'bacs' ? 'BACS' : 'APER';
              return (
                <div key={fw} className="flex items-center gap-2">
                  <span className="text-xs text-gray-500 w-36 truncate">{fwLabel}</span>
                  <div className="flex-1 h-2 bg-gray-100 rounded-full overflow-hidden">
                    <div
                      className={`h-full rounded-full ${score >= COMPLIANCE_SCORE_THRESHOLDS.ok ? 'bg-green-500' : score >= COMPLIANCE_SCORE_THRESHOLDS.warn ? 'bg-amber-500' : 'bg-red-500'}`}
                      style={{ width: `${Math.min(100, score)}%` }}
                    />
                  </div>
                  <span
                    className={`text-xs font-semibold w-10 text-right ${getComplianceScoreColor(score)}`}
                  >
                    {Math.round(score)}
                  </span>
                </div>
              );
            })}
        </div>
        <ConfidenceBadge complianceScore={complianceScore} />
      </div>
    </div>
  );
}

const CONFIDENCE_PILL_CLASSES = {
  high: 'bg-green-100 text-green-700',
  medium: 'bg-amber-100 text-amber-700',
  low: 'bg-red-100 text-red-700',
};

function ConfidenceBadge({ complianceScore }) {
  const level = complianceScore.confidence || resolvePortfolioConfidence(complianceScore);
  if (!level) return null;

  const evaluated = complianceScore.frameworks_evaluated;
  const total = complianceScore.frameworks_total ?? DEFAULT_FRAMEWORKS_TOTAL;
  const portfolioHigh = complianceScore.high_confidence_count;
  const portfolioTotal = complianceScore.total_sites;
  const hasPortfolioCounts = portfolioHigh != null && portfolioTotal != null;

  return (
    <div className="relative group inline-block text-center">
      <p className="text-xs text-gray-500 mb-1">Confiance</p>
      <span
        data-testid="compliance-confidence-badge"
        data-confidence-level={level}
        className={`text-xs font-medium px-2 py-0.5 rounded-full cursor-help ${CONFIDENCE_PILL_CLASSES[level]}`}
      >
        {CONFIDENCE_DATA_LABELS[level]}
      </span>
      <div className="hidden group-hover:block absolute z-50 right-0 top-6 w-64 bg-white border border-gray-200 rounded-lg shadow-lg p-3 text-xs text-gray-600 text-left">
        <div className="font-semibold text-gray-800 mb-1">Niveau de confiance</div>
        {hasPortfolioCounts ? (
          <div>
            {portfolioHigh}/{portfolioTotal} sites avec données fiables
          </div>
        ) : (
          <div>
            {evaluated}/{total} frameworks évalués
            {evaluated < total && (
              <div className="text-gray-400 mt-1">
                Frameworks manquants : score basé sur fallback (50 pts par défaut)
              </div>
            )}
          </div>
        )}
        <div className="text-gray-400 mt-1">
          High = {DEFAULT_FRAMEWORKS_TOTAL}/{DEFAULT_FRAMEWORKS_TOTAL} · Medium = 2/
          {DEFAULT_FRAMEWORKS_TOTAL} · Low = 0-1/{DEFAULT_FRAMEWORKS_TOTAL}
        </div>
      </div>
    </div>
  );
}
